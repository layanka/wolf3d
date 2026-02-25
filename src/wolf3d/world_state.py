from __future__ import annotations

from dataclasses import dataclass

from .contracts import LevelSpec


@dataclass(frozen=True)
class WorldState:
    level_id: str
    spawn_x: float
    spawn_y: float
    spawn_angle: float
    enemy_spawn_count: int
    weapon_pickup_count: int


def build_world_state(level: LevelSpec) -> WorldState:
    spawn_x = float(level.spawn.get("x", 1.5))
    spawn_y = float(level.spawn.get("y", 1.5))
    spawn_angle = float(level.spawn.get("angle", 0.0))
    return WorldState(
        level_id=level.id,
        spawn_x=spawn_x,
        spawn_y=spawn_y,
        spawn_angle=spawn_angle,
        enemy_spawn_count=len(level.enemy_spawns),
        weapon_pickup_count=len(level.weapon_pickups),
    )
