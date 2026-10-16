# aura-kde

**[Español](#español) · [English](#english)**

---

<a name="español"></a>
## Español

**Adaptador KDE para [Aura](https://antwny.github.io/aura/) — Wallpaper Engine en todas las pantallas.**

Este proyecto es una modificación de [Aura](https://github.com/antwny/aura) de [antwny](https://github.com/antwny), orientada a Arch Linux con soporte completo para KDE Plasma 6 + Wallpaper Engine: aplica fondos del Workshop en **1, 2 o 3 monitores simultáneamente** con cambio automático de plugin entre el backend de Wallpaper Engine ([catsout](https://github.com/catsout/wallpaper-engine-kde-plugin)) y el backend nativo de imágenes.

> **Este proyecto es una modificación de [Aura](https://github.com/antwny/aura) de [antwny](https://github.com/antwny), licenciada bajo GPL-3.0.**
> No está afiliado ni respaldado por Valve, Steam ni Wallpaper Engine.
> "Wallpaper Engine" es marca registrada de Kristjan Skutta / Wallpaper Engine Ltd.

---

### Qué agrega a Aura

| Función | Notas |
|---|---|
| Biblioteca Workshop en la UI de Aura | Lee las bibliotecas de Steam; respeta la lista negra de Guardian si está instalado |
| 1, 2 o 3 pantallas actualizadas a la vez | Respaldo por pantalla; rollback completo si falla |
| Vídeos (Workshop, MotionBGS) | Activa **catsout** automáticamente |
| Imágenes (Wallhaven, Bing, Minimalistas) | Activa **org.kde.image** automáticamente |
| Restaurar fondo anterior | Un clic en la barra; restaura plugin + configuración |
| **Auto-theming** | Toggle en ajustes; extrae el color dominante del fondo y lo aplica como accent color de KDE |
| **Restaurar colores originales** | Botón en ajustes o comando; restaura el acento guardado antes del auto-tema |
| Integración con Guardian (opcional) | Lee `~/.config/wallpaper-engine-safe/blacklist.txt` para ocultar fondos bloqueados |

> **Nota:** Los fondos de Wallpaper Engine se descargan desde el [Workshop oficial de Steam](https://steamcommunity.com/app/431960/workshop/). Aura lee los fondos ya instalados en tus bibliotecas de Steam. Para agregar nuevos fondos, suscríbete a ellos en Steam Workshop y se sincronizarán automáticamente.

---

### Requisitos

- Arch Linux (o derivado: CachyOS, EndeavourOS, Manjaro…)
- KDE Plasma 6, sesión Wayland
- [catsout](https://github.com/catsout/wallpaper-engine-kde-plugin) instalado y activo en ambos monitores
- Python 3.10+, Node.js
- Rust + Cargo (para compilar Aura)
- `ffprobe` — validación de vídeo (opcional; del paquete `ffmpeg`)
- `python-pillow` — validación de imágenes y extracción de paleta de colores (opcional)

---

### Instalación

#### 1. Clonar este repositorio

```bash
git clone https://github.com/TU_USUARIO/aura-kde.git
```

#### 2. Clonar Aura y aplicar el parche

```bash
git clone https://github.com/antwny/aura.git
cd aura
git apply ../aura-kde/patches/aura-kde.patch
```

Verificar la base del parche antes de aplicar:

```bash
git log --oneline -1
# debe mostrar: c41ac5e docs(website): update version pill to v1.6.1
```

#### 3. Descargar dependencias de Cargo (una vez, requiere internet)

```bash
cargo fetch --locked
```

#### 4. Compilar

```bash
cargo build --features kde --locked --release --target-dir target-kde
```

La primera compilación tarda 5–15 minutos. Las siguientes son incrementales.

#### 5. Instalar

```bash
cd ../aura-kde
python3 scripts/install.py
# o especificar el binario:
# python3 scripts/install.py --binary ../aura/target-kde/release/aura
```

Instala en `~/.local` — sin root, sin autostart.
El icono de Aura también se instala automáticamente.

#### 6. Ejecutar

```bash
aura-kde-lab
```

O busca **Aura KDE Lab** en el lanzador de aplicaciones.

---

### Auto-theming — Colores desde el fondo

#### Activar / desactivar

Ve a **Ajustes → "Acento de color · KDE Plasma"** dentro de Aura y activa el toggle **"Color de acento según el fondo"**. Desde ese momento, cada vez que cambies el fondo Aura extrae su color más vibrante y lo aplica como accent color de KDE Plasma (barra de tareas, decoraciones de ventanas, widgets).

Para desactivarlo, apaga el mismo toggle.

#### Restaurar colores originales

El botón **"Restaurar colores originales"** (en la misma sección de ajustes) vuelve al acento guardado la primera vez que activaste el auto-tema. Equivale a buscar **"Restaurar estilos Aura"** en el lanzador de aplicaciones, o ejecutar:

```bash
aura-kde-lab theme-restore
```

Si quieres guardar manualmente un nuevo punto de referencia:

```bash
aura-kde-lab theme-snapshot
```

Los colores guardados se almacenan en `~/.local/state/aura-kde-lab/theme_defaults.json`.

> **Nota:** El auto-theming solo modifica el accent color de KDE. No toca la configuración de terminales (Ghostty, Konsole), temas de aplicaciones específicas ni ningún archivo fuera de `kdeglobals`.

---

### Actualizar

```bash
cd aura-kde
python3 scripts/install.py
```

Si el parche cambió, recompila Aura primero:

```bash
cd aura
git apply ../aura-kde/patches/aura-kde.patch
cargo build --features kde --locked --release --target-dir target-kde
cd ../aura-kde
python3 scripts/install.py
```

---

### Desinstalar

```bash
python3 scripts/install.py --uninstall
```

Los ajustes y registros de operaciones en `~/.local/state/aura-kde-lab/` se conservan.

---

### Opcional: Wallpaper Guardian

**Wallpaper Guardian** es una herramienta comunitaria separada que monitoriza los fondos en ejecución y detiene automáticamente los que crashean o desestabilizan Plasma. Mantiene una lista negra en `~/.config/wallpaper-engine-safe/blacklist.txt`.

`aura-kde` se integra con Guardian **automáticamente si está instalado**: los fondos en la lista negra se ocultan de la biblioteca sin configuración adicional. La lista negra solo se lee, nunca se escribe.

Guardian es completamente opcional. Sin él, la biblioteca muestra todos los fondos.

> ⚠️ Guardian no forma parte de este proyecto. Instálalo, configúralo y adminístralo por separado.

---

### Cómo funciona

```
aura-kde-lab (binario, --features kde)
    ↓ mensaje ApplyWallpaper
src/engine/kde.rs → python3 tools/aura_kde_bridge.py select PROYECTO
    ↓
aura_kde_bridge.py
    ├── aura_kde_catalog.py   — items Workshop + filtro Guardian
    ├── aura_kde_store.py     — items Store descargados (vídeo/imagen)
    ├── aura_kde_theme.py     — extrae paleta → aplica accent color KDE
    └── aura_kde_v2.py        — prepara registro → ejecuta transacción
            ↓
        plasma_snapshot_v2.js   — lee estado actual de Plasma
        plasma_transaction_v2.js — escribe todas las pantallas (1–3), verifica, rollback si falla
```

---

### Ejecutar tests

```bash
cd aura-kde
python3 -m unittest discover -s tests -v
```

49 tests cubren: filtrado de catálogo, lista negra Guardian, validación de snapshots, apply/restore v1, validación de vídeo/imagen Store, cambio de plugin v2, detección de conflictos, recuperación de operaciones interrumpidas y auto-theming.

---

### Limitaciones

- **1 a 3 monitores:** la transacción soporta de 1 a 3 escritorios activos; con 4 o más fallará.
- **Requiere sesión activa:** `evaluateScript` necesita una sesión Plasma en vivo.
- **Confirmación de reproducción:** el adaptador verifica valores de configuración, no la reproducción real. Confirma visualmente.
- **Fondos web** (tipo Workshop `web`): presentes en la biblioteca pero la reproducción no está probada.
- **catsout requerido en todas las pantallas:** si una pantalla usa un plugin diferente al aplicar, la operación falla.

---

### Licencia

Los archivos en `tools/`, `tests/` y `scripts/` son trabajo original de este adaptador.
Los archivos en `src/`, `patches/` y `assets/` modifican o derivan de [Aura](https://github.com/antwny/aura), que está bajo [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html).
Estas modificaciones son también **GPL-3.0**.

> Aura está desarrollado por [antwny](https://github.com/antwny) y colaboradores.
> Este adaptador es un proyecto comunitario independiente y no está afiliado con los autores de Aura.

---
---

<a name="english"></a>
## English

**KDE Plasma adapter for [Aura](https://antwny.github.io/aura/) — Wallpaper Engine on all screens.**

This is an Arch Linux–focused modification of [Aura](https://github.com/antwny/aura) by [antwny](https://github.com/antwny) that adds KDE Plasma 6 + Wallpaper Engine support: applies Workshop wallpapers to **1, 2 or 3 monitors simultaneously** with automatic plugin switching between the Wallpaper Engine backend ([catsout](https://github.com/catsout/wallpaper-engine-kde-plugin)) and the native image backend.

> **This project is a modification of [Aura](https://github.com/antwny/aura) by [antwny](https://github.com/antwny), licensed under GPL-3.0.**
> It is not affiliated with or endorsed by Valve, Steam, or Wallpaper Engine.
> "Wallpaper Engine" is a trademark of Kristjan Skutta / Wallpaper Engine Ltd.

---

### What it adds to Aura

| Feature | Notes |
|---|---|
| Workshop library in Aura's UI | Reads Steam libraries; respects Guardian blacklist if present |
| 1, 2 or 3 screens updated at once | Per-screen backup; full rollback on failure |
| Videos (Workshop, MotionBGS) | Activates **catsout** automatically |
| Images (Wallhaven, Bing, Minimalistic) | Activates **org.kde.image** automatically |
| Restore previous wallpaper | One click in the bar; restores plugin + config |
| **Auto-theming** | Settings toggle; extracts dominant color from wallpaper and applies it as KDE accent color |
| **Restore original colors** | Settings button or command; reverts to the accent saved before auto-theme first ran |
| Guardian integration (optional) | Reads `~/.config/wallpaper-engine-safe/blacklist.txt` to hide blocked wallpapers |

> **Note:** Wallpaper Engine wallpapers are downloaded from the [official Steam Workshop](https://steamcommunity.com/app/431960/workshop/). Aura reads wallpapers already installed in your Steam libraries. To add new wallpapers, subscribe to them on Steam Workshop and they will sync automatically.

---

### Requirements

- Arch Linux (or derivative: CachyOS, EndeavourOS, Manjaro…)
- KDE Plasma 6, Wayland session
- [catsout](https://github.com/catsout/wallpaper-engine-kde-plugin) installed and active on both monitors
- Python 3.10+, Node.js
- Rust + Cargo (to compile Aura)
- `ffprobe` — video validation (optional; from the `ffmpeg` package)
- `python-pillow` — image validation and color palette extraction (optional)

---

### Installation

#### 1. Clone this repo

```bash
git clone https://github.com/YOUR_USER/aura-kde.git
```

#### 2. Clone Aura and apply the patch

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

#### 3. Fetch Cargo dependencies (one-time, needs internet)

```bash
cargo fetch --locked
```

#### 4. Compile

```bash
cargo build --features kde --locked --release --target-dir target-kde
```

First build takes 5–15 minutes. Subsequent builds are incremental.

#### 5. Install

```bash
cd ../aura-kde
python3 scripts/install.py
# or specify the binary explicitly:
# python3 scripts/install.py --binary ../aura/target-kde/release/aura
```

Installs to `~/.local` — no root required, no autostart.
The Aura icon is also installed automatically.

#### 6. Run

```bash
aura-kde-lab
```

Or launch **Aura KDE Lab** from your application menu.

---

### Auto-theming — Colors from wallpaper

#### Enable / disable

Go to **Settings → "Accent color · KDE Plasma"** inside Aura and toggle **"Accent color from wallpaper"**. From that point on, every wallpaper change will extract the most vibrant color from the wallpaper and apply it as KDE Plasma's accent color (taskbar, window decorations, widgets).

To disable it, flip the same toggle off.

#### Restoring original colors

The **"Restore original colors"** button (in the same settings section) reverts to the accent that was saved the first time auto-theme was activated. Equivalent to searching for **"Restaurar estilos Aura"** in the application launcher, or running:

```bash
aura-kde-lab theme-restore
```

To manually save a new reference point:

```bash
aura-kde-lab theme-snapshot
```

Saved colors are stored in `~/.local/state/aura-kde-lab/theme_defaults.json`.

> **Note:** Auto-theming only modifies the KDE accent color. It does not touch terminal configurations (Ghostty, Konsole), application-specific themes, or any file outside `kdeglobals`.

---

### Updating

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

### Uninstalling

```bash
python3 scripts/install.py --uninstall
```

Settings and operation records in `~/.local/state/aura-kde-lab/` are preserved.

---

### Optional: Wallpaper Guardian

**Wallpaper Guardian** is a separate community tool that monitors running wallpapers and automatically stops ones that crash or destabilize Plasma. It maintains a blacklist at `~/.config/wallpaper-engine-safe/blacklist.txt`.

`aura-kde` integrates with Guardian **automatically if it is installed**: wallpapers listed in the blacklist are hidden from the library without any extra configuration. The blacklist is read on every catalog load and is **never written** by this adapter.

Guardian is entirely optional. If it is not installed, the library shows all wallpapers.

> ⚠️ Guardian is not part of this project. Install, configure, and manage it separately.

---

### How it works

```
aura-kde-lab (binary, --features kde)
    ↓ ApplyWallpaper message
src/engine/kde.rs → python3 tools/aura_kde_bridge.py select PROJECT
    ↓
aura_kde_bridge.py
    ├── aura_kde_catalog.py   — Workshop items + Guardian blacklist filter
    ├── aura_kde_store.py     — downloaded Store items (video/image)
    ├── aura_kde_theme.py     — extract palette → apply KDE accent color
    └── aura_kde_v2.py        — prepare record → run transaction
            ↓
        plasma_snapshot_v2.js   — read current state from Plasma
        plasma_transaction_v2.js — write all screens (1–3), verify, rollback on failure
```

### Key design decisions

- **No mpvpaper**: the KDE build excludes the original process-based engine entirely.
- **Two-phase apply**: source is blanked first (forces backend reload), then set to the new value.
- **Empty string normalization**: `writeConfig(key, '')` in Plasma leaves the key present with `""` in `configKeys` instead of deleting it; the adapter normalizes `""` to absent on every read to keep verification consistent.
- **Plugin switching**: `d.wallpaperPlugin = ...` defers activation until script cleanup.
- **Guardian integration**: blacklist is read on every catalog load, never written.
- **Auto-theming disabled by default**: enable via Aura's settings toggle; only the KDE accent color is changed.

---

### Running tests

```bash
cd aura-kde
python3 -m unittest discover -s tests -v
```

49 tests cover: catalog filtering, Guardian blacklist, snapshot validation, v1 apply/restore, Store video/image validation, v2 plugin switching, conflict detection, recovery from interrupted operations, and auto-theming.

---

### Repository layout

```
aura-kde/
├── assets/
│   └── io.github.antwny.aura.svg  — Aura's icon (from upstream, GPL-3.0)
├── patches/
│   └── aura-kde.patch       — diff against Aura v1.6.1 (c41ac5e)
├── src/
│   ├── engine/kde.rs         — KDE WallpaperEngine (stub + bridge caller)
│   └── kde_cli.rs            — KDE CLI entry (--kde-info marker)
├── tools/
│   ├── aura_kde_bridge.py    — main entry: catalog / select / restore / theme
│   ├── aura_kde_catalog.py   — Workshop catalog + Guardian filter
│   ├── aura_kde_store.py     — downloaded Store items
│   ├── aura_kde_apply.py     — v1 apply/restore/recover
│   ├── aura_kde_v2.py        — v2 plugin-aware apply/restore
│   ├── aura_kde_snapshot.py  — evaluateScript wrapper
│   ├── aura_kde_theme.py     — auto-theming: palette extraction + KDE accent
│   ├── plasma_snapshot.js    — v1 Plasma state reader
│   ├── plasma_snapshot_v2.js — v2 reader (both plugin groups)
│   ├── plasma_transaction.js — v1 writer
│   └── plasma_transaction_v2.js — v2 writer (plugin switch + rollback)
├── tests/                    — unittest suite (49 tests)
├── scripts/
│   ├── install.py            — install / uninstall
│   └── dev-run.sh            — development launcher
└── README.md
```

---

### Limitations

- **1 to 3 monitors**: the transaction supports 1 to 3 active desktops; 4 or more will fail.
- **Active session required**: `evaluateScript` needs a live Plasma session.
- **Playback confirmation**: the adapter verifies config values, not actual playback.
- **Web wallpapers** (Workshop type `web`): present in the library but playback is untested.
- **catsout required on all screens**: if one screen uses a different plugin at apply time, the operation fails.

---

### Patch base

The patch applies to Aura commit `c41ac5e` (v1.6.1):

```bash
cd aura
git log --oneline -1
# c41ac5e docs(website): update version pill to v1.6.1
```

---

### License

The files in `tools/`, `tests/` and `scripts/` are original work for this adapter.
The files in `src/`, `patches/` and `assets/` modify or derive from [Aura](https://github.com/antwny/aura), which is [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html).
These modifications are therefore also **GPL-3.0**.

> Aura is developed by [antwny](https://github.com/antwny) and contributors.
> This adapter is an independent community project and is not affiliated with Aura's authors.
