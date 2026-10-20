# Spike: navegación web para Monito

## Objetivo

Dar a Monito capacidad de explorar páginas, leer contenido e interactuar con sitios sin construir un navegador o un controlador desde cero. Reducir bloqueos es deseable, pero ningún navegador garantiza acceso universal ni evita restricciones de cuentas.

## Decisión

**Primero nos enfocaremos en la opción 1: Monito → Browser Use CLI/Harness → Chromium local.**

- Monito conserva el razonamiento y utiliza el controlador como herramienta; no se busca incorporar otro agente autónomo ni cambiar de modelo.
- El navegador se ejecuta en infraestructura propia. No se contratará Browser Use Cloud para esta primera fase.
- Reutilizaremos software existente para navegación, lectura e interacción.
- Camofox queda como alternativa posterior, no como parte de la primera implementación.
- Esta decisión define la dirección de investigación. No implica que la integración, instalación o despliegue ya estén realizados.

## Qué es cada componente

| Componente | Qué es | Licencia y coste |
| --- | --- | --- |
| Chromium | Navegador completo que ejecuta páginas, JavaScript, cookies y sesiones. | Código abierto; revisar licencias del paquete distribuido y dependencias. |
| Browser Use | Proyecto y biblioteca principalmente Python para agentes que controlan navegadores. | MIT en el repositorio revisado; uso local sin pagar licencia. |
| Browser Use CLI / Browser Harness | Herramienta de terminal y motor de control que un agente existente puede utilizar. Hermes describe su CLI como una capa sobre browser-harness. | MIT en el repositorio de Browser Harness revisado. |
| Browser Use Cloud | Servicio comercial de navegadores y agentes alojados. Es distinto del software local. | De pago; fuera de la primera fase. |
| Browserbase | Otro proveedor comercial de navegadores alojados. | Fuera de la primera fase. |
| CDP | Protocolo de control remoto de Chrome/Chromium. | No es un navegador ni una solución antibloqueo. |
| Camoufox | Navegador basado en Firefox, modificado para reducir señales de automatización. | Sus licencias y las de sus dependencias requieren revisión si se distribuye. |
| Camofox-browser | Servidor Node.js que envuelve Camoufox y expone una API HTTP para agentes. | MIT para el servidor; no sustituye las licencias del motor. |

MIT permite uso, modificación y distribución, incluso comercial, conservando los avisos de copyright y licencia. Ejecutar software local no elimina costes de infraestructura ni del modelo.

## Cómo lo hace Hermes

Investigación sobre NousResearch/hermes-agent; revisión consultada: `9cb34e9e285dadd0c6d2463e9b094052530fc365`.

- El modo predeterminado documentado utiliza Browser Use CLI / browser-harness mediante `browser_exec`: el agente ejecuta Python para controlar el navegador.
- Sin proveedor cloud ni conexión explícita, utiliza Chromium local empaquetado.
- También admite conexión a navegadores Chromium existentes mediante CDP.
- Sus herramientas integradas ofrecen lectura mediante árboles de accesibilidad, referencias a elementos y capturas para análisis visual.
- Admite proveedores cloud: Browser Use Cloud, Browserbase y Firecrawl.
- Camofox usa una ruta distinta: herramientas que llaman a su API HTTP. No expone el endpoint CDP que necesita el controlador principal.
- Gestiona aislamiento de sesiones, cierre por inactividad y opciones de perfiles autenticados.

Hermes integra piezas existentes; no demuestra una capacidad propia de navegar sin bloqueos.

Detalles observados en código:
- El proveedor Browserbase solicita proxies por defecto, pero `advancedStealth` está desactivado por defecto. Puede reintentar sin determinadas funciones ante errores de pago.
- El proveedor Browser Use examinado crea sesiones sin seleccionar explícitamente un perfil persistente. Que el servicio soporte perfiles no significa que toda integración los reutilice automáticamente.

## Opciones locales consideradas

### Opción 1 — seleccionada primero

**Monito → Browser Use CLI/Harness → Chromium**

Ventajas: reutiliza un controlador existente, usa un navegador estándar y mantiene la navegación en infraestructura propia. Es la ruta que priorizaremos para validar capacidades básicas e integración.

