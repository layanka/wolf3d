from __future__ import annotations

import math

from src.wolf3d.entities.models import EnemyState, FireResult, PlayerState
from src.wolf3d.world.simulation import WorldSimulation

ENEMY_HIT_ANGLE = math.radians(4.0)


def normalize_angle(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def compute_enemy_shot_distance(
    player: PlayerState,
    enemy: EnemyState,
    wall_depth: float,
    shot_range: float,
    shot_angle: float | None = None,
) -> float | None:
    if not enemy.alive:
        return None

    dx = enemy.x - player.x
    dy = enemy.y - player.y
    distance = math.hypot(dx, dy)
    if distance > shot_range:
        return None

    enemy_angle = math.atan2(dy, dx)
    view_angle = player.angle if shot_angle is None else shot_angle
    if abs(normalize_angle(enemy_angle - view_angle)) > ENEMY_HIT_ANGLE:
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
    ray_offsets: tuple[float, ...] = (0.0,),
) -> tuple[FireResult, EnemyState | None]:
    if cooldown_timer > 0.0:
        return FireResult(False, False, False, 0.0, cooldown_timer), None

    impact_distance = float("inf")
    target: EnemyState | None = None
    hit_enemy = False
    enemy_down = False
    hit_targets: set[int] = set()

    for offset in ray_offsets:
        ray_angle = player.angle + offset
        ray_hit = world.cast_ray(player.x, player.y, ray_angle)
        impact_distance = min(impact_distance, ray_hit.depth)
        nearest_target: EnemyState | None = None
        nearest_distance = float("inf")

        for enemy in enemies:
            if id(enemy) in hit_targets:
                continue

            enemy_distance = compute_enemy_shot_distance(player, enemy, ray_hit.depth, max_range, shot_angle=ray_angle)
            if enemy_distance is not None and enemy_distance < nearest_distance:
                nearest_target = enemy
                nearest_distance = enemy_distance

        if nearest_target is None:
            continue

        hit_targets.add(id(nearest_target))
        hit_enemy = True
        target = nearest_target
        alive_before = nearest_target.alive
        nearest_target.health -= damage
        if nearest_target.health <= 0:
            nearest_target.alive = False
        enemy_down = enemy_down or (alive_before and not nearest_target.alive)
        impact_distance = min(impact_distance, nearest_distance)

    if impact_distance == float("inf"):
        impact_distance = 0.0

    return FireResult(True, hit_enemy, enemy_down, impact_distance, cooldown), target
