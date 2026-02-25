from __future__ import annotations

from src.wolf3d.runtime import (
    _level_econ_factor,
    _scale_ammo,
    enemy_ammo_drop_chance,
    enemy_drop_ammo,
    enemy_drop_heal,
    enemy_heal_drop_chance,
)


def test_scale_ammo_preserves_minimum_positive_amount() -> None:
    scaled = _scale_ammo({"light": 1, "shell": 0}, ammo_gain_mult=0.2)
    assert scaled["light"] == 1
    assert scaled["shell"] == 0


def test_level_econ_factor_increases_and_caps() -> None:
    assert _level_econ_factor(0) == 1.0
    assert _level_econ_factor(1) > _level_econ_factor(0)
    assert _level_econ_factor(8) == _level_econ_factor(99)


def test_enemy_drop_ammo_scales_by_level() -> None:
    early = enemy_drop_ammo("guard", ammo_gain_mult=1.0, level_idx=0)["light"]
    late = enemy_drop_ammo("guard", ammo_gain_mult=1.0, level_idx=2)["light"]
    assert late >= early


def test_enemy_drop_heal_scales_with_level() -> None:
    early = enemy_drop_heal("assault", heal_gain_mult=1.0, level_idx=0)
    late = enemy_drop_heal("assault", heal_gain_mult=1.0, level_idx=2)
    assert late >= early


def test_drop_chances_are_clamped() -> None:
    for difficulty in ("easy", "normal", "hard"):
        for level_idx in (0, 2, 8):
            ammo_chance = enemy_ammo_drop_chance("hound", difficulty, level_idx)
            heal_chance = enemy_heal_drop_chance("hound", difficulty, level_idx, missing_health=50)
            assert 0.08 <= ammo_chance <= 1.0
            assert 0.08 <= heal_chance <= 1.0


def test_heal_drop_chance_respects_health_pressure() -> None:
    low_pressure = enemy_heal_drop_chance("guard", "normal", level_idx=1, missing_health=10)
    high_pressure = enemy_heal_drop_chance("guard", "normal", level_idx=1, missing_health=90)
    assert high_pressure > low_pressure
