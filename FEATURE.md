# FEATURE.md

## Purpose
Living feature backlog for the full game (post-PoC), with sprint IDs, status, order, and playable acceptance criteria.

## Working Rules
- Each sprint should end in a playable checkpoint.
- Prefer one coherent commit per sprint.
- Update this file whenever a sprint is completed, split, or reprioritized.

## Current Baseline (Implemented)
- 3-level campaign runtime with objectives, doors, enemies, pickups, checkpoints.
- Weapons with ammo types, magazines/reload, recoil/spread model, crosshair feedback.
- Audio runtime lane (SFX + footsteps) with persistent volume/mute controls.
- Settings persistence (`saves/settings.json`) and quick-save persistence (`saves/quicksave.pkl`).
- Sprint movement, stamina/exhaustion, camera bob/FOV kick, minimap controls.

## Sprint Status Key
- `done`: implemented and committed.
- `next`: highest-priority next sprint.
- `planned`: not started.

## Feature Sprints

### Core Gameplay
- `FS-001` `done`: Magazine/reload model, reload UX, auto-reload-on-empty trigger.
  - Accept: weapons show mag/reserve, `R` reloads while alive, reload timing visible.
- `FS-002` `done`: Sprint polish (momentum + exhaustion lockout).
  - Accept: sprint ramps in/out, lockout at 0 stamina, unlock after recovery threshold.
- `FS-003` `done`: Movement/camera feel (head-bob, sprint FOV kick, hit kick).
  - Accept: camera motion aligns with movement/combat and remains stable.
- `FS-004` `done`: Accuracy model (movement/sprint/recoil bloom).
  - Accept: sustained fire and movement reduce non-shotgun precision.
- `FS-005` `done`: Crosshair readability (recoil expansion + reload color + hit/kill marker).
  - Accept: clear instant feedback for reload/hit/down.

### UX, HUD, and Guidance
- `FS-006` `done`: Objective nav HUD line + compass arrow + contextual door prompt.
  - Accept: player can orient toward objective without minimap.
- `FS-007` `done`: Perf HUD toggle (`F6`) with FPS/frame-time/counters.
  - Accept: overlay toggle persists and does not disturb gameplay.
- `FS-008` `done`: Runtime control polish (mouse sensitivity hotkeys + notices).
  - Accept: sensitivity tuning available in-session and persisted.

### Persistence and Session Flow
- `FS-009` `done`: Disk quick-save/load (`F5/F9`) and startup quickload flag.
  - Accept: save survives process restart; `--quickload` restores run.
- `FS-010` `done`: Settings persistence hardening + write throttling.
  - Accept: malformed settings do not crash startup; no excessive write bursts.
- `FS-011` `done`: Quick-save lifecycle tools (`F11` delete + in-memory clear).
  - Accept: delete action leaves no hidden restore source in same session.

### Audio and Feedback
- `FS-012` `done`: Runtime SFX integration (shoot/hit/down/door/steps).
  - Accept: combat/interaction movement sounds play in runtime shell.
- `FS-013` `done`: In-game audio controls (volume, mute) + persistence.
  - Accept: `9/0`, `F10` work and survive restart.

### Planned: Combat and AI Expansion
- `FS-014` `done`: Enemy reaction model (stagger, flinch windows, short suppression behavior).
  - Accept: hit enemies react differently by archetype; behavior is readable and fair.
- `FS-015` `done`: Enemy archetype depth pass (distinct attack timings, preferred ranges, path pressure).
  - Accept: guard/assault/hound/commander feel tactically distinct.
- `FS-016` `done`: Projectile/combat polish (impact VFX differentiation, near-miss cue, damage direction hint).
  - Accept: player can infer incoming threat direction and impact type.

### Planned: Weapons and Items
- `FS-017` `done`: Weapon personality pass (per-weapon recoil curves, reload interrupt policy, swap timings).
  - Accept: each weapon has unique handling profile without balance breaks.
- `FS-018` `done`: Secondary fire prototype for one weapon.
  - Accept: alternate mode implemented, documented, and balanced enough for playtest.
- `FS-019` `done`: Pickup economy pass (ammo/medkit drop tuning by difficulty + level).
  - Accept: resource flow avoids starvation and trivial abundance.

### Planned: Level and Content Pipeline
- `FS-020` `done`: Level scripting events (triggered spawns/locks/objective beats).
  - Accept: at least one scripted encounter per level.
- `FS-021` `next`: Story/briefing pass (consistent narrative arc and objective language).
  - Accept: briefings clearly communicate stakes and level intent.
- `FS-022` `planned`: Extended map set prep (3 production-ready levels with pacing pass).
  - Accept: each level has distinct route/encounter identity.

### Planned: Menus and Frontend Shell
- `FS-023` `planned`: Title/options shell (new run, continue, settings, controls).
  - Accept: no code-side flag requirement for common startup flows.
- `FS-024` `planned`: Pause/restart UX pass (clear state transitions, confirmations where needed).
  - Accept: no ambiguous key overlap and no accidental run loss.

### Planned: Stabilization and Release Readiness
- `FS-025` `planned`: Test harness foundation (`tests/`) for loader/runtime pure logic paths.
  - Accept: CI-style deterministic checks for settings/save/load/contracts.
- `FS-026` `planned`: Performance pass (hotspot profiling, selective optimization).
  - Accept: steady 60 FPS target on typical maps; bottlenecks documented.
- `FS-027` `planned`: Documentation/release pack (controls matrix, feature list, known limits).
  - Accept: repo is handoff-ready for new sessions/contributors.

## Execution Order
1. `FS-014` to `FS-016` (combat depth)
2. `FS-017` to `FS-019` (weapon/item tuning)
3. `FS-020` to `FS-022` (content/level pipeline)
4. `FS-023` to `FS-024` (shell UX)
5. `FS-025` to `FS-027` (stability/release)

## Resume Protocol
- Check latest `done` sprint ID.
- Start from the first `next`, or first `planned` if none marked `next`.
- After completion:
  - set sprint to `done`
  - mark following sprint `next`
  - add commit hash next to completed item.
