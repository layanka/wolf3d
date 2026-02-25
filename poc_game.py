from __future__ import annotations

import argparse
import math
import os
from array import array
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
DOOR_THICKNESS_CLOSED = 0.44
DOOR_FRAME_THICKNESS = 0.07
DOOR_SLIDE_DISTANCE = 0.38
DOOR_OPENING_HALF_WIDTH = 0.28
DOOR_SOLID_THRESHOLD = 0.20
ENEMY_HIT_ANGLE = math.radians(4.0)
ENEMY_SHOOT_RANGE = 8.0
WEAPON_COOLDOWN = 0.24
WEAPON_RECOIL_DURATION = 0.12
MUZZLE_FLASH_DURATION = 0.08
SFX_SAMPLE_RATE = 22050
TRACER_DURATION = 0.07
STEP_INTERVAL_BASE = 0.35
PLAYER_RADIUS = 0.14


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


@dataclass
class ShotTrace:
    timer: float = 0.0
    distance: float = 0.0
    hit_enemy: bool = False


@dataclass
class RayHit:
    depth: float
    shade: int
    hit_kind: int


class AudioManager:
    def __init__(self) -> None:
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.step_toggle = False
        base = Path(__file__).resolve().parent / "assets" / "audio" / "sfx"
        try:
            pygame.mixer.init(frequency=SFX_SAMPLE_RATE, size=-16, channels=1)
            self.sounds["shoot"] = load_sound_or(base / "shoot.ogg", synth_shot)
            self.sounds["hit"] = load_sound_or(base / "hit.ogg", synth_hit)
            self.sounds["down"] = load_sound_or(base / "down.ogg", synth_down)
            self.sounds["door"] = load_sound_or(base / "door.ogg", synth_door)
            self.sounds["step1"] = load_sound_or(base / "step1.ogg", lambda: synth_step(0.0))
            self.sounds["step2"] = load_sound_or(base / "step2.ogg", lambda: synth_step(0.25))
            self.sounds["shoot"].set_volume(0.48)
            self.sounds["hit"].set_volume(0.42)
            self.sounds["down"].set_volume(0.42)
            self.sounds["door"].set_volume(0.30)
            self.sounds["step1"].set_volume(0.04)
            self.sounds["step2"].set_volume(0.04)
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def play_step(self) -> None:
        if not self.enabled:
            return
        key = "step1" if not self.step_toggle else "step2"
        self.step_toggle = not self.step_toggle
        sound = self.sounds.get(key)
        if sound is not None:
            sound.play()


def synth_tone(frequency: float, duration: float, volume: float, decay: float = 8.0) -> pygame.mixer.Sound:
    sample_count = max(1, int(SFX_SAMPLE_RATE * duration))
    data = array("h")
    amplitude = int(32767 * max(0.0, min(1.0, volume)))
    for i in range(sample_count):
        t = i / SFX_SAMPLE_RATE
        env = math.exp(-decay * t)
        value = int(amplitude * env * math.sin(2.0 * math.pi * frequency * t))
        data.append(value)
    return pygame.mixer.Sound(buffer=data.tobytes())


def load_sound_or(path: Path, fallback: Callable[[], pygame.mixer.Sound]) -> pygame.mixer.Sound:
    try:
        if path.exists():
            return pygame.mixer.Sound(str(path))
    except pygame.error:
        pass
    return fallback()


def synth_wave(
    duration: float, volume: float, sample_fn: Callable[[float], float], decay: float = 6.0
) -> pygame.mixer.Sound:
    sample_count = max(1, int(SFX_SAMPLE_RATE * duration))
    amplitude = int(32767 * max(0.0, min(1.0, volume)))
    data = array("h")
    for i in range(sample_count):
        t = i / SFX_SAMPLE_RATE
        env = math.exp(-decay * t)
        value = int(amplitude * env * max(-1.0, min(1.0, sample_fn(t))))
        data.append(value)
    return pygame.mixer.Sound(buffer=data.tobytes())


