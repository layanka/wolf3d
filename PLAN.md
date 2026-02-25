# Wolf3D Python Project Plan (Lead-Agent Workflow)

## 1. Purpose

Build a Wolfenstein-3D-style game in Python with a clean architecture, iterative playable checkpoints, and a lead-agent workflow where multiple coding agents can work in parallel by module.

This file is the source of truth for project direction and resume state.

## 2. Current Snapshot (Resume Anchor)

- Date: 2026-02-24
- Branch: `main`
- Last committed hash: `086ee85`
- Local uncommitted changes currently present: `poc_game.py`, `README.md`
- Remote: `origin` -> `https://github.com/layanka/wolf3d.git`

Recent committed checkpoints:
1. `086ee85` weapon overlay + recoil + flash + cooldown
2. `499c707` basic enemy + shooting combat loop
3. `8648e4f` narrower centered door opening
4. `c2740da` interactive doors + safety checks
5. `afebc7a` initial raycasting PoC

## 3. Product Direction

### 3.1 Core Gameplay Target

- Fast first-person movement in a grid map
- Raycasted walls and doors
- Hitscan combat with enemies
- Retro visual and audio feel

### 3.2 Engineering Constraints

- Python + `pygame`
- Keep frame time stable (target 60 FPS, acceptable 30 FPS)
- Keep architecture modular as feature count grows
- Prefer readable, testable systems over clever shortcuts

## 4. Target Architecture (Planned Refactor from Current Single-File PoC)

Planned package layout:

1. `src/engine/core/`
- game loop
- timing
- game state orchestration

2. `src/engine/render/`
- raycaster
- sprite rendering
- HUD/weapon overlay rendering

3. `src/engine/world/`
- map representation
- door logic
- collision queries

4. `src/engine/entities/`
- player
- enemies
- future pickups/projectiles

5. `src/engine/gameplay/`
- weapon firing logic
- hit resolution
- AI state updates

6. `src/engine/audio/`
- audio manager
- SFX loading and playback

7. `src/engine/io/`
- config
- save/load
- level format parsing

8. `tests/`
- unit tests for world/gameplay math
- deterministic smoke/sim tests

## 5. Milestone Plan (Playable Checkpoints)

Each milestone must end with a playtest request to Philippe before moving on.

1. `M1` Raycasting movement baseline (done)
2. `M2` Doors: interaction + animation + safety + auto-close (done)
3. `M3` Combat baseline: enemy + hitscan + weapon feedback + tracer (in progress; uncommitted working tree)
4. `M4` Enemy behavior upgrade
- patrol/chase/attack state machine
- line-of-sight and attack timing
5. `M5` Content and level pipeline
- load maps/enemies/doors from data file
- at least 2 playable levels
6. `M6` UX polish
- title/pause/restart
- score/health/ammo HUD
- better feedback loops
7. `M7` Stabilization
- profiling + hotspot cleanup
- regression tests
- release checklist

## 6. Lead-Agent Workflow

## 6.1 Roles

1. Lead agent (Ada)
- owns architecture, contracts, integration, review quality bar
- resolves conflicts between modules
- controls merge gates

2. Module agents
- each works in a bounded module and branch/worktree
- must satisfy contract + tests for that module

## 6.2 Parallel Work Split (Default)

1. Agent A: `render`
2. Agent B: `world + io`
3. Agent C: `entities + gameplay`
4. Agent D: `audio + ui`
5. Lead agent: integration + performance + review

## 6.3 Branch/Worktree Convention

- Keep `main` stable and playable.
- One feature branch per agent task.
- Recommended branch naming:
  - `codex/render-<task>`
  - `codex/world-<task>`
  - `codex/gameplay-<task>`
  - `codex/audio-ui-<task>`

Worktree example:

```bash
git worktree add ../wolf3d-render codex/render-sprite-pass
git worktree add ../wolf3d-world codex/world-map-loader
```

## 6.4 Merge Rules

- PR/squash only after:
  1. module tests pass
  2. smoke run passes
  3. no contract breaks
  4. lead-agent review complete

## 7. System Contracts (Initial)

These interfaces should remain stable while modules evolve:

1. World query contract
- `is_blocked(x, y) -> bool`
- `cast_ray(px, py, angle) -> hit`
- `update_doors(dt, player_state)`

2. Combat contract
- `attempt_fire(player_state, world_state, enemy_state) -> fire_result`
- `fire_result` includes: fired, hit_enemy, enemy_down, impact_distance

3. Render contract
- input: immutable frame snapshot (`player`, `world`, `enemies`, `fx`)
- output: frame draw only (no game-state mutation)

4. Audio contract
- `play(event_name)` only; no direct gameplay logic in audio layer

## 8. Quality Gates per Checkpoint

Required before advancing:

1. Runtime
- `UV_CACHE_DIR=.uv-cache uv run python poc_game.py --smoke-test`

2. Playability
- manual test by Philippe with explicit feedback

3. Repository hygiene
- commit message describes one coherent checkpoint

## 9. Session Resume Protocol

When starting a new session:

1. Read this file (`PLAN.md`) first.
2. Run:
```bash
git status --short
git log --oneline -n 10
```
3. If working tree is dirty, summarize uncommitted scope before editing.
4. Continue from the next unchecked milestone item.
5. Stop at the next playable checkpoint and ask Philippe for feedback.

## 10. Immediate Next Action

Finalize current uncommitted `M3` combat enhancements (tracer/audio tweaks), run smoke test, ask Philippe for playtest feedback, then commit as one checkpoint if approved.
