from __future__ import annotations

import math

from src.wolf3d.entities.models import PlayerState, ProjectileState
from src.wolf3d.world.simulation import WorldSimulation

PROJECTILE_RADIUS = 0.03
PLAYER_HIT_RADIUS = 0.18


def update_projectiles(
    world: WorldSimulation,
    player: PlayerState,
    projectiles: list[ProjectileState],
    dt: float,
) -> tuple[list[ProjectileState], int]:
    """Advance projectiles and return survivors plus damage applied to player."""
    survivors: list[ProjectileState] = []
    damage_to_player = 0

    for projectile in projectiles:
        travel = projectile.speed * dt
        if travel <= 1e-6:
            survivors.append(projectile)
            continue

        steps = max(1, int(travel / 0.06) + 1)
        step_dist = travel / steps
        alive = True

        for _ in range(steps):
            projectile.x += projectile.dir_x * step_dist
            projectile.y += projectile.dir_y * step_dist
            projectile.remaining_range -= step_dist

            if projectile.remaining_range <= 0.0:
                alive = False
                break

            if world.is_blocked_with_radius(projectile.x, projectile.y, PROJECTILE_RADIUS):
                alive = False
                break

            dx = projectile.x - player.x
            dy = projectile.y - player.y
            if dx * dx + dy * dy <= PLAYER_HIT_RADIUS * PLAYER_HIT_RADIUS:
                damage_to_player += projectile.damage
                alive = False
                break

        if alive:
            survivors.append(projectile)

    return survivors, damage_to_player


def build_enemy_projectile(
    x: float,
    y: float,
    target_x: float,
    target_y: float,
    speed: float,
    damage: int,
    max_range: float,
    spread_radians: float,
) -> ProjectileState:
    dx = target_x - x
    dy = target_y - y
    length = math.hypot(dx, dy)
    if length <= 1e-6:
        dx, dy = 1.0, 0.0
        length = 1.0

    dir_x = dx / length
    dir_y = dy / length

    if abs(spread_radians) > 1e-6:
        cos_a = math.cos(spread_radians)
        sin_a = math.sin(spread_radians)
        rot_x = dir_x * cos_a - dir_y * sin_a
        rot_y = dir_x * sin_a + dir_y * cos_a
        dir_x, dir_y = rot_x, rot_y

    return ProjectileState(
        x=x,
        y=y,
        dir_x=dir_x,
        dir_y=dir_y,
        speed=speed,
        damage=damage,
        remaining_range=max_range,
    )