def synth_shot() -> pygame.mixer.Sound:
    return synth_wave(
        0.09,
        0.42,
        lambda t: 0.55 * math.sin(2 * math.pi * (160 + 120 * t) * t)
        + 0.30 * math.sin(2 * math.pi * 55 * t)
        + 0.28 * math.sin(2 * math.pi * (370 + 40 * math.sin(30 * t)) * t),
        decay=8.5,
    )


def synth_hit() -> pygame.mixer.Sound:
    return synth_wave(
        0.07,
        0.32,
        lambda t: 0.7 * math.sin(2 * math.pi * (660 - 180 * t) * t) + 0.22 * math.sin(2 * math.pi * 1200 * t),
        decay=10.5,
    )


def synth_down() -> pygame.mixer.Sound:
    return synth_wave(
        0.20,
        0.35,
        lambda t: 0.65 * math.sin(2 * math.pi * (150 - 70 * t) * t) + 0.24 * math.sin(2 * math.pi * 70 * t),
        decay=4.2,
    )


def synth_door() -> pygame.mixer.Sound:
    return synth_wave(
        0.14,
        0.24,
        lambda t: 0.55 * math.sin(2 * math.pi * 220 * t) + 0.30 * math.sin(2 * math.pi * 110 * t),
        decay=3.2,
    )


def synth_step(phase: float) -> pygame.mixer.Sound:
    return synth_wave(
        0.11,
        0.22,
        lambda t: 0.65 * math.sin(2 * math.pi * (95 + 12 * phase) * t)
        + 0.20 * math.sin(2 * math.pi * (180 + 20 * phase) * t),
        decay=12.0,
    )


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
        if door.open_amount <= DOOR_SOLID_THRESHOLD:
            # Closed door tiles are fully non-enterable to prevent camera penetration.
            return True
        return door_blocks_point(tx, ty, x, y, door)
    return False


def is_blocked_with_radius(x: float, y: float, doors: dict[tuple[int, int], Door], radius: float = PLAYER_RADIUS) -> bool:
    offsets = (
        (0.0, 0.0),
        (radius, 0.0),
        (-radius, 0.0),
        (0.0, radius),
        (0.0, -radius),
        (radius * 0.7, radius * 0.7),
        (radius * 0.7, -radius * 0.7),
        (-radius * 0.7, radius * 0.7),
        (-radius * 0.7, -radius * 0.7),
    )
    return any(is_blocked(x + ox, y + oy, doors) for ox, oy in offsets)


def door_local_hit_kind(fx: float, fy: float, door: Door) -> int:
    slab_half = (DOOR_THICKNESS_CLOSED * 0.5) * (1.0 - door.open_amount)
    # When effectively closed, fill the doorway opening (but not the side jambs) so the
    # door reads as a closed door rather than a full wall tile.
    if door.open_amount <= DOOR_SOLID_THRESHOLD:
        slab_half = DOOR_OPENING_HALF_WIDTH - 0.002

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


def closed_door_entry_hit_kind(fx: float, fy: float, door: Door) -> int:
    if door.orientation == "vertical":
        return 2 if abs(fy - 0.5) > DOOR_OPENING_HALF_WIDTH else 1
    return 2 if abs(fx - 0.5) > DOOR_OPENING_HALF_WIDTH else 1


def door_hit_kind(tx: int, ty: int, x: float, y: float, door: Door) -> int:
    return door_local_hit_kind(x - tx, y - ty, door)


def door_blocks_point(tx: int, ty: int, x: float, y: float, door: Door) -> bool:
    return door_hit_kind(tx, ty, x, y, door) != 0


