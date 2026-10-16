#!/usr/bin/env python3
"""KDE accent color auto-theming: extract palette from wallpaper, apply as KDE accent."""
import json
import subprocess
from pathlib import Path

STATE_DIR = Path.home() / '.local/state/aura-kde-lab'
DEFAULTS_FILE = STATE_DIR / 'theme_defaults.json'


def _rgb_to_hex(r, g, b):
    return f'#{r:02X}{g:02X}{b:02X}'


def _scheme_default_accent():
    """Read the DecorationFocus color from the active color scheme file.
    This is the scheme's built-in accent — used when no custom accent override is set."""
    try:
        scheme = subprocess.run(
            ['kreadconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', 'ColorScheme'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip() or 'BreezeDark'
        for d in (Path.home() / '.local/share/color-schemes',
                  Path('/usr/share/color-schemes'),
                  Path('/usr/local/share/color-schemes')):
            f = d / f'{scheme}.colors'
            if f.exists():
                import configparser
                cfg = configparser.RawConfigParser()
                cfg.read(str(f))
                val = cfg.get('Colors:Button', 'DecorationFocus', fallback=None)
                if val:
                    parts = val.split(',')
                    if len(parts) == 3:
                        return _rgb_to_hex(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        pass
    return None


def _read_current_accent():
    """Read current KDE accent color as '#RRGGBB' string.
    Returns the custom override if set, otherwise the scheme's built-in default."""
    try:
        result = subprocess.run(
            ['kreadconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', 'accentColor'],
            capture_output=True, text=True, timeout=5
        )
        val = result.stdout.strip()
        if val:
            parts = val.split(',')
            if len(parts) == 3:
                return _rgb_to_hex(int(parts[0]), int(parts[1]), int(parts[2]))
            if val.startswith('#'):
                return val
    except Exception:
        pass
    # No custom override — read from the scheme file so snapshot always has a real color
    return _scheme_default_accent()


def _write_accent(accent_hex):
    """Apply accent color via plasma-apply-colorscheme --accent-color.
    Pass None to resolve and apply the current scheme's built-in default."""
    if accent_hex is None:
        accent_hex = _scheme_default_accent()
    if accent_hex is None:
        return
    try:
        subprocess.run(
            ['plasma-apply-colorscheme', '--accent-color', accent_hex],
            capture_output=True, check=True, timeout=10
        )
    except Exception:
        pass


def extract_palette(image_path):
    """Extract dominant vibrant color and brightness.
    Returns (r, g, b, is_dark) with r/g/b as 0-255 ints, or None if Pillow unavailable."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        img = Image.open(image_path).convert('RGB').resize((100, 100), Image.NEAREST)
    except Exception:
        return None

    best_vibrancy = -1.0
    best_r, best_g, best_b = 255, 127, 0
    total_lum = 0.0
    count = img.width * img.height

    for pr8, pg8, pb8 in img.getdata():
        pr, pg, pb = pr8 / 255.0, pg8 / 255.0, pb8 / 255.0
        max_c = max(pr, pg, pb)
        min_c = min(pr, pg, pb)
        delta = max_c - min_c
        v = max_c
        s = (delta / max_c) if max_c > 0 else 0.0
        if 0.15 < v < 0.97:
            vibrancy = s * v
            if vibrancy > best_vibrancy:
                best_vibrancy = vibrancy
                best_r, best_g, best_b = pr8, pg8, pb8
        total_lum += 0.299 * pr8 + 0.587 * pg8 + 0.114 * pb8

    is_dark = (total_lum / count) < 128.0

    if best_vibrancy < 0.06:
        best_r, best_g, best_b = (114, 140, 165) if is_dark else (89, 114, 140)

    return best_r, best_g, best_b, is_dark


def snapshot_defaults():
    """Save current KDE accent color as the user's saved defaults.
    Call once before the first auto-apply so restore always works."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    defaults = {'accent': _read_current_accent()}
    DEFAULTS_FILE.write_text(json.dumps(defaults, indent=2))
    return defaults


def load_defaults():
    """Return saved defaults dict or None if not yet snapshotted."""
    if not DEFAULTS_FILE.exists():
        return None
    try:
        return json.loads(DEFAULTS_FILE.read_text())
    except Exception:
        return None


def ensure_defaults_snapshotted():
    """Snapshot defaults the first time auto-theming is used."""
    if not DEFAULTS_FILE.exists():
        snapshot_defaults()


def apply_from_wallpaper(preview_path):
    """Extract palette from preview and apply as KDE accent color.
    Returns the applied '#RRGGBB' hex string, or None if nothing was applied."""
    if not preview_path:
        return None
    palette = extract_palette(preview_path)
    if not palette:
        return None
    r, g, b, _ = palette
    accent = _rgb_to_hex(r, g, b)
    _write_accent(accent)
    return accent


def restore_defaults():
    """Restore the user's saved default KDE accent color.
    Returns True on success, False if no defaults have been saved yet."""
    defaults = load_defaults()
    if defaults is None:
        return False
    _write_accent(defaults.get('accent'))
    return True
