from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlayerState:
    x: float = 1.5
    y: float = 1.5
    angle: float = 0.2
    move_speed: float = 3.0
    turn_speed: float = 2.2
    health: int = 100


@dataclass
class DoorState:
    open_amount: float = 0.0
    target_open: bool = False
    orientation: str = "vertical"
    auto_close_timer: float = 0.0
    slide_sign: int = 1


@dataclass
class EnemyState:
    type_id: str
    x: float
    y: float
    health: int
    alive: bool = True
    attack_cooldown: float = 0.0
    behavior_phase: float = 0.0


@dataclass(frozen=True)
class RayHit:
    depth: float
    shade: int
    hit_kind: int


@dataclass(frozen=True)
class FireResult:
    fired: bool
    hit_enemy: bool
    enemy_down: bool
    impact_distance: float
    next_cooldown: float
