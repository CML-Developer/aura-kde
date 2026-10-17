#!/usr/bin/env python3
"""Install/remove only owned Aura KDE files; settings and recovery records are preserved."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

MANIFEST = Path('share/aura-kde-lab/install.json')

CANDIDATE_BINARIES = [
    ROOT.parent / 'aura' / 'target-kde' / 'release' / 'aura',
    ROOT.parent / 'aura' / 'target' / 'release' / 'aura',
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def find_binary(hint=None):
    candidates = ([Path(hint).resolve()] if hint else []) + CANDIDATE_BINARIES
    for path in candidates:
        if path.is_file():
            return path
    paths = '\n  '.join(str(p) for p in candidates)
    print(f'Binary not found. Searched:\n  {paths}', file=sys.stderr)
    print('Pass --binary /path/to/aura to specify it explicitly.', file=sys.stderr)
    sys.exit(1)


def package(prefix, binary_path):
    check = subprocess.run([str(binary_path), '--kde-info'], capture_output=True, text=True, check=True)
    if check.stdout.strip() != 'aura-kde-lab: KDE adapter, both screens':
        print('Binary is not the KDE build. Compile with --features kde.', file=sys.stderr)
        sys.exit(1)
    files = {'lib/aura-kde-lab/aura': (binary_path.read_bytes(), 0o755)}
    tool_names = [
        'aura_kde_v2.py', 'plasma_snapshot_v2.js', 'plasma_transaction_v2.js',
        'aura_kde_store.py', 'aura_kde_bridge.py', 'aura_kde_apply.py',
        'aura_kde_catalog.py', 'aura_kde_snapshot.py', 'aura_kde_theme.py',
        'plasma_snapshot.js', 'plasma_transaction.js', 'aura_kde_force_restore.py',
    ]
    for name in tool_names:
        files['lib/aura-kde-lab/tools/' + name] = ((ROOT / 'tools' / name).read_bytes(), 0o644)
    # Autostart files for wallpaper restoration on login
    autostart_script = (ROOT / 'autostart' / 'aura-kde-restore-on-login').read_bytes()
    autostart_desktop = (ROOT / 'autostart' / 'aura-kde-restore.desktop').read_bytes()
    files['bin/aura-kde-restore-on-login'] = (autostart_script, 0o755)
    files['../../../.config/autostart/aura-kde-restore.desktop'] = (autostart_desktop, 0o644)
    icon_path = ROOT / 'assets' / 'io.github.antwny.aura.svg'
    if icon_path.exists():
        icon_data = icon_path.read_bytes()
        # Install under both names: the upstream icon name and the KDE build app_id.
        # KDE Wayland uses the app_id ("local.aura.kde.lab") for taskbar icon lookup.
        files['share/icons/hicolor/scalable/apps/io.github.antwny.aura.svg'] = (icon_data, 0o644)
        files['share/icons/hicolor/scalable/apps/local.aura.kde.lab.svg'] = (icon_data, 0o644)
    launcher = '''#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import sys
base = Path(__file__).resolve().parents[1] / 'lib/aura-kde-lab'
os.environ['AURA_KDE_BRIDGE'] = str(base / 'tools/aura_kde_bridge.py')
# theme-* commands go directly to the bridge (not handled by the Rust binary)
if len(sys.argv) > 1 and sys.argv[1].startswith('theme-'):
    r = subprocess.run([sys.executable, str(base / 'tools/aura_kde_bridge.py'), *sys.argv[1:]])
    sys.exit(r.returncode)
os.execv(str(base / 'aura'), [str(base / 'aura'), *sys.argv[1:]])
'''
    files['bin/aura-kde-lab'] = (launcher.encode(), 0o755)
    command = str(prefix / 'bin/aura-kde-lab').replace('\\', '\\\\').replace('"', '\\"')
    desktop = f'''[Desktop Entry]
Type=Application
Name=Aura KDE Lab
Comment=Workshop wallpapers on both screens
Exec="{command}"
Icon=local.aura.kde.lab
StartupWMClass=local.aura.kde.lab
Terminal=false
Categories=Utility;
'''
    files['share/applications/aura-kde-lab.desktop'] = (desktop.encode(), 0o644)
    restore_desktop = f'''[Desktop Entry]
Type=Application
Name=Restaurar estilos Aura
Comment=Restore your saved default KDE accent color
Exec="{command}" theme-restore
Icon=local.aura.kde.lab
Terminal=false
Categories=Utility;
NoDisplay=false
'''
    files['share/applications/aura-kde-theme-restore.desktop'] = (restore_desktop.encode(), 0o644)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, default=Path.home() / '.local')
    parser.add_argument('--binary', help='Path to the compiled aura binary (--features kde)')
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    prefix = args.prefix.resolve()
    manifest = prefix / MANIFEST
    old = json.loads(manifest.read_text()) if manifest.exists() else {}
    if args.uninstall and not old:
        print('No installation manifest; nothing removed.')
        return
    if args.uninstall:
        files = {}
    else:
        binary = find_binary(args.binary)
        files = package(prefix, binary)
    for rel, expected in old.items():
        path = prefix / rel
        if not path.resolve().is_relative_to(prefix) or path.is_symlink():
            raise ValueError(f'Unsafe manifest path: {path}')
        if path.exists() and digest(path.read_bytes()) != expected:
            raise ValueError(f'Preserving modified installed file: {path}')
    for rel in files:
        path = prefix / rel
        if not path.resolve().is_relative_to(prefix) or path.is_symlink():
            raise ValueError(f'Unsafe destination: {path}')
        if path.exists() and rel not in old:
            raise ValueError(f'Refusing to overwrite unowned file: {path}')
    verb = 'Remove' if args.uninstall else 'Install'
    targets = old if args.uninstall else files
    print(verb + ':\n' + '\n'.join(str(prefix / r) for r in targets))
    if args.dry_run:
        return
    if args.uninstall:
        for rel in old:
            (prefix / rel).unlink(missing_ok=True)
        manifest.unlink()
        return
    for rel, (data, mode) in files.items():
        target = prefix / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(mode)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({rel: digest(data) for rel, (data, _) in files.items()}, indent=2))
    print('Installed. No autostart enabled.')
    print(f'Run: {prefix}/bin/aura-kde-lab')


if __name__ == '__main__':
    main()
