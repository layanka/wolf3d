from __future__ import annotations

from src.wolf3d.entities.models import FireResult


class AudioEvent:
    SHOOT = "shoot"
    HIT = "hit"
    DOWN = "down"
    DOOR = "door"


def route_simulation_audio_events(door_toggled: bool, fire: FireResult) -> list[str]:
    events: list[str] = []
    if door_toggled:
        events.append(AudioEvent.DOOR)
    if fire.fired:
        events.append(AudioEvent.SHOOT)
    if fire.hit_enemy:
        events.append(AudioEvent.HIT)
    if fire.enemy_down:
        events.append(AudioEvent.DOWN)
    return events
