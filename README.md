# Monito

Monorepo de herramientas CLI para agentes Monito.

Las decisiones estructurales del proyecto están documentadas en [`docs/architecture.md`](docs/architecture.md).

## Estructura

- `tools/<nombre>/`: CLI, agente manager y tests de una herramienta independiente.
- `packages/<nombre>/`: código común cuando exista una necesidad real; cada paquete incluye sus tests unitarios.
- `monito/`: agente desarrollador de este repositorio.
- Herramientas actuales: `sk-telegram` y `sk-cloudflared`.
- `VERSION`: versión única de todos los paquetes.

Las herramientas no dependen entre sí. No hay tests globales: cada herramienta y paquete prueba su propio comportamiento.

## Desarrollo

Instalar el workspace y ejecutar una herramienta:

```bash
uv sync --all-packages --all-extras
uv run sk-telegram --help
uv run sk-cloudflared login status
# Tras autorizar Cloudflare y confirmar los valores del túnel:
uv run sk-cloudflared tunnel register --name telegram --config ~/.cloudflared/telegram.yml
uv run sk-cloudflared tunnel open --name telegram
uv run sk-cloudflared tunnel open --name telegram
```

Ejecutar las comprobaciones:

```bash
uv run --package sk-telegram pytest tools/telegram/tests
uv run ruff check tools/telegram/src tools/telegram/tests
```

## Versionado y publicación

Todos los paquetes toman la misma versión de `VERSION`. Cualquier release incrementa esa versión y publica nuevamente todas las herramientas y paquetes comunes. El tag de Git usa la forma `v<versión>`.

El desarrollo y la release son conjuntos, pero la instalación es independiente:

```bash
uv tool install sk-telegram==0.1.0
```
> Temporary CI branch-policy verification PR.
