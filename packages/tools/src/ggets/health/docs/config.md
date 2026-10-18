# Health configuration

JSON section: `health`.

| Field | Required | Default | Purpose |
| --- | --- | --- | --- |
| `label` | No | `tools` | Instance label returned by health checks. |

## Minimal JSON (required fields only)

```json
{
  "health": {}
}
```

## Effective configuration (with defaults)

```json
{
  "health": {
    "label": "tools"
  }
}
```
