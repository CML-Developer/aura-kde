

<!-- continuidad-local:inicio -->
## Continuidad entre Claude Code y Codex
- Al iniciar, lee docs/CONTINUIDAD.md, docs/DECISIONES.md y .continuidad/estado.json si existen.
- Contrasta el resumen con git status y el diff pertinente. Puede haber una interrupción sin resumen final.
- Conserva cambios previos y ajenos, incluidos los que no tienen commit. No reinicies el trabajo ya terminado.
- Actualiza docs/CONTINUIDAD.md al terminar cada subtarea, antes de una operación larga y al cerrar.
- Registra objetivo, estado, archivos, pruebas realmente ejecutadas, errores, trabajo incompleto y próximo paso concreto.
- No declares una prueba exitosa si no se ejecutó. Si está en curso, escribe pendiente.
- Anota decisiones duraderas y sus motivos en docs/DECISIONES.md.
- No guardes secretos, claves, tokens ni contenido de .env en estos documentos.
- El registro automático solo captura metadatos Git; tú debes documentar intención y decisiones.
- No hagas commit, reset, stash, limpieza o despliegue solo por cambiar de asistente.
- No modifiques .continuidad/estado.json: lo administra el gestor. No ejecutes otro agente simultáneamente.
<!-- continuidad-local:fin -->
