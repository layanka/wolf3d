from __future__ import annotations

import math

from src.wolf3d.entities.models import DoorState, PlayerState, RayHit

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
PLAYER_RADIUS = 0.14


class WorldSimulation:
    def __init__(self, tile_map: list[str]) -> None:
        self.tile_map = tile_map
        self.doors = self._init_doors()

    def _tile_at(self, tx: int, ty: int) -> str:
        if tx < 0 or ty < 0:
            return WALL_TILE
        if ty >= len(self.tile_map) or tx >= len(self.tile_map[0]):
            return WALL_TILE
        return self.tile_map[ty][tx]

    def _door_local_hit_kind(self, fx: float, fy: float, door: DoorState) -> int:
        slab_half = (DOOR_THICKNESS_CLOSED * 0.5) * (1.0 - door.open_amount)
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

    def _door_hit_kind(self, tx: int, ty: int, x: float, y: float, door: DoorState) -> int:
        return self._door_local_hit_kind(x - tx, y - ty, door)

    def _door_blocks_point(self, tx: int, ty: int, x: float, y: float, door: DoorState) -> bool:
        return self._door_hit_kind(tx, ty, x, y, door) != 0

    def _closed_door_entry_hit_kind(self, fx: float, fy: float, door: DoorState) -> int:
        if door.orientation == "vertical":
            return 2 if abs(fy - 0.5) > DOOR_OPENING_HALF_WIDTH else 1
        return 2 if abs(fx - 0.5) > DOOR_OPENING_HALF_WIDTH else 1

    def _is_blocked_point(self, x: float, y: float) -> bool:
        tx, ty = int(x), int(y)
        tile = self._tile_at(tx, ty)
        if tile == WALL_TILE:
            return True
        if tile == DOOR_TILE:
            door = self.doors[(tx, ty)]
            if door.open_amount <= DOOR_SOLID_THRESHOLD:
                return True
            return self._door_blocks_point(tx, ty, x, y, door)
        return False

    def is_blocked_with_radius(self, x: float, y: float, radius: float = PLAYER_RADIUS) -> bool:
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
        return any(self._is_blocked_point(x + ox, y + oy) for ox, oy in offsets)

    def move_player(self, player: PlayerState, forward: float, strafe: float, dt: float) -> None:
        sin_a = math.sin(player.angle)
        cos_a = math.cos(player.angle)
        step = player.move_speed * dt
        dx_total = (cos_a * forward - sin_a * strafe) * step
        dy_total = (sin_a * forward + cos_a * strafe) * step

        max_delta = max(abs(dx_total), abs(dy_total))
        steps = max(1, int(max_delta / 0.03) + 1)
        dx = dx_total / steps
        dy = dy_total / steps

        for _ in range(steps):
            candidate_x = player.x + dx
            if not self.is_blocked_with_radius(candidate_x, player.y):
                player.x = candidate_x

            candidate_y = player.y + dy
            if not self.is_blocked_with_radius(player.x, candidate_y):
                player.y = candidate_y

    def cast_ray(self, px: float, py: float, ray_angle: float, max_depth: float = 20.0) -> RayHit:
        ray_dir_x = math.cos(ray_angle)
        ray_dir_y = math.sin(ray_angle)

        map_x = int(px)
        map_y = int(py)
        if self._tile_at(map_x, map_y) == DOOR_TILE:
            door_here = self.doors[(map_x, map_y)]
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

            tile = self._tile_at(map_x, map_y)
            if tile == WALL_TILE:
                hit_x = px + ray_dir_x * depth
                shade = 180 if int(hit_x * 2) % 2 == 0 else 220
                return RayHit(depth, shade, 0)

            if tile == DOOR_TILE:
                door = self.doors[(map_x, map_y)]
                if door.open_amount <= DOOR_SOLID_THRESHOLD:
                    hit_x = px + ray_dir_x * depth
                    hit_y = py + ray_dir_y * depth
                    hit_kind = self._closed_door_entry_hit_kind(hit_x - map_x, hit_y - map_y, door)
                    shade = 155 if hit_kind == 2 else 210
                    return RayHit(depth, shade, hit_kind)

                # opened/partially-opened door tile segment sampling
                start = max(0.0, depth) + 0.0005
                end = max(start, min(next_boundary, max_depth))
                steps = max(1, int((end - start) / 0.002) + 1)
                for i in range(steps + 1):
                    sample_depth = start + (end - start) * (i / steps)
                    x = px + ray_dir_x * sample_depth
                    y = py + ray_dir_y * sample_depth
                    hit_kind = self._door_hit_kind(map_x, map_y, x, y, door)
                    if hit_kind == 2:
                        return RayHit(sample_depth, 155, 2)
                    if hit_kind == 1:
                        return RayHit(sample_depth, 235, 1)

    def _init_doors(self) -> dict[tuple[int, int], DoorState]:
        doors: dict[tuple[int, int], DoorState] = {}
        for y, row in enumerate(self.tile_map):
            for x, tile in enumerate(row):
                if tile == DOOR_TILE:
                    left_wall = self._tile_at(x - 1, y) == WALL_TILE
                    right_wall = self._tile_at(x + 1, y) == WALL_TILE
                    up_wall = self._tile_at(x, y - 1) == WALL_TILE
                    down_wall = self._tile_at(x, y + 1) == WALL_TILE

                    if up_wall and down_wall and not (left_wall and right_wall):
                        orientation = "vertical"
                    elif left_wall and right_wall and not (up_wall and down_wall):
                        orientation = "horizontal"
                    else:
                        orientation = "vertical"

                    if orientation == "vertical":
                        slide_sign = 1 if self._tile_at(x + 1, y) != WALL_TILE else -1
                    else:
                        slide_sign = 1 if self._tile_at(x, y + 1) != WALL_TILE else -1
                    doors[(x, y)] = DoorState(orientation=orientation, slide_sign=slide_sign)
        return doors

    def toggle_door_in_front(self, player: PlayerState, max_dist: float = 0.9) -> bool:
        pos = self.find_door_in_front(player, max_dist=max_dist)
        if pos is None:
            return False
        door = self.doors[pos]
        if door.target_open:
            door.target_open = False
            door.auto_close_timer = 0.0
        else:
            door.target_open = True
            door.auto_close_timer = DOOR_AUTO_CLOSE_DELAY
        return True

    def find_door_in_front(self, player: PlayerState, max_dist: float = 0.9) -> tuple[int, int] | None:
        step = 0.05
        sin_a = math.sin(player.angle)
        cos_a = math.cos(player.angle)
        depth = step
        while depth <= max_dist:
            tx = int(player.x + cos_a * depth)
            ty = int(player.y + sin_a * depth)
            if (tx, ty) in self.doors:
                return tx, ty
            if self._tile_at(tx, ty) == WALL_TILE:
                return None
            depth += step
        return None

    def update_doors(self, player: PlayerState, dt: float) -> None:
        delta = DOOR_SPEED * dt
        for door_pos, door in self.doors.items():
            if door.target_open:
                door.open_amount = min(1.0, door.open_amount + delta)
                if door.open_amount >= 0.999:
                    if self._player_near_door(player, door_pos):
                        door.auto_close_timer = DOOR_AUTO_CLOSE_DELAY
                    else:
                        door.auto_close_timer = max(0.0, door.auto_close_timer - dt)
                        if door.auto_close_timer <= 0.0:
                            door.target_open = False
            else:
                if door.open_amount > 0.0 and self._player_in_door_tile(player, door_pos):
                    door.target_open = True
                    door.auto_close_timer = DOOR_AUTO_CLOSE_DELAY
                    continue
                door.open_amount = max(0.0, door.open_amount - delta)

    @staticmethod
    def _player_in_door_tile(player: PlayerState, door_pos: tuple[int, int]) -> bool:
        return int(player.x) == door_pos[0] and int(player.y) == door_pos[1]

    @staticmethod
    def _player_near_door(player: PlayerState, door_pos: tuple[int, int], hold_distance: float = DOOR_HOLD_DISTANCE) -> bool:
        dx = player.x - (door_pos[0] + 0.5)
        dy = player.y - (door_pos[1] + 0.5)
        return (dx * dx + dy * dy) <= hold_distance * hold_distance
