#!/usr/bin/env python3
"""Query live Plasma state without changing wallpapers or configuration."""
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


def evaluate(script):
    query = subprocess.run(['gdbus', 'introspect', '--session', '--dest',
                            'org.kde.plasmashell', '--object-path', '/PlasmaShell', '--xml'],
                           text=True, capture_output=True, timeout=15, check=True)
    tree = ET.fromstring(query.stdout)
    method = tree.find("./interface[@name='org.kde.PlasmaShell']/method[@name='evaluateScript']")
    if method is None:
        raise ValueError('Plasma does not expose evaluateScript')
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    response = subprocess.run(['qdbus6', 'org.kde.plasmashell', '/PlasmaShell',
                               'org.kde.PlasmaShell.evaluateScript', script],
                              env=env, text=True, capture_output=True, timeout=15, check=True)
    return json.loads(response.stdout)


def snapshot():
    data = evaluate(Path(__file__).with_name('plasma_snapshot.js').read_text())
    if not isinstance(data, dict) or data.get('schema') != 1 or not isinstance(data.get('targets'), list):
        raise ValueError('unexpected Plasma snapshot format')
    return data


if __name__ == '__main__':
    try:
        print(json.dumps(snapshot(), ensure_ascii=False, indent=2))
    except (OSError, ValueError, ET.ParseError, subprocess.SubprocessError) as exc:
        detail = getattr(exc, 'stderr', '') or str(exc)
        print(f'Unable to read Plasma: {detail.strip()}', file=sys.stderr)
        sys.exit(1)
