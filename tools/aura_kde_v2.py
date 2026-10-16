"""Reversible plugin switching for two Plasma desktops; v1 records remain separate."""
import copy
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import time

from aura_kde_catalog import PLUGIN, KEYS, catalog
from aura_kde_snapshot import evaluate
from aura_kde_apply import restore_value, save_record
import aura_kde_store as store

IMAGE = 'org.kde.image'
SPECS = {PLUGIN: KEYS, IMAGE: ('Image', 'PreviewImage')}


def validate(state):
    if state.get('schema') != 2 or not isinstance(state.get('activity'), str) or not state['activity']:
        raise ValueError('Invalid v2 snapshot')
    targets = state.get('targets', [])
    if not (1 <= len(targets) <= 3):
        raise ValueError('Expected 1–3 active desktops')
    seen_ids, seen_screens = set(), set()
    for t in targets:
        if t.get('plugin') not in SPECS:
            raise ValueError('Only Image and Wallpaper Engine desktop types are supported')
        for key, seen in [('containment', seen_ids), ('screen', seen_screens)]:
            value = t.get(key)
            if type(value) is not int or value < 0 or value in seen:
                raise ValueError('Ambiguous desktop identity')
            seen.add(value)
        g = t.get('geometry', {})
        if any(type(g.get(k)) is not int for k in ('x','y','width','height')) or g['width'] <= 0 or g['height'] <= 0:
            raise ValueError('Invalid geometry')
        if set(t.get('groups', {})) != set(SPECS):
            raise ValueError('Invalid wallpaper groups')
        for plugin, keys in SPECS.items():
            values = t['groups'][plugin]
            if set(values) != set(keys):
                raise ValueError('Invalid wallpaper keys')
            for value in values.values():
                if type(value.get('present')) is not bool or (value['present'] and not isinstance(value.get('value'), str)) or (not value['present'] and value.get('value') is not None):
                    raise ValueError('Invalid wallpaper value')


def snapshot():
    data = evaluate(Path(__file__).with_name('plasma_snapshot_v2.js').read_text())
    validate(data)
    data['targets'].sort(key=lambda t: t['containment'])
    return data


def normalized(state):
    result = copy.deepcopy(state)
    for t in result['targets']:
        for plugin, values in t['groups'].items():
            for key, value in values.items():
                if value['present']:
                    # Image is an ordinary URI, without catsout's +type suffix.
                    value['value'] = restore_value('SteamLibraryPath' if key in ('Image','PreviewImage') else key, value['value'])
    return result


def resolve_item(selection):
    if selection.get('provider') == 'aura-store':
        return store.inspect_media(Path(selection['project']), probe=True)
    matches = [i for i in catalog(Path(selection['library'])) if i['id'] == selection['id']]
    if len(matches) != 1 or matches[0].get('project') != selection['project']:
        raise ValueError('Workshop wallpaper unavailable or blacklisted')
    return dict(matches[0], library=selection['library'])


def desired_state(before, item):
    after = copy.deepcopy(before)
    for t in after['targets']:
        if item['type'] == 'image':
            t['plugin'] = IMAGE
            proposed = {'Image': Path(item['project']).as_uri(), 'PreviewImage': 'null'}
        else:
            t['plugin'] = PLUGIN
            prior = t['groups'][PLUGIN]['SteamLibraryPath']
            library = (Path(item['library']).resolve().as_uri() if 'library' in item else
                       restore_value('SteamLibraryPath', prior['value']) if prior['present'] else '')
            proposed = dict(SteamLibraryPath=library, WallpaperWorkShopId=item['id'], WallpaperSource=item['source'])
        t['groups'][t['plugin']] = {k:dict(present=True,value=v) for k,v in proposed.items()}
    return after


