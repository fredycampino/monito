# Contexto de continuidad — 20 de octubre

Resumen de la conversación, decisiones, estado del repositorio y verificaciones. No es una copia literal del prompt ni contiene credenciales. Los resultados históricos indicados proceden de mensajes anteriores; las comprobaciones de la implementación actual se ejecutaron en esta sesión.

## Identidad y forma de trabajar acordada

- El asistente se llamará **Nexo**; el usuario eligió ese nombre, pero pidió posponer el cambio de identidad/configuración. Monito es el producto y agente que desarrollamos.
- Responder en español, de forma breve, directa y concreta. El usuario pide proactividad, verificaciones reales y no repetir condiciones ya conocidas.
- Presentar el objetivo antes que el procedimiento. No convertir documentación o instrucciones en tutoriales innecesarios: autorización y propósito primero, ejemplos breves después.
- Inspeccionar antes de proponer mecanismos: el plan no debe depender de supuestos no comprobados.
- Mantener separado el desarrollo local del despliegue en Max. No reiniciar, cambiar montajes ni perder sesiones por accidente.
- No crear commits, publicar, fusionar o desplegar sin la autorización correspondiente. Para las PR usamos el agente/flow `@pr`, que ya permitió crearlas mediante MCP GitHub; `gh` no es un requisito.
- La release es beta: evitar ampliar el alcance con instaladores o refinamientos no necesarios.

## Repositorios y entorno

- Repositorio de trabajo: `/home/fede/develop/monito`.
- Fuente de Skiller disponible para consultar: `/home/fede/develop/py/skiller`. No se modifica como parte del trabajo en Monito.
- Entorno actual comprobado: host de desarrollo, no Box Docker.
- Box instala recursos en `/usr/local/lib/python3.12/site-packages/packages/`; el workspace es `/data/workspace` y HOME es `/data/home`.
- Configuración Runtime montada en `/etc/monito/config.json`, perfil del agente en `/etc/monito/agent.json`, ambos de solo lectura.
- DB habitual: `/data/home/.skiller/db/agent.db`. No modificar manualmente una DB activa ni leer/imprimir secretos.

## Historial de integración y release

- PR #14: refactor de herramientas e introducción de Ggets; merge `9904d11`.
- PR #15: preparación del despliegue y ejemplos, instrucciones, perfil externo y fix del cwd de webhook; merge `54d767c`.
- PR #16: release `0.1.0-beta.5`; merge `6c0f124`, actual base de main al comenzar esta feature.
- Monito y Ggets comparten versión. Imágenes `ghcr.io/fredycampino/monito-box:0.1.0-beta.5` y `ghcr.io/fredycampino/ggets:0.1.0-beta.5`.
- La CI sí construía/publicaba Ggets. El error `unauthorized` se debía a que el paquete GHCR estaba privado; el usuario cambió la visibilidad y Max pudo descargarlo.
- Publicar una release no despliega automáticamente el servidor.

## Organización de despliegue y ejemplos

- Un único `compose.yaml` para desarrollo y despliegue. Variables en `docker/compose.env`.
- Local: prefijo de imagen vacío y versión `dev`. Publicado: prefijo `ghcr.io/fredycampino/` y versión explícita, sin `v`.
- Deploy publicado: descargar ambas imágenes y levantar con `--no-build`; no construir en servidor.
- `data-examples/` refleja la estructura de `data/`, con nombres finales de archivos, no sufijos `.example`.
- Estructura: `monito/settings/{config.json,agent.json}`, `monito/home/`, `monito/workspace/`, `ggets/config.json`, `ggets/secrets/`, `ggets/state/`.
- Se añadieron ejemplos vacíos de secretos de Skiller. Para Telegram existen `telegram_bot_token` y `telegram_webhook_secret`; una línea `# secret here` es placeholder a reemplazar, no comentario interpretado por el consumidor.
- Preparación documentada por objetivo: disponer de estructura, configuración, credenciales y permisos correctos. No imponer comandos de copia innecesarios.
- `agent.json` del wheel se eliminó. El flow selecciona directamente `/etc/monito/agent.json`, sin `MONITO_AGENT_CONFIG_FILE`.
- La protección es el montaje read-only, no el nombre `/etc`. El usuario puede cambiar el perfil desde el host; se recarga antes de los turnos. Un shell hijo no cambia el entorno del proceso padre. Ejecutar otros procesos es un problema distinto de seguridad.
- Configuración global de proveedor/modelo vive también en HOME: `.skiller/settings/agent.json` y `providers.json`. Omitir estos archivos provocó errores de `llm` requerido y búsqueda de `AGENT_MINIMAX_API_KEY` pese a existir archivos de secretos.

