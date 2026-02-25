# Lead-Agent Supervision Board

## Active Program
- Program: Full game production (3 levels, multiple enemies, multiple weapons)
- Supervisor: Ada
- Workflow basis: `PLAN.md`, section 6

## Parallel Lanes

1. Lane A - Render Agent
- Goal: extract render pipeline from PoC and expose frame-snapshot render API
- Inputs: `poc_game.py`, `src/wolf3d/contracts.py`
- Deliverables: `src/wolf3d/render/*`
- Status: READY

2. Lane B - World + IO Agent
- Goal: map loader + world queries + door mechanics on level JSON data
- Inputs: `game_data/levels/*.json`
- Deliverables: `src/wolf3d/world/*`, `src/wolf3d/io/*`
- Status: READY

3. Lane C - Gameplay + AI Agent
- Goal: weapon/enemy systems from archetype files, AI state machine shell
- Inputs: `game_data/enemies.json`, `game_data/weapons.json`
- Deliverables: `src/wolf3d/gameplay/*`, `src/wolf3d/entities/*`
- Status: READY

4. Lane D - Audio + UI Agent
- Goal: menu/HUD shell + robust file-based audio integration
- Inputs: `assets/audio/sfx/*`
- Deliverables: `src/wolf3d/audio/*`, `src/wolf3d/ui/*`
- Status: READY

5. Lane E - Story/Level/Gun/Enemy Design Agent
- Goal: narrative pacing, encounter design, balancing pass on archetypes
- Inputs: `game_data/*`, `docs/FULL_GAME_BOOTSTRAP.md`
- Deliverables: revised campaign/enemy/weapon/level data + design rationale doc
- Status: READY

## Integration Gates (Lead Agent)
1. All lane changes compile.
2. Content references validate (`real_game.py`).
3. No contract break in `src/wolf3d/contracts.py` without approval.
4. Smoke run of PoC still possible (`poc_game.py --smoke-test`) until migration complete.

## Current Immediate Execution Order
1. Lock contracts and content schema (now done).
2. Start lane B and C first (world + gameplay foundations).
3. Start lane A once world query API is stable.
4. Merge lane D and E continuously as data/UI/audio are low-conflict.
