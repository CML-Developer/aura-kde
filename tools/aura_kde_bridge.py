#!/usr/bin/env python3
"""JSON bridge for the KDE build of Aura. No execution of Workshop content."""
import json
import os
from pathlib import Path
import re
import sys
from aura_kde_catalog import catalog, child_path
from aura_kde_apply import prepare, prepare_video, run
import aura_kde_store as store


def libraries():
    override = os.environ.get('AURA_KDE_LIBRARY')
    if override:
        return [Path(override).resolve()]
    home = Path.home()
    roots = [home / '.local/share/Steam', home / '.steam/steam', home / '.var/app/com.valvesoftware.Steam/data/Steam']
    found = set()
    for base in roots:
        if not base.exists():
            continue
        found.add(base.resolve())
        vdf = base / 'steamapps/libraryfolders.vdf'
        if vdf.exists():
            for raw in re.findall(r'"path"\s+"((?:\\.|[^"\\])*)"', vdf.read_text()):
                path = Path(raw.replace('\\\\', '\\').replace('\\"', '"'))
                if path.is_absolute():
                    found.add(path.resolve())
    return sorted(found)


def items():
    output = []
    for library in libraries():
        if not (library / 'steamapps/workshop/content/431960').is_dir():
            continue
        for item in catalog(library):
            item['library'] = str(library)
            if 'project' in item:
                item['modified'] = int(Path(item['project']).stat().st_mtime)
                data = json.loads(Path(item['project']).read_text(encoding='utf-8-sig'))
                preview = data.get('preview')
                if isinstance(preview, str) and preview:
                    try:
                        path = child_path(Path(item['project']).parent, preview)
                        if path.is_file(): item['preview'] = str(path)
                    except ValueError: pass
            output.append(item)
    return output + store.items()


def main():
    if sys.argv[1:] == ['catalog']:
        print(json.dumps(items(), ensure_ascii=False))
    elif len(sys.argv) == 3 and sys.argv[1] == 'select':
        project = Path(sys.argv[2]).resolve()
        matches = [item for item in items() if item.get('project') == str(project) and item['usable']]
        if len(matches) != 1: raise ValueError('Wallpaper not found in the available Aura catalog')
        item = matches[0]
        from aura_kde_v2 import prepare as prepare_v2
        path = prepare_v2(item)
        print(json.dumps({'record': str(path)}), flush=True)
        run(path, False)
    elif len(sys.argv) == 3 and sys.argv[1] == 'restore':
        run(Path(sys.argv[2]), True)
    else:
        raise ValueError('Expected catalog, select PROJECT_JSON or restore RECORD')


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