## Generación de config.json: decisión pendiente

- Se discutió automatizar `config.json`, pero se abandonó hacerlo durante build o en entrypoint.
- La propuesta pendiente es un script/configurador que copie la estructura de ejemplos y complete valores, manteniendo las ubicaciones actuales.
- La IP viene de Compose (`MONITO_INTERNAL_IP`, default `172.28.0.3`), no del ENV de la imagen. Compose no lee ENV de imágenes para resolver su topología.
- No confundir este pendiente con el entrypoint de servidor aprobado ahora: este último no genera configuración.

## Incidentes locales y lecciones

- El usuario renombró `data` a `_data` para conservar credenciales y estado mientras probábamos instalación limpia; `_data/` se añadió a `.gitignore`.
- Inicialmente solo se copiaron secretos al nuevo data, sin recrear contenedores: los procesos seguían con montajes antiguos.
- Una recreación posterior cambió al HOME limpio y desaparecieron de la vista sesiones y configuración LLM. No se borró la DB antigua, pero se interrumpió el contexto del usuario.
- Se recuperaron HOME y workspace desde `_data/monito/`, manteniendo la imagen corregida. No asumir que un reinicio conserva el mismo montaje: verificarlo antes.
- El ensayo de instalación limpia no debe confundirse con las pruebas funcionales del entorno recuperado.

## Telegram y cwd

- Ggets contiene GgTelegram. Recibe Telegram en un endpoint público HTTPS y entrega a Skiller por red interna.
- Skiller y el listener deben compartir DB; el listener entrega texto al run suscriptor usando `skiller input receive`.
- El agente responde mediante Ggets `/telegram/send`, no directamente a Telegram ni accediendo a sus credenciales.
- `WEBHOOK_WAIT_CONFLICT` identifica el listener existente. Las instrucciones autorizan relevarlo: mostrar el conflicto, eliminar solo el listener indicado y registrar otro dirigido al run solicitado, sin una confirmación adicional. Nunca borrar el suscriptor por ese conflicto.
- Se corrigió `packages/webhook/webhook.yaml`: `deliver_event` usa `cwd: /data/workspace`, no `{{flow.dir}}`. Antes la reanudación desde webhook propagaba el directorio del paquete y bloqueaba herramientas por `allowed_paths`.
- También se corrigió la instrucción que afirmaba que los permisos estaban restringidos al directorio empaquetado: en Box el workspace es `/data/workspace`.
- Los perfiles antiguo, nuevo y ejemplo tenían las mismas restricciones: no se había activado un bloqueo nuevo. `allowlist_enabled: false` desactiva la lista de comandos, no las restricciones de rutas. El problema observado era cwd, no prohibición de ejecutar `skiller` o `curl`.
- El usuario confirmó que el fix de cwd resolvió la recepción/respuesta.

## Instrucciones y herramientas del agente

