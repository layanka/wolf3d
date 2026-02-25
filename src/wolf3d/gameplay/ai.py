from __future__ import annotations

import math

from src.wolf3d.contracts import EnemyType
from src.wolf3d.entities.models import EnemyState, PlayerState, ProjectileState
from src.wolf3d.gameplay.projectiles import build_enemy_projectile
from src.wolf3d.world.simulation import WorldSimulation

ENEMY_RADIUS = 0.12
PLAYER_COLLISION_RADIUS = 0.24


def update_enemies(
    player: PlayerState,
    enemies: list[EnemyState],
    enemy_defs: dict[str, EnemyType],
    world: WorldSimulation,
    dt: float,
) -> tuple[int, list[ProjectileState]]:
    """Advance enemy behavior and return melee damage plus spawned projectiles."""
    melee_damage = 0
    spawned_projectiles: list[ProjectileState] = []

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

        if not has_los or distance > spec.attack_range or enemy.attack_cooldown > 0.0:
            continue

        if behavior == "rush_melee":
            melee_damage += spec.attack_damage
            enemy.attack_cooldown = 0.85
            continue

        spread = _projectile_spread(enemy)
        projectile_speed = _projectile_speed(spec)
        projectile = build_enemy_projectile(
            x=enemy.x,
            y=enemy.y,
            target_x=player.x,
            target_y=player.y,
            speed=projectile_speed,
            damage=spec.attack_damage,
            max_range=spec.attack_range + 1.4,
            spread_radians=spread,
        )
        spawned_projectiles.append(projectile)
        enemy.attack_cooldown = _attack_cadence(spec)

    return melee_damage, spawned_projectiles


def _attack_cadence(spec: EnemyType) -> float:
    if spec.behavior == "boss_phase":
        return 0.52
    if spec.behavior == "aggressive_flank":
        return 0.62
    return 0.75


def _projectile_speed(spec: EnemyType) -> float:
    if spec.behavior == "boss_phase":
        return 8.2
    if spec.behavior == "aggressive_flank":
        return 7.3
    return 6.2


def _projectile_spread(enemy: EnemyState) -> float:
    return 0.04 * math.sin(enemy.behavior_phase * 3.2 + len(enemy.type_id))


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
