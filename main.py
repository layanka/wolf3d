from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass

import pygame


WORLD_MAP = [
    "111111111111",
    "100000000001",
    "101111011101",
    "100001000001",
    "101101111101",
    "100100000001",
    "101101011101",
    "100001000001",
    "101111011101",
    "100000000001",
    "111111111111",
]


@dataclass
class Player:
    x: float = 1.5
    y: float = 1.5
    angle: float = 0.2
    move_speed: float = 3.0
    turn_speed: float = 2.2


def is_wall(x: float, y: float) -> bool:
    if x < 0 or y < 0:
        return True
    tx, ty = int(x), int(y)
    if ty >= len(WORLD_MAP) or tx >= len(WORLD_MAP[0]):
        return True
    return WORLD_MAP[ty][tx] == "1"


def move_with_collision(player: Player, forward: float, strafe: float, dt: float) -> None:
    sin_a = math.sin(player.angle)
    cos_a = math.cos(player.angle)
    step = player.move_speed * dt
    dx = (cos_a * forward - sin_a * strafe) * step
    dy = (sin_a * forward + cos_a * strafe) * step

    candidate_x = player.x + dx
    if not is_wall(candidate_x, player.y):
        player.x = candidate_x

    candidate_y = player.y + dy
    if not is_wall(player.x, candidate_y):
        player.y = candidate_y


def cast_ray(px: float, py: float, ray_angle: float, max_depth: float = 20.0) -> tuple[float, int]:
    sin_a = math.sin(ray_angle)
    cos_a = math.cos(ray_angle)
    depth = 0.0
    step = 0.02

    while depth < max_depth:
        depth += step
        test_x = px + cos_a * depth
        test_y = py + sin_a * depth
        if is_wall(test_x, test_y):
            shade = 180 if int(test_x * 2) % 2 == 0 else 220
            return depth, shade
    return max_depth, 120


def draw_minimap(surface: pygame.Surface, player: Player, scale: int = 8) -> None:
    map_h = len(WORLD_MAP)
    map_w = len(WORLD_MAP[0])
    pad = 6
    for y in range(map_h):
        for x in range(map_w):
            color = (55, 55, 60) if WORLD_MAP[y][x] == "1" else (135, 135, 145)
            rect = (pad + x * scale, pad + y * scale, scale - 1, scale - 1)
            pygame.draw.rect(surface, color, rect)

    px = int(pad + player.x * scale)
    py = int(pad + player.y * scale)
    pygame.draw.circle(surface, (30, 210, 80), (px, py), 2)
    lx = int(px + math.cos(player.angle) * 6)
    ly = int(py + math.sin(player.angle) * 6)
    pygame.draw.line(surface, (20, 30, 40), (px, py), (lx, ly), 2)


def run(smoke_test: bool = False) -> None:
    if smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    screen_w, screen_h = 960, 600
    internal_w, internal_h = 320, 200
    screen = pygame.display.set_mode((screen_w, screen_h))
    surface = pygame.Surface((internal_w, internal_h))
    clock = pygame.time.Clock()
    pygame.display.set_caption("Wolf3D PoC - M1")

    fov = math.radians(60)
    player = Player()
    show_minimap = True

    running = True
    frames = 0
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        frames += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_m:
                    show_minimap = not show_minimap

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
        move_with_collision(player, forward, strafe, dt)

        surface.fill((35, 35, 40))
        pygame.draw.rect(surface, (70, 78, 102), (0, internal_h // 2, internal_w, internal_h // 2))

        for col in range(internal_w):
            ray_angle = player.angle - fov / 2.0 + (col / internal_w) * fov
            depth, shade = cast_ray(player.x, player.y, ray_angle)
            corrected = depth * math.cos(ray_angle - player.angle)
            wall_h = min(int(internal_h / max(corrected, 0.0001)), internal_h)

            intensity = max(40, int(shade / (1.0 + corrected * 0.15)))
            color = (intensity // 2, intensity // 2, intensity)
            top = (internal_h - wall_h) // 2
            pygame.draw.line(surface, color, (col, top), (col, top + wall_h))

        if show_minimap:
            draw_minimap(surface, player)

        scaled = pygame.transform.scale(surface, (screen_w, screen_h))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()

        if smoke_test and frames >= 5:
            running = False

    pygame.quit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wolf3D-style raycasting PoC")
    parser.add_argument("--smoke-test", action="store_true", help="Run a short headless loop")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(smoke_test=args.smoke_test)


if __name__ == "__main__":
    main()
