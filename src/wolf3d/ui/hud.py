from __future__ import annotations

from src.wolf3d.render.frame import FrameSnapshot


def format_hud_lines(snapshot: FrameSnapshot) -> list[str]:
    weapon_state = "READY" if snapshot.weapon_cooldown <= 0.0 else "COOLDOWN"
    enemy_text = "Enemy: DOWN" if not snapshot.enemy_alive else f"Enemy HP: {snapshot.enemy_health}"
    lines = [
        f"{enemy_text} | Weapon: {weapon_state}",
        f"Player @ ({snapshot.player_x:.2f}, {snapshot.player_y:.2f}) angle={snapshot.player_angle:.2f}",
    ]
    if snapshot.door_in_front:
        lines.append("Hint: SPACE to interact with door")
    return lines
