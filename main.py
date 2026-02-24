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
    "100002000001",
    "101101111101",
    "100100000001",
    "101101011101",
    "100001000001",
    "101111011101",
    "100000000001",
    "111111111111",
]
WALL_TILE = "1"
DOOR_TILE = "2"
DOOR_SPEED = 1.8
DOOR_AUTO_CLOSE_DELAY = 2.0
DOOR_HOLD_DISTANCE = 0.95
DOOR_THICKNESS = 0.12
DOOR_FRAME_THICKNESS = 0.07
DOOR_SLIDE_DISTANCE = 0.38
DOOR_OPENING_HALF_WIDTH = 0.28


@dataclass
class Player:
    x: float = 1.5
    y: float = 1.5
    angle: float = 0.2
    move_speed: float = 3.0
    turn_speed: float = 2.2


@dataclass
class Door:
    open_amount: float = 0.0
    target_open: bool = False
    orientation: str = "vertical"
    auto_close_timer: float = 0.0
    slide_sign: int = 1


def tile_at(tx: int, ty: int) -> str:
    if tx < 0 or ty < 0:
        return WALL_TILE
    if ty >= len(WORLD_MAP) or tx >= len(WORLD_MAP[0]):
        return WALL_TILE
    return WORLD_MAP[ty][tx]


def is_blocked(x: float, y: float, doors: dict[tuple[int, int], Door]) -> bool:
    tx, ty = int(x), int(y)
    tile = tile_at(tx, ty)
    if tile == WALL_TILE:
        return True
    if tile == DOOR_TILE:
        door = doors[(tx, ty)]
        return door_blocks_point(tx, ty, x, y, door)
    return False


def door_blocks_point(tx: int, ty: int, x: float, y: float, door: Door) -> bool:
    fx = x - tx
    fy = y - ty
    slab_half = (DOOR_THICKNESS * 0.5) * (1.0 - door.open_amount)
    if slab_half <= 0.003:
        return False

    if door.orientation == "vertical":
        if abs(fy - 0.5) > DOOR_OPENING_HALF_WIDTH:
            return True
        if fy <= DOOR_FRAME_THICKNESS or fy >= 1.0 - DOOR_FRAME_THICKNESS:
            return True
        center = 0.5 + door.slide_sign * door.open_amount * DOOR_SLIDE_DISTANCE
        return abs(fx - center) <= slab_half
    if abs(fx - 0.5) > DOOR_OPENING_HALF_WIDTH:
        return True
    if fx <= DOOR_FRAME_THICKNESS or fx >= 1.0 - DOOR_FRAME_THICKNESS:
        return True
    center = 0.5 + door.slide_sign * door.open_amount * DOOR_SLIDE_DISTANCE
    return abs(fy - center) <= slab_half


def door_hit_kind(tx: int, ty: int, x: float, y: float, door: Door) -> int:
    fx = x - tx
    fy = y - ty
    slab_half = (DOOR_THICKNESS * 0.5) * (1.0 - door.open_amount)
    if door.orientation == "vertical":
        if abs(fy - 0.5) > DOOR_OPENING_HALF_WIDTH:
            return 2
        if fy <= DOOR_FRAME_THICKNESS or fy >= 1.0 - DOOR_FRAME_THICKNESS:
            return 2
        center = 0.5 + door.slide_sign * door.open_amount * DOOR_SLIDE_DISTANCE
        if slab_half > 0.003 and abs(fx - center) <= slab_half:
            return 1
        return 0
    if abs(fx - 0.5) > DOOR_OPENING_HALF_WIDTH:
        return 2
    if fx <= DOOR_FRAME_THICKNESS or fx >= 1.0 - DOOR_FRAME_THICKNESS:
        return 2
    center = 0.5 + door.slide_sign * door.open_amount * DOOR_SLIDE_DISTANCE
    if slab_half > 0.003 and abs(fy - center) <= slab_half:
        return 1
    return 0