def normalize_angle(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def move_with_collision(player: Player, forward: float, strafe: float, dt: float, doors: dict[tuple[int, int], Door]) -> None:
    sin_a = math.sin(player.angle)
    cos_a = math.cos(player.angle)
    step = player.move_speed * dt
    dx_total = (cos_a * forward - sin_a * strafe) * step
    dy_total = (sin_a * forward + cos_a * strafe) * step

    # Sub-step movement to avoid tunneling through thin door slabs.
    max_delta = max(abs(dx_total), abs(dy_total))
    steps = max(1, int(max_delta / 0.03) + 1)
    dx = dx_total / steps
    dy = dy_total / steps

    for _ in range(steps):
        candidate_x = player.x + dx
        if not is_blocked_with_radius(candidate_x, player.y, doors):
            player.x = candidate_x

        candidate_y = player.y + dy
        if not is_blocked_with_radius(player.x, candidate_y, doors):
            player.y = candidate_y


def trace_door_segment(
    px: float,
    py: float,
    ray_dir_x: float,
    ray_dir_y: float,
    tx: int,
    ty: int,
    door: Door,
    start_depth: float,
    end_depth: float,
) -> tuple[float, int, int] | None:
    # Conservative sampling inside the crossed tile segment to avoid ray leaks
    # through thin door features at grazing angles.
    start = max(0.0, start_depth) + 0.0005
    end = max(start, end_depth)
    max_step = 0.002
    steps = max(1, int((end - start) / max_step) + 1)
    for i in range(steps + 1):
        depth = start + (end - start) * (i / steps)
        x = px + ray_dir_x * depth
        y = py + ray_dir_y * depth
        hit_kind = door_hit_kind(tx, ty, x, y, door)
        if hit_kind == 2:
            return depth, 155, 2
        if hit_kind == 1:
            return depth, 235, 1
    return None


def cast_ray(px: float, py: float, ray_angle: float, doors: dict[tuple[int, int], Door], max_depth: float = 20.0) -> RayHit:
    ray_dir_x = math.cos(ray_angle)
    ray_dir_y = math.sin(ray_angle)

    map_x = int(px)
    map_y = int(py)
    if tile_at(map_x, map_y) == DOOR_TILE:
        door_here = doors[(map_x, map_y)]
        if door_here.open_amount <= DOOR_SOLID_THRESHOLD:
            return RayHit(0.001, 210, 1)

    delta_dist_x = abs(1.0 / ray_dir_x) if abs(ray_dir_x) > 1e-8 else float("inf")
    delta_dist_y = abs(1.0 / ray_dir_y) if abs(ray_dir_y) > 1e-8 else float("inf")

    if ray_dir_x < 0.0:
        step_x = -1
        side_dist_x = (px - map_x) * delta_dist_x
    else:
        step_x = 1
        side_dist_x = (map_x + 1.0 - px) * delta_dist_x

    if ray_dir_y < 0.0:
        step_y = -1
        side_dist_y = (py - map_y) * delta_dist_y
    else:
        step_y = 1
        side_dist_y = (map_y + 1.0 - py) * delta_dist_y

    while True:
        if side_dist_x < side_dist_y:
            depth = side_dist_x
            side_dist_x += delta_dist_x
            map_x += step_x
            next_boundary = min(side_dist_x, side_dist_y)
        else:
            depth = side_dist_y
            side_dist_y += delta_dist_y
            map_y += step_y
            next_boundary = min(side_dist_x, side_dist_y)

        if depth >= max_depth:
            return RayHit(max_depth, 120, 0)

        tile = tile_at(map_x, map_y)
        if tile == WALL_TILE:
            hit_x = px + ray_dir_x * depth
            shade = 180 if int(hit_x * 2) % 2 == 0 else 220
            return RayHit(depth, shade, 0)
        if tile == DOOR_TILE:
            door = doors[(map_x, map_y)]
            if door.open_amount <= DOOR_SOLID_THRESHOLD:
                hit_x = px + ray_dir_x * depth
                hit_y = py + ray_dir_y * depth
                hit_kind = closed_door_entry_hit_kind(hit_x - map_x, hit_y - map_y, door)
                shade = 155 if hit_kind == 2 else 210
                return RayHit(depth, shade, hit_kind)
            door_hit = trace_door_segment(
                px, py, ray_dir_x, ray_dir_y, map_x, map_y, door, depth, min(next_boundary, max_depth)
            )
            if door_hit is not None:
                door_depth, door_shade, door_kind = door_hit
                return RayHit(door_depth, door_shade, door_kind)


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
            # Closed doors should not auto-open by proximity; only keep opening if already partially open.
            if door.open_amount > 0.0 and player_in_door_tile(player, door_pos):
                # Mirror classic behavior: a door won't close on top of the player.
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


def compute_enemy_shot_distance(player: Player, enemy: Enemy, wall_depth: float) -> float | None:
    if not enemy.alive:
        return None

    dx = enemy.x - player.x
    dy = enemy.y - player.y
    distance = math.hypot(dx, dy)
    if distance > ENEMY_SHOOT_RANGE:
        return None

    enemy_angle = math.atan2(dy, dx)
    if abs(normalize_angle(enemy_angle - player.angle)) > ENEMY_HIT_ANGLE:
        return None

    if distance >= wall_depth - 0.05:
        return None
    return distance


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
) -> tuple[float, bool, bool, bool, float]:
    if cooldown_timer > 0.0:
        return cooldown_timer, False, False, False, 0.0
    ray_hit = cast_ray(player.x, player.y, player.angle, doors)
    hit_distance = ray_hit.depth

    enemy_distance = compute_enemy_shot_distance(player, enemy, ray_hit.depth)
    alive_before = enemy.alive
    hit_enemy = enemy_distance is not None
    if hit_enemy:
        enemy.health -= 1
        if enemy.health <= 0:
            enemy.alive = False
    if enemy_distance is not None:
        hit_distance = min(hit_distance, enemy_distance)
    enemy_down = alive_before and not enemy.alive
    return WEAPON_COOLDOWN, True, hit_enemy, enemy_down, hit_distance


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


