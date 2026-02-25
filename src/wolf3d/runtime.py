from __future__ import annotations

import math
import os

import pygame

from src.wolf3d.audio.manager import route_simulation_audio_events
from src.wolf3d.entities.models import EnemyState, PlayerState
from src.wolf3d.gameplay.combat import attempt_fire, normalize_angle
from src.wolf3d.render.frame import build_frame_snapshot
from src.wolf3d.ui.hud import format_hud_lines
from src.wolf3d.world.simulation import WorldSimulation


DEFAULT_MAP = [
    "111111111111",
    "100000000001",
    "101111011101",
    "100002000001",
    "101101111101",
    "100100000001",
    "101101011101",
    "100001000001",
    "101111011101",
    "100000000001",
    "111111111111",
]


def render_enemy(surface: pygame.Surface, enemy: EnemyState, player: PlayerState, fov: float, depth_buffer: list[float]) -> None:
    if not enemy.alive:
        return
    w, h = surface.get_width(), surface.get_height()

    dx = enemy.x - player.x
    dy = enemy.y - player.y
    distance = math.hypot(dx, dy)
    if distance <= 0.05:
        return

    angle = normalize_angle(math.atan2(dy, dx) - player.angle)
    if abs(angle) > fov * 0.65:
        return

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


def run_runtime(smoke_test: bool = False) -> None:
    if smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    screen_w, screen_h = 960, 600
    internal_w, internal_h = 320, 200
    screen = pygame.display.set_mode((screen_w, screen_h))
    surface = pygame.Surface((internal_w, internal_h))
    font = pygame.font.Font(None, 18)
    clock = pygame.time.Clock()
    pygame.display.set_caption("Wolf3D Real Runtime (Extracted)")

    world = WorldSimulation(DEFAULT_MAP)
    player = PlayerState(x=1.5, y=1.5, angle=0.2)
    enemy = EnemyState(type_id="guard", x=8.5, y=3.5, health=50)
    fov = math.radians(60)

    show_minimap = True
    shot_cooldown = 0.0
    running = True
    frames = 0

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        frames += 1
        fire_requested = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:
                    show_minimap = not show_minimap
                elif event.key == pygame.K_SPACE:
                    world.toggle_door_in_front(player)
                elif event.key == pygame.K_f:
                    fire_requested = True
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

        player.angle += turn * player.turn_speed * dt
        world.update_doors(player, dt)
        world.move_player(player, forward, strafe, dt)

        if fire_requested:
            fire = attempt_fire(shot_cooldown, player, world, enemy)
            shot_cooldown = fire.next_cooldown
            _ = route_simulation_audio_events(False, fire)
        shot_cooldown = max(0.0, shot_cooldown - dt)

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

        render_enemy(surface, enemy, player, fov, depth_buffer)

        snapshot = build_frame_snapshot(player, enemy, world, shot_cooldown)
        for i, line in enumerate(format_hud_lines(snapshot)):
            hud_surface = font.render(line, True, (220, 220, 225))
            surface.blit(hud_surface, (6, internal_h - 26 + i * 10))

        cx, cy = internal_w // 2, internal_h // 2
        crosshair_color = (245, 190, 75) if snapshot.door_in_front else (245, 245, 245)
        pygame.draw.line(surface, crosshair_color, (cx - 4, cy), (cx + 4, cy), 1)
        pygame.draw.line(surface, crosshair_color, (cx, cy - 4), (cx, cy + 4), 1)

        if show_minimap:
            scale = 8
            pad = 6
            for y, row in enumerate(DEFAULT_MAP):
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

        screen.blit(pygame.transform.scale(surface, (screen_w, screen_h)), (0, 0))
        pygame.display.flip()

        if smoke_test and frames >= 5:
            running = False

    pygame.quit()
