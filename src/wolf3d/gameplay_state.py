from __future__ import annotations

from dataclasses import dataclass

from .contracts import EnemyType, LevelSpec, WeaponType


@dataclass(frozen=True)
class GameplaySummary:
    level_id: str
    enemy_types_present: tuple[str, ...]
    weapon_pickups_present: tuple[str, ...]
    estimated_threat_score: int


def summarize_level_gameplay(level: LevelSpec, enemy_types: list[EnemyType], weapon_types: list[WeaponType]) -> GameplaySummary:
    enemy_by_id = {e.id: e for e in enemy_types}
    weapon_ids = {w.id for w in weapon_types}

    present_enemies: list[str] = []
    threat_score = 0
    for spawn in level.enemy_spawns:
        if spawn.type in enemy_by_id:
            enemy = enemy_by_id[spawn.type]
            present_enemies.append(enemy.id)
            threat_score += enemy.health + enemy.attack_damage

    present_weapons: list[str] = []
    for pickup in level.weapon_pickups:
        weapon_id = str(pickup.get("type", ""))
        if weapon_id in weapon_ids:
            present_weapons.append(weapon_id)

    return GameplaySummary(
        level_id=level.id,
        enemy_types_present=tuple(sorted(set(present_enemies))),
        weapon_pickups_present=tuple(sorted(set(present_weapons))),
        estimated_threat_score=threat_score,
    )