def draw_shot_trace(surface: pygame.Surface, w: int, h: int, trace: ShotTrace) -> None:
    if trace.timer <= 0.0:
        return

    fade = min(1.0, trace.timer / TRACER_DURATION) if TRACER_DURATION > 0 else 0.0
    beam_color = (255, 245, 170) if trace.hit_enemy else (235, 210, 120)
    impact_color = (255, 140, 90) if trace.hit_enemy else (240, 230, 190)

    cx, cy = w // 2, h // 2
    start = (cx, int(h * 0.86))
    end = (cx, cy)
    pygame.draw.line(surface, beam_color, start, end, 1 if fade < 0.5 else 2)

    impact_radius = max(1, min(5, int(8.0 / max(trace.distance, 0.25))))
    pygame.draw.circle(surface, impact_color, end, impact_radius)


def handle_fire_request(
    fire_requested: bool,
    shot_cooldown_timer: float,
    player: Player,
    doors: dict[tuple[int, int], Door],
    enemy: Enemy,
    audio: AudioManager,
    hit_flash_timer: float,
) -> tuple[float, float, float, ShotTrace]:
    if not fire_requested:
        return shot_cooldown_timer, 0.0, hit_flash_timer, ShotTrace()

    shot_cooldown_timer, did_fire, did_hit, did_down, trace_distance = attempt_fire(shot_cooldown_timer, player, doors, enemy)
    if not did_fire:
        return shot_cooldown_timer, 0.0, hit_flash_timer, ShotTrace()

    recoil_timer = WEAPON_RECOIL_DURATION
    muzzle_flash_timer = MUZZLE_FLASH_DURATION
    shot_trace = ShotTrace(timer=TRACER_DURATION, distance=trace_distance, hit_enemy=did_hit)
    audio.play("shoot")
    if did_hit:
        hit_flash_timer = 0.12
        audio.play("hit")
    if did_down:
        audio.play("down")
    return shot_cooldown_timer, recoil_timer, hit_flash_timer, shot_trace


