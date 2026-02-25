# Release Pack

## Scope

This repository contains:
- `poc_game.py`: original PoC entry point.
- `src/wolf3d/runtime_entry.py`: campaign runtime entry point.
- `game_data/`: campaign, levels, maps, enemies, weapons.

## Controls Matrix

| Context | Control | Action |
|---|---|---|
| Title shell | `N` / `Enter` | Start new campaign |
| Title shell | `C` | Continue from quick-save (if available) |
| Title shell | `1/2/3` | Set starting difficulty |
| Title shell | `H` | Toggle controls help |
| Runtime | `WASD` / arrows | Move/strafe |
| Runtime | `Shift` | Sprint |
| Runtime | `Q/E` or arrows | Turn |
| Runtime | `Tab` | Toggle mouse-look |
| Runtime | `F` / left click | Primary fire |
| Runtime | `G` / right click | Shotgun slug alt-fire |
| Runtime | `R` | Reload (alive) / retry (death) |
| Runtime | `Space` | Door interaction |
| Runtime | `X` | Objective interaction |
| Runtime | `M`, `Z` | Minimap toggle/zoom |
| Runtime | `P` | Pause/resume |
| Runtime paused | `Q` twice | Confirm quit |
| Runtime | `C`, `F5`, `F9`, `F11` | Checkpoint save/quick-save/quick-load/delete |
| Runtime | `F1/F2/F3` | Difficulty preset |
| Runtime | `9/0`, `F10` | Audio down/up, mute |
| Runtime | `F6` | Perf HUD |
| Runtime | `H` | Help overlay |
| Runtime | `Esc` | Pause/back |
| Campaign complete | `N` twice | Confirm full campaign restart |

## Feature Checklist

- 3-level campaign with objective modes (key/extract, consoles, commander/beacon).
- Weapon progression with pickups (`pistol`, `smg`, `shotgun`, `autorifle`).
- Per-weapon handling profile + shotgun secondary slug fire.
- Enemy archetype depth and projectile combat feedback.
- Door interaction model with explicit open requirement and auto-close behavior.
- Runtime audio with file-based SFX and subtle footsteps.
- Checkpoints (in-memory and disk quick-save) and persisted runtime settings.
- Title/options shell for new/continue flows.
- Scripted encounter triggers per level.
- Deterministic pytest suite for loader/runtime logic paths.

## Verification Commands

```bash
UV_CACHE_DIR=.uv-cache uv sync
UV_CACHE_DIR=.uv-cache uv run python -m src.wolf3d.runtime_entry
UV_CACHE_DIR=.uv-cache uv run python -m src.wolf3d.runtime_entry --smoke-test
UV_CACHE_DIR=.uv-cache uv run pytest -q
```

## Known Limits

- Visual style remains low-res flat-shaded; no texture mapping yet.
- Enemy navigation is lightweight and can show simplistic pursuit in tight corridors.
- Audio mixing is intentionally minimal (single SFX-focused layer).
- Save format uses pickle and is not guaranteed stable across major schema rewrites.
- No CI pipeline is configured yet (tests are local command-driven).

## Session Resume Pointers

- Sprint plan: `FEATURE.md`
- Multi-agent workflow/process notes: `PLAN.md`
- Runtime entry: `src/wolf3d/runtime_entry.py`
- Core gameplay loop: `src/wolf3d/runtime.py`
