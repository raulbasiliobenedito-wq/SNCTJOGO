"""Backends mínimos de áudio para as entradas desktop e web."""

from pathlib import Path

import pygame


class AudioUnavailable(RuntimeError):
    """Indica que o ponto de entrada não configurou um backend de áudio."""


class SilentAudioBackend:
    """Backend inicial: mantém chamadas seguras antes da plataforma subir."""

    def set_music_volume(self, _volume):
        return None

    def play_music(self, _name, _loop):
        raise AudioUnavailable("backend de áudio ainda não configurado")

    def play_sfx(self, _name, _volume):
        raise AudioUnavailable("backend de áudio ainda não configurado")


class PygameMixerAudioBackend:
    """Carrega áudio por caminho no desktop e no laço WASM do pygbag."""

    MUSIC_EXTENSIONS = ("mp3", "ogg", "oga")
    SOUND_EXTENSIONS = ("wav", "mp3", "ogg", "oga")

    def __init__(self, music_dir, sounds_dir, mixer=pygame.mixer):
        self.music_dir = Path(music_dir)
        self.sounds_dir = Path(sounds_dir)
        self.mixer = mixer
        self._sounds = {}

    def _ensure_ready(self):
        if not self.mixer.get_init():
            self.mixer.init()

    @staticmethod
    def _resolve(root, name, extensions):
        relative = Path(*name.split("."))
        path = root / relative
        if path.is_file():
            return path
        for extension in extensions:
            candidate = path.with_suffix(f".{extension}")
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(f"recurso de áudio não encontrado: {name}")

    def set_music_volume(self, volume):
        self._ensure_ready()
        self.mixer.music.set_volume(volume)

    def play_music(self, name, loop):
        self._ensure_ready()
        path = self._resolve(self.music_dir, name, self.MUSIC_EXTENSIONS)
        self.mixer.music.load(str(path))
        self.mixer.music.play(-1 if loop else 0)

    def play_sfx(self, name, volume):
        self._ensure_ready()
        sound = self._sounds.get(name)
        if sound is None:
            path = self._resolve(self.sounds_dir, name, self.SOUND_EXTENSIONS)
            sound = self._sounds[name] = self.mixer.Sound(str(path))
        sound.set_volume(volume)
        sound.play()
