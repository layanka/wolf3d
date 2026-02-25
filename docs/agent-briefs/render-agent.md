# Render Agent Brief

## Scope
- Raycaster rendering path.
- Sprite composition, depth, HUD layering.
- Weapon and FX visuals.

## Constraints
- Do not mutate gameplay state in render functions.
- Input: immutable frame snapshot.

## Deliverables
- Render module split from monolithic runtime.
- Tests for projection math and sprite depth ordering.
