from __future__ import annotations

from pathlib import Path

import pytest

from src.wolf3d.content_loader import load_campaign, load_enemy_types, load_level_specs, load_weapon_types, validate_cross_refs
from src.wolf3d.contracts import LevelSpec, LevelSpawn, ScriptedEvent


def _data_root() -> Path:
    return Path(__file__).resolve().parents[1] / "game_data"


def test_level_specs_include_scripted_events() -> None:
    specs = load_level_specs(_data_root())
    assert specs, "expected at least one level spec"
    for spec in specs:
        assert spec.scripted_events, f"expected scripted events for {spec.id}"
        for event in spec.scripted_events:
            assert event.id
            assert event.trigger_radius > 0.0
            assert event.enemy_spawns, f"event {event.id} in {spec.id} should spawn enemies"


def test_validate_cross_refs_rejects_unknown_script_enemy_type() -> None:
    data_root = _data_root()
    campaign = load_campaign(data_root)
    levels = load_level_specs(data_root)
    enemies = load_enemy_types(data_root)
    weapons = load_weapon_types(data_root)

    base = levels[0]
    broken_event = ScriptedEvent(
        id="bad_spawn",
        trigger_x=2.5,
        trigger_y=2.5,
        trigger_radius=1.0,
        enemy_spawns=[LevelSpawn(type="unknown_enemy", x=3.5, y=3.5)],
        announcement="broken",
    )
    broken_level = LevelSpec(
        id=base.id,
        map_file=base.map_file,
        spawn=base.spawn,
        enemy_spawns=base.enemy_spawns,
        weapon_pickups=base.weapon_pickups,
        scripted_events=[broken_event],
    )
    replaced = [broken_level] + [lvl for lvl in levels if lvl.id != base.id]

    with pytest.raises(ValueError, match="unknown enemy type"):
        validate_cross_refs(campaign, replaced, enemies, weapons)