def run(smoke_test: bool = False) -> None:
    if smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    screen_w, screen_h = 960, 600
    internal_w, internal_h = 320, 200
    screen = pygame.display.set_mode((screen_w, screen_h))
    surface = pygame.Surface((internal_w, internal_h))
    font = pygame.font.Font(None, 18)
    audio = AudioManager()
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
    shot_trace = ShotTrace()
    depth_buffer = [20.0] * internal_w
    step_timer = 0.0

    running = True
    frames = 0
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        frames += 1

        fire_requested = False
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
                        audio.play("door")
                if event.key == pygame.K_f:
                    fire_requested = True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
        update_doors(doors, player, dt)
        move_with_collision(player, forward, strafe, dt, doors)

        shot_cooldown_timer, new_recoil_timer, hit_flash_timer, new_shot_trace = handle_fire_request(
            fire_requested, shot_cooldown_timer, player, doors, enemy, audio, hit_flash_timer
        )
        recoil_timer = max(recoil_timer, new_recoil_timer)
        if new_recoil_timer > 0.0:
            muzzle_flash_timer = MUZZLE_FLASH_DURATION
            shot_trace = new_shot_trace

        hit_flash_timer = max(0.0, hit_flash_timer - dt)
        shot_cooldown_timer = max(0.0, shot_cooldown_timer - dt)
        recoil_timer = max(0.0, recoil_timer - dt)
        muzzle_flash_timer = max(0.0, muzzle_flash_timer - dt)
        shot_trace.timer = max(0.0, shot_trace.timer - dt)
        door_in_front = find_door_in_front(player, doors)
        moving = abs(forward) + abs(strafe) > 0.01
        step_timer = max(0.0, step_timer - dt)
        if moving and step_timer <= 0.0:
            audio.play_step()
            step_timer = STEP_INTERVAL_BASE

        surface.fill((35, 35, 40))
        pygame.draw.rect(surface, (70, 78, 102), (0, internal_h // 2, internal_w, internal_h // 2))

        for col in range(internal_w):
            ray_angle = player.angle - fov / 2.0 + (col / internal_w) * fov
            ray_hit = cast_ray(player.x, player.y, ray_angle, doors)
            corrected = ray_hit.depth * math.cos(ray_angle - player.angle)
            depth_buffer[col] = corrected
            wall_h = min(int(internal_h / max(corrected, 0.0001)), internal_h)

            intensity = max(40, int(ray_hit.shade / (1.0 + corrected * 0.15)))
            if ray_hit.hit_kind == 1:
                # Door slab uses a warm palette so it stands out from wall faces.
                color = (intensity, max(30, intensity // 2), 20)
            elif ray_hit.hit_kind == 2:
                # Door frame stays darker than slab for better depth cues.
                color = (max(20, intensity // 2), max(15, intensity // 3), 10)
            else:
                color = (intensity // 2, intensity // 2, intensity)
            top = (internal_h - wall_h) // 2
            pygame.draw.line(surface, color, (col, top), (col, top + wall_h))

        render_enemy(surface, enemy, player, fov, depth_buffer, internal_w, internal_h)
        draw_shot_trace(surface, internal_w, internal_h, shot_trace)

        crosshair_color = (245, 245, 245) if hit_flash_timer <= 0.0 else (245, 120, 80)
        if door_in_front is not None:
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
        status_text = f"Enemy: DOWN | Weapon: {weapon_state}" if not enemy.alive else f"Enemy HP: {enemy.health} | Weapon: {weapon_state}"
        status_surface = font.render(status_text, True, (220, 220, 225))
        surface.blit(status_surface, (6, internal_h - 14))
        if door_in_front is not None:
            hint_surface = font.render("SPACE: Door", True, (245, 190, 75))
            surface.blit(hint_surface, (internal_w - 72, internal_h - 14))

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