def move_with_collision(player: Player, forward: float, strafe: float, dt: float, doors: dict[tuple[int, int], Door]) -> None:
    sin_a = math.sin(player.angle)
    cos_a = math.cos(player.angle)
    step = player.move_speed * dt
    dx = (cos_a * forward - sin_a * strafe) * step
    dy = (sin_a * forward + cos_a * strafe) * step

    candidate_x = player.x + dx
    if not is_blocked(candidate_x, player.y, doors):
        player.x = candidate_x

    candidate_y = player.y + dy
    if not is_blocked(player.x, candidate_y, doors):
        player.y = candidate_y


def cast_ray(
    px: float, py: float, ray_angle: float, doors: dict[tuple[int, int], Door], max_depth: float = 20.0
) -> tuple[float, int, int]:
    sin_a = math.sin(ray_angle)
    cos_a = math.cos(ray_angle)
    depth = 0.0
    step = 0.02

    while depth < max_depth:
        depth += step
        test_x = px + cos_a * depth
        test_y = py + sin_a * depth
        tx, ty = int(test_x), int(test_y)
        tile = tile_at(tx, ty)
        if tile == WALL_TILE:
            shade = 180 if int(test_x * 2) % 2 == 0 else 220
            return depth, shade, 0
        if tile == DOOR_TILE:
            hit_kind = door_hit_kind(tx, ty, test_x, test_y, doors[(tx, ty)])
            if hit_kind == 2:
                return depth, 155, 2
            if hit_kind == 1:
                return depth, 235, 1
    return max_depth, 120, 0


def draw_minimap(surface: pygame.Surface, player: Player, doors: dict[tuple[int, int], Door], scale: int = 8) -> None:
    map_h = len(WORLD_MAP)
    map_w = len(WORLD_MAP[0])
    pad = 6
    for y in range(map_h):
        for x in range(map_w):
            tile = WORLD_MAP[y][x]
            if tile == WALL_TILE:
                color = (55, 55, 60)
            elif tile == DOOR_TILE:
                openness = doors[(x, y)].open_amount
                v = int(70 + openness * 150)
                color = (v, 120, 55)
            else:
                color = (135, 135, 145)
            rect = (pad + x * scale, pad + y * scale, scale - 1, scale - 1)
            pygame.draw.rect(surface, color, rect)

    px = int(pad + player.x * scale)
    py = int(pad + player.y * scale)
    pygame.draw.circle(surface, (30, 210, 80), (px, py), 2)
    lx = int(px + math.cos(player.angle) * 6)
    ly = int(py + math.sin(player.angle) * 6)
    pygame.draw.line(surface, (20, 30, 40), (px, py), (lx, ly), 2)


def init_doors() -> dict[tuple[int, int], Door]:
    doors: dict[tuple[int, int], Door] = {}
    for y, row in enumerate(WORLD_MAP):
        for x, tile in enumerate(row):
            if tile == DOOR_TILE:
                left_wall = tile_at(x - 1, y) == WALL_TILE
                right_wall = tile_at(x + 1, y) == WALL_TILE
                up_wall = tile_at(x, y - 1) == WALL_TILE
                down_wall = tile_at(x, y + 1) == WALL_TILE

                if up_wall and down_wall and not (left_wall and right_wall):
                    orientation = "vertical"
                elif left_wall and right_wall and not (up_wall and down_wall):
                    orientation = "horizontal"
                else:
                    orientation = "vertical"
                if orientation == "vertical":
                    slide_sign = 1 if tile_at(x + 1, y) != WALL_TILE else -1
                else:
                    slide_sign = 1 if tile_at(x, y + 1) != WALL_TILE else -1
                doors[(x, y)] = Door(orientation=orientation, slide_sign=slide_sign)
    return doors


def player_in_door_tile(player: Player, door_pos: tuple[int, int]) -> bool:
    return int(player.x) == door_pos[0] and int(player.y) == door_pos[1]


