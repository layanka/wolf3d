from __future__ import annotations

import math
import os
import pickle
import random
import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pygame

from src.wolf3d.audio.manager import route_simulation_audio_events
from src.wolf3d.audio.runtime_audio import RuntimeAudioManager
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
from src.wolf3d.gameplay.combat import attempt_fire_multi, compute_enemy_shot_distance, normalize_angle
from src.wolf3d.gameplay.projectiles import update_projectiles
from src.wolf3d.render.frame import build_frame_snapshot
from src.wolf3d.ui.hud import format_hud_lines
from src.wolf3d.world.simulation import WorldSimulation

INTERACT_RANGE = 0.7
MAX_PLAYER_HEALTH = 100
STAMINA_MAX = 100.0
SPRINT_SPEED_MULT = 1.55
SPRINT_DRAIN_PER_SECOND = 40.0
STAMINA_RECOVER_PER_SECOND = 26.0
MIN_STAMINA_TO_SPRINT = 6.0
SPRINT_RECOVER_UNLOCK = 22.0
SPRINT_BLEND_IN_PER_SECOND = 7.0
SPRINT_BLEND_OUT_PER_SECOND = 10.0
STEP_INTERVAL_BASE = 0.35
BASE_FOV_DEG = 60.0
SPRINT_FOV_BOOST_DEG = 6.0
HEAD_BOB_FREQ_BASE = 8.0
HEAD_BOB_AMPLITUDE = 2.8
IMPACT_KICK_PIXELS = 2.0
RECOIL_BLOOM_DECAY_PER_SECOND = 0.95
MOVE_SPREAD_RAD = 0.012
SPRINT_SPREAD_RAD = 0.02
RECOIL_SPREAD_MAX_RAD = 0.055
QUICKSAVE_FILE = "quicksave.pkl"
SETTINGS_FILE = "settings.json"
MOUSE_SENSITIVITY_MIN = 0.0012
MOUSE_SENSITIVITY_MAX = 0.0065
MOUSE_SENSITIVITY_STEP = 0.0003


@dataclass
class ObjectiveNode:
    kind: Literal["extract", "console", "beacon"]
    x: float
    y: float
    activated: bool = False


@dataclass
class ObjectiveState:
    mode: Literal["key_extract", "consoles", "commander_beacon"]
    keycard_weapon_id: str | None = None
    keycard_collected: bool = False
    nodes: list[ObjectiveNode] = field(default_factory=list)


@dataclass(frozen=True)
class DifficultyProfile:
    id: Literal["easy", "normal", "hard"]
    damage_mult: float
    ammo_gain_mult: float
    heal_gain_mult: float


@dataclass
class RunCheckpoint:
    level_idx: int
    world: WorldSimulation
    player: PlayerState
    enemies: list[EnemyState]
    pickups: list[dict[str, float | str]]
    ammo_pickups: list[dict[str, float | str]]
    health_pickups: list[dict[str, float | str]]
    objective_state: ObjectiveState
    active_projectiles: list[ProjectileState]
    shot_cooldown: float
    current_weapon_idx: int
    unlocked_weapons: set[str]
    ammo_counts: dict[str, int]
    magazine_counts: dict[str, int]
    reload_timer: float
    reload_weapon_id: str | None
    campaign_elapsed: float
    level_elapsed: float
    shots_fired: int
    shots_hit: int
    kills_total: int
    level_kills: int
    level_title: str
    difficulty_id: str
    stamina: float
    sprint_exhausted: bool
    sprint_blend: float


DIFFICULTY_PROFILES: dict[str, DifficultyProfile] = {
    "easy": DifficultyProfile(id="easy", damage_mult=0.75, ammo_gain_mult=1.35, heal_gain_mult=1.25),
    "normal": DifficultyProfile(id="normal", damage_mult=1.0, ammo_gain_mult=1.0, heal_gain_mult=1.0),
    "hard": DifficultyProfile(id="hard", damage_mult=1.35, ammo_gain_mult=0.75, heal_gain_mult=0.7),
}


def build_objective_state(level_id: str) -> ObjectiveState:
    if level_id == "level_01":
        return ObjectiveState(
            mode="key_extract",
            keycard_weapon_id="smg",
            nodes=[ObjectiveNode(kind="extract", x=13.5, y=9.5)],
        )
    if level_id == "level_02":
        return ObjectiveState(
            mode="consoles",
            nodes=[
                ObjectiveNode(kind="console", x=3.5, y=1.5),
                ObjectiveNode(kind="console", x=7.5, y=5.5),
                ObjectiveNode(kind="console", x=12.5, y=9.5),
            ],
        )
    return ObjectiveState(
        mode="commander_beacon",
        nodes=[ObjectiveNode(kind="beacon", x=2.5, y=9.5)],
    )


def objective_complete(state: ObjectiveState, enemies: list[EnemyState]) -> bool:
    if state.mode == "key_extract":
        extract_node = state.nodes[0]
        return state.keycard_collected and extract_node.activated
    if state.mode == "consoles":
        return all(node.activated for node in state.nodes)
    commander_alive = any(e.alive and e.type_id == "commander" for e in enemies)
    beacon_node = state.nodes[0]
    return (not commander_alive) and beacon_node.activated


def objective_status_line(state: ObjectiveState, enemies: list[EnemyState]) -> str:
    if state.mode == "key_extract":
        card = "yes" if state.keycard_collected else "no"
        extract = "ready" if state.nodes[0].activated else "pending"
        return f"Objective: keycard={card} extraction={extract}"
    if state.mode == "consoles":
        done = sum(1 for node in state.nodes if node.activated)
        return f"Objective: consoles {done}/{len(state.nodes)}"
    commander_alive = any(e.alive and e.type_id == "commander" for e in enemies)
    commander = "alive" if commander_alive else "down"
    beacon = "online" if state.nodes[0].activated else "offline"
    return f"Objective: commander={commander} beacon={beacon}"


def nearest_objective_node(player: PlayerState, state: ObjectiveState) -> ObjectiveNode | None:
    nearest: ObjectiveNode | None = None
    nearest_dist = float("inf")
    for node in state.nodes:
        if node.activated:
            continue
        dist = math.hypot(node.x - player.x, node.y - player.y)
        if dist <= INTERACT_RANGE and dist < nearest_dist:
            nearest = node
            nearest_dist = dist
    return nearest


def objective_interact_hint(node: ObjectiveNode, state: ObjectiveState, enemies: list[EnemyState]) -> str:
    if node.kind == "extract":
        if not state.keycard_collected:
            return "Find keycard before extraction"
        return "Press X to extract"
    if node.kind == "console":
        return "Press X to disable console"
    commander_alive = any(e.alive and e.type_id == "commander" for e in enemies)
    if commander_alive:
        return "Commander must be eliminated first"
    return "Press X to activate beacon"


