"""Regressões executáveis com python -m unittest discover -s tests -v."""

import json
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from input_adapter import mouse_down, mouse_move, mouse_up
from progress import decode_progress, read_progress, write_progress
from test_support import isolated_game_data


class ProgressTests(unittest.TestCase):
    def valid(self):
        return dict(version=1, level=0, checkpoint=[2351, 466], lives=4.5,
                    shield=0, inventory={}, ranged_unlocked=False, collected=[0])

    def test_fractional_lives_and_existing_v1_format(self):
        data = decode_progress(self.valid(), ("vila", 0, 1, 2))
        self.assertEqual(data["lives"], 4.5)
        self.assertEqual(data["checkpoint"], (2351, 466))
        self.assertFalse(data["ranged_unlocked"])

    def test_invalid_data_rejected_before_use(self):
        cases = [None, [], {**self.valid(), "version": True}]
        for key, value in [("level", True), ("level", []), ("level", 1.5),
                           ("checkpoint", [0]), ("checkpoint", [float("nan"), 0]), ("checkpoint", [10**1000, 0]),
                           ("checkpoint", [1e100, 0]),
                           ("lives", -1), ("lives", float("inf")), ("shield", -2),
                           ("inventory", []), ("inventory", {"gororoba": -1}),
                           ("collected", ["0"]), ("ranged_unlocked", "false")]:
            cases.append({**self.valid(), key: value})
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode_progress(data, ("vila", 0, 1, 2))

    def test_legacy_later_phase_recovers_ranged_unlock(self):
        self.assertTrue(decode_progress({**self.valid(), "level": 1}, (0, 1, 2))["ranged_unlocked"])

    def test_atomic_write_and_failed_replace_preserve_old_save(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            write_progress(path, self.valid())
            before = path.read_bytes()
            with patch.object(Path, "replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    write_progress(path, {**self.valid(), "lives": 2})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])
            self.assertEqual(read_progress(path, (0, 1, 2))["lives"], 4.5)


class InputTests(unittest.TestCase):
    def game(self, state, active=False):
        return Mock(state=state, minigame=SimpleNamespace(active=active))

    def test_minigame_has_priority_over_menu(self):
        game = self.game("settings", True)
        for handler in (mouse_down, mouse_move, mouse_up):
            handler(game, (10, 20))
        self.assertEqual([c[0] for c in game.mock_calls],
                         ["handle_minigame_click", "handle_minigame_drag", "handle_minigame_release"])

    def test_click_routes_menus_and_combat(self):
        for state in ("title", "settings", "paused", "playing"):
            with self.subTest(state=state):
                game = self.game(state)
                mouse_down(game, (10, 20))
                if state == "playing":
                    game.request_mouse_attack.assert_called_once_with()
                else:
                    game.handle_menu_click.assert_called_once_with((10, 20))

    def test_drag_and_release_keep_previous_behavior(self):
        for state in ("title", "settings", "paused", "playing"):
            game = self.game(state)
            mouse_move(game, (10, 20))
            self.assertEqual(game.handle_menu_drag.call_count, int(state in ("settings", "paused")))
            mouse_up(game, (10, 20))
            game.handle_menu_release.assert_called_once_with()


class RenderCacheTests(unittest.TestCase):
    def test_optimized_draws_match_original_pixels(self):
        from minigame import draw_modal_backdrop
        from projectile import Projectile
        for kind, expected in (
            ("projectile", "0cc144d56717128aa7a43fbfde64b45c749ee377603f8f8eb8fdaad148268440"),
            ("modal", "0cb653bbef3238ea0545fe32dd1d8d957d72385396bd29acb593e56e4df16f73"),
        ):
            # Referências capturadas antes da refatoração, com pygame 2.6.1.
            for _ in range(2):
                with self.subTest(kind=kind):
                    surface = pygame.Surface((640, 480), pygame.SRCALPHA)
                    surface.fill((42, 75, 91, 255))
                    if kind == "projectile":
                        Projectile(200, 200, 1, 14, 1, 500).draw(surface, 10, 20)
                    else:
                        draw_modal_backdrop(surface, pygame.Rect(50, 50, 500, 360), 640, 480)
                    self.assertEqual(hashlib.sha256(pygame.image.tostring(surface, "RGBA")).hexdigest(), expected)


class GameRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        cls.isolation = isolated_game_data()
        cls.directory = cls.isolation.__enter__()
        from game import Game
        cls.game = Game()

    @classmethod
    def tearDownClass(cls):
        cls.isolation.__exit__(None, None, None)
        pygame.quit()

    def setUp(self):
        game = self.game
        game.load_level(0)
        game.lives = 5
        game.shield = 0
        game.inventory = {}
        game.ranged_unlocked = False
        game.dialogue.close()

    def test_microscope_drag_order_and_resume(self):
        from minigame import MICROSCOPE_ORDER, MicroscopeMinigame
        game = self.game
        state = dict.fromkeys(MICROSCOPE_ORDER, False)
        def create():
            return MicroscopeMinigame(1920, 1080, game._microscope_sprites_by_identity(),
                                      game.assets.puzzle_sprites["microscope_complete"], state)
        mini = create()
        def place(identity):
            piece = next(p for p in mini.field.pieces if p["key"] == identity)
            target = mini.field.slot(identity)["rect"].center
            mini.on_click(piece["rect"].center)
            mini.on_drag(target)
            mini.on_release(target)
        place("ocular")
        self.assertFalse(state["ocular"])
        for _ in range(10):
            mini.update(1 / 60)
        place(MICROSCOPE_ORDER[0])
        self.assertTrue(state[MICROSCOPE_ORDER[0]])
        mini.close()
        mini = create()
        self.assertTrue(next(p for p in mini.field.pieces if p["key"] == MICROSCOPE_ORDER[0])["placed"])
        for identity in MICROSCOPE_ORDER[1:]:
            place(identity)
        for _ in range(mini.COMPLETE_HOLD_FRAMES):
            mini.update(1 / 60)
        self.assertEqual(mini.result, "completed")
        self.assertTrue(all(state.values()))

    def test_web_entrypoint_dispatches_events_and_exits(self):
        import asyncio
        namespace = {"__name__": "web_smoke", "__file__": "main_web.py"}
        source = (Path(__file__).resolve().parents[1] / "main_web.py").read_text(encoding="utf-8")
        # Define o ponto de entrada sem deixar asyncio.run iniciar o laço infinito.
        def discard(coroutine):
            coroutine.close()
        with patch("asyncio.run", side_effect=discard):
            exec(compile(source, "main_web.py", "exec"), namespace)
        events = [
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1, 1)),
            pygame.event.Event(pygame.MOUSEMOTION, pos=(2, 2), rel=(1, 1)),
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(2, 2)),
        ]
        with patch("pygame.event.get", side_effect=[events, [pygame.event.Event(pygame.QUIT)]]), patch("pygame.quit") as quit_game:
            asyncio.run(namespace["main"]())
        quit_game.assert_called_once_with()

    def test_new_phase_save_contains_ranged_unlock(self):
        game = self.game
        game.collected = set(range(len(game.level.research)))
        game.lab_microscope_assembled = True
        game.inventory = {"essencia_slime": 1}
        game.player.x = game.level.world_width - 90
        game._advance_level_if_ready(game.player)
        saved = json.loads(game.SAVE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(saved["level"], 1)
        self.assertTrue(saved["ranged_unlocked"])
        self.assertTrue(game.ranged_unlocked)

    def test_village_transition_saves_school_checkpoint(self):
        game = self.game
        game.load_level("vila")
        game.collected = set(range(len(game.level.research)))
        game.player.x = game.level.world_width - 90
        game._advance_level_if_ready(game.player)
        saved = json.loads(game.SAVE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(saved["level"], 0)
        self.assertEqual(saved["checkpoint"], list(game.level.spawn))

    def test_room_artifacts_are_independent_and_remembered(self):
        game = self.game
        game.load_level(1)
        for room in ("biblioteca", "laboratorio"):
            game.enter_room(room)
            self.assertTrue(game.level.artifacts)
            item = game.level.artifacts[0][0]
            player = SimpleNamespace(rect=item.copy())
            self.assertTrue(game._collect_artifacts(player))
            self.assertEqual(game.artifacts_collected, {0})
            game.exit_room()
            self.assertEqual(game.artifacts_collected, set())
        game.enter_room("biblioteca")
        self.assertEqual(game.artifacts_collected, {0})
        self.assertFalse(game._collect_artifacts(SimpleNamespace(rect=game.level.artifacts[0][0])))
        game.load_level(1)
        game.enter_room("biblioteca")
        self.assertEqual(game.artifacts_collected, set())

    def test_invalid_save_does_not_partially_change_session(self):
        game = self.game
        old_level, old_position = game.level, (game.player.x, game.player.y)
        game.SAVE_PATH.write_text(json.dumps(dict(version=1, level=2, checkpoint=[0])), encoding="utf-8")
        with self.assertLogs("game", level="WARNING"):
            self.assertFalse(game.load_progress())
        self.assertIs(game.level, old_level)
        self.assertEqual((game.player.x, game.player.y), old_position)

    def test_save_roundtrip_and_room_save_guard(self):
        game = self.game
        game.lives = 3.5
        game.inventory = {"gororoba": 2}
        game.save_progress()
        before = game.SAVE_PATH.read_bytes()
        game.enter_room("laboratorio_secreto")
        game.save_progress()
        self.assertEqual(game.SAVE_PATH.read_bytes(), before)
        game.lives = 1
        self.assertTrue(game.load_progress())
        self.assertEqual(game.lives, 3.5)
        self.assertEqual(game.inventory, {"gororoba": 2})
        self.assertIsNone(game.level.room)


if __name__ == "__main__":
    unittest.main()