- Instrucciones locales añadidas/adaptadas: `install-packages.md`, `use-internet-search.md`, `use-box.md`, `use-telegram.md`.
- `env-box.md` se renombró a `use-box.md`: introducción breve Docker/Monito/Ggets, árbol del entorno y CLI instaladas.
- Se permite instalar paquetes en venvs propios del workspace, sin modificar Python de Skiller o la imagen. No convertirlo en tutorial largo.
- DDGS se puede instalar en un venv; no viene instalado por defecto. Se adaptó la instrucción nativa `ddgs-use` a `use-internet-search.md`.
- Se observó que un User-Agent personalizado mejoró respuestas de Yahoo Finance frente a un 429 previo. Se añadió una nota breve: puede ayudar, no garantiza superar bloqueos ni justifica ignorar límites.
- Pendiente: instrucciones instalables/actualizables fuera del build; distinguir actualizar archivos referenciados de añadir nuevas referencias y verificar cuándo se recargan. Documentado en `docs/todo/runtime-instructions.md`.

## Max: servidor de despliegue

- Usuario SSH: `max`. Host: `max-server`.
- IP cableada anterior: `192.168.1.199`. Al desconectar Ethernet, se encontró Wi-Fi en `192.168.1.202` y se verificó identidad. También anuncia `max-server.local`.
- Inspecciones recientes usaron `ssh -o HostKeyAlias=192.168.1.199 max@192.168.1.202` para validar la clave conocida.
- Administración: `/home/max/server-admin/monito/`, no `monito-deploy`.
- Datos: `/opt/monito/data/`, propiedad `max:max`, UID/GID `1000:1000`.
- El usuario autorizó borrar el data anterior y ejecutó él mismo el comando de borrado; después corrigió propiedad/permisos desde su sesión SSH.
- Se copiaron Compose y entornos, estructura y configuración. Secretos Skiller tomados de `/home/max/.skiller/secrets/`: solo `minimax_api_key` y `openai-codex.json`; NO `github_mcp_token`.
- Secretos Telegram copiados del despliegue local. Comparten bot: cambiar el webhook público traslada la recepción.
- Contenedores desplegados: `monito-monito-1` y `monito-ggets-1`, ambos beta.5.
- Ggets publica `127.0.0.1:8001 -> 8001/tcp`. Monito no publica puertos.
- Acceso a STUI desde Max: `docker exec -it monito-monito-1 skiller @monito`.
- Alternativa Compose: desde `~/server-admin/monito`, `docker compose --env-file docker/compose.env exec monito skiller @monito`. El env-file ayuda a resolver Compose; no reconfigura el contenedor al hacer exec.

## Túnel en Max

- Configuración: `/home/max/.cloudflared/monito.yaml`.
- Dominio: `monito.campino.me`; destino `http://127.0.0.1:8001`.
- El usuario instaló Cloudflared como servicio systemd; se informó verificado active y enabled.
- Ggets tiene `telegram.base_url=https://monito.campino.me`.
- Prueba pública sin secreto respondió 401 como corresponde.
- Ejecutar un túnel en primer plano por SSH no garantiza supervivencia al cierre de sesión; systemd lo independiza y lo inicia tras reboot.

## Revisión del run persistente en Max

Run: `74f6c9f4-6b67-4392-a57b-8e4257d5d791`.

Verificado mediante CLI de solo inspección:
- Creación: 2026-10-18 22:49:49 UTC.
- 633 eventos: 46 INPUT_RECEIVED, 46 RUN_RESUME, 46 respuestas finales, 108 llamadas y 108 resultados de herramientas.
- Sin eventos de fallo del run; no equivale a que todas las herramientas fueran exitosas.
- Último evento: RUN_WAITING, 2026-10-19 14:43:27 UTC, espera de input.
- Listener `f0bfea51-f481-4394-b07b-2d6eea22b2dc`, WAITING en `telegram:inbox`.
- Tras arrancar Max, contenedores activos desde 2026-10-19 20:06 UTC, 0 reinicios registrados, sin OOM.
- `skiller server status`: running=false, pid=null, endpoint `http://172.28.0.3:8001/health`.
- No había actividad nueva del run después del arranque. DB/listener persistieron, servidor HTTP no.
- El periodo de eventos observado cubría unas 16 horas; no se afirmó verificar 24 horas completas.
- No se arrancó ni modificó nada en Max durante esta revisión.

## Feature actual: arranque automático del servidor Skiller