def current_objective_target(state: ObjectiveState, enemies: list[EnemyState]) -> tuple[float, float] | None:
    if state.mode == "key_extract":
        if state.keycard_collected:
            node = state.nodes[0]
            if not node.activated:
                return node.x, node.y
        return None
    if state.mode == "consoles":
        for node in state.nodes:
            if not node.activated:
                return node.x, node.y
        return None

    commander = next((enemy for enemy in enemies if enemy.alive and enemy.type_id == "commander"), None)
    if commander is not None:
        return commander.x, commander.y
    node = state.nodes[0]
    if not node.activated:
        return node.x, node.y
    return None


def objective_nav_hint(player: PlayerState, target: tuple[float, float] | None) -> str | None:
    if target is None:
        return None
    dx = target[0] - player.x
    dy = target[1] - player.y
    distance = math.hypot(dx, dy)
    if distance <= 0.01:
        return "Objective nav: here"

    target_angle = math.atan2(dy, dx)
    delta = normalize_angle(target_angle - player.angle)
    if abs(delta) < 0.2:
        turn_hint = "ahead"
    elif delta > 0.0:
        turn_hint = "turn right"
    else:
        turn_hint = "turn left"
    return f"Objective nav: {turn_hint} ({distance:.1f}m)"


def process_objective_interaction(player: PlayerState, state: ObjectiveState, enemies: list[EnemyState]) -> None:
    node = nearest_objective_node(player, state)
    if node is None:
        return
    if node.kind == "extract":
        if state.keycard_collected:
            node.activated = True
        return
    if node.kind == "console":
        node.activated = True
        return
    commander_alive = any(e.alive and e.type_id == "commander" for e in enemies)
    if not commander_alive:
        node.activated = True


