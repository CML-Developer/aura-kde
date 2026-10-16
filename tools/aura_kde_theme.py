#!/usr/bin/env python3
"""KDE accent color auto-theming: extract palette from wallpaper, apply as KDE accent."""
import json
import subprocess
from pathlib import Path

STATE_DIR = Path.home() / '.local/state/aura-kde-lab'
DEFAULTS_FILE = STATE_DIR / 'theme_defaults.json'


def _read_current_accent():
    """Read current KDE accent color from kdeglobals; returns 'R,G,B' string or None."""
    try:
        result = subprocess.run(
            ['kreadconfig6', '--file', 'kdeglobals', '--group', 'General', '--key', 'accentColor'],
            capture_output=True, text=True, timeout=5
        )
        val = result.stdout.strip()
        return val if val else None
    except Exception:
        return None


def _write_accent(accent_csv):
    """Write accent color e.g. '61,174,233' to kdeglobals and notify KDE.
    Pass None to delete the key (revert to scheme default)."""
    try:
        if accent_csv is None:
            subprocess.run(
                ['kwriteconfig6', '--file', 'kdeglobals', '--group', 'General',
                 '--key', 'accentColor', '--delete'],
                capture_output=True, timeout=5
            )
        else:
            subprocess.run(
                ['kwriteconfig6', '--file', 'kdeglobals', '--group', 'General',
                 '--key', 'accentColor', accent_csv],
                capture_output=True, check=True, timeout=5
            )
        subprocess.run(
            ['qdbus6', 'org.kde.KWin', '/KWin', 'reconfigure'],
            capture_output=True, timeout=5
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
    Returns the applied 'R,G,B' string, or None if nothing was applied."""
    if not preview_path:
        return None
    palette = extract_palette(preview_path)
    if not palette:
        return None
    r, g, b, _ = palette
    accent = f'{r},{g},{b}'
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
