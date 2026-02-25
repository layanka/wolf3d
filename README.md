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
UV_CACHE_DIR=.uv-cache uv run python poc_game.py
```

### Run Extracted Runtime (Real Game Shell)

```bash
UV_CACHE_DIR=.uv-cache uv run python -m src.wolf3d.runtime_entry
```

Runtime shell data sources:
- `game_data/campaign.json`
- `game_data/levels/*.json`
- `game_data/maps/*.map`

### Controls

- `W/S` or `Up/Down`: move forward/backward
- `A/D`: strafe left/right
- `Left/Right` or `Q/E`: rotate
- `Space`: open/close door in front of you
- `F` or left mouse click: shoot
- `X`: interact with mission objectives (extraction, consoles, beacon)
- `1/2/3/4`: switch weapon archetype (`pistol` / `smg` / `shotgun` / `autorifle`)
- `M`: toggle minimap
- `Enter`: dismiss level briefing / advance to next level after level clear (runtime shell)
- `R`: retry current level after death (runtime shell)
- `N`: restart campaign after final level completion (runtime shell)
- `Esc`: quit

Door behavior:
- Doors auto-close after a short delay.
- Doors stay open if you are inside the doorway tile.
- Doors are rendered as a thin sliding slab with a darker frame and fixed side posts.
- Weapon uses a hitscan model with a short-lived visual tracer and impact spark.
- Closed doors require explicit `Space` interaction to open.
- Closed doors fully block visibility and shots.

Expected visuals:
- Blue-gray floor/ceiling bands
- Vertical wall slices with depth shading
- Door faces rendered in warm amber/orange to distinguish from regular walls
- One enemy target rendered as a red sprite (occluded by walls/doors)
- Top-left minimap with a green player dot and facing direction line
- Door tiles shown in amber on the minimap (brighter when open)
- Enemy marker on minimap (red when alive, gray when down)
- Small center reticle appears when aiming at an interactable door
- Bottom-center weapon overlay with recoil and muzzle flash on fire
- File-based SFX (`OGG`) for shooting, hits, enemy down, door, and footsteps
- Footsteps are intentionally low-volume/subtle while moving
- Weapon pickups are shown as yellow dots on the minimap and unlock additional weapon keys
- Ranged enemies now fire visible projectiles that are blocked by walls/doors
- Player muzzle flash is now weapon-specific (pistol/smg/shotgun/autorifle)
- Incoming enemy rounds are shown as orange dots on the minimap
- Objective nodes are shown as cyan minimap markers
- Shotgun now uses a 5-pellet spread pattern
- Combat feedback includes a brief red damage flash and hit-confirm text
- HUD/runtime now tracks level+campaign time, kills, and shooting accuracy

Audio source and license notes:
- [assets/audio/CREDITS.md](/Users/philippe.lefebvre2/Code/testing1/assets/audio/CREDITS.md)

### Smoke test

```bash
UV_CACHE_DIR=.uv-cache uv run python poc_game.py --smoke-test
UV_CACHE_DIR=.uv-cache uv run python -m src.wolf3d.runtime_entry --smoke-test
```
