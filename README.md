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
- `Space`: open/close door in front of you
- `F` or left mouse click: shoot
- `M`: toggle minimap
- `Esc`: quit

Door behavior:
- Doors auto-close after a short delay.
- Doors stay open while you are in or near the doorway.
- Doors are rendered as a thin sliding slab with a darker frame and fixed side posts.

Expected visuals:
- Blue-gray floor/ceiling bands
- Vertical wall slices with depth shading
- Door faces rendered in warm amber/orange to distinguish from regular walls
- One enemy target rendered as a red sprite (occluded by walls/doors)
- Top-left minimap with a green player dot and facing direction line
- Door tiles shown in amber on the minimap (brighter when open)
- Enemy marker on minimap (red when alive, gray when down)
- Small center reticle appears when aiming at an interactable door

### Smoke test

```bash
UV_CACHE_DIR=.uv-cache uv run python main.py --smoke-test
```