def render_enemies(
    surface: pygame.Surface,
    enemies: list[EnemyState],
    player: PlayerState,
    fov: float,
    depth_buffer: list[float],
    view_center_y: int,
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
        top = int(view_center_y - sprite_h // 2)
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
    view_center_y: int,
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
        y = view_center_y
        color = (250, 130, 70)
        pygame.draw.circle(surface, color, (screen_x, y), size)


def draw_weapon_vfx(surface: pygame.Surface, weapon_id: str, timer: float, view_center_y: int) -> None:
    if timer <= 0.0:
        return

    cx, cy = surface.get_width() // 2, view_center_y
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


def draw_help_overlay(surface: pygame.Surface, font: pygame.font.Font) -> None:
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((6, 8, 12, 205))
    surface.blit(overlay, (0, 0))

    lines = [
        "Controls",
        "WASD / Arrows: move and strafe",
        "Hold Shift: sprint (uses stamina)",
        "Q/E or Left/Right: turn",
        "TAB: toggle mouse-look",
        "- / =: adjust mouse sensitivity",
        "F or Left Click: fire",
        "Mouse Wheel / [ ]: cycle weapons",
        "Space: door interaction",
        "X: objective interaction",
        "1/2/3/4: weapon select",
        "C: save checkpoint",
        "F5/F9: quick save/load",
        "R: reload (or restore/retry on death)",
        "M: minimap toggle",
        "Z: minimap zoom",
        "F1/F2/F3: difficulty",
        "H: toggle help",
        "ESC: quit",
    ]
    for idx, line in enumerate(lines):
        color = (245, 210, 120) if idx == 0 else (225, 225, 230)
        text_surface = font.render(line, True, color)
        surface.blit(text_surface, (18, 22 + idx * 12))


def enemy_in_sights(
    player: PlayerState,
    enemies: list[EnemyState],
    world: WorldSimulation,
    max_range: float,
) -> EnemyState | None:
    ray_hit = world.cast_ray(player.x, player.y, player.angle)
    nearest: EnemyState | None = None
    nearest_distance = float("inf")
    for enemy in enemies:
        distance = compute_enemy_shot_distance(player, enemy, ray_hit.depth, max_range)
        if distance is None:
            continue
        if distance < nearest_distance:
            nearest_distance = distance
            nearest = enemy
    return nearest


def format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def _scale_ammo(values: dict[str, int], ammo_gain_mult: float) -> dict[str, int]:
    scaled: dict[str, int] = {}
    for ammo_type, amount in values.items():
        if amount <= 0:
            scaled[ammo_type] = 0
        else:
            scaled[ammo_type] = max(1, int(round(amount * ammo_gain_mult)))
    return scaled


def default_ammo_counts(ammo_gain_mult: float) -> dict[str, int]:
    return _scale_ammo({"light": 60, "shell": 12, "rifle": 0}, ammo_gain_mult)


def pickup_ammo_bonus(weapon_id: str, ammo_gain_mult: float) -> dict[str, int]:
    if weapon_id == "smg":
        return _scale_ammo({"light": 30}, ammo_gain_mult)
    if weapon_id == "shotgun":
        return _scale_ammo({"shell": 10}, ammo_gain_mult)
    if weapon_id == "autorifle":
        return _scale_ammo({"rifle": 48}, ammo_gain_mult)
    return _scale_ammo({"light": 12}, ammo_gain_mult)


def enemy_drop_ammo(enemy_type_id: str, ammo_gain_mult: float) -> dict[str, int]:
    if enemy_type_id == "guard":
        return _scale_ammo({"light": 8}, ammo_gain_mult)
    if enemy_type_id == "assault":
        return _scale_ammo({"rifle": 12}, ammo_gain_mult)
    if enemy_type_id == "hound":
        return _scale_ammo({"light": 4}, ammo_gain_mult)
    if enemy_type_id == "commander":
        return _scale_ammo({"rifle": 24, "shell": 6}, ammo_gain_mult)
    return _scale_ammo({"light": 5}, ammo_gain_mult)


def enemy_drop_heal(enemy_type_id: str, heal_gain_mult: float) -> int:
    if enemy_type_id == "hound":
        base = 4
    elif enemy_type_id == "guard":
        base = 6
    elif enemy_type_id == "assault":
        base = 8
    elif enemy_type_id == "commander":
        base = 15
    else:
        base = 5
    return max(1, int(round(base * heal_gain_mult)))


def build_initial_magazines(
    weapon_cycle: list[str],
    weapons_by_id: dict[str, object],
    ammo_counts: dict[str, int],
) -> dict[str, int]:
    magazines = {weapon_id: 0 for weapon_id in weapon_cycle}
    if not weapon_cycle:
        return magazines
    starter_weapon_id = weapon_cycle[0]
    starter_weapon = weapons_by_id[starter_weapon_id]
    reserve = ammo_counts.get(starter_weapon.ammo_type, 0)
    rounds = min(starter_weapon.magazine_size, reserve)
    magazines[starter_weapon_id] = rounds
    ammo_counts[starter_weapon.ammo_type] = reserve - rounds
    return magazines


def refill_weapon_magazine(
    weapon_id: str,
    weapons_by_id: dict[str, object],
    ammo_counts: dict[str, int],
    magazine_counts: dict[str, int],
) -> int:
    weapon = weapons_by_id[weapon_id]
    current_mag = magazine_counts.get(weapon_id, 0)
    missing = max(0, weapon.magazine_size - current_mag)
    reserve = ammo_counts.get(weapon.ammo_type, 0)
    transfer = min(missing, reserve)
    if transfer > 0:
        magazine_counts[weapon_id] = current_mag + transfer
        ammo_counts[weapon.ammo_type] = reserve - transfer
    return transfer


def choose_fallback_weapon(
    current_idx: int,
    weapon_cycle: list[str],
    unlocked_weapons: set[str],
    weapons_by_id: dict[str, object],
    ammo_counts: dict[str, int],
    magazine_counts: dict[str, int],
) -> int:
    current_id = weapon_cycle[current_idx]
    current_weapon = weapons_by_id[current_id]
    current_mag = magazine_counts.get(current_id, 0)
    current_reserve = ammo_counts.get(current_weapon.ammo_type, 0)
    if current_mag > 0 or current_reserve > 0:
        return current_idx

    for idx, weapon_id in enumerate(weapon_cycle):
        if weapon_id not in unlocked_weapons:
            continue
        weapon = weapons_by_id[weapon_id]
        if magazine_counts.get(weapon_id, 0) > 0 or ammo_counts.get(weapon.ammo_type, 0) > 0:
            return idx
    return current_idx


def cycle_weapon_index(
    current_idx: int,
    step: int,
    weapon_cycle: list[str],
    unlocked_weapons: set[str],
) -> int:
    if not weapon_cycle or step == 0:
        return current_idx
    idx = current_idx
    for _ in range(len(weapon_cycle)):
        idx = (idx + step) % len(weapon_cycle)
        if weapon_cycle[idx] in unlocked_weapons:
            return idx
    return current_idx


def build_checkpoint(
    level_idx: int,
    world: WorldSimulation,
    player: PlayerState,
    enemies: list[EnemyState],
    pickups: list[dict[str, float | str]],
    ammo_pickups: list[dict[str, float | str]],
    health_pickups: list[dict[str, float | str]],
    objective_state: ObjectiveState,
    active_projectiles: list[ProjectileState],
    shot_cooldown: float,
    current_weapon_idx: int,
    unlocked_weapons: set[str],
    ammo_counts: dict[str, int],
    magazine_counts: dict[str, int],
    reload_timer: float,
    reload_weapon_id: str | None,
    campaign_elapsed: float,
    level_elapsed: float,
    shots_fired: int,
    shots_hit: int,
    kills_total: int,
    level_kills: int,
    level_title: str,
    difficulty_id: str,
    stamina: float,
    sprint_exhausted: bool,
    sprint_blend: float,
    ) -> RunCheckpoint:
    return RunCheckpoint(
        level_idx=level_idx,
        world=deepcopy(world),
        player=deepcopy(player),
        enemies=deepcopy(enemies),
        pickups=deepcopy(pickups),
        ammo_pickups=deepcopy(ammo_pickups),
        health_pickups=deepcopy(health_pickups),
        objective_state=deepcopy(objective_state),
        active_projectiles=deepcopy(active_projectiles),
        shot_cooldown=shot_cooldown,
        current_weapon_idx=current_weapon_idx,
        unlocked_weapons=set(unlocked_weapons),
        ammo_counts=dict(ammo_counts),
        magazine_counts=dict(magazine_counts),
        reload_timer=reload_timer,
        reload_weapon_id=reload_weapon_id,
        campaign_elapsed=campaign_elapsed,
        level_elapsed=level_elapsed,
        shots_fired=shots_fired,
        shots_hit=shots_hit,
        kills_total=kills_total,
        level_kills=level_kills,
        level_title=level_title,
        difficulty_id=difficulty_id,
        stamina=stamina,
        sprint_exhausted=sprint_exhausted,
        sprint_blend=sprint_blend,
    )


def quicksave_path(project_root: Path) -> Path:
    return project_root / "saves" / QUICKSAVE_FILE


def settings_path(project_root: Path) -> Path:
    return project_root / "saves" / SETTINGS_FILE


def load_runtime_settings(project_root: Path) -> dict[str, object]:
    path = settings_path(project_root)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def save_runtime_settings(
    project_root: Path,
    mouse_sensitivity: float,
    show_minimap: bool,
    minimap_scale_idx: int,
) -> bool:
    path = settings_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mouse_sensitivity": mouse_sensitivity,
        "show_minimap": show_minimap,
        "minimap_scale_idx": minimap_scale_idx,
    }
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except OSError:
        return False
    return True


def save_checkpoint_to_disk(project_root: Path, checkpoint: RunCheckpoint) -> bool:
    path = quicksave_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("wb") as f:
            pickle.dump(checkpoint, f)
    except (OSError, pickle.PickleError):
        return False
    return True


def load_checkpoint_from_disk(project_root: Path) -> RunCheckpoint | None:
    path = quicksave_path(project_root)
    if not path.exists():
        return None
    try:
        with path.open("rb") as f:
            loaded = pickle.load(f)
    except (OSError, pickle.PickleError, AttributeError, EOFError):
        return None
    if isinstance(loaded, RunCheckpoint):
        return loaded
    return None


def run_runtime(smoke_test: bool = False, data_root: Path | None = None, quickload: bool = False) -> None:
    if smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    project_root = Path(__file__).resolve().parents[2]
    if data_root is None:
        data_root = project_root / "game_data"

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
    audio = RuntimeAudioManager(project_root)
    clock = pygame.time.Clock()
    pygame.display.set_caption("Wolf3D Real Runtime (Campaign Shell)")

    settings = load_runtime_settings(project_root)

    fov = math.radians(BASE_FOV_DEG)
    show_minimap = bool(settings.get("show_minimap", True))
    minimap_scale_levels = (6, 8, 12)
    minimap_scale_idx = int(settings.get("minimap_scale_idx", 1))
    minimap_scale_idx = max(0, min(len(minimap_scale_levels) - 1, minimap_scale_idx))
    shot_cooldown = 0.0
    current_weapon_idx = 0
    unlocked_weapons = {weapon_cycle[0]}
    show_briefing = True
    player_dead = False
    campaign_complete = False
    active_projectiles: list[ProjectileState] = []
    weapon_fx_timer = 0.0
    weapon_fx_id = weapon_cycle[0]
    damage_flash_timer = 0.0
    hit_confirm_timer = 0.0
    campaign_elapsed = 0.0
    level_elapsed = 0.0
    shots_fired = 0
    shots_hit = 0
    kills_total = 0
    level_kills = 0
    difficulty = DIFFICULTY_PROFILES["normal"]
    ammo_counts = default_ammo_counts(difficulty.ammo_gain_mult)
    magazine_counts = build_initial_magazines(weapon_cycle, weapons_by_id, ammo_counts)
    reload_timer = 0.0
    reload_weapon_id: str | None = None
    dry_fire_timer = 0.0
    heal_flash_timer = 0.0
    checkpoint: RunCheckpoint | None = None
    checkpoint_notice_timer = 0.0
    checkpoint_notice_text = ""
    settings_notice_timer = 0.0
    settings_notice_text = ""
    show_help = False
    paused = False
    mouse_look = False
    loaded_sens = float(settings.get("mouse_sensitivity", 0.0028))
    mouse_sensitivity = max(MOUSE_SENSITIVITY_MIN, min(MOUSE_SENSITIVITY_MAX, loaded_sens))
    stamina = STAMINA_MAX
    sprint_exhausted = False
    sprint_blend = 0.0
    step_timer = 0.0
    view_bob_phase = 0.0
    recoil_bloom = 0.0

    level_idx = 0
    objective_state = build_objective_state(campaign[level_idx].id)

    def load_level_state(
        index: int,
    ) -> tuple[
        WorldSimulation,
        PlayerState,
        list[EnemyState],
        list[dict[str, float | str]],
        list[dict[str, float | str]],
        list[dict[str, float | str]],
        str,
        str,
    ]:
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
        ammo_pickups: list[dict[str, float | str]] = []
        health_pickups: list[dict[str, float | str]] = []
        return world, player, enemies, pickups, ammo_pickups, health_pickups, campaign_level.title, campaign_level.win_condition

    world, player, enemies, pickups, ammo_pickups, health_pickups, level_title, level_win_condition = load_level_state(level_idx)

    def restore_checkpoint_state() -> bool:
        nonlocal level_idx
        nonlocal world, player, enemies, pickups, ammo_pickups, health_pickups
        nonlocal objective_state, active_projectiles, shot_cooldown, current_weapon_idx
        nonlocal unlocked_weapons, ammo_counts, magazine_counts, campaign_elapsed, level_elapsed
        nonlocal shots_fired, shots_hit, kills_total, level_kills, level_title
        nonlocal difficulty, stamina, sprint_exhausted, sprint_blend, show_briefing, player_dead, campaign_complete
        nonlocal dry_fire_timer, heal_flash_timer, paused, reload_timer, reload_weapon_id, step_timer, view_bob_phase, recoil_bloom
        nonlocal checkpoint_notice_timer, checkpoint_notice_text, settings_notice_timer, settings_notice_text

        if checkpoint is None:
            return False

        level_idx = checkpoint.level_idx
        world = deepcopy(checkpoint.world)
        player = deepcopy(checkpoint.player)
        enemies = deepcopy(checkpoint.enemies)
        pickups = deepcopy(checkpoint.pickups)
        ammo_pickups = deepcopy(checkpoint.ammo_pickups)
        health_pickups = deepcopy(checkpoint.health_pickups)
        objective_state = deepcopy(checkpoint.objective_state)
        active_projectiles = deepcopy(checkpoint.active_projectiles)
        shot_cooldown = checkpoint.shot_cooldown
        current_weapon_idx = checkpoint.current_weapon_idx
        unlocked_weapons = set(checkpoint.unlocked_weapons)
        ammo_counts = dict(checkpoint.ammo_counts)
        magazine_counts = dict(checkpoint.magazine_counts)
        reload_timer = checkpoint.reload_timer
        reload_weapon_id = checkpoint.reload_weapon_id
        campaign_elapsed = checkpoint.campaign_elapsed
        level_elapsed = checkpoint.level_elapsed
        shots_fired = checkpoint.shots_fired
        shots_hit = checkpoint.shots_hit
        kills_total = checkpoint.kills_total
        level_kills = checkpoint.level_kills
        level_title = checkpoint.level_title
        difficulty = DIFFICULTY_PROFILES.get(checkpoint.difficulty_id, DIFFICULTY_PROFILES["normal"])
        stamina = checkpoint.stamina
        sprint_exhausted = checkpoint.sprint_exhausted
        sprint_blend = checkpoint.sprint_blend

        show_briefing = False
        player_dead = False
        campaign_complete = False
        dry_fire_timer = 0.0
        heal_flash_timer = 0.0
        paused = False
        step_timer = 0.0
        view_bob_phase = 0.0
        recoil_bloom = 0.0
        checkpoint_notice_text = "Checkpoint restored"
        checkpoint_notice_timer = 1.0
        settings_notice_timer = 0.0
        settings_notice_text = ""
        return True

    if quickload:
        loaded_checkpoint = load_checkpoint_from_disk(project_root)
        if loaded_checkpoint is not None:
            checkpoint = loaded_checkpoint
            restored = restore_checkpoint_state()
            if restored:
                checkpoint_notice_text = "Quick-load restored"
                checkpoint_notice_timer = 1.0
        else:
            checkpoint_notice_text = "No quick-save found"
            checkpoint_notice_timer = 1.0

    running = True
    frames = 0
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        frames += 1
        fire_requested = False
        next_level_requested = False
        interact_requested = False
        checkpoint_requested = False
        quicksave_requested = False
        reload_requested = False
        weapon_cycle_step = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:
                    show_minimap = not show_minimap
                    _ = save_runtime_settings(project_root, mouse_sensitivity, show_minimap, minimap_scale_idx)
                elif event.key == pygame.K_h:
                    show_help = not show_help
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_z:
                    minimap_scale_idx = (minimap_scale_idx + 1) % len(minimap_scale_levels)
                    _ = save_runtime_settings(project_root, mouse_sensitivity, show_minimap, minimap_scale_idx)
                elif event.key == pygame.K_TAB:
                    mouse_look = not mouse_look
                    pygame.event.set_grab(mouse_look)
                    pygame.mouse.set_visible(not mouse_look)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    mouse_sensitivity = max(MOUSE_SENSITIVITY_MIN, mouse_sensitivity - MOUSE_SENSITIVITY_STEP)
                    _ = save_runtime_settings(project_root, mouse_sensitivity, show_minimap, minimap_scale_idx)
                    settings_notice_text = f"Mouse sensitivity: {mouse_sensitivity:.4f}"
                    settings_notice_timer = 1.0
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    mouse_sensitivity = min(MOUSE_SENSITIVITY_MAX, mouse_sensitivity + MOUSE_SENSITIVITY_STEP)
                    _ = save_runtime_settings(project_root, mouse_sensitivity, show_minimap, minimap_scale_idx)
                    settings_notice_text = f"Mouse sensitivity: {mouse_sensitivity:.4f}"
                    settings_notice_timer = 1.0
                elif event.key == pygame.K_SPACE:
                    if not paused and not show_briefing and not player_dead and not campaign_complete:
                        if world.toggle_door_in_front(player):
                            audio.play("door")
                elif event.key == pygame.K_f:
                    fire_requested = True
                elif event.key == pygame.K_x:
                    interact_requested = True
                elif event.key == pygame.K_c:
                    checkpoint_requested = True
                elif event.key == pygame.K_F5:
                    checkpoint_requested = True
                    quicksave_requested = True
                elif event.key == pygame.K_F9:
                    loaded_checkpoint = load_checkpoint_from_disk(project_root)
                    if loaded_checkpoint is not None:
                        checkpoint = loaded_checkpoint
                        restored = restore_checkpoint_state()
                        if restored:
                            checkpoint_notice_text = "Quick-load restored"
                            checkpoint_notice_timer = 1.0
                    else:
                        restored = restore_checkpoint_state()
                        if not restored:
                            checkpoint_notice_text = "No quick-save found"
                            checkpoint_notice_timer = 1.0
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
                elif event.key == pygame.K_LEFTBRACKET:
                    weapon_cycle_step = -1
                elif event.key == pygame.K_RIGHTBRACKET:
                    weapon_cycle_step = 1
                elif event.key == pygame.K_r and player_dead:
                    restored = restore_checkpoint_state() if checkpoint is not None and checkpoint.level_idx == level_idx else False
                    if not restored:
                        world, player, enemies, pickups, ammo_pickups, health_pickups, level_title, level_win_condition = load_level_state(level_idx)
                        shot_cooldown = 0.0
                        current_weapon_idx = 0
                        show_briefing = True
                        objective_state = build_objective_state(campaign[level_idx].id)
                        level_elapsed = 0.0
                        level_kills = 0
                        stamina = STAMINA_MAX
                        sprint_exhausted = False
                        sprint_blend = 0.0
                        step_timer = 0.0
                        view_bob_phase = 0.0
                        recoil_bloom = 0.0
                        reload_timer = 0.0
                        reload_weapon_id = None
                    player_dead = False
                    campaign_complete = False
                    dry_fire_timer = 0.0
                    heal_flash_timer = 0.0
                    step_timer = 0.0
                    view_bob_phase = 0.0
                    recoil_bloom = 0.0
                elif event.key == pygame.K_r and not paused and not show_briefing and not player_dead and not campaign_complete:
                    reload_requested = True
                elif event.key == pygame.K_n and campaign_complete:
                    level_idx = 0
                    world, player, enemies, pickups, ammo_pickups, health_pickups, level_title, level_win_condition = load_level_state(level_idx)
                    shot_cooldown = 0.0
                    current_weapon_idx = 0
                    unlocked_weapons = {weapon_cycle[0]}
                    show_briefing = True
                    player_dead = False
                    campaign_complete = False
                    active_projectiles.clear()
                    objective_state = build_objective_state(campaign[level_idx].id)
                    campaign_elapsed = 0.0
                    level_elapsed = 0.0
                    shots_fired = 0
                    shots_hit = 0
                    kills_total = 0
                    level_kills = 0
                    ammo_counts = default_ammo_counts(difficulty.ammo_gain_mult)
                    magazine_counts = build_initial_magazines(weapon_cycle, weapons_by_id, ammo_counts)
                    reload_timer = 0.0
                    reload_weapon_id = None
                    dry_fire_timer = 0.0
                    heal_flash_timer = 0.0
                    stamina = STAMINA_MAX
                    sprint_exhausted = False
                    sprint_blend = 0.0
                    step_timer = 0.0
                    view_bob_phase = 0.0
                    recoil_bloom = 0.0
                    checkpoint = None
                    checkpoint_notice_timer = 0.0
                elif event.key == pygame.K_F1:
                    difficulty = DIFFICULTY_PROFILES["easy"]
                elif event.key == pygame.K_F2:
                    difficulty = DIFFICULTY_PROFILES["normal"]
                elif event.key == pygame.K_F3:
                    difficulty = DIFFICULTY_PROFILES["hard"]
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                fire_requested = True
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    weapon_cycle_step = 1
                elif event.y < 0:
                    weapon_cycle_step = -1
            elif event.type == pygame.MOUSEMOTION and mouse_look and not paused and not player_dead and not campaign_complete:
                player.angle += event.rel[0] * mouse_sensitivity

        keys = pygame.key.get_pressed()
        forward = (float(keys[pygame.K_w]) - float(keys[pygame.K_s])) + (
            float(keys[pygame.K_UP]) - float(keys[pygame.K_DOWN])
        )
        strafe = float(keys[pygame.K_d]) - float(keys[pygame.K_a])
        turn = float(keys[pygame.K_RIGHT]) - float(keys[pygame.K_LEFT])
        wants_sprint = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        if keys[pygame.K_q]:
            turn -= 1.0
        if keys[pygame.K_e]:
            turn += 1.0

        simulation_active = not paused and not show_briefing and not player_dead and not campaign_complete
        moving = abs(forward) > 0.01 or abs(strafe) > 0.01
        if sprint_exhausted and stamina >= SPRINT_RECOVER_UNLOCK:
            sprint_exhausted = False
        sprint_requested = simulation_active and moving and wants_sprint
        can_sprint = sprint_requested and (not sprint_exhausted) and stamina > MIN_STAMINA_TO_SPRINT
        sprint_target = 1.0 if can_sprint else 0.0
        if sprint_target > sprint_blend:
            sprint_blend = min(1.0, sprint_blend + SPRINT_BLEND_IN_PER_SECOND * dt)
        elif sprint_target < sprint_blend:
            sprint_blend = max(0.0, sprint_blend - SPRINT_BLEND_OUT_PER_SECOND * dt)
        is_sprinting = sprint_blend > 0.1

        base_speed = player.move_speed
        speed_mult = 1.0 + (SPRINT_SPEED_MULT - 1.0) * sprint_blend
        player.move_speed = base_speed * speed_mult
        fov = math.radians(BASE_FOV_DEG + SPRINT_FOV_BOOST_DEG * sprint_blend)

        player.angle += 0.0 if (player_dead or campaign_complete or paused) else turn * player.turn_speed * dt
        if simulation_active:
            campaign_elapsed += dt
            level_elapsed += dt
        world.update_doors(player, 0.0 if paused else dt)
        if not player_dead and not campaign_complete and not paused:
            world.move_player(player, forward, strafe, dt)
        player.move_speed = base_speed

        if simulation_active:
            if moving and sprint_blend > 0.05:
                stamina = max(0.0, stamina - SPRINT_DRAIN_PER_SECOND * sprint_blend * dt)
            else:
                stamina = min(STAMINA_MAX, stamina + STAMINA_RECOVER_PER_SECOND * dt)
            step_timer = max(0.0, step_timer - dt)
            if moving and step_timer <= 0.0:
                audio.play_step()
                step_interval = max(0.14, STEP_INTERVAL_BASE / max(1.0, speed_mult))
                step_timer = step_interval
            bob_freq = HEAD_BOB_FREQ_BASE + sprint_blend * 2.5
            view_bob_phase = (view_bob_phase + dt * bob_freq * math.tau) % math.tau
        else:
            view_bob_phase = 0.0
        if stamina <= 0.01:
            sprint_exhausted = True
        melee_damage = 0
        spawned_projectiles: list[ProjectileState] = []
        if simulation_active:
            melee_damage, spawned_projectiles = update_enemies(player, enemies, enemy_types, world, dt)
        if spawned_projectiles:
            active_projectiles.extend(spawned_projectiles)

        active_projectiles, projectile_damage = update_projectiles(world, player, active_projectiles, 0.0 if paused else dt)
        enemy_damage_scale = (1.0 + level_idx * 0.2) * difficulty.damage_mult
        scaled_damage = int(math.ceil((melee_damage + projectile_damage) * enemy_damage_scale))
        if scaled_damage > 0:
            damage_flash_timer = 0.17
        player.health = max(0, player.health - scaled_damage)
        player_dead = player.health <= 0

        for pickup in pickups[:]:
            dx = float(pickup["x"]) - player.x
            dy = float(pickup["y"]) - player.y
            if dx * dx + dy * dy <= 0.35 * 0.35:
                pickup_type = str(pickup["type"])
                unlocked_weapons.add(pickup_type)
                magazine_counts.setdefault(pickup_type, 0)
                for ammo_type, amount in pickup_ammo_bonus(pickup_type, difficulty.ammo_gain_mult).items():
                    ammo_counts[ammo_type] = ammo_counts.get(ammo_type, 0) + amount
                refill_weapon_magazine(pickup_type, weapons_by_id, ammo_counts, magazine_counts)
                if objective_state.keycard_weapon_id == pickup_type:
                    objective_state.keycard_collected = True
                pickups.remove(pickup)
        for ammo_pickup in ammo_pickups[:]:
            dx = float(ammo_pickup["x"]) - player.x
            dy = float(ammo_pickup["y"]) - player.y
            if dx * dx + dy * dy <= 0.35 * 0.35:
                pickup_ammo_type = str(ammo_pickup["ammo_type"])
                pickup_amount = int(ammo_pickup["amount"])
                ammo_counts[pickup_ammo_type] = ammo_counts.get(pickup_ammo_type, 0) + pickup_amount
                ammo_pickups.remove(ammo_pickup)
        for health_pickup in health_pickups[:]:
            dx = float(health_pickup["x"]) - player.x
            dy = float(health_pickup["y"]) - player.y
            if dx * dx + dy * dy <= 0.35 * 0.35:
                heal_amount = int(health_pickup["amount"])
                if player.health < MAX_PLAYER_HEALTH:
                    player.health = min(MAX_PLAYER_HEALTH, player.health + heal_amount)
                    heal_flash_timer = 0.15
                health_pickups.remove(health_pickup)

        for enemy in enemies:
            if enemy.alive or enemy.loot_dropped:
                continue
            enemy.loot_dropped = True
            for ammo_type, amount in enemy_drop_ammo(enemy.type_id, difficulty.ammo_gain_mult).items():
                ammo_pickups.append(
                    {"ammo_type": ammo_type, "amount": float(amount), "x": enemy.x, "y": enemy.y}
                )
            health_pickups.append(
                {
                    "amount": float(enemy_drop_heal(enemy.type_id, difficulty.heal_gain_mult)),
                    "x": enemy.x + 0.08,
                    "y": enemy.y - 0.06,
                }
            )
            kills_total += 1
            level_kills += 1

        if interact_requested and simulation_active:
            process_objective_interaction(player, objective_state, enemies)
        if checkpoint_requested and simulation_active:
            checkpoint = build_checkpoint(
                level_idx=level_idx,
                world=world,
                player=player,
                enemies=enemies,
                pickups=pickups,
                ammo_pickups=ammo_pickups,
                health_pickups=health_pickups,
                objective_state=objective_state,
                active_projectiles=active_projectiles,
                shot_cooldown=shot_cooldown,
                current_weapon_idx=current_weapon_idx,
                unlocked_weapons=unlocked_weapons,
                ammo_counts=ammo_counts,
                magazine_counts=magazine_counts,
                reload_timer=reload_timer,
                reload_weapon_id=reload_weapon_id,
                campaign_elapsed=campaign_elapsed,
                level_elapsed=level_elapsed,
                shots_fired=shots_fired,
                shots_hit=shots_hit,
                kills_total=kills_total,
                level_kills=level_kills,
                level_title=level_title,
                difficulty_id=difficulty.id,
                stamina=stamina,
                sprint_exhausted=sprint_exhausted,
                sprint_blend=sprint_blend,
            )
            if quicksave_requested:
                disk_saved = save_checkpoint_to_disk(project_root, checkpoint)
                checkpoint_notice_text = "Quick-save written" if disk_saved else "Quick-save failed"
            else:
                checkpoint_notice_text = "Checkpoint saved"
            checkpoint_notice_timer = 1.0

        prev_weapon_idx = current_weapon_idx
        while weapon_cycle[current_weapon_idx] not in unlocked_weapons and current_weapon_idx > 0:
            current_weapon_idx -= 1
        if weapon_cycle_step != 0:
            current_weapon_idx = cycle_weapon_index(current_weapon_idx, weapon_cycle_step, weapon_cycle, unlocked_weapons)
        current_weapon_idx = choose_fallback_weapon(
            current_weapon_idx, weapon_cycle, unlocked_weapons, weapons_by_id, ammo_counts, magazine_counts
        )
        if reload_timer > 0.0 and prev_weapon_idx != current_weapon_idx:
            selected_weapon_id = weapon_cycle[current_weapon_idx]
            if reload_weapon_id is not None and selected_weapon_id != reload_weapon_id:
                reload_timer = 0.0
                reload_weapon_id = None

        active_weapon = weapons_by_id[weapon_cycle[current_weapon_idx]]
        target_enemy = enemy_in_sights(player, enemies, world, active_weapon.range)
        ammo_type = active_weapon.ammo_type
        reserve_ammo = ammo_counts.get(ammo_type, 0)
        magazine_ammo = magazine_counts.get(active_weapon.id, 0)
        can_fire = magazine_ammo > 0 and reload_timer <= 0.0
        if (
            reload_requested
            and simulation_active
            and reload_timer <= 0.0
            and magazine_ammo < active_weapon.magazine_size
            and reserve_ammo > 0
        ):
            reload_timer = active_weapon.reload_time
            reload_weapon_id = active_weapon.id
        if fire_requested and simulation_active:
            if reload_timer > 0.0:
                pass
            else:
                if not can_fire and magazine_ammo <= 0 and reserve_ammo > 0:
                    reload_timer = active_weapon.reload_time
                    reload_weapon_id = active_weapon.id
                elif not can_fire:
                    dry_fire_timer = 0.15
                ray_offsets: tuple[float, ...] = (0.0,)
                per_pellet_damage = active_weapon.damage
                if active_weapon.id == "shotgun":
                    ray_offsets = (-0.08, -0.04, 0.0, 0.04, 0.08)
                    per_pellet_damage = max(1, active_weapon.damage // 3)
                else:
                    dynamic_spread = recoil_bloom
                    if moving:
                        dynamic_spread += MOVE_SPREAD_RAD
                    if is_sprinting:
                        dynamic_spread += SPRINT_SPREAD_RAD
                    dynamic_spread = min(RECOIL_SPREAD_MAX_RAD, dynamic_spread)
                    if dynamic_spread > 0.0005:
                        ray_offsets = (random.uniform(-dynamic_spread, dynamic_spread),)
                if can_fire:
                    fire, _target = attempt_fire_multi(
                        shot_cooldown,
                        player,
                        world,
                        enemies,
                        damage=per_pellet_damage,
                        max_range=active_weapon.range,
                        cooldown=active_weapon.cooldown,
                        ray_offsets=ray_offsets,
                    )
                    shot_cooldown = fire.next_cooldown
                    for event_name in route_simulation_audio_events(False, fire):
                        audio.play(event_name)
                    if fire.fired:
                        magazine_counts[active_weapon.id] = max(0, magazine_ammo - 1)
                        if active_weapon.id == "smg":
                            recoil_bloom = min(RECOIL_SPREAD_MAX_RAD, recoil_bloom + 0.0085)
                        elif active_weapon.id == "autorifle":
                            recoil_bloom = min(RECOIL_SPREAD_MAX_RAD, recoil_bloom + 0.006)
                        elif active_weapon.id == "pistol":
                            recoil_bloom = min(RECOIL_SPREAD_MAX_RAD, recoil_bloom + 0.01)
                        shots_fired += 1
                    if fire.hit_enemy:
                        shots_hit += 1
                        hit_confirm_timer = 0.08
                    weapon_fx_id = active_weapon.id
                    if active_weapon.id == "smg":
                        weapon_fx_timer = 0.045
                    elif active_weapon.id == "shotgun":
                        weapon_fx_timer = 0.11
                    elif active_weapon.id == "autorifle":
                        weapon_fx_timer = 0.075
                    else:
                        weapon_fx_timer = 0.065
        decay_dt = 0.0 if paused else dt
        shot_cooldown = max(0.0, shot_cooldown - decay_dt)
        weapon_fx_timer = max(0.0, weapon_fx_timer - decay_dt)
        damage_flash_timer = max(0.0, damage_flash_timer - decay_dt)
        hit_confirm_timer = max(0.0, hit_confirm_timer - decay_dt)
        recoil_bloom = max(0.0, recoil_bloom - RECOIL_BLOOM_DECAY_PER_SECOND * decay_dt)
        dry_fire_timer = max(0.0, dry_fire_timer - decay_dt)
        heal_flash_timer = max(0.0, heal_flash_timer - decay_dt)
        checkpoint_notice_timer = max(0.0, checkpoint_notice_timer - decay_dt)
        settings_notice_timer = max(0.0, settings_notice_timer - decay_dt)
        was_reloading = reload_timer > 0.0
        reload_timer = max(0.0, reload_timer - decay_dt)
        if was_reloading and reload_timer <= 0.0 and reload_weapon_id is not None:
            refill_weapon_magazine(reload_weapon_id, weapons_by_id, ammo_counts, magazine_counts)
            reload_weapon_id = None
        level_cleared = objective_complete(objective_state, enemies)
        if level_cleared and not player_dead and next_level_requested:
            if level_idx < len(campaign) - 1:
                level_idx += 1
                world, player, enemies, pickups, ammo_pickups, health_pickups, level_title, level_win_condition = load_level_state(level_idx)
                shot_cooldown = 0.0
                current_weapon_idx = 0
                show_briefing = True
                active_projectiles.clear()
                objective_state = build_objective_state(campaign[level_idx].id)
                for ammo_type, amount in _scale_ammo(
                    {"light": 12, "shell": 4, "rifle": 10},
                    difficulty.ammo_gain_mult,
                ).items():
                    ammo_counts[ammo_type] = ammo_counts.get(ammo_type, 0) + amount
                for weapon_id in list(magazine_counts):
                    if weapon_id in unlocked_weapons:
                        refill_weapon_magazine(weapon_id, weapons_by_id, ammo_counts, magazine_counts)
                level_elapsed = 0.0
                level_kills = 0
                sprint_exhausted = False
                sprint_blend = 0.0
                step_timer = 0.0
                view_bob_phase = 0.0
                recoil_bloom = 0.0
                reload_timer = 0.0
                reload_weapon_id = None
                checkpoint = None
                checkpoint_notice_timer = 0.0
            else:
                campaign_complete = True

        bob_offset = math.sin(view_bob_phase) * HEAD_BOB_AMPLITUDE if simulation_active and moving else 0.0
        impact_offset = -IMPACT_KICK_PIXELS * (damage_flash_timer / 0.17) if damage_flash_timer > 0.0 else 0.0
        view_center_y = int((internal_h // 2) + bob_offset + impact_offset)
        view_center_y = max(24, min(internal_h - 24, view_center_y))

        surface.fill((35, 35, 40))
        pygame.draw.rect(surface, (70, 78, 102), (0, view_center_y, internal_w, internal_h - view_center_y))
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
            top = int(view_center_y - wall_h // 2)
            pygame.draw.line(surface, color, (col, top), (col, top + wall_h))

        render_enemies(surface, enemies, player, fov, depth_buffer, view_center_y)
        render_projectiles(surface, player, active_projectiles, fov, depth_buffer, view_center_y)

        snapshot = build_frame_snapshot(player, enemies, world, shot_cooldown, active_weapon.label)
        hud_lines = [f"Level {level_idx + 1}/{len(campaign)}: {level_title}"] + format_hud_lines(snapshot)
        hud_lines.append(f"Goal: {level_win_condition}")
        if level_cleared:
            if campaign_complete:
                hud_lines.append("Campaign complete! Press N for a new run")
            else:
                hud_lines.append("Level clear! Press ENTER for next level")
        if show_briefing:
            hud_lines.append("Mission briefing active: ENTER to deploy")
        if paused:
            hud_lines.append("Paused: press P to resume")
        if show_help:
            hud_lines.append("Help open: press H to close")
        if mouse_look:
            hud_lines.append("Mouse-look: TAB to release")
        if show_minimap:
            hud_lines.append(f"Minimap zoom: {minimap_scale_levels[minimap_scale_idx]} (Z)")
        if player_dead:
            if checkpoint is not None and checkpoint.level_idx == level_idx:
                hud_lines.append("You were eliminated: press R to restore checkpoint")
            else:
                hud_lines.append("You were eliminated: press R to retry level")
        elif target_enemy is not None:
            hud_lines.append("Target in sights")
        hud_lines.append(objective_status_line(objective_state, enemies))
        if active_projectiles:
            hud_lines.append(f"Incoming: {len(active_projectiles)}")
        if level_idx > 0:
            hud_lines.append(f"Threat scale: x{1.0 + level_idx * 0.2:.1f}")
        if hit_confirm_timer > 0.0:
            hud_lines.append("Hit confirmed")
        if shots_fired > 0:
            accuracy = int((shots_hit / shots_fired) * 100)
            hud_lines.append(f"Accuracy: {accuracy}%")
        hud_lines.append(f"Stamina: {int(stamina)}%")
        if sprint_exhausted:
            hud_lines.append("Exhausted: recover stamina")
        elif simulation_active and is_sprinting:
            hud_lines.append("Sprinting")
        if active_weapon.id != "shotgun":
            stability = max(0, min(100, int(100 - (recoil_bloom / RECOIL_SPREAD_MAX_RAD) * 100)))
            hud_lines.append(f"Weapon stability: {stability}%")
        active_mag = magazine_counts.get(active_weapon.id, 0)
        active_reserve = ammo_counts.get(ammo_type, 0)
        hud_lines.append(f"Ammo ({ammo_type}): {active_mag}/{active_weapon.magazine_size} | reserve {active_reserve}")
        hud_lines.append(
            f"Reserves L/S/R: {ammo_counts.get('light', 0)}/{ammo_counts.get('shell', 0)}/{ammo_counts.get('rifle', 0)}"
        )
        hud_lines.append(f"Difficulty: {difficulty.id} (F1/F2/F3)")
        if active_mag == 0 and active_reserve > 0 and reload_timer <= 0.0:
            hud_lines.append("Press R to reload")
        elif reload_timer > 0.0 and reload_weapon_id == active_weapon.id:
            hud_lines.append("Reloading...")
        if active_mag <= 3 and (active_mag + active_reserve) > 0:
            hud_lines.append("Low ammo")
        if dry_fire_timer > 0.0 and active_mag <= 0 and active_reserve <= 0:
            hud_lines.append("Out of ammo")
        if player.health <= 30:
            hud_lines.append("Low health")
        if heal_flash_timer > 0.0:
            hud_lines.append("Medkit used")
        if checkpoint_notice_timer > 0.0:
            hud_lines.append(checkpoint_notice_text)
        if settings_notice_timer > 0.0:
            hud_lines.append(settings_notice_text)
        nav_hint = objective_nav_hint(player, current_objective_target(objective_state, enemies))
        if nav_hint is not None:
            hud_lines.append(nav_hint)
        hud_lines.append(f"Time L/C: {format_duration(level_elapsed)} / {format_duration(campaign_elapsed)}")
        hud_lines.append(f"Kills L/C: {level_kills} / {kills_total}")
        objective_hint_node = nearest_objective_node(player, objective_state)
        if objective_hint_node is not None:
            hud_lines.append(objective_interact_hint(objective_hint_node, objective_state, enemies))
        for i, line in enumerate(hud_lines):
            color = (245, 210, 120) if "Level clear" in line else (220, 220, 225)
            hud_surface = font.render(line, True, color)
            surface.blit(hud_surface, (6, internal_h - 36 + i * 10))

        cx, cy = internal_w // 2, view_center_y
        if target_enemy is not None:
            crosshair_color = (245, 90, 90)
        elif snapshot.door_in_front:
            crosshair_color = (245, 190, 75)
        else:
            crosshair_color = (245, 245, 245)
        pygame.draw.line(surface, crosshair_color, (cx - 4, cy), (cx + 4, cy), 1)
        pygame.draw.line(surface, crosshair_color, (cx, cy - 4), (cx, cy + 4), 1)
        draw_weapon_vfx(surface, weapon_fx_id, weapon_fx_timer, view_center_y)

        if show_minimap:
            scale = minimap_scale_levels[minimap_scale_idx]
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
            for ammo_pickup in ammo_pickups:
                ax = int(pad + float(ammo_pickup["x"]) * scale)
                ay = int(pad + float(ammo_pickup["y"]) * scale)
                pygame.draw.circle(surface, (120, 230, 235), (ax, ay), 1)
            for health_pickup in health_pickups:
                hx = int(pad + float(health_pickup["x"]) * scale)
                hy = int(pad + float(health_pickup["y"]) * scale)
                pygame.draw.circle(surface, (80, 240, 120), (hx, hy), 1)
            for projectile in active_projectiles:
                sx = int(pad + projectile.x * scale)
                sy = int(pad + projectile.y * scale)
                if 0 <= sx < internal_w and 0 <= sy < internal_h:
                    pygame.draw.circle(surface, (250, 120, 70), (sx, sy), 1)
            for node in objective_state.nodes:
                ox = int(pad + node.x * scale)
                oy = int(pad + node.y * scale)
                color = (80, 225, 245) if not node.activated else (70, 130, 140)
                pygame.draw.circle(surface, color, (ox, oy), 2)

        if show_briefing:
            overlay = pygame.Surface((internal_w, internal_h), pygame.SRCALPHA)
            overlay.fill((8, 8, 12, 190))
            surface.blit(overlay, (0, 0))
            title_surface = font.render(level_title, True, (245, 210, 120))
            briefing_surface = font.render(campaign[level_idx].briefing, True, (232, 232, 236))
            win_surface = font.render(level_win_condition, True, (218, 226, 188))
            deploy_surface = font.render("Press ENTER to deploy", True, (245, 210, 120))
            surface.blit(title_surface, (16, 70))
            surface.blit(briefing_surface, (16, 86))
            surface.blit(win_surface, (16, 102))
            surface.blit(deploy_surface, (16, 118))
        elif player_dead:
            overlay = pygame.Surface((internal_w, internal_h), pygame.SRCALPHA)
            overlay.fill((18, 2, 2, 170))
            surface.blit(overlay, (0, 0))
            dead_surface = font.render("MISSION FAILED", True, (235, 125, 125))
            retry_text = "Press R to restore checkpoint" if checkpoint is not None and checkpoint.level_idx == level_idx else "Press R to retry this level"
            retry_surface = font.render(retry_text, True, (235, 210, 160))
            surface.blit(dead_surface, (16, 86))
            surface.blit(retry_surface, (16, 102))
        elif campaign_complete:
            overlay = pygame.Surface((internal_w, internal_h), pygame.SRCALPHA)
            overlay.fill((6, 18, 10, 170))
            surface.blit(overlay, (0, 0))
            win_surface = font.render("MISSION COMPLETE", True, (145, 235, 165))
            acc = int((shots_hit / shots_fired) * 100) if shots_fired > 0 else 0
            stats_surface = font.render(
                f"Stats: time {format_duration(campaign_elapsed)} | kills {kills_total} | acc {acc}%",
                True,
                (225, 235, 185),
            )
            restart_surface = font.render("Press N to restart campaign", True, (235, 235, 185))
            surface.blit(win_surface, (16, 86))
            surface.blit(stats_surface, (16, 102))
            surface.blit(restart_surface, (16, 118))
        elif paused:
            overlay = pygame.Surface((internal_w, internal_h), pygame.SRCALPHA)
            overlay.fill((8, 10, 14, 165))
            surface.blit(overlay, (0, 0))
            paused_surface = font.render("PAUSED", True, (240, 220, 150))
            resume_surface = font.render("Press P to continue", True, (230, 230, 220))
            surface.blit(paused_surface, (16, 86))
            surface.blit(resume_surface, (16, 102))

        if damage_flash_timer > 0.0:
            flash = pygame.Surface((internal_w, internal_h), pygame.SRCALPHA)
            alpha = int(80 * (damage_flash_timer / 0.17))
            flash.fill((170, 18, 18, max(0, min(120, alpha))))
            surface.blit(flash, (0, 0))
        if heal_flash_timer > 0.0:
            flash = pygame.Surface((internal_w, internal_h), pygame.SRCALPHA)
            alpha = int(70 * (heal_flash_timer / 0.15))
            flash.fill((20, 140, 55, max(0, min(100, alpha))))
            surface.blit(flash, (0, 0))
        if show_help:
            draw_help_overlay(surface, font)

        screen.blit(pygame.transform.scale(surface, (screen_w, screen_h)), (0, 0))
        pygame.display.flip()

        if smoke_test and frames >= 5:
            running = False

    pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)
    pygame.quit()
