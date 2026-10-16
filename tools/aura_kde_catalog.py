#!/usr/bin/env python3
"""Read-only Workshop catalog and persisted-state preview; never applies changes."""
import argparse
import configparser
import json
from pathlib import Path
import re
import sys

PLUGIN = 'com.github.catsout.wallpaperEngineKde'
KEYS = ('SteamLibraryPath', 'WallpaperWorkShopId', 'WallpaperSource')


def child_path(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError('expected nonempty relative resource path')
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('resource escapes wallpaper directory')
    return path


def inspect_project(project):
    data = json.loads(project.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('project.json must be an object')
    kind = data.get('type', '')
    kind = kind.lower() if isinstance(kind, str) else ''
    item = dict(id=project.parent.name, title=data.get('title', project.parent.name),
                type=kind or 'unknown', project=str(project), usable=False)
    if kind not in ('video', 'scene', 'web'):
        item['reason'] = 'unsupported or missing type'
        return item
    resource = child_path(project.parent, data.get('file'))
    # Scenes may contain the declared scene.json inside scene.pkg.
    packed = kind == 'scene' and child_path(project.parent, 'scene.pkg').is_file()
    item['usable'] = resource.is_file() or packed
    PROBLEMATIC_IDS = {'2888802755', '3011666990'}  # Shadow Garden y otros que crashean
    if item['id'] in PROBLEMATIC_IDS:
        item['usable'] = False
        item['reason'] = 'known to crash on Linux'
    item['source'] = resource.as_uri() + '+' + kind
    # Buscar archivo preview
    preview_candidates = [
        project.parent / 'preview.jpg',
        project.parent / 'preview.gif',
        project.parent / 'preview.png'
    ]
    for preview in preview_candidates:
        if preview.is_file():
            item['preview'] = str(preview)
            break
    item['validation'] = 'files-only; playback untested'
    if not item['usable']:
        item.setdefault('reason', 'declared resource missing')
    return item


def guardian_blacklist():
    """Read Guardian's IDs without creating or modifying its files."""
    path = Path.home() / '.config/wallpaper-engine-safe/blacklist.txt'
    try:
        content = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return set()
    return {line.strip() for line in content.splitlines()
            if re.fullmatch(r'[0-9]+', line.strip())}


def catalog(library):
    root = library.resolve() / 'steamapps/workshop/content/431960'
    if not root.is_dir():
        raise ValueError(f'Workshop directory missing: {root}')
    blocked = guardian_blacklist()
    result = []
    for project in sorted(root.glob('*/project.json')):
        if not project.parent.name.isdecimal() or project.parent.name in blocked:
            continue
        try:
            if not project.resolve().is_relative_to(root.resolve()):
                raise ValueError('project escapes Workshop directory')
            result.append(inspect_project(project))
        except (ValueError, OSError) as exc:
            result.append(dict(id=project.parent.name, usable=False, reason=str(exc)))
    return [item for item in result if item.get('usable', False)]


def persisted_targets(path, activity):
    cfg = configparser.RawConfigParser(strict=True)
    cfg.optionxform = str
    with path.open(encoding='utf-8') as stream:
        cfg.read_file(stream)
    targets = []
    for section in cfg.sections():
        match = re.fullmatch(r'Containments\]\[(\d+)', section)
        if not match or cfg.get(section, 'activityId', fallback='') != activity:
            continue
        if cfg.get(section, 'plugin', fallback='') not in ('org.kde.desktopcontainment', 'org.kde.plasma.folder'):
            continue
        screen = cfg.getint(section, 'lastScreen', fallback=-1)
        if screen < 0:
            continue
        plugin = cfg.get(section, 'wallpaperplugin', fallback='')
        if plugin != PLUGIN:
            raise ValueError('target is not using the audited plugin')
        group = section + '][Wallpaper][' + PLUGIN + '][General'
        before = {}
        for key in KEYS:
            values = {k: v for k, v in cfg.items(group) if k in (key, key + '[$e]')} if cfg.has_section(group) else {}
            before[key] = dict(present=bool(values), raw_entries=values)
        targets.append(dict(containment=int(match[1]), saved_screen=screen,
                            activity=activity, plugin=plugin, before=before))
    if len(targets) != 2 or len({t['saved_screen'] for t in targets}) != 2:
        raise ValueError('expected exactly two distinct saved desktop screens for this activity')
    return sorted(targets, key=lambda t: t['saved_screen'])


def plan(library, wallpaper_id, config, activity):
    matches = [i for i in catalog(library) if i['id'] == wallpaper_id]
    if len(matches) != 1 or not matches[0]['usable']:
        raise ValueError('selected wallpaper is unavailable or unsupported')
    item = matches[0]
    selection = dict(SteamLibraryPath=library.resolve().as_uri(),
                     WallpaperWorkShopId=wallpaper_id, WallpaperSource=item['source'])
    return dict(mode='preview-only', can_apply=False,
                limitation='Persisted state only. Live targets, backup and restore API not verified.',
                wallpaper=item, targets=persisted_targets(config, activity), proposed=selection)


def validate_snapshot(snapshot):
    """Require two unambiguous targets with restorable existing values."""
    if not isinstance(snapshot, dict):
        raise ValueError('snapshot must be an object')
    if snapshot.get('schema') != 1 or not isinstance(snapshot.get('activity'), str) or not snapshot['activity']:
        raise ValueError('invalid live snapshot activity/schema')
    targets = snapshot.get('targets', [])
    if not isinstance(targets, list) or len(targets) != 2:
        raise ValueError('expected exactly two active desktop targets')
    seen_screens, seen_ids, seen_geometry = set(), set(), set()
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError('target must be an object')
        screen, ident = target.get('screen'), target.get('containment')
        if type(screen) is not int or screen < 0 or type(ident) is not int or ident < 0:
            raise ValueError('invalid target identity')
        if screen in seen_screens or ident in seen_ids or target.get('plugin') != PLUGIN:
            raise ValueError('ambiguous target or unexpected plugin')
        geo = target.get('geometry', {})
        if not isinstance(geo, dict) or not isinstance(target.get('values'), dict):
            raise ValueError('invalid geometry or values')
        rect = tuple(geo.get(k) for k in ('x', 'y', 'width', 'height'))
        if any(type(v) is not int for v in rect) or rect[2] <= 0 or rect[3] <= 0 or rect in seen_geometry:
            raise ValueError('invalid or ambiguous screen geometry')
        for key in KEYS:
            value = target.get('values', {}).get(key, {})
            if not isinstance(value, dict) or value.get('present') is not True or not isinstance(value.get('value'), str):
                raise ValueError('initial operation requires all three keys already present for exact restore')
        seen_screens.add(screen)
        seen_ids.add(ident)
        seen_geometry.add(rect)


def live_plan(library, wallpaper_id, snapshot):
    """Validate a captured live snapshot; never treat it as authorization."""
    validate_snapshot(snapshot)
    targets = snapshot['targets']
    items = [i for i in catalog(library) if i['id'] == wallpaper_id and i['usable']]
    if len(items) != 1:
        raise ValueError('selected wallpaper unavailable')
    proposed = dict(SteamLibraryPath=library.resolve().as_uri(),
                    WallpaperWorkShopId=wallpaper_id, WallpaperSource=items[0]['source'])
    return dict(mode='live-snapshot-preview', can_apply=False, activity=snapshot['activity'],
                targets=targets, proposed=proposed,
                limitation='Must re-read and compare live state and save private backup before applying.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', required=True, type=Path)
    parser.add_argument('--plan', metavar='WORKSHOP_ID')
    parser.add_argument('--activity')
    parser.add_argument('--snapshot', type=Path, help='JSON from aura_kde_snapshot.py; preview only')
    parser.add_argument('--config', type=Path, default=Path.home() / '.config/plasma-org.kde.plasma.desktop-appletsrc')
    args = parser.parse_args()
    if args.plan and not args.activity and not args.snapshot:
        parser.error('--plan requires --activity or --snapshot')
    if args.snapshot and not args.plan:
        parser.error('--snapshot requires --plan')
    try:
        if args.snapshot:
            output = live_plan(args.library, args.plan, json.loads(args.snapshot.read_text()))
        else:
            output = plan(args.library, args.plan, args.config, args.activity) if args.plan else catalog(args.library)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except (ValueError, OSError, configparser.Error) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