def blank_state(state):
    result = copy.deepcopy(state)
    for t in result['targets']:
        if t['plugin'] == PLUGIN:
            t['groups'][PLUGIN]['WallpaperSource'] = dict(present=False,value=None)
        else:
            # Image's QML initializes this key when its component is created.
            t['groups'][IMAGE]['PreviewImage'] = dict(present=True,value='null')
    return result


def prepare(selection):
    item = resolve_item(selection)
    before = snapshot()
    after = desired_state(before, item)
    record = dict(schema=2, created=datetime.now(timezone.utc).isoformat(), before=before, after=after,
                  selection=selection, fingerprint=item.get('fingerprint'))
    return save_record(record, True)


def script(before, after):
    validate(before); validate(after)
    if before['activity'] != after['activity'] or len(before['targets']) != len(after['targets']):
        raise ValueError('Mismatched transaction targets')
    for a,b in zip(before['targets'],after['targets']):
        if any(a[k] != b[k] for k in ('containment','screen','geometry')):
            raise ValueError('Mismatched transaction identity')
    return 'var REQUEST = ' + json.dumps(dict(before=before,after=after,recovery=normalized(before)),ensure_ascii=True) + ';\n' + Path(__file__).with_name('plasma_transaction_v2.js').read_text()


def transition(before, after):
    if before == after:
        return
    response = evaluate(script(before, after))
    if not response.get('ok'):
        raise ValueError(json.dumps(response))
    # A value read inside the setter script is not proof of activation.
    for _ in range(12):
        time.sleep(0.25)
        actual = snapshot()
        if actual == after:
            return
    raise ValueError('Plugin/configuration did not reach the expected state; backup retained')


def known_state(actual, states):
    validate(actual)
    if any(s['activity'] != actual['activity'] for s in states):
        return False
    # Allow different completed phases per screen, but not arbitrary mixtures of keys.
    normalized_states = [normalized(s) for s in states]
    return all(any(t == candidate for s in normalized_states for candidate in s['targets'])
               for t in normalized(actual)['targets'])


def run(path, restore=False):
    with path.open() as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record = json.load(stream)
        if record.get('schema') != 2:
            raise ValueError('Expected a v2 record')
        before, after = record['before'], record['after']
        validate(before); validate(after)
        original = normalized(before)
        states = [before, original, blank_state(after), after, blank_state(original)]
        current = snapshot()
        if restore:
            if not known_state(current, states):
                raise ValueError('Desktop changed outside Aura; refusing to overwrite it')
            desired = original
        else:
            if current != before:
                raise ValueError('Desktop changed after backup')
            item = resolve_item(record['selection'])
            if item.get('fingerprint') != record.get('fingerprint') or desired_state(before,item) != after:
                raise ValueError('Wallpaper changed after backup')
            desired = after
        # Only use blank phase if plugin changes (avoids black screen flash on same-plugin transitions)
        needs_blank = any(t1['plugin'] != t2['plugin'] for t1, t2 in zip(current['targets'], desired['targets']))
        try:
            if needs_blank:
                stage = blank_state(desired)
                transition(current, stage)
                transition(stage, desired)
            else:
                transition(current, desired)
        except Exception as error:
            # Only roll back recognized operation states; preserve any external change.
            try:
                actual = snapshot()
                if not known_state(actual, states):
                    raise ValueError('Rollback conflict: external change preserved')
                needs_blank_rollback = any(t1['plugin'] != t2['plugin'] for t1, t2 in zip(actual['targets'], original['targets']))
                if needs_blank_rollback:
                    recovery = blank_state(original)
                    transition(actual, recovery)
                    transition(recovery, original)
                else:
                    transition(actual, original)
            except Exception as rollback:
                raise ValueError(f'{error}; recovery incomplete: {rollback}; record: {path}') from error
            raise ValueError(f'{error}; previous configuration restored; record: {path}') from error
        print(json.dumps(dict(ok=True, restored=restore,record=str(path),verified_targets=len(before['targets']),
                              verification='configuration-only; confirm playback visually')))
