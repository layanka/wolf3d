from __future__ import annotations

from pathlib import Path

import pygame

SFX_SAMPLE_RATE = 22050


class RuntimeAudioManager:
    def __init__(self, project_root: Path) -> None:
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
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

            self.sounds["shoot"].set_volume(0.46)
            self.sounds["hit"].set_volume(0.44)
            self.sounds["down"].set_volume(0.44)
            self.sounds["door"].set_volume(0.28)
            self.sounds["step1"].set_volume(0.018)
            self.sounds["step2"].set_volume(0.018)
            self.enabled = True
        except (pygame.error, FileNotFoundError):
            self.enabled = False

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
