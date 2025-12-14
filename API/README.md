# CAD Renderer API

This project exposes a simple HTTP API that takes a CAD-style JSON structure
plus optional filters and returns a **base64-encoded PNG** image of the
filtered view.

It is designed to be called by tools like **OpenAI Custom GPTs**.

---

## Endpoints

- `GET /health` — health check
- `POST /render` — render filtered CAD JSON to base64 PNG

### Request body (POST /render)

```json
{
  "data": {
    "entities": [
      {
        "id": 1,
        "type": "LINE",
        "layer": "A-WALL",
        "vertices": [[0, 0], [10, 0]]
      }
    ]
  },
  "filters": {
    "layers": ["A-WALL"],
    "types": ["LINE"],
    "ids": ["1"]
  },
  "show_background": true
}
