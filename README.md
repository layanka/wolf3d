## Wolf3D PoC

First playable proof of concept for a Wolfenstein-3D-style raycaster in Python.

### Runtime

- Python: `3.12`
- Dependency manager: `uv`

Python 3.14 is available locally, but this PoC is pinned to 3.12 for stronger `pygame` compatibility and fewer wheel/build edge cases during early iteration.

### Setup

```bash
UV_CACHE_DIR=.uv-cache uv sync
```

### Run

```bash
UV_CACHE_DIR=.uv-cache uv run python main.py
```

### Controls

- `W/S` or `Up/Down`: move forward/backward
- `A/D`: strafe left/right
- `Left/Right` or `Q/E`: rotate
- `M`: toggle minimap
- `Esc`: quit

Expected visuals:
- Blue-gray floor/ceiling bands
- Vertical wall slices with depth shading
- Top-left minimap with a green player dot and facing direction line

### Smoke test

```bash
UV_CACHE_DIR=.uv-cache uv run python main.py --smoke-test
```
