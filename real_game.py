from __future__ import annotations

from pathlib import Path

from src.wolf3d.audio.manager import route_simulation_audio_events
from src.wolf3d.entrypoint import bootstrap
from src.wolf3d.content_loader import load_enemy_types, load_level_map, load_level_specs, load_weapon_types
from src.wolf3d.entities.models import EnemyState, PlayerState
from src.wolf3d.gameplay.combat import attempt_fire_multi
from src.wolf3d.gameplay_state import summarize_level_gameplay
from src.wolf3d.render.frame import build_frame_snapshot
from src.wolf3d.ui.hud import format_hud_lines
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

    # Lane B/C/A/D integration smoke: world simulation + combat + HUD/audio route.
    tile_map = load_level_map(data_root, first_level)
    world_sim = WorldSimulation(tile_map)
    player = PlayerState(x=world.spawn_x, y=world.spawn_y, angle=world.spawn_angle)
    enemy_defs = {e.id: e for e in enemies}
    enemy_states = [
        EnemyState(type_id=spawn.type, x=spawn.x, y=spawn.y, health=enemy_defs[spawn.type].health)
        for spawn in first_level.enemy_spawns
    ]

    door_toggled = world_sim.toggle_door_in_front(player)
    world_sim.update_doors(player, 0.016)
    fire, _target = attempt_fire_multi(0.0, player, world_sim, enemy_states)
    audio_events = route_simulation_audio_events(door_toggled, fire)
    frame = build_frame_snapshot(player, enemy_states, world_sim, fire.next_cooldown)
    hud_lines = format_hud_lines(frame)
    print(f"World sim smoke: door_toggled={door_toggled} first_door_open_amount={next(iter(world_sim.doors.values())).open_amount:.2f}")
    print(f"Combat smoke: fired={fire.fired} hit_enemy={fire.hit_enemy} enemy_down={fire.enemy_down} impact={fire.impact_distance:.2f}")
    print(f"Audio route smoke: events={audio_events}")
    print("HUD smoke:")
    for line in hud_lines:
        print(f"  - {line}")
    print("Real game runtime shell is initialized. Next step: extract loop/render/audio runtime from poc_game.py")


if __name__ == "__main__":
    main()
