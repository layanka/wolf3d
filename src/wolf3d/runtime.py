from __future__ import annotations

import math
import os
from pathlib import Path

import pygame

from src.wolf3d.audio.manager import route_simulation_audio_events
from src.wolf3d.content_loader import (
    load_campaign,
    load_enemy_types,
    load_level_map,
    load_level_specs,
    load_weapon_types,
    validate_cross_refs,
)
from src.wolf3d.entities.models import EnemyState, PlayerState, ProjectileState
from src.wolf3d.gameplay.ai import update_enemies
from src.wolf3d.gameplay.combat import attempt_fire_multi, normalize_angle
from src.wolf3d.gameplay.projectiles import update_projectiles
from src.wolf3d.render.frame import build_frame_snapshot
from src.wolf3d.ui.hud import format_hud_lines
from src.wolf3d.world.simulation import WorldSimulation


def render_enemies(
    surface: pygame.Surface,
    enemies: list[EnemyState],
    player: PlayerState,
    fov: float,
    depth_buffer: list[float],
) -> None:
    w, h = surface.get_width(), surface.get_height()
    for enemy in enemies:
        if not enemy.alive:
            continue

        dx = enemy.x - player.x
        dy = enemy.y - player.y
        distance = math.hypot(dx, dy)
        if distance <= 0.05:
            continue

        angle = normalize_angle(math.atan2(dy, dx) - player.angle)
        if abs(angle) > fov * 0.65:
            continue

        screen_x = int((angle / fov + 0.5) * w)
        sprite_h = max(8, min(int(h / distance), h))
        sprite_w = max(4, sprite_h // 2)
        top = (h - sprite_h) // 2
        bottom = top + sprite_h
        left = screen_x - sprite_w // 2
        right = left + sprite_w

        intensity = max(45, int(230 / (1.0 + distance * 0.18)))
        color = (intensity, max(20, intensity // 4), max(20, intensity // 4))
        for col in range(max(0, left), min(w, right)):
            if distance < depth_buffer[col]:
                pygame.draw.line(surface, color, (col, top), (col, bottom))


def render_projectiles(
    surface: pygame.Surface,
    player: PlayerState,
    projectiles: list[ProjectileState],
    fov: float,
    depth_buffer: list[float],
) -> None:
    w, h = surface.get_width(), surface.get_height()
    for projectile in projectiles:
        dx = projectile.x - player.x
        dy = projectile.y - player.y
        distance = math.hypot(dx, dy)
        if distance <= 0.08:
            continue

        angle = normalize_angle(math.atan2(dy, dx) - player.angle)
        if abs(angle) > fov * 0.6:
            continue

        screen_x = int((angle / fov + 0.5) * w)
        if screen_x < 0 or screen_x >= w or distance >= depth_buffer[screen_x]:
            continue

        size = max(1, min(5, int(7 / (distance + 0.2))))
        y = h // 2
        color = (250, 130, 70)
        pygame.draw.circle(surface, color, (screen_x, y), size)


def draw_weapon_vfx(surface: pygame.Surface, weapon_id: str, timer: float) -> None:
    if timer <= 0.0:
        return

    cx, cy = surface.get_width() // 2, surface.get_height() // 2
    if weapon_id == "shotgun":
        color = (255, 185, 90)
        radius = 16
        thickness = 3
    elif weapon_id == "smg":
        color = (180, 225, 255)
        radius = 9
        thickness = 1
    elif weapon_id == "autorifle":
        color = (240, 230, 120)
        radius = 12
        thickness = 2
    else:
        color = (245, 245, 235)
        radius = 10
        thickness = 2

    pygame.draw.circle(surface, color, (cx, cy), radius, thickness)
    pygame.draw.line(surface, color, (cx - radius + 1, cy), (cx + radius - 1, cy), 1)


def run_runtime(smoke_test: bool = False, data_root: Path | None = None) -> None:
    if smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    if data_root is None:
        data_root = Path(__file__).resolve().parents[2] / "game_data"

    campaign = load_campaign(data_root)
    enemy_types = {e.id: e for e in load_enemy_types(data_root)}
    level_specs = {l.id: l for l in load_level_specs(data_root)}
    weapon_types = load_weapon_types(data_root)
    validate_cross_refs(campaign, list(level_specs.values()), list(enemy_types.values()), weapon_types)
    weapons_by_id = {weapon.id: weapon for weapon in weapon_types}
    weapon_cycle = [w.id for w in weapon_types]

    pygame.init()
    screen_w, screen_h = 960, 600
    internal_w, internal_h = 320, 200
    screen = pygame.display.set_mode((screen_w, screen_h))
    surface = pygame.Surface((internal_w, internal_h))
    font = pygame.font.Font(None, 18)
    clock = pygame.time.Clock()
    pygame.display.set_caption("Wolf3D Real Runtime (Campaign Shell)")

    fov = math.radians(60)
    show_minimap = True
    shot_cooldown = 0.0
    current_weapon_idx = 0
    unlocked_weapons = {weapon_cycle[0]}
    show_briefing = True
    player_dead = False
    active_projectiles: list[ProjectileState] = []
    weapon_fx_timer = 0.0
    weapon_fx_id = weapon_cycle[0]

    level_idx = 0

    def load_level_state(index: int) -> tuple[WorldSimulation, PlayerState, list[EnemyState], list[dict[str, float | str]], str]:
        campaign_level = campaign[index]
        spec = level_specs[campaign_level.id]
        tile_map = load_level_map(data_root, spec)
        world = WorldSimulation(tile_map)
        spawn = spec.spawn
        player = PlayerState(x=float(spawn.get("x", 1.5)), y=float(spawn.get("y", 1.5)), angle=float(spawn.get("angle", 0.0)))
        enemies: list[EnemyState] = []
        for spawn_enemy in spec.enemy_spawns:
            enemy_type = enemy_types[spawn_enemy.type]
            enemies.append(
                EnemyState(
                    type_id=enemy_type.id,
                    x=spawn_enemy.x,
                    y=spawn_enemy.y,
                    health=enemy_type.health,
                    alive=True,
                )
            )
        pickups: list[dict[str, float | str]] = []
        for pickup in spec.weapon_pickups:
            pickups.append({"type": str(pickup["type"]), "x": float(pickup["x"]), "y": float(pickup["y"])})
        return world, player, enemies, pickups, campaign_level.title

    world, player, enemies, pickups, level_title = load_level_state(level_idx)

    running = True
    frames = 0
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        frames += 1
        fire_requested = False
        next_level_requested = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:
                    show_minimap = not show_minimap
                elif event.key == pygame.K_SPACE:
                    if not show_briefing and not player_dead:
                        world.toggle_door_in_front(player)
                elif event.key == pygame.K_f:
                    fire_requested = True
                elif event.key == pygame.K_RETURN:
                    if show_briefing:
                        show_briefing = False
                    else:
                        next_level_requested = True
                elif event.key == pygame.K_1:
                    current_weapon_idx = 0
                elif event.key == pygame.K_2 and len(weapon_cycle) >= 2 and weapon_cycle[1] in unlocked_weapons:
                    current_weapon_idx = 1
                elif event.key == pygame.K_3 and len(weapon_cycle) >= 3 and weapon_cycle[2] in unlocked_weapons:
                    current_weapon_idx = 2
                elif event.key == pygame.K_4 and len(weapon_cycle) >= 4 and weapon_cycle[3] in unlocked_weapons:
                    current_weapon_idx = 3
                elif event.key == pygame.K_r and player_dead:
                    world, player, enemies, pickups, level_title = load_level_state(level_idx)
                    shot_cooldown = 0.0
                    current_weapon_idx = 0
                    show_briefing = True
                    player_dead = False
                    active_projectiles.clear()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                fire_requested = True

        keys = pygame.key.get_pressed()
        forward = (float(keys[pygame.K_w]) - float(keys[pygame.K_s])) + (
            float(keys[pygame.K_UP]) - float(keys[pygame.K_DOWN])
        )
        strafe = float(keys[pygame.K_d]) - float(keys[pygame.K_a])
        turn = float(keys[pygame.K_RIGHT]) - float(keys[pygame.K_LEFT])
        if keys[pygame.K_q]:
            turn -= 1.0
        if keys[pygame.K_e]:
            turn += 1.0

        player.angle += 0.0 if player_dead else turn * player.turn_speed * dt
        world.update_doors(player, dt)
        if not player_dead:
            world.move_player(player, forward, strafe, dt)
        melee_damage = 0
        spawned_projectiles: list[ProjectileState] = []
        if not show_briefing and not player_dead:
            melee_damage, spawned_projectiles = update_enemies(player, enemies, enemy_types, world, dt)
        if spawned_projectiles:
            active_projectiles.extend(spawned_projectiles)

        active_projectiles, projectile_damage = update_projectiles(world, player, active_projectiles, dt)
        player.health = max(0, player.health - melee_damage - projectile_damage)
        player_dead = player.health <= 0

        for pickup in pickups[:]:
            dx = float(pickup["x"]) - player.x
            dy = float(pickup["y"]) - player.y
            if dx * dx + dy * dy <= 0.35 * 0.35:
                unlocked_weapons.add(str(pickup["type"]))
                pickups.remove(pickup)

        while weapon_cycle[current_weapon_idx] not in unlocked_weapons and current_weapon_idx > 0:
            current_weapon_idx -= 1

        active_weapon = weapons_by_id[weapon_cycle[current_weapon_idx]]
        if fire_requested and not show_briefing and not player_dead:
            fire, _target = attempt_fire_multi(
                shot_cooldown,
                player,
                world,
                enemies,
                damage=active_weapon.damage,
                max_range=active_weapon.range,
                cooldown=active_weapon.cooldown,
            )
            shot_cooldown = fire.next_cooldown
            _ = route_simulation_audio_events(False, fire)
            weapon_fx_id = active_weapon.id
            if active_weapon.id == "smg":
                weapon_fx_timer = 0.045
            elif active_weapon.id == "shotgun":
                weapon_fx_timer = 0.11
            elif active_weapon.id == "autorifle":
                weapon_fx_timer = 0.075
            else:
                weapon_fx_timer = 0.065
        shot_cooldown = max(0.0, shot_cooldown - dt)
        weapon_fx_timer = max(0.0, weapon_fx_timer - dt)

        level_cleared = all(not e.alive for e in enemies)
        if level_cleared and not player_dead and next_level_requested and level_idx < len(campaign) - 1:
            level_idx += 1
            world, player, enemies, pickups, level_title = load_level_state(level_idx)
            shot_cooldown = 0.0
            current_weapon_idx = 0
            show_briefing = True
            active_projectiles.clear()

        surface.fill((35, 35, 40))
        pygame.draw.rect(surface, (70, 78, 102), (0, internal_h // 2, internal_w, internal_h // 2))
        depth_buffer = [20.0] * internal_w

        for col in range(internal_w):
            ray_angle = player.angle - fov / 2.0 + (col / internal_w) * fov
            ray_hit = world.cast_ray(player.x, player.y, ray_angle)
            corrected = ray_hit.depth * math.cos(ray_angle - player.angle)
            depth_buffer[col] = corrected
            wall_h = min(int(internal_h / max(corrected, 0.0001)), internal_h)

            intensity = max(40, int(ray_hit.shade / (1.0 + corrected * 0.15)))
            if ray_hit.hit_kind == 1:
                color = (intensity, max(30, intensity // 2), 20)
            elif ray_hit.hit_kind == 2:
                color = (max(20, intensity // 2), max(15, intensity // 3), 10)
            else:
                color = (intensity // 2, intensity // 2, intensity)
            top = (internal_h - wall_h) // 2
            pygame.draw.line(surface, color, (col, top), (col, top + wall_h))

        render_enemies(surface, enemies, player, fov, depth_buffer)
        render_projectiles(surface, player, active_projectiles, fov, depth_buffer)

        snapshot = build_frame_snapshot(player, enemies, world, shot_cooldown, active_weapon.label)
        hud_lines = [f"Level {level_idx + 1}/{len(campaign)}: {level_title}"] + format_hud_lines(snapshot)
        if level_cleared:
            hud_lines.append("Level clear! Press ENTER for next level")
        if show_briefing:
            hud_lines.append("Mission briefing active: ENTER to deploy")
        if player_dead:
            hud_lines.append("You were eliminated: press R to retry level")
        if active_projectiles:
            hud_lines.append(f"Incoming: {len(active_projectiles)}")
        for i, line in enumerate(hud_lines):
            color = (245, 210, 120) if "Level clear" in line else (220, 220, 225)
            hud_surface = font.render(line, True, color)
            surface.blit(hud_surface, (6, internal_h - 36 + i * 10))

        cx, cy = internal_w // 2, internal_h // 2
        crosshair_color = (245, 190, 75) if snapshot.door_in_front else (245, 245, 245)
        pygame.draw.line(surface, crosshair_color, (cx - 4, cy), (cx + 4, cy), 1)
        pygame.draw.line(surface, crosshair_color, (cx, cy - 4), (cx, cy + 4), 1)
        draw_weapon_vfx(surface, weapon_fx_id, weapon_fx_timer)

        if show_minimap:
            scale = 8
            pad = 6
            for y, row in enumerate(world.tile_map):
                for x, tile in enumerate(row):
                    if tile == "1":
                        c = (55, 55, 60)
                    elif tile == "2":
                        openness = world.doors[(x, y)].open_amount
                        v = int(70 + openness * 150)
                        c = (v, 120, 55)
                    else:
                        c = (135, 135, 145)
                    pygame.draw.rect(surface, c, (pad + x * scale, pad + y * scale, scale - 1, scale - 1))
            px = int(pad + player.x * scale)
            py = int(pad + player.y * scale)
            pygame.draw.circle(surface, (30, 210, 80), (px, py), 2)
            for pickup in pickups:
                wx = int(pad + float(pickup["x"]) * scale)
                wy = int(pad + float(pickup["y"]) * scale)
                pygame.draw.circle(surface, (210, 180, 50), (wx, wy), 2)

        if show_briefing:
            overlay = pygame.Surface((internal_w, internal_h), pygame.SRCALPHA)
            overlay.fill((8, 8, 12, 190))
            surface.blit(overlay, (0, 0))
            title_surface = font.render(level_title, True, (245, 210, 120))
            briefing_surface = font.render(campaign[level_idx].briefing, True, (232, 232, 236))
            deploy_surface = font.render("Press ENTER to deploy", True, (245, 210, 120))
            surface.blit(title_surface, (16, 70))
            surface.blit(briefing_surface, (16, 86))
            surface.blit(deploy_surface, (16, 102))
        elif player_dead:
            overlay = pygame.Surface((internal_w, internal_h), pygame.SRCALPHA)
            overlay.fill((18, 2, 2, 170))
            surface.blit(overlay, (0, 0))
            dead_surface = font.render("MISSION FAILED", True, (235, 125, 125))
            retry_surface = font.render("Press R to retry this level", True, (235, 210, 160))
            surface.blit(dead_surface, (16, 86))
            surface.blit(retry_surface, (16, 102))

        screen.blit(pygame.transform.scale(surface, (screen_w, screen_h)), (0, 0))
        pygame.display.flip()

        if smoke_test and frames >= 5:
            running = False

    pygame.quit()
