from __future__ import annotations

import math

from src.wolf3d.entities.models import EnemyState, FireResult, PlayerState
from src.wolf3d.world.simulation import WorldSimulation

ENEMY_HIT_ANGLE = math.radians(4.0)
ENEMY_SHOOT_RANGE = 8.0
WEAPON_COOLDOWN = 0.24


def normalize_angle(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def compute_enemy_shot_distance(player: PlayerState, enemy: EnemyState, wall_depth: float) -> float | None:
    if not enemy.alive:
        return None

    dx = enemy.x - player.x
    dy = enemy.y - player.y
    distance = math.hypot(dx, dy)
    if distance > ENEMY_SHOOT_RANGE:
        return None

    enemy_angle = math.atan2(dy, dx)
    if abs(normalize_angle(enemy_angle - player.angle)) > ENEMY_HIT_ANGLE:
        return None

    if distance >= wall_depth - 0.05:
        return None
    return distance


def attempt_fire(cooldown_timer: float, player: PlayerState, world: WorldSimulation, enemy: EnemyState) -> FireResult:
    if cooldown_timer > 0.0:
        return FireResult(False, False, False, 0.0, cooldown_timer)

    ray_hit = world.cast_ray(player.x, player.y, player.angle)
    impact_distance = ray_hit.depth

    enemy_distance = compute_enemy_shot_distance(player, enemy, ray_hit.depth)
    alive_before = enemy.alive
    hit_enemy = enemy_distance is not None
    if hit_enemy:
        enemy.health -= 1
        if enemy.health <= 0:
            enemy.alive = False

    if enemy_distance is not None:
        impact_distance = min(impact_distance, enemy_distance)

    enemy_down = alive_before and not enemy.alive
    return FireResult(True, hit_enemy, enemy_down, impact_distance, WEAPON_COOLDOWN)
