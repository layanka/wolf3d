from __future__ import annotations

from pathlib import Path

from src.wolf3d.entrypoint import bootstrap
from src.wolf3d.content_loader import load_enemy_types, load_level_specs, load_weapon_types
from src.wolf3d.entities.models import EnemyState, PlayerState
from src.wolf3d.gameplay.combat import attempt_fire
from src.wolf3d.gameplay_state import summarize_level_gameplay
from src.wolf3d.world.simulation import WorldSimulation
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

    # Lane B/C integration smoke: world simulation + combat attempt.
    map_stub = [
        "111111111111",
        "100000000001",
        "101111011101",
        "100002000001",
        "101101111101",
        "100100000001",
        "101101011101",
        "100001000001",
        "101111011101",
        "100000000001",
        "111111111111",
    ]
    world_sim = WorldSimulation(map_stub)
    player = PlayerState(x=world.spawn_x, y=world.spawn_y, angle=world.spawn_angle)
    first_enemy_spec = first_level.enemy_spawns[0]
    first_enemy_type = {e.id: e for e in enemies}[first_enemy_spec.type]
    enemy = EnemyState(type_id=first_enemy_type.id, x=first_enemy_spec.x, y=first_enemy_spec.y, health=first_enemy_type.health)

    door_toggled = world_sim.toggle_door_in_front(player)
    world_sim.update_doors(player, 0.016)
    fire = attempt_fire(0.0, player, world_sim, enemy)
    print(f"World sim smoke: door_toggled={door_toggled} first_door_open_amount={next(iter(world_sim.doors.values())).open_amount:.2f}")
    print(f"Combat smoke: fired={fire.fired} hit_enemy={fire.hit_enemy} enemy_down={fire.enemy_down} impact={fire.impact_distance:.2f}")
    print("Real game runtime shell is initialized. Next step: split render/audio runtime from poc_game.py")


if __name__ == "__main__":
    main()
