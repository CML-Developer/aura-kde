# aura-kde

**KDE Plasma adapter for [Aura](https://antwny.github.io/aura/) — Wallpaper Engine on both screens.**

This is an Arch Linux–focused patch and bridge for Aura that adds KDE Plasma 6 + Wallpaper Engine support: it applies Workshop wallpapers to **both monitors simultaneously** with automatic plugin switching between the Wallpaper Engine backend ([catsout](https://github.com/catsout/wallpaper-engine-kde-plugin)) and the native image backend.

> **This project is a modification of [Aura](https://github.com/antwny/aura) by [antwny](https://github.com/antwny), licensed under GPL-3.0.**  
> It is not affiliated with or endorsed by Valve, Steam, or Wallpaper Engine.  
> "Wallpaper Engine" is a trademark of Kristjan Skutta / Wallpaper Engine Ltd.

---

## What it adds to Aura

| Feature | Notes |
|---|---|
| Workshop library in Aura's UI | Reads Steam libraries; respects Guardian blacklist if present |
| Both screens updated at once | Per-screen backup; full rollback on failure |
| Videos (Workshop, MotionBGS) | Activates **catsout** automatically |
| Images (Wallhaven, Bing, Minimalistic) | Activates **org.kde.image** automatically |
| Restore previous wallpaper | One click in the bar; restores plugin + config |
| Guardian integration (optional) | Reads `~/.config/wallpaper-engine-safe/blacklist.txt` to hide blocked wallpapers |

---

## Requirements

- Arch Linux (or derivative: CachyOS, EndeavourOS, Manjaro…)
- KDE Plasma 6, Wayland session
- [catsout](https://github.com/catsout/wallpaper-engine-kde-plugin) installed and active on both monitors
- Python 3.10+, Node.js
- Rust + Cargo (to compile Aura)
- `ffprobe` — video validation (optional; from the `ffmpeg` package)
- `python-pillow` — image validation (optional)

---

## Installation

### 1. Clone this repo

```bash
git clone https://github.com/YOUR_USER/aura-kde.git
```

### 2. Clone Aura and apply the patch

```bash
git clone https://github.com/antwny/aura.git
cd aura
git apply ../aura-kde/patches/aura-kde.patch
```

Check the patch base before applying:

```bash
git log --oneline -1
# should show: c41ac5e docs(website): update version pill to v1.6.1
```

### 3. Fetch Cargo dependencies (one-time, needs internet)

```bash
cargo fetch --locked
```

### 4. Compile

```bash
cargo build --features kde --locked --release --target-dir target-kde
```

First build takes 5–15 minutes. Subsequent builds are incremental.

### 5. Install

```bash
cd ../aura-kde
python3 scripts/install.py
# or specify the binary explicitly:
# python3 scripts/install.py --binary ../aura/target-kde/release/aura
```

Installs to `~/.local` — no root required, no autostart.  
The Aura icon is also installed automatically.

### 6. Run

```bash
aura-kde-lab
```

Or launch **Aura KDE Lab** from your application menu (the Aura icon should appear).

---

## Updating

```bash
cd aura-kde
python3 scripts/install.py
```

If the patch changed, rebuild Aura first:

```bash
cd aura
git apply ../aura-kde/patches/aura-kde.patch
cargo build --features kde --locked --release --target-dir target-kde
cd ../aura-kde
python3 scripts/install.py
```

---

## Uninstalling

```bash
python3 scripts/install.py --uninstall
```

Settings and operation records in `~/.local/state/aura-kde-lab/` are preserved.

---

## Optional: Wallpaper Guardian

**Wallpaper Guardian** is a separate community tool that monitors running wallpapers and automatically stops ones that crash or destabilize Plasma. It maintains a blacklist at `~/.config/wallpaper-engine-safe/blacklist.txt`.

`aura-kde` integrates with Guardian **automatically if it is installed**: wallpapers listed in the blacklist are hidden from the library and the selector without any extra configuration. The blacklist is read on every catalog load and is **never written** by this adapter.

Guardian is entirely optional. If it is not installed, the library shows all wallpapers.

> ⚠️ Guardian is not part of this project. Install, configure, and manage it separately.  
> This adapter is read-only with respect to Guardian's files.

---

## How it works

```
aura-kde-lab (binary, --features kde)
    ↓ ApplyWallpaper message
src/engine/kde.rs → python3 tools/aura_kde_bridge.py select PROJECT
    ↓
aura_kde_bridge.py
    ├── aura_kde_catalog.py   — Workshop items + Guardian blacklist filter
    ├── aura_kde_store.py     — Downloaded Store items (video/image)
    └── aura_kde_v2.py        — prepare record → run transaction
            ↓
        plasma_snapshot_v2.js   — read current state from Plasma
        plasma_transaction_v2.js — write both screens, verify, rollback on failure
```

### Key design decisions

- **No mpvpaper**: the KDE build excludes the original process-based engine entirely. Plasma owns playback via catsout.
- **Two-phase apply**: source is blanked first (forces backend reload), then set to the new value. Avoids the `$HOME` literal bug in KConfig.
- **ConfigFile not used**: `evaluateScript` only exposes `readConfig`/`writeConfig`. `ConfigFile()` is unavailable there. An empty-string write (`writeConfig(key, '')`) removes the entry.
- **Plugin switching**: `d.wallpaperPlugin = ...` defers activation until script cleanup. A separate snapshot confirms the change landed before returning.
- **Guardian integration**: blacklist is read on every catalog load, never written.

---

## Running tests

```bash
cd aura-kde
python3 -m unittest discover -s tests -v
```

35 tests cover: catalog filtering, Guardian blacklist, snapshot validation, v1 apply/restore, Store video/image validation, v2 plugin switching, conflict detection, and recovery from interrupted operations.

Node.js is required for the v2 tests (they run `plasma_v2_harness.js` to simulate the Plasma scripting environment).

---

## Repository layout

```
aura-kde/
├── assets/
│   └── io.github.antwny.aura.svg  — Aura's icon (from upstream, GPL-3.0)
├── patches/
│   └── aura-kde.patch       — diff against Aura v1.6.1 (c41ac5e)
├── src/
│   ├── engine/kde.rs         — KDE WallpaperEngine (stub + bridge caller)
│   └── kde_cli.rs            — KDE CLI entry (--kde-info marker)
├── tools/                    — Python bridge (installed to ~/.local/lib)
│   ├── aura_kde_bridge.py    — main entry: catalog / select / restore
│   ├── aura_kde_catalog.py   — Workshop catalog + Guardian filter
│   ├── aura_kde_store.py     — downloaded Store items
│   ├── aura_kde_apply.py     — v1 apply/restore/recover
│   ├── aura_kde_v2.py        — v2 plugin-aware apply/restore
│   ├── aura_kde_snapshot.py  — evaluateScript wrapper
│   ├── plasma_snapshot.js    — v1 Plasma state reader
│   ├── plasma_snapshot_v2.js — v2 reader (both plugin groups)
│   ├── plasma_transaction.js — v1 writer
│   └── plasma_transaction_v2.js — v2 writer (plugin switch + rollback)
├── tests/                    — unittest suite (35 tests)
├── scripts/
│   ├── install.py            — install / uninstall
│   └── dev-run.sh            — development launcher
└── README.md
```

---

## Limitations

- **Two monitors only**: the transaction validates exactly two active desktops. Single-monitor or 3+ setups are rejected cleanly.
- **Active session required**: `evaluateScript` needs a live Plasma session. No headless apply.
- **Playback confirmation**: the adapter verifies config values, not actual playback. Confirm visually after applying.
- **Web wallpapers** (Workshop type `web`): present in the library but playback is untested.
- **catsout required on both screens**: if one screen uses a different plugin at apply time, the operation fails.

---

## Patch base

The patch applies to Aura commit `c41ac5e` (v1.6.1):

```bash
cd aura
git log --oneline -1
# c41ac5e docs(website): update version pill to v1.6.1
```

---

## License

The files in `tools/`, `tests/` and `scripts/` are original work for this adapter.  
The files in `src/`, `patches/` and `assets/` modify or derive from [Aura](https://github.com/antwny/aura), which is [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html).  
These modifications are therefore also **GPL-3.0**.

> Aura is developed by [antwny](https://github.com/antwny) and contributors.  
> This adapter is an independent community project and is not affiliated with Aura's authors.