def player_near_door(player: Player, door_pos: tuple[int, int], hold_distance: float = DOOR_HOLD_DISTANCE) -> bool:
    dx = player.x - (door_pos[0] + 0.5)
    dy = player.y - (door_pos[1] + 0.5)
    return (dx * dx + dy * dy) <= hold_distance * hold_distance


def update_doors(doors: dict[tuple[int, int], Door], player: Player, dt: float) -> None:
    delta = DOOR_SPEED * dt
    for door_pos, door in doors.items():
        if door.target_open:
            door.open_amount = min(1.0, door.open_amount + delta)
            if door.open_amount >= 0.999:
                if player_near_door(player, door_pos):
                    door.auto_close_timer = DOOR_AUTO_CLOSE_DELAY
                else:
                    door.auto_close_timer = max(0.0, door.auto_close_timer - dt)
                    if door.auto_close_timer <= 0.0:
                        door.target_open = False
        else:
            if player_in_door_tile(player, door_pos) or player_near_door(player, door_pos):
                # Mirror classic behavior: a door won't close on top of or near the player.
                door.target_open = True
                door.auto_close_timer = DOOR_AUTO_CLOSE_DELAY
                continue
            door.open_amount = max(0.0, door.open_amount - delta)


def find_door_in_front(
    player: Player, doors: dict[tuple[int, int], Door], max_dist: float = 0.9
) -> tuple[int, int] | None:
    step = 0.05
    sin_a = math.sin(player.angle)
    cos_a = math.cos(player.angle)
    depth = step
    while depth <= max_dist:
        tx = int(player.x + cos_a * depth)
        ty = int(player.y + sin_a * depth)
        if (tx, ty) in doors:
            return tx, ty
        if tile_at(tx, ty) == WALL_TILE:
            return None
        depth += step
    return None


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
    doors = init_doors()
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
                if event.key == pygame.K_SPACE:
                    door_pos = find_door_in_front(player, doors)
                    if door_pos is not None:
                        door = doors[door_pos]
                        if door.target_open:
                            door.target_open = False
                            door.auto_close_timer = 0.0
                        else:
                            door.target_open = True
                            door.auto_close_timer = DOOR_AUTO_CLOSE_DELAY

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
        update_doors(doors, player, dt)
        move_with_collision(player, forward, strafe, dt, doors)

        surface.fill((35, 35, 40))
        pygame.draw.rect(surface, (70, 78, 102), (0, internal_h // 2, internal_w, internal_h // 2))

        for col in range(internal_w):
            ray_angle = player.angle - fov / 2.0 + (col / internal_w) * fov
            depth, shade, hit_kind = cast_ray(player.x, player.y, ray_angle, doors)
            corrected = depth * math.cos(ray_angle - player.angle)
            wall_h = min(int(internal_h / max(corrected, 0.0001)), internal_h)

            intensity = max(40, int(shade / (1.0 + corrected * 0.15)))
            if hit_kind == 1:
                # Door slab uses a warm palette so it stands out from wall faces.
                color = (intensity, max(30, intensity // 2), 20)
            elif hit_kind == 2:
                # Door frame stays darker than slab for better depth cues.
                color = (max(20, intensity // 2), max(15, intensity // 3), 10)
            else:
                color = (intensity // 2, intensity // 2, intensity)
            top = (internal_h - wall_h) // 2
            pygame.draw.line(surface, color, (col, top), (col, top + wall_h))

        if find_door_in_front(player, doors) is not None:
            cx, cy = internal_w // 2, internal_h // 2
            pygame.draw.line(surface, (245, 190, 75), (cx - 4, cy), (cx + 4, cy), 1)
            pygame.draw.line(surface, (245, 190, 75), (cx, cy - 4), (cx, cy + 4), 1)

        if show_minimap:
            draw_minimap(surface, player, doors)

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