Límites: Chromium y el controlador no garantizan superar sistemas antibot. Hay que gestionar sesiones, recursos, permisos y fallos.

### Opción 3 — alternativa posterior

**Monito → herramientas HTTP → Camofox-browser → Camoufox**

No necesita Browser Use como intermediario. Su API ya permite pestañas, navegación, lectura, clics, escritura, desplazamiento y capturas. Documenta aislamiento de sesiones, importación de cookies y login visual mediante noVNC.

Dificultad estimada, no medida:
- Arranque de prueba: baja; dispone de instalación npm y Docker. La documentación indica una descarga inicial del navegador de aproximadamente 300 MB.
- Integración con Monito: media; requiere adaptar herramientas a su API HTTP.
- Operación estable: media; proteger API, gestionar estado, recursos, actualizaciones y errores.

La incompatibilidad con CDP cambia el adaptador, no obliga a desarrollar un navegador. Revisar la telemetría de fallos, documentada como activa por defecto, antes de utilizar sesiones privadas.

## Qué influye en los bloqueos

- Compatibilidad: navegador completo con JavaScript, cookies y almacenamiento.
- Conexión: reputación y estabilidad de la IP; un navegador modificado no resuelve una IP bloqueada.
- Identidad: perfiles dedicados y persistentes para evitar autenticaciones continuas; las cookies son credenciales.
- Comportamiento: concurrencia limitada por sitio, caché, respeto de `Retry-After` y reintentos acotados.
- Tipo de problema: distinguir CAPTCHA, límite de tráfico, fallo técnico y suspensión de cuenta.

La exploración de lectura puede ser autónoma. Login, MFA, desafíos no resueltos y operaciones con consecuencias necesitan reglas e intervención humana cuando corresponda. No copiar por defecto el perfil personal completo del usuario ni exponer la API de control públicamente.

## Verificación pendiente

Antes de implementar, revisar instalación, contrato de CLI/Harness, compatibilidad de versiones y herramientas disponibles en Monito/Skiller. La integración concreta aún no está diseñada.

Una prueba posterior debe usar perfiles y datos aislados, con sitios y alcance autorizados, y medir:
- Tareas completadas y contenido correcto.
- Bloqueos, CAPTCHA e intervenciones humanas.
- Persistencia de sesiones.
- Latencia, consumo de recursos y coste por tarea.

No se han instalado navegadores ni realizado pruebas contra sitios objetivo. Las capacidades antibloqueo citadas son declaraciones de los proyectos/proveedores, no resultados propios. El benchmark de Hermes revisado usa sitios de pruebas sin protección antibot: sirve para comparar ejecución y consumo, no para demostrar resistencia a bloqueos.

## Fuentes

- [Hermes: documentación de navegación](https://github.com/NousResearch/hermes-agent/blob/9cb34e9e285dadd0c6d2463e9b094052530fc365/website/docs/user-guide/features/browser.md)
- [Hermes: proveedor Browser Use](https://github.com/NousResearch/hermes-agent/blob/9cb34e9e285dadd0c6d2463e9b094052530fc365/plugins/browser/browser_use/provider.py)
- [Hermes: proveedor Browserbase](https://github.com/NousResearch/hermes-agent/blob/9cb34e9e285dadd0c6d2463e9b094052530fc365/plugins/browser/browserbase/provider.py)
- [Hermes: integración Camofox](https://github.com/NousResearch/hermes-agent/blob/9cb34e9e285dadd0c6d2463e9b094052530fc365/tools/browser_camofox.py)
- [Hermes: benchmark y limitaciones](https://github.com/NousResearch/hermes-agent/blob/9cb34e9e285dadd0c6d2463e9b094052530fc365/evals/browser_use/README.md)
- [Browser Use: proyecto y licencia](https://github.com/browser-use/browser-use)
- [Browser Harness: proyecto y licencia](https://github.com/browser-use/browser-harness)
- [Camofox-browser: documentación y licencia](https://github.com/jo-inc/camofox-browser)
- [Browser Use Cloud: stealth](https://docs.browser-use.com/cloud/browser/stealth)
- [Browser Use Cloud: proxies](https://docs.browser-use.com/cloud/browser/proxies)
