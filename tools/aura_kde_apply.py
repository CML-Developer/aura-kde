#!/usr/bin/env python3
"""Prepare private backup, apply to both screens, or restore an existing operation."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sys
import time
import copy
import uuid

from aura_kde_catalog import KEYS, live_plan, validate_snapshot
from aura_kde_snapshot import evaluate, snapshot


def restore_value(key, value):
    """Resolve KConfig HOME expressions before writing through writeConfig.

    writeConfig does not preserve the original [$e] expansion flag.
    Only expand the known HOME prefix, never arbitrary environment variables.
    """
    if key in ('SteamLibraryPath', 'WallpaperSource'):
        for prefix in ('file:$HOME/', 'file:${HOME}/'):
            if value.startswith(prefix):
                suffix = value[len(prefix):]
                kind = ''
                if key == 'WallpaperSource':
                    suffix, sep, kind = suffix.rpartition('+')
                    if not sep or kind not in ('scene', 'video', 'web'):
                        raise ValueError('Unsupported saved wallpaper source')
                result = (Path.home() / suffix).as_uri()
                return result + ('+' + kind if kind else '')
    return value


def transaction_script(record, restore=False):
    # Validate record shape with the same rules as live plans, without rereading media.
    before = record['before']
    validate_snapshot(before)
    if record.get('schema') != 1 or len(before['targets']) != 2:
        raise ValueError('Invalid operation record')
    if set(record['proposed']) != set(KEYS) or any(not isinstance(v, str) for v in record['proposed'].values()):
        raise ValueError('Invalid proposed values')
    for t in before['targets']:
        if any(t['values'][k]['present'] is not True or not isinstance(t['values'][k]['value'], str) for k in KEYS):
            raise ValueError('Cannot restore absent keys')
    restored = {str(t['containment']): {k: restore_value(k, t['values'][k]['value']) for k in KEYS} for t in before['targets']}
    payload = dict(before=before, proposed=record['proposed'], restore=restore, restored=restored)
    template = Path(__file__).with_name('plasma_transaction.js').read_text()
    return 'var REQUEST = ' + json.dumps(payload, ensure_ascii=True) + ';\n' + template


def prepare(library, wallpaper, quiet=False):
    before = snapshot()
    plan = live_plan(library, wallpaper, before)
    record = dict(schema=1, created=datetime.now(timezone.utc).isoformat(),
                  before=before, proposed=plan['proposed'], library=str(library.resolve()), wallpaper=wallpaper)
    return save_record(record, quiet)


def prepare_video(path):
    from aura_kde_store import video_plan
    before = snapshot()
    plan = video_plan(path, before)
    record = dict(schema=1, created=datetime.now(timezone.utc).isoformat(),
                  before=before, proposed=plan['proposed'], kind='store-video',
                  file=plan['item']['project'], fingerprint=plan['item']['fingerprint'])
    return save_record(record, True)


def save_record(record, quiet=False):
    folder = Path.home() / '.local/state/aura-kde-lab/operations'
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    if folder.is_symlink() or folder.stat().st_mode & 0o077:
        raise ValueError('Backup directory must be private (mode 700)')
    path = folder / (str(uuid.uuid4()) + '.json')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    if quiet:
        return path
    print(json.dumps(dict(record=str(path), targets=record['before']['targets'], proposed=record['proposed'],
                         next='apply --record PATH; restore --record PATH reverses this selection'), ensure_ascii=False, indent=2))


def run(path, restore, reload_scene=False):
    if json.loads(path.read_text()).get('schema') == 2:
        from aura_kde_v2 import run as run_v2
        return run_v2(path, restore)
    with path.open() as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record = json.load(stream)
        current = snapshot()
        validate_snapshot(current)
        if current['activity'] != record['before']['activity']:
            raise ValueError('Activity changed')
        for original in record['before']['targets']:
            target = next((t for t in current['targets'] if t['containment'] == original['containment']), None)
            if target is None or any(target[k] != original[k] for k in ('screen', 'geometry', 'plugin')):
                raise ValueError('Target changed')
            for key in KEYS:
                old = original['values'][key]['value']
                allowed = [old, restore_value(key, old)]
                if restore:
                    allowed.append(record['proposed'][key])
                    if key == 'WallpaperSource':
                        allowed.append('')  # incomplete two-phase operation
                if target['values'][key]['value'] not in allowed:
                    raise ValueError('Conflict: ' + key)
        if restore:
            desired = [{k: restore_value(k, t['values'][k]['value']) for k in KEYS} for t in record['before']['targets']]
            if desired[0] != desired[1]:
                raise ValueError('Restore currently requires identical previous wallpaper on both screens')
            selection = desired[0]
        else:
            if record.get('kind') == 'store-video':
                from aura_kde_store import video_plan
                checked = video_plan(Path(record['file']), record['before'])
                if checked['item']['fingerprint'] != record['fingerprint']:
                    raise ValueError('Downloaded video changed; prepare again')
            else:
                checked = live_plan(Path(record['library']), record['wallpaper'], record['before'])
            if checked['proposed'] != record['proposed']:
                raise ValueError('Wallpaper metadata changed; prepare again')
            selection = record['proposed']
        # Unload first, with final asset path already set, then recreate the backend.
        blank = dict(selection, WallpaperSource='')
        stage = dict(schema=1, before=current, proposed=blank)
        result = evaluate(transaction_script(stage))
        if not result.get('ok'):
            raise ValueError(json.dumps(result))
        time.sleep(0.6)
        expected_blank = copy.deepcopy(current)
        for target in expected_blank['targets']:
            target['values'] = {k: dict(present=True, value=v) for k, v in blank.items()}
        final = dict(schema=1, before=expected_blank, proposed=selection)
        result = evaluate(transaction_script(final))
        if not result.get('ok'):
            raise ValueError(json.dumps(result) + '; use restore with the original record')
        after = snapshot()
        if after['activity'] != record['before']['activity']:
            raise ValueError('Activity changed after operation; inspect before restoring')
        expected_targets = record['before']['targets']
        if len(after['targets']) != len(expected_targets):
            raise ValueError('Screen count changed after operation')
        for t in expected_targets:
            actual = next((a for a in after['targets'] if a['containment'] == t['containment']), None)
            if actual is None or any(actual[k] != t[k] for k in ('screen', 'plugin', 'geometry')):
                raise ValueError('Target changed after operation')
            for key in KEYS:
                expected = restore_value(key, t['values'][key]['value']) if restore else record['proposed'][key]
                if actual['values'][key] != dict(present=True, value=expected):
                    raise ValueError('Post-operation verification failed; use saved record for recovery')
        print(json.dumps(dict(ok=True, restored=restore, record=str(path), verified_targets=2, verification='configuration-only; confirm playback visually')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--library', type=Path, required=True)
    p.add_argument('--wallpaper', required=True)
    select = sub.add_parser('select')
    select.add_argument('--library', type=Path, required=True)
    select.add_argument('--wallpaper', required=True)
    for name in ('apply', 'restore', 'recover'):
        sub.add_parser(name).add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'select':
            path = prepare(args.library, args.wallpaper, quiet=True)
            print(json.dumps(dict(record=str(path))), flush=True)
            run(path, False)
        elif args.action == 'prepare':
            prepare(args.library, args.wallpaper)
        else:
            run(args.record, args.action in ('restore', 'recover'), args.action == 'recover')
    except Exception as exc:
        print(f'Operation stopped: {exc}\nAny saved record remains available; do not blindly retry a timed-out apply.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
