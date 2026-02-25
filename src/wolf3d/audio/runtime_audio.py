from __future__ import annotations

from pathlib import Path

import pygame

SFX_SAMPLE_RATE = 22050


class RuntimeAudioManager:
    def __init__(self, project_root: Path) -> None:
        self.enabled = False
        self.master_volume = 1.0
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.base_volumes: dict[str, float] = {}
        self.step_toggle = False
        sfx_root = project_root / "assets" / "audio" / "sfx"
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SFX_SAMPLE_RATE, size=-16, channels=1)
            self.sounds["shoot"] = pygame.mixer.Sound(str(sfx_root / "shoot.ogg"))
            self.sounds["hit"] = pygame.mixer.Sound(str(sfx_root / "hit.ogg"))
            self.sounds["down"] = pygame.mixer.Sound(str(sfx_root / "down.ogg"))
            self.sounds["door"] = pygame.mixer.Sound(str(sfx_root / "door.ogg"))
            self.sounds["step1"] = pygame.mixer.Sound(str(sfx_root / "step1.ogg"))
            self.sounds["step2"] = pygame.mixer.Sound(str(sfx_root / "step2.ogg"))

            self.base_volumes = {
                "shoot": 0.46,
                "hit": 0.44,
                "down": 0.44,
                "door": 0.28,
                "step1": 0.018,
                "step2": 0.018,
            }
            self.set_master_volume(1.0)
            self.enabled = True
        except (pygame.error, FileNotFoundError):
            self.enabled = False

    def set_master_volume(self, value: float) -> None:
        self.master_volume = max(0.0, min(1.0, value))
        for name, sound in self.sounds.items():
            base = self.base_volumes.get(name, 1.0)
            sound.set_volume(base * self.master_volume)

    def play(self, event_name: str) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(event_name)
        if sound is not None:
            sound.play()

    def play_step(self) -> None:
        if not self.enabled:
            return
        key = "step1" if not self.step_toggle else "step2"
        self.step_toggle = not self.step_toggle
        sound = self.sounds.get(key)
        if sound is not None:
            sound.play()
