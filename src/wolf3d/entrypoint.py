from __future__ import annotations

from pathlib import Path

from .content_loader import (
    load_campaign,
    load_enemy_types,
    load_level_specs,
    load_weapon_types,
    validate_cross_refs,
)


def bootstrap(data_root: Path) -> str:
    campaign = load_campaign(data_root)
    enemies = load_enemy_types(data_root)
    weapons = load_weapon_types(data_root)
    levels = load_level_specs(data_root)
    validate_cross_refs(campaign, levels, enemies, weapons)

    return (
        f"Loaded campaign '{campaign[0].id}' with {len(campaign)} levels, "
        f"{len(enemies)} enemy types, {len(weapons)} weapon types."
    )
