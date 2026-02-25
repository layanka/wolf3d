from __future__ import annotations

import math

from src.wolf3d.entities.models import EnemyState, FireResult, PlayerState
from src.wolf3d.world.simulation import WorldSimulation

ENEMY_HIT_ANGLE = math.radians(4.0)


def normalize_angle(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def compute_enemy_shot_distance(
    player: PlayerState, enemy: EnemyState, wall_depth: float, shot_range: float
) -> float | None:
    if not enemy.alive:
        return None

    dx = enemy.x - player.x
    dy = enemy.y - player.y
    distance = math.hypot(dx, dy)
    if distance > shot_range:
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

    enemy_distance = compute_enemy_shot_distance(player, enemy, ray_hit.depth, shot_range=8.0)
    alive_before = enemy.alive
    hit_enemy = enemy_distance is not None
    if hit_enemy:
        enemy.health -= 1
        if enemy.health <= 0:
            enemy.alive = False

    if enemy_distance is not None:
        impact_distance = min(impact_distance, enemy_distance)

    enemy_down = alive_before and not enemy.alive
    return FireResult(True, hit_enemy, enemy_down, impact_distance, 0.24)


def attempt_fire_multi(
    cooldown_timer: float,
    player: PlayerState,
    world: WorldSimulation,
    enemies: list[EnemyState],
    damage: int = 1,
    max_range: float = 8.0,
    cooldown: float = 0.24,
) -> tuple[FireResult, EnemyState | None]:
    if cooldown_timer > 0.0:
        return FireResult(False, False, False, 0.0, cooldown_timer), None

    ray_hit = world.cast_ray(player.x, player.y, player.angle)
    impact_distance = ray_hit.depth
    target: EnemyState | None = None
    target_dist = float("inf")

    for enemy in enemies:
        enemy_distance = compute_enemy_shot_distance(player, enemy, ray_hit.depth, max_range)
        if enemy_distance is not None and enemy_distance < target_dist:
            target = enemy
            target_dist = enemy_distance

    hit_enemy = target is not None
    enemy_down = False
    if target is not None:
        alive_before = target.alive
        target.health -= damage
        if target.health <= 0:
            target.alive = False
        enemy_down = alive_before and not target.alive
        impact_distance = min(impact_distance, target_dist)

    return FireResult(True, hit_enemy, enemy_down, impact_distance, cooldown), target
