from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CampaignLevel:
    id: str
    title: str
    briefing: str
    win_condition: str
    next_level: str | None


@dataclass(frozen=True)
class EnemyType:
    id: str
    label: str
    health: int
    move_speed: float
    attack_range: float
    attack_damage: int
    behavior: str


@dataclass(frozen=True)
class WeaponType:
    id: str
    label: str
    damage: int
    cooldown: float
    range: float
    ammo_type: str
    magazine_size: int
    reload_time: float


@dataclass(frozen=True)
class LevelSpawn:
    type: str
    x: float
    y: float


@dataclass(frozen=True)
class LevelSpec:
    id: str
    map_file: str
    spawn: dict[str, Any]
    enemy_spawns: list[LevelSpawn]
    weapon_pickups: list[dict[str, Any]]
