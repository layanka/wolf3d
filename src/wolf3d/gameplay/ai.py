from __future__ import annotations

import math

from src.wolf3d.contracts import EnemyType
from src.wolf3d.entities.models import EnemyState, PlayerState
from src.wolf3d.world.simulation import WorldSimulation

ENEMY_RADIUS = 0.12
PLAYER_COLLISION_RADIUS = 0.24


def update_enemies(
    player: PlayerState,
    enemies: list[EnemyState],
    enemy_defs: dict[str, EnemyType],
    world: WorldSimulation,
    dt: float,
) -> int:
    """Advance enemy movement/attacks and return total damage dealt to player."""
    total_damage = 0
    for enemy in enemies:
        if not enemy.alive:
            continue

        enemy.attack_cooldown = max(0.0, enemy.attack_cooldown - dt)
        enemy.behavior_phase += dt
        spec = enemy_defs[enemy.type_id]

        dx = player.x - enemy.x
        dy = player.y - enemy.y
        distance = math.hypot(dx, dy)
        if distance <= 1e-6:
            continue

        toward_x = dx / distance
        toward_y = dy / distance
        has_los = _has_line_of_sight(world, enemy.x, enemy.y, player.x, player.y, distance)

        behavior = spec.behavior
        if behavior == "rush_melee":
            if has_los and distance > spec.attack_range * 0.75:
                _move_enemy(world, player, enemy, toward_x, toward_y, spec.move_speed * 1.15, dt)
        elif behavior == "aggressive_flank":
            if has_los:
                strafe_sign = 1.0 if math.sin(enemy.behavior_phase * 1.4) >= 0.0 else -1.0
                flank_x = -toward_y * strafe_sign
                flank_y = toward_x * strafe_sign
                push = 1.0 if distance > spec.attack_range * 0.85 else 0.2
                move_x = toward_x * push + flank_x * 0.85
                move_y = toward_y * push + flank_y * 0.85
                _move_enemy(world, player, enemy, move_x, move_y, spec.move_speed, dt)
        elif behavior == "boss_phase":
            if has_los:
                if distance > spec.attack_range * 0.8:
                    _move_enemy(world, player, enemy, toward_x, toward_y, spec.move_speed * 0.9, dt)
                elif distance < 3.0:
                    _move_enemy(world, player, enemy, -toward_x, -toward_y, spec.move_speed * 0.75, dt)
                else:
                    strafe = 1.0 if math.sin(enemy.behavior_phase) >= 0.0 else -1.0
                    _move_enemy(world, player, enemy, -toward_y * strafe, toward_x * strafe, spec.move_speed * 0.6, dt)
        else:  # patrol_chase_shoot and unknown defaults
            if has_los and distance > spec.attack_range * 0.9:
                _move_enemy(world, player, enemy, toward_x, toward_y, spec.move_speed, dt)

        if has_los and distance <= spec.attack_range and enemy.attack_cooldown <= 0.0:
            total_damage += spec.attack_damage
            # Slight cadence variation keeps fights less robotic.
            enemy.attack_cooldown = 0.7 + (len(spec.id) % 3) * 0.1

    return total_damage


def _has_line_of_sight(world: WorldSimulation, x0: float, y0: float, x1: float, y1: float, distance: float) -> bool:
    angle = math.atan2(y1 - y0, x1 - x0)
    hit = world.cast_ray(x0, y0, angle, max_depth=distance + 0.2)
    return hit.depth >= distance - 0.12


def _move_enemy(
    world: WorldSimulation,
    player: PlayerState,
    enemy: EnemyState,
    dir_x: float,
    dir_y: float,
    speed: float,
    dt: float,
) -> None:
    norm = math.hypot(dir_x, dir_y)
    if norm <= 1e-6:
        return
    dir_x /= norm
    dir_y /= norm

    step = speed * dt
    candidate_x = enemy.x + dir_x * step
    candidate_y = enemy.y + dir_y * step

    if world.is_blocked_with_radius(candidate_x, enemy.y, ENEMY_RADIUS):
        candidate_x = enemy.x
    if world.is_blocked_with_radius(candidate_x, candidate_y, ENEMY_RADIUS):
        candidate_y = enemy.y

    if (candidate_x - player.x) ** 2 + (candidate_y - player.y) ** 2 < PLAYER_COLLISION_RADIUS**2:
        return

    enemy.x = candidate_x
    enemy.y = candidate_y
