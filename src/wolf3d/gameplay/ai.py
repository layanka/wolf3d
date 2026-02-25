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
        enemy.stagger_timer = max(0.0, enemy.stagger_timer - dt)
        enemy.suppression_timer = max(0.0, enemy.suppression_timer - dt)
        enemy.behavior_phase += dt
        spec = enemy_defs[enemy.type_id]
        _apply_hit_reaction(enemy, spec)

        dx = player.x - enemy.x
        dy = player.y - enemy.y
        distance = math.hypot(dx, dy)
        if distance <= 1e-6:
            continue

        toward_x = dx / distance
        toward_y = dy / distance
        has_los = _has_line_of_sight(world, enemy.x, enemy.y, player.x, player.y, distance)

        if enemy.stagger_timer > 0.0:
            continue

        behavior = spec.behavior
        preferred_range = _preferred_range(spec)
        movement_mult = 0.75 if enemy.suppression_timer > 0.0 else 1.0
        if behavior == "rush_melee":
            if has_los and distance > preferred_range:
                charge = min(1.45, 1.1 + max(0.0, distance - preferred_range) * 0.08)
                _move_enemy(world, player, enemy, toward_x, toward_y, spec.move_speed * charge * movement_mult, dt)
        elif behavior == "aggressive_flank":
            if has_los:
                strafe_sign = 1.0 if math.sin(enemy.behavior_phase * 1.4) >= 0.0 else -1.0
                flank_x = -toward_y * strafe_sign
                flank_y = toward_x * strafe_sign
                push = max(0.25, min(1.25, 0.75 + (distance - preferred_range) * 0.22))
                move_x = toward_x * push + flank_x * 0.85
                move_y = toward_y * push + flank_y * 0.85
                _move_enemy(world, player, enemy, move_x, move_y, spec.move_speed * 1.05 * movement_mult, dt)
        elif behavior == "boss_phase":
            if has_los:
                if distance > preferred_range + 1.0:
                    _move_enemy(world, player, enemy, toward_x, toward_y, spec.move_speed * 1.0 * movement_mult, dt)
                elif distance < preferred_range - 1.8:
                    _move_enemy(world, player, enemy, -toward_x, -toward_y, spec.move_speed * 0.82 * movement_mult, dt)
                else:
                    strafe = 1.0 if math.sin(enemy.behavior_phase) >= 0.0 else -1.0
                    forward_pulse = 0.28 if math.sin(enemy.behavior_phase * 2.2) > 0.65 else 0.0
                    _move_enemy(
                        world,
                        player,
                        enemy,
                        -toward_y * strafe + toward_x * forward_pulse,
                        toward_x * strafe + toward_y * forward_pulse,
                        spec.move_speed * 0.66 * movement_mult,
                        dt,
                    )
        else:  # patrol_chase_shoot and unknown defaults
            if has_los:
                if distance > preferred_range + 0.6:
                    _move_enemy(world, player, enemy, toward_x, toward_y, spec.move_speed * 0.92 * movement_mult, dt)
                elif distance < preferred_range - 0.8:
                    _move_enemy(world, player, enemy, -toward_x, -toward_y, spec.move_speed * 0.78 * movement_mult, dt)
                elif abs(math.sin(enemy.behavior_phase * 0.8)) > 0.55:
                    strafe_sign = 1.0 if math.sin(enemy.behavior_phase * 1.6) >= 0.0 else -1.0
                    _move_enemy(
                        world,
                        player,
                        enemy,
                        -toward_y * strafe_sign,
                        toward_x * strafe_sign,
                        spec.move_speed * 0.42 * movement_mult,
                        dt,
                    )

        if enemy.suppression_timer > 0.0 and behavior != "rush_melee":
            if has_los and distance < spec.attack_range * 0.95:
                _move_enemy(world, player, enemy, -toward_x, -toward_y, spec.move_speed * 0.45, dt)
            continue

        if not has_los or distance > spec.attack_range or enemy.attack_cooldown > 0.0:
            continue

        if behavior == "rush_melee":
            melee_damage += spec.attack_damage
            enemy.attack_cooldown = _melee_cadence(spec, distance, preferred_range)
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
        enemy.attack_cooldown = _attack_cadence(spec, enemy, distance, preferred_range)

    return melee_damage, spawned_projectiles


def _apply_hit_reaction(enemy: EnemyState, spec: EnemyType) -> None:
    if enemy.last_health_snapshot < 0:
        enemy.last_health_snapshot = enemy.health
        return
    if enemy.health >= enemy.last_health_snapshot:
        enemy.last_health_snapshot = enemy.health
        return

    if spec.behavior == "rush_melee":
        enemy.stagger_timer = max(enemy.stagger_timer, 0.08)
        enemy.attack_cooldown = max(enemy.attack_cooldown, 0.18)
    elif spec.behavior == "aggressive_flank":
        enemy.stagger_timer = max(enemy.stagger_timer, 0.12)
        enemy.suppression_timer = max(enemy.suppression_timer, 0.32)
        enemy.attack_cooldown = max(enemy.attack_cooldown, 0.28)
    elif spec.behavior == "boss_phase":
        enemy.stagger_timer = max(enemy.stagger_timer, 0.06)
        enemy.suppression_timer = max(enemy.suppression_timer, 0.18)
        enemy.attack_cooldown = max(enemy.attack_cooldown, 0.16)
    else:
        enemy.stagger_timer = max(enemy.stagger_timer, 0.1)
        enemy.suppression_timer = max(enemy.suppression_timer, 0.25)
        enemy.attack_cooldown = max(enemy.attack_cooldown, 0.24)

    enemy.last_health_snapshot = enemy.health

def _preferred_range(spec: EnemyType) -> float:
    if spec.behavior == "rush_melee":
        return max(0.75, spec.attack_range * 0.85)
    if spec.behavior == "aggressive_flank":
        return max(2.8, spec.attack_range * 0.56)
    if spec.behavior == "boss_phase":
        return max(5.6, spec.attack_range * 0.72)
    return max(3.8, spec.attack_range * 0.78)


def _attack_cadence(spec: EnemyType, enemy: EnemyState, distance: float, preferred_range: float) -> float:
    if spec.behavior == "boss_phase":
        burst = 0.12 if math.sin(enemy.behavior_phase * 2.3) > 0.7 else 0.0
        range_penalty = 0.08 if distance < preferred_range - 1.0 else 0.0
        return max(0.34, 0.5 - burst + range_penalty)
    if spec.behavior == "aggressive_flank":
        pressure_bonus = 0.08 if distance > preferred_range + 1.2 else 0.0
        return max(0.5, 0.64 - pressure_bonus)
    return 0.88


def _melee_cadence(spec: EnemyType, distance: float, preferred_range: float) -> float:
    if spec.behavior != "rush_melee":
        return 0.9
    if distance > preferred_range + 0.4:
        return 0.68
    return 0.82


def _projectile_speed(spec: EnemyType) -> float:
    if spec.behavior == "boss_phase":
        return 8.4
    if spec.behavior == "aggressive_flank":
        return 7.5
    return 5.9


def _projectile_spread(enemy: EnemyState) -> float:
    base = 0.03
    if enemy.type_id == "assault":
        base = 0.045
    elif enemy.type_id == "commander":
        base = 0.035
    return base * math.sin(enemy.behavior_phase * 3.2 + len(enemy.type_id))


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
