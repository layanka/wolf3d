from __future__ import annotations

import json
from pathlib import Path

from .contracts import CampaignLevel, EnemyType, LevelSpawn, LevelSpec, WeaponType


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_map(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        rows = [line.strip() for line in f if line.strip()]
    if not rows:
        raise ValueError(f"map file is empty: {path}")
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise ValueError(f"map rows have inconsistent width: {path}")
    return rows


def load_campaign(data_root: Path) -> list[CampaignLevel]:
    raw = _read_json(data_root / "campaign.json")
    levels = []
    for item in raw["levels"]:
        levels.append(
            CampaignLevel(
                id=item["id"],
                title=item["title"],
                briefing=item["briefing"],
                win_condition=item["win_condition"],
                next_level=item["next_level"],
            )
        )
    return levels


def load_enemy_types(data_root: Path) -> list[EnemyType]:
    raw = _read_json(data_root / "enemies.json")
    enemies = []
    for item in raw["enemy_types"]:
        enemies.append(
            EnemyType(
                id=item["id"],
                label=item["label"],
                health=int(item["health"]),
                move_speed=float(item["move_speed"]),
                attack_range=float(item["attack_range"]),
                attack_damage=int(item["attack_damage"]),
                behavior=item["behavior"],
            )
        )
    return enemies


def load_weapon_types(data_root: Path) -> list[WeaponType]:
    raw = _read_json(data_root / "weapons.json")
    weapons = []
    for item in raw["weapon_types"]:
        weapons.append(
            WeaponType(
                id=item["id"],
                label=item["label"],
                damage=int(item["damage"]),
                cooldown=float(item["cooldown"]),
                range=float(item["range"]),
                ammo_type=item["ammo_type"],
                magazine_size=int(item["magazine_size"]),
                reload_time=float(item["reload_time"]),
            )
        )
    return weapons


def load_level_specs(data_root: Path) -> list[LevelSpec]:
    level_dir = data_root / "levels"
    specs: list[LevelSpec] = []
    for path in sorted(level_dir.glob("*.json")):
        raw = _read_json(path)
        enemy_spawns = [LevelSpawn(type=s["type"], x=float(s["x"]), y=float(s["y"])) for s in raw["enemy_spawns"]]
        specs.append(
            LevelSpec(
                id=raw["id"],
                map_file=raw["map_file"],
                spawn=raw["spawn"],
                enemy_spawns=enemy_spawns,
                weapon_pickups=raw["weapon_pickups"],
            )
        )
    return specs


def validate_cross_refs(campaign: list[CampaignLevel], levels: list[LevelSpec], enemies: list[EnemyType], weapons: list[WeaponType]) -> None:
    level_ids = {l.id for l in levels}
    enemy_ids = {e.id for e in enemies}
    weapon_ids = {w.id for w in weapons}

    for item in campaign:
        if item.id not in level_ids:
            raise ValueError(f"campaign references missing level: {item.id}")
        if item.next_level is not None and item.next_level not in level_ids:
            raise ValueError(f"campaign next_level missing: {item.next_level}")

    for level in levels:
        for spawn in level.enemy_spawns:
            if spawn.type not in enemy_ids:
                raise ValueError(f"level {level.id} has unknown enemy type: {spawn.type}")
        for pickup in level.weapon_pickups:
            if pickup["type"] not in weapon_ids:
                raise ValueError(f"level {level.id} has unknown weapon type: {pickup['type']}")


def load_level_map(data_root: Path, level: LevelSpec) -> list[str]:
    map_path = data_root / level.map_file
    if not map_path.exists():
        raise ValueError(f"level {level.id} map file missing: {level.map_file}")
    return _read_map(map_path)
