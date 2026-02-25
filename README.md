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
UV_CACHE_DIR=.uv-cache uv run python -m src.wolf3d.runtime_entry --quickload
```

Runtime shell data sources:
- `game_data/campaign.json`
- `game_data/levels/*.json`
- `game_data/maps/*.map`

### Controls

- `W/S` or `Up/Down`: move forward/backward
- `A/D`: strafe left/right
- `Left Shift`/`Right Shift`: sprint (consumes stamina, auto-recovers)
- `Left/Right` or `Q/E`: rotate
- `Tab`: toggle mouse-look and cursor capture
- `-` / `=`: decrease/increase mouse sensitivity
- `9` / `0`: decrease/increase audio volume
- `F10`: mute/unmute audio
- `F6`: toggle performance HUD (FPS/frame-time/counters)
- `Mouse wheel` or `[` `]`: cycle through unlocked weapons
- `Space`: open/close door in front of you
- `F` or left mouse click: shoot
- `G` or right mouse click: alt-fire shotgun slug (single-shell precision shot)
- `X`: interact with mission objectives (extraction, consoles, beacon)
- `C`: save a manual checkpoint (runtime shell)
- `F5`: quick-save checkpoint
- `F9`: quick-load checkpoint
- `F11`: delete disk quick-save file
- `P`: pause/resume gameplay
- `1/2/3/4`: switch weapon archetype (`pistol` / `smg` / `shotgun` / `autorifle`)
- `M`: toggle minimap
- `Z`: cycle minimap zoom levels
- `Enter`: dismiss level briefing / advance to next level after level clear (runtime shell)
- `R`: reload current weapon magazine (runtime shell)
- `R`: restore checkpoint / retry current level after death (runtime shell)
- `N`: restart campaign after final level completion (runtime shell)
- `F1/F2/F3`: set difficulty (`easy` / `normal` / `hard`) at runtime
- `H`: show/hide in-game controls help overlay
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
- Weapons now consume ammo by ammo type, with pickup and between-level ammo gains
- Weapons now use per-weapon magazines with timed reloads from shared reserves
- Triggering fire on an empty magazine now auto-starts reload if reserve ammo is available
- Defeated enemies drop ammo packs (shown as cyan dots on minimap)
- Defeated enemies also drop medkits (shown as green dots on minimap)
- Runtime auto-switches to another unlocked weapon when current ammo is empty
- Difficulty now scales incoming damage and ammo gains (drops/pickups/resupply)
- Manual checkpoints can be restored on death from the same level
- F5/F9 quick-save now persists to disk (`saves/quicksave.pkl`) and survives restarts
- F11 deletes `saves/quicksave.pkl` from inside the game runtime
- Runtime preferences persist to `saves/settings.json` (mouse sensitivity + minimap state/zoom)
- Runtime preferences also persist audio volume/mute state
- Runtime preferences also persist perf HUD visibility
- Runtime preferences also persist selected difficulty preset
- Sprint now ramps in/out smoothly and applies a short exhaustion lockout at zero stamina
- Camera now adds subtle movement head-bob, sprint FOV kick, and light hit-impact kick
- Non-shotgun weapons now lose accuracy while moving/sprinting and during sustained recoil bloom
- Crosshair now expands with recoil instability and turns blue while reloading
- Crosshair now shows hit and kill marker pulses on confirmed damage/down
- HUD now shows contextual prompts when a door is in front (`SPACE`)
- HUD now provides objective direction and distance guidance
- HUD now includes a top-screen objective compass arrow
- Enemy hit reactions now include short stagger/suppression windows by archetype
- Enemy archetypes now hold distinct preferred ranges and attack pressure/cadence patterns
- Projectile feedback now includes near-miss cue and directional damage indicators
- Weapon handling now differs by archetype (swap timing, recoil curve, spread multipliers, reload interrupt policy)
- Crosshair now turns red when an enemy is in direct line of fire
- HUD/briefing now display each level's campaign goal text (`win_condition`)
- Shotgun now supports alt-fire slug mode with higher precision/range and slower cadence
- Enemy loot economy now scales by difficulty and level, with chance-based ammo/medkit drops

Audio source and license notes:
- [assets/audio/CREDITS.md](/Users/philippe.lefebvre2/Code/testing1/assets/audio/CREDITS.md)

### Smoke test

```bash
UV_CACHE_DIR=.uv-cache uv run python poc_game.py --smoke-test
UV_CACHE_DIR=.uv-cache uv run python -m src.wolf3d.runtime_entry --smoke-test
```