Objetivo aprobado: quitar al agente la responsabilidad de iniciar el servidor, conservando su capacidad de verificarlo. Arrancarlo mediante entrypoint al iniciar/reiniciar el contenedor.

Rama actual: `feature/skiller-server-startup`, creada desde main actualizado a `6c0f124`. No hay commits nuevos ni push de esta feature.

Verificación previa del contrato:
- Dockerfile original: sin entrypoint, CMD sleep infinity.
- Compose: init=true, restart=unless-stopped, usuario no root, rootfs read-only; HOME y workspace escribibles.
- Skiller `server start` lanza un proceso background y espera hasta 10 segundos por HTTP 200 del health. El CLI devuelve error si el arranque falla.
- Estado gestionado en `~/.skiller/webhooks/managed-<port>.json`; comprueba PID/proceso previo. `ps` ya está en la imagen.
- Arranque automático no equivale a supervisión de caídas posteriores. No se cambió Runtime ni TUI.

Implementado:
- Nuevo `docker/monito-entrypoint.sh`: `set -eu`, `skiller server start`, `exec "$@"`.
- Dockerfile copia script con modo 755, declara ENTRYPOINT y conserva sleep infinity.
- `use-telegram.md`: comprobar server status; si está parado, reportar fallo del despliegue, no iniciar manualmente ni registrar mientras esté indisponible.
- Actualizados `docs/deployment.md`, `docs/local-deployment.md`, `docs/docker-spec.md` y CHANGELOG.
- Tests añadidos en `packages/monito/tests/test_deployment.py`: orden de ejecución, no ejecutar comando principal cuando start falla, preservación de argumento con espacios y wiring del Dockerfile.
- TODO local `docs/todo/skiller-server-lifecycle.md` actualizado para dejar pendiente supervisión y apagado ordenado; está ignorado por Git.

Verificaciones ejecutadas:
- `.venv/bin/pytest -q`: **101 passed**.
- `.venv/bin/ruff check .`: correcto.
- `git diff --check`: correcto.
- Imagen construida: `monito-box:startup-check`.
- Contenedor de prueba aislado, sin root, rootfs read-only, cap-drop ALL, no-new-privileges, HOME/workspace temporales y AGENT_DB_PATH separado.
- Health inicial correcto; listener de prueba WAITING persistió al docker restart; servidor volvió a arrancar; POST HTTP local reanudó el run y terminó SUCCEEDED.
- Configuración inválida: salida no cero y comando principal no ejecutado.
- Contenedores y directorios temporales de ensayo eliminados. Imagen de prueba permanece.
- No se tocaron Max, su DB, credenciales, listener ni contenedores locales activos.
- No se probó Telegram real en esta feature: la prueba fue entrega HTTP local a un listener aislado.

Incidencias de verificación, sin alterar alcance:
- `uv run` no pudo iniciar por workspace `packages/*` que incluye `packages/webhook` sin pyproject.toml. Se usaron pytest y Ruff del venv existente; no se cambió configuración uv.
- La primera aserción del ensayo esperaba SUCCESS en vez de SUCCEEDED; el run había finalizado correctamente. Se corrigió la expectativa y se repitió el ensayo con éxito.

## Pendientes y límites

- Revisar diff y preparar commit/PR cuando el usuario lo pida. No desplegar automáticamente la feature actual.
- La caída del servidor después de arrancar no se supervisa: sleep infinity sigue vivo. Sigue pendiente definir supervisión y apagado ordenado.
- Otros TODO conocidos: recuperación/retención de entregas fallidas, lifecycle del receptor Telegram al ejecutar CLI Ggets, script de preparación de config/flow_paths e instrucciones en runtime.
- TODO retirados por resueltos: herramientas de imagen (curl) y relevo de listener (ahora definido en instrucciones).
- `docs/todo/` está ignorado: no asumir que editar un TODO lo incluye en una PR.
- Preservar siempre el entorno activo y confirmar montajes antes de recrear. Nunca volver a confundir datos nuevos de prueba con HOME/DB del usuario.
