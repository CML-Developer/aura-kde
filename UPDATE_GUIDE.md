# Aplicar correcciones en otro equipo

Este documento explica cómo actualizar aura-kde en otro equipo donde ya lo instalaste desde el repositorio.

## Lo que se actualizó

- ✅ **Auto-restore de fondos**: El último fondo seleccionado se restaura automáticamente en ~5 segundos al iniciar sesión
- ✅ **Lista completa de archivos modificados**: Transparencia GPL-3.0
- ✅ **Correcciones de documentación**: Fechas, monitores soportados, etc.

## Pasos para actualizar

### 1. Actualizar el repositorio

```bash
cd ~/ruta/donde/clonaste/aura-kde
git pull
```

**Salida esperada:**
```
Actualizando 76e8cc4..b74d834
...
5 files changed, 193 insertions(+)
create mode 100644 autostart/README.md
create mode 100755 autostart/aura-kde-restore-on-login
...
```

### 2. Reinstalar

```bash
python3 scripts/install.py --binary .build/target-kde/release/aura
```

**Qué hace:**
- Actualiza todos los archivos en `~/.local/lib/aura-kde-lab/`
- Instala `~/.local/bin/aura-kde-restore-on-login`
- Instala `~/.config/autostart/aura-kde-restore.desktop`
- Registra todos los archivos en el manifiesto

**Salida esperada:**
```
Installing 37 files under /home/usuario/.local
Manifest: /home/usuario/.local/lib/aura-kde-lab/MANIFEST.json
```

### 3. Verificar instalación

```bash
# Verificar que el script existe
ls -l ~/.local/bin/aura-kde-restore-on-login

# Verificar que el autostart existe
ls -l ~/.config/autostart/aura-kde-restore.desktop

# Verificar que el script de force restore existe
ls -l ~/.local/lib/aura-kde-lab/tools/aura_kde_force_restore.py
```

### 4. Probar el autostart

1. Abre Aura y selecciona un fondo diferente
2. Espera a que se aplique
3. **Cierra sesión** (logout)
4. **Inicia sesión** de nuevo
5. Espera ~5 segundos
6. El fondo debería restaurarse automáticamente

### 5. Verificar que funcionó

```bash
# Ver el log del autostart
tail ~/.local/state/aura-kde-lab/autostart.log
```

**Salida esperada:**
```
[fecha]: Force restoring [id] - [título del fondo]
Current plugin: ...
Desired plugin: ...
✓ Successfully applied: ...
[fecha]: ✓ Force restore successful
```

## Solución de problemas

### El autostart no se ejecuta

Verifica que el archivo .desktop existe:
```bash
cat ~/.config/autostart/aura-kde-restore.desktop
```

### El restore falla

Revisa el log de errores:
```bash
tail -20 ~/.local/state/aura-kde-lab/autostart.log
```

### Quiero deshabilitar el autostart temporalmente

```bash
# Opción 1: Eliminar el .desktop
rm ~/.config/autostart/aura-kde-restore.desktop

# Opción 2: Marcarlo como Hidden
echo "Hidden=true" >> ~/.config/autostart/aura-kde-restore.desktop
```

### Quiero cambiar el tiempo de espera

Edita el script:
```bash
nano ~/.local/bin/aura-kde-restore-on-login
```

Busca la línea `sleep 3` y cámbiala al número de segundos que prefieras (1-10 recomendado).

## Desinstalación completa

Si quieres eliminar aura-kde completamente:

```bash
cd ~/ruta/donde/clonaste/aura-kde
python3 scripts/install.py --uninstall
```

Esto elimina todos los archivos instalados, incluyendo el autostart.

## Notas importantes

- ✅ El autostart solo restaura fondos seleccionados **desde Aura**
- ✅ Si cambias el fondo desde la configuración de KDE, ese cambio NO se guardará en Aura
- ✅ Funciona con fondos del Workshop y de la Store (descargados)
- ✅ Funciona con videos (catsout) e imágenes (org.kde.image)
- ✅ No interfiere con el funcionamiento normal de Aura

## Más información

Ver `autostart/README.md` para detalles técnicos sobre cómo funciona el sistema.
