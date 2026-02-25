from __future__ import annotations

from pathlib import Path

from src.wolf3d.entrypoint import bootstrap
from src.wolf3d.content_loader import load_enemy_types, load_level_specs, load_weapon_types
from src.wolf3d.gameplay_state import summarize_level_gameplay
from src.wolf3d.world_state import build_world_state


def main() -> None:
    data_root = Path(__file__).resolve().parent / "game_data"
    message = bootstrap(data_root)
    print(message)
    levels = load_level_specs(data_root)
    enemies = load_enemy_types(data_root)
    weapons = load_weapon_types(data_root)
    first_level = levels[0]
    world = build_world_state(first_level)
    gameplay = summarize_level_gameplay(first_level, enemies, weapons)
    print(
        f"World shell: level={world.level_id} spawn=({world.spawn_x:.1f}, {world.spawn_y:.1f}) "
        f"enemies={world.enemy_spawn_count} pickups={world.weapon_pickup_count}"
    )
    print(
        f"Gameplay shell: enemy_types={list(gameplay.enemy_types_present)} "
        f"weapons={list(gameplay.weapon_pickups_present)} threat={gameplay.estimated_threat_score}"
    )
    print("Real game runtime shell is initialized. Next step: engine module extraction from poc_game.py")


if __name__ == "__main__":
    main()
