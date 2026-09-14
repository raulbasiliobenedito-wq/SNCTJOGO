"""Contratos da fachada de áudio e de suas preferências persistidas."""

import json
import os
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from test_support import configure_game_imports

configure_game_imports()

import audio
from audio_backend import PygameMixerAudioBackend


class _FakeMusic:
    def __init__(self):
        self.calls = []
        self.fail_names = set()

    def play(self, name):
        self.calls.append(("play", name))
        if name in self.fail_names:
            raise FileNotFoundError(name)

    def play_once(self, name):
        self.calls.append(("play_once", name))
        if name in self.fail_names:
            raise FileNotFoundError(name)

    def set_volume(self, volume):
        self.calls.append(("volume", volume))


class _FakeSound:
    def __init__(self):
        self.calls = []

    def set_volume(self, volume):
        self.calls.append(("volume", volume))

    def play(self):
        self.calls.append(("play",))


class _FakeBackend:
    def __init__(self, music, sounds):
        self.music = music
        self.sounds = sounds

    def set_music_volume(self, volume):
        self.music.set_volume(volume)

    def play_music(self, name, loop):
        if loop:
            self.music.play(name)
        else:
            self.music.play_once(name)

    def play_sfx(self, name, volume):
        sound = self.sounds
        for part in name.split("."):
            sound = getattr(sound, part)
        sound.set_volume(volume)
        sound.play()


class AudioFacadeTests(unittest.TestCase):
    def setUp(self):
        audio._current_track = None
        audio.music_volume = 1.0
        audio.sfx_volume = 1.0
        audio.shake_scale = 1.0
        audio.text_speed = 0.65
        self.music = _FakeMusic()
        self.punch = _FakeSound()
        self.jump = _FakeSound()
        self.sounds = SimpleNamespace(
            jump=self.jump,
            punch=SimpleNamespace(punch_2=self.punch),
        )
        audio.set_backend(_FakeBackend(self.music, self.sounds))

    def tearDown(self):
        audio.reset_backend()

    def test_music_loop_once_volume_and_same_track_guard(self):
        audio.set_music_volume(0.35)
        audio.play_music("theme")
        audio.play_music("theme")
        audio.play_music("sting", loop=False)

        self.assertEqual(
            self.music.calls,
            [
                ("volume", 0.35),
                ("play", "theme"),
                ("volume", 0.35),
                ("play_once", "sting"),
                ("volume", 0.35),
            ],
        )
        self.assertEqual(audio._current_track, "sting")

    def test_failed_music_is_not_cached_and_can_be_retried(self):
        self.music.fail_names.add("missing")
        audio.play_music("missing")
        audio.play_music("missing")

        self.assertEqual(
            self.music.calls,
            [("play", "missing"), ("play", "missing")],
        )
        self.assertIsNone(audio._current_track)

    def test_nested_sound_uses_relative_and_master_volumes(self):
        audio.set_sfx_volume(0.5)
        audio.play_sfx("punch.punch_2", volume=0.4)

        self.assertEqual(self.punch.calls, [("volume", 0.2), ("play",)])
        self.assertEqual(self.jump.calls, [])

    def test_public_values_are_clamped(self):
        audio.set_music_volume(2.0)
        audio.set_sfx_volume(-2.0)
        audio.set_shake_scale(4.0)
        audio.set_text_speed(-1.0)

        self.assertEqual(audio.music_volume, 1.0)
        self.assertEqual(audio.sfx_volume, 0.0)
        self.assertEqual(audio.shake_scale, 1.0)
        self.assertEqual(audio.text_speed, 0.0)

    def test_settings_roundtrip_keeps_existing_json_shape(self):
        with TemporaryDirectory(prefix="echoes-audio-test-") as directory:
            path = Path(directory) / "audio_settings.json"
            with patch.object(audio, "_SETTINGS_PATH", path):
                audio.music_volume = 0.2
                audio.sfx_volume = 0.4
                audio.shake_scale = 0.6
                audio.text_speed = 1.2
                audio.save_settings()
                saved = json.loads(path.read_text(encoding="utf-8"))

                audio.music_volume = audio.sfx_volume = 1.0
                audio.shake_scale = audio.text_speed = 1.0
                audio.load_settings()

        self.assertEqual(
            saved,
            {
                "music_volume": 0.2,
                "sfx_volume": 0.4,
                "shake_scale": 0.6,
                "text_speed": 1.2,
            },
        )
        self.assertEqual(
            (
                audio.music_volume,
                audio.sfx_volume,
                audio.shake_scale,
                audio.text_speed,
            ),
            (0.2, 0.4, 0.6, 1.2),
        )


class _FakeMixerMusic:
    def __init__(self):
        self.calls = []

    def load(self, path):
        self.calls.append(("load", path))

    def play(self, loops):
        self.calls.append(("play", loops))

    def set_volume(self, volume):
        self.calls.append(("volume", volume))


class _FakeMixer:
    def __init__(self):
        self.initialized = False
        self.init_calls = 0
        self.music = _FakeMixerMusic()
        self.sound_paths = []
        self.sounds = []

    def get_init(self):
        return self.initialized

    def init(self):
        self.init_calls += 1
        self.initialized = True

    def Sound(self, path):
        self.sound_paths.append(path)
        sound = _FakeSound()
        self.sounds.append(sound)
        return sound


class PygameMixerBackendTests(unittest.TestCase):
    def test_resolves_music_nested_sfx_loop_and_cache(self):
        with TemporaryDirectory(prefix="echoes-mixer-test-") as directory:
            root = Path(directory)
            music_dir = root / "music"
            sounds_dir = root / "sounds"
            punch_dir = sounds_dir / "punch"
            music_dir.mkdir()
            punch_dir.mkdir(parents=True)
            track = music_dir / "theme.mp3"
            effect = punch_dir / "punch_2.mp3"
            track.write_bytes(b"track")
            effect.write_bytes(b"effect")
            mixer = _FakeMixer()
            backend = PygameMixerAudioBackend(music_dir, sounds_dir, mixer)

            backend.play_music("theme", loop=True)
            backend.set_music_volume(0.3)
            backend.play_sfx("punch.punch_2", 0.2)
            backend.play_sfx("punch.punch_2", 0.4)

        self.assertEqual(mixer.init_calls, 1)
        self.assertEqual(
            mixer.music.calls,
            [("load", str(track)), ("play", -1), ("volume", 0.3)],
        )
        self.assertEqual(mixer.sound_paths, [str(effect)])
        self.assertEqual(
            mixer.sounds[0].calls,
            [("volume", 0.2), ("play",), ("volume", 0.4), ("play",)],
        )

    def test_missing_resource_stays_nonfatal_at_facade(self):
        with TemporaryDirectory(prefix="echoes-mixer-test-") as directory:
            root = Path(directory)
            (root / "music").mkdir()
            (root / "sounds").mkdir()
            backend = PygameMixerAudioBackend(
                root / "music", root / "sounds", _FakeMixer()
            )
            audio.set_backend(backend)
            try:
                audio.play_music("missing")
                audio.play_sfx("also_missing")
                self.assertIsNone(audio._current_track)
            finally:
                audio.reset_backend()


if __name__ == "__main__":
    unittest.main()
