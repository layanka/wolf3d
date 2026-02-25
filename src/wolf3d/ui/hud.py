from __future__ import annotations

from src.wolf3d.render.frame import FrameSnapshot


def format_hud_lines(snapshot: FrameSnapshot, show_debug: bool = False) -> list[str]:
    weapon_state = "READY" if snapshot.weapon_cooldown <= 0.0 else "COOLDOWN"
    enemy_text = f"Enemies: {snapshot.enemies_alive}/{snapshot.enemies_total}"
    lines = [
        f"HP: {snapshot.player_health} | {enemy_text}",
        f"Weapon: {snapshot.weapon_label} ({weapon_state})",
    ]
    if show_debug:
        lines.append(f"Player @ ({snapshot.player_x:.2f}, {snapshot.player_y:.2f}) angle={snapshot.player_angle:.2f}")
    if snapshot.door_in_front:
        lines.append("Hint: SPACE to interact with door")
    return lines
