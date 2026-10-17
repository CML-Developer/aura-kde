# Auto-restore de fondos al iniciar sesión

## Problema que resuelve

Cuando cambias de fondo desde Aura, el cambio se hace via `writeConfig()` de KDE, que solo modifica la configuración en memoria. Al reiniciar el sistema, KDE carga la configuración desde disco (`appletsrc`), que puede tener un fondo antiguo.

## Solución

Este sistema restaura automáticamente el último fondo seleccionado desde Aura al iniciar sesión.

## Archivos

### `aura_kde_force_restore.py`
- **Ubicación instalada**: `~/.local/lib/aura-kde-lab/tools/`
- Script Python que aplica el fondo sin validar el estado previo
- Lee la última operación de `~/.local/state/aura-kde-lab/operations/`
- Usa `transition()` de `aura_kde_v2.py` para aplicar el fondo
- Maneja correctamente cambios de plugin (imagen ↔ video)

### `aura-kde-restore-on-login`
- **Ubicación instalada**: `~/.local/bin/`
- Script bash que se ejecuta al iniciar sesión
- Espera 3 segundos a que Plasma inicialice
- Llama a `aura_kde_force_restore.py`
- Registra resultado en `~/.local/state/aura-kde-lab/autostart.log`

### `aura-kde-restore.desktop`
- **Ubicación instalada**: `~/.config/autostart/`
- Desktop file de KDE autostart
- Phase 2 (después de panel)
- Se ejecuta después de que Plasma carga

## Comportamiento

1. Al iniciar sesión, el script espera ~3 segundos
2. Lee la última operación guardada por Aura
3. Aplica ese fondo directamente (sin validar estado previo)
4. **Tiempo total**: ~5 segundos desde login hasta que aparece el fondo

## Instalación

El instalador (`scripts/install.py`) instala automáticamente estos archivos:
```bash
python3 scripts/install.py --binary .build/target-kde/release/aura
```

## Desinstalación

```bash
python3 scripts/install.py --uninstall
```

Esto elimina todos los archivos instalados, incluyendo el autostart.

## Log

Para ver si el autostart está funcionando:
```bash
tail -f ~/.local/state/aura-kde-lab/autostart.log
```

## Aplicar en otro equipo

Si ya instalaste aura-kde desde el repositorio en otro equipo:

1. Actualiza el repositorio:
```bash
cd aura-kde
git pull
```

2. Reinstala para obtener los archivos de autostart:
```bash
python3 scripts/install.py --binary .build/target-kde/release/aura
```

3. Cierra sesión y vuelve a entrar
4. El fondo se restaurará automáticamente en ~5 segundos
