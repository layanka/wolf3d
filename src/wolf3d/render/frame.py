from __future__ import annotations

from dataclasses import dataclass

from src.wolf3d.entities.models import EnemyState, PlayerState
from src.wolf3d.world.simulation import WorldSimulation


@dataclass(frozen=True)
class FrameSnapshot:
    player_x: float
    player_y: float
    player_angle: float
    enemy_alive: bool
    enemy_health: int
    weapon_cooldown: float
    door_in_front: bool


def build_frame_snapshot(
    player: PlayerState,
    enemy: EnemyState,
    world: WorldSimulation,
    weapon_cooldown: float,
) -> FrameSnapshot:
    return FrameSnapshot(
        player_x=player.x,
        player_y=player.y,
        player_angle=player.angle,
        enemy_alive=enemy.alive,
        enemy_health=enemy.health,
        weapon_cooldown=weapon_cooldown,
        door_in_front=world.find_door_in_front(player) is not None,
    )
