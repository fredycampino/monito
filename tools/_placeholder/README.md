# Nueva herramienta

Este directorio representa futuras herramientas dentro del monorepo.

Cada herramienta real debe tener esta forma:

```text
tools/<nombre>/
├── agent/          # Agente manager de la herramienta
├── src/            # Implementación y CLI
├── tests/          # Tests propios
├── pyproject.toml
└── README.md
```

Al crear una herramienta:

- Usar el nombre de la capacidad para el directorio: `tools/telegram/`.
- Usar `sk-<nombre>` tanto para el paquete como para la CLI: `sk-telegram`.
- Mantenerla independiente de las demás herramientas.
