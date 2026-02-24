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
ENEMY_HIT_ANGLE = math.radians(4.0)
ENEMY_SHOOT_RANGE = 8.0
WEAPON_COOLDOWN = 0.24
WEAPON_RECOIL_DURATION = 0.12
MUZZLE_FLASH_DURATION = 0.08


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


@dataclass
class Enemy:
    x: float
    y: float
    health: int = 3
    alive: bool = True


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


def normalize_angle(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


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


def try_shoot_enemy(player: Player, doors: dict[tuple[int, int], Door], enemy: Enemy) -> bool:
    if not enemy.alive:
        return False

    dx = enemy.x - player.x
    dy = enemy.y - player.y
    distance = math.hypot(dx, dy)
    if distance > ENEMY_SHOOT_RANGE:
        return False

    enemy_angle = math.atan2(dy, dx)
    if abs(normalize_angle(enemy_angle - player.angle)) > ENEMY_HIT_ANGLE:
        return False

    wall_depth, _, _ = cast_ray(player.x, player.y, player.angle, doors)
    if distance >= wall_depth - 0.05:
        return False

    enemy.health -= 1
    if enemy.health <= 0:
        enemy.alive = False
    return True


def render_enemy(
    surface: pygame.Surface, enemy: Enemy, player: Player, fov: float, depth_buffer: list[float], w: int, h: int
) -> None:
    if not enemy.alive:
        return

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
    body_color = (intensity, max(25, intensity // 4), max(25, intensity // 4))

    for col in range(max(0, left), min(w, right)):
        if distance < depth_buffer[col]:
            pygame.draw.line(surface, body_color, (col, top), (col, bottom))


def attempt_fire(
    cooldown_timer: float, player: Player, doors: dict[tuple[int, int], Door], enemy: Enemy
) -> tuple[float, bool, bool]:
    if cooldown_timer > 0.0:
        return cooldown_timer, False, False
    hit_enemy = try_shoot_enemy(player, doors, enemy)
    return WEAPON_COOLDOWN, True, hit_enemy


def draw_weapon_overlay(
    surface: pygame.Surface, w: int, h: int, recoil_timer: float, muzzle_flash_timer: float
) -> None:
    recoil_ratio = min(1.0, recoil_timer / WEAPON_RECOIL_DURATION) if WEAPON_RECOIL_DURATION > 0.0 else 0.0
    recoil_drop = int(10 * recoil_ratio)
    recoil_kick = int(4 * recoil_ratio)

    gun_w = int(w * 0.36)
    gun_h = int(h * 0.28)
    gun_x = (w - gun_w) // 2 + recoil_kick
    gun_y = h - gun_h + recoil_drop

    pygame.draw.rect(surface, (34, 34, 42), (gun_x, gun_y, gun_w, gun_h))
    barrel_w = int(gun_w * 0.24)
    barrel_h = int(gun_h * 0.52)
    barrel_x = (w - barrel_w) // 2 + recoil_kick
    barrel_y = gun_y - barrel_h + int(gun_h * 0.2)
    pygame.draw.rect(surface, (62, 62, 72), (barrel_x, barrel_y, barrel_w, barrel_h))

    if muzzle_flash_timer > 0.0:
        flash_w = int(barrel_w * 1.8)
        flash_h = int(barrel_h * 0.9)
        flash_x = (w - flash_w) // 2 + recoil_kick
        flash_y = barrel_y - flash_h + 2
        pygame.draw.polygon(
            surface,
            (245, 210, 90),
            [(flash_x, flash_y + flash_h), (flash_x + flash_w // 2, flash_y), (flash_x + flash_w, flash_y + flash_h)],
        )


def run(smoke_test: bool = False) -> None:
    if smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    screen_w, screen_h = 960, 600
    internal_w, internal_h = 320, 200
    screen = pygame.display.set_mode((screen_w, screen_h))
    surface = pygame.Surface((internal_w, internal_h))
    font = pygame.font.Font(None, 18)
    clock = pygame.time.Clock()
    pygame.display.set_caption("Wolf3D PoC - M1")

    fov = math.radians(60)
    player = Player()
    enemy = Enemy(8.5, 3.5)
    doors = init_doors()
    show_minimap = True
    hit_flash_timer = 0.0
    shot_cooldown_timer = 0.0
    recoil_timer = 0.0
    muzzle_flash_timer = 0.0

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
                if event.key == pygame.K_f:
                    shot_cooldown_timer, did_fire, did_hit = attempt_fire(shot_cooldown_timer, player, doors, enemy)
                    if did_fire:
                        recoil_timer = WEAPON_RECOIL_DURATION
                        muzzle_flash_timer = MUZZLE_FLASH_DURATION
                    if did_hit:
                        hit_flash_timer = 0.12
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                shot_cooldown_timer, did_fire, did_hit = attempt_fire(shot_cooldown_timer, player, doors, enemy)
                if did_fire:
                    recoil_timer = WEAPON_RECOIL_DURATION
                    muzzle_flash_timer = MUZZLE_FLASH_DURATION
                if did_hit:
                    hit_flash_timer = 0.12

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
        hit_flash_timer = max(0.0, hit_flash_timer - dt)
        shot_cooldown_timer = max(0.0, shot_cooldown_timer - dt)
        recoil_timer = max(0.0, recoil_timer - dt)
        muzzle_flash_timer = max(0.0, muzzle_flash_timer - dt)

        surface.fill((35, 35, 40))
        pygame.draw.rect(surface, (70, 78, 102), (0, internal_h // 2, internal_w, internal_h // 2))
        depth_buffer = [20.0] * internal_w

        for col in range(internal_w):
            ray_angle = player.angle - fov / 2.0 + (col / internal_w) * fov
            depth, shade, hit_kind = cast_ray(player.x, player.y, ray_angle, doors)
            corrected = depth * math.cos(ray_angle - player.angle)
            depth_buffer[col] = corrected
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

        render_enemy(surface, enemy, player, fov, depth_buffer, internal_w, internal_h)

        crosshair_color = (245, 245, 245) if hit_flash_timer <= 0.0 else (245, 120, 80)
        if find_door_in_front(player, doors) is not None:
            crosshair_color = (245, 190, 75)

        cx, cy = internal_w // 2, internal_h // 2
        pygame.draw.line(surface, crosshair_color, (cx - 4, cy), (cx + 4, cy), 1)
        pygame.draw.line(surface, crosshair_color, (cx, cy - 4), (cx, cy + 4), 1)

        if show_minimap:
            draw_minimap(surface, player, doors)
            ex = int(6 + enemy.x * 8)
            ey = int(6 + enemy.y * 8)
            enemy_color = (170, 25, 25) if enemy.alive else (80, 80, 80)
            pygame.draw.circle(surface, enemy_color, (ex, ey), 2)

        draw_weapon_overlay(surface, internal_w, internal_h, recoil_timer, muzzle_flash_timer)

        weapon_state = "READY" if shot_cooldown_timer <= 0.0 else "COOLDOWN"
        hud_text = (
            f"Enemy: down  Weapon: {weapon_state}"
            if not enemy.alive
            else f"Enemy HP: {enemy.health}  Weapon: {weapon_state}  (F or LMB to shoot)"
        )
        hud_surface = font.render(hud_text, True, (220, 220, 225))
        surface.blit(hud_surface, (6, internal_h - 14))

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
