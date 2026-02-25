# Full Game Bootstrap

## Objective
Build a full Wolf3D-style game with:
- 3 levels
- multiple enemy archetypes
- multiple weapon archetypes
- data-driven content and clear module contracts

## Scope For Phase 1
1. Lock content schema and contracts.
2. Build a playable campaign flow (Level 1 -> Level 2 -> Level 3).
3. Integrate enemy and weapon type systems.
4. Keep `poc_game.py` as stable reference while the real game is built in `src/wolf3d`.

## Success Criteria
- Game boots through new entrypoint.
- Campaign data validates and loads.
- Level progression model is in place.
- Agent tasks can execute in parallel with minimal merge conflict.

## Active Architecture
- `src/wolf3d/contracts.py`: shared schemas.
- `src/wolf3d/content_loader.py`: content loading and validation.
- `src/wolf3d/entrypoint.py`: real-game startup shell.
- `game_data/*.json`: campaign, enemies, weapons.
- `game_data/levels/*.json`: level design payloads.
