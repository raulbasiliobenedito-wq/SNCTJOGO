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

from test_support import GAME_DIR, configure_game_imports, isolated_game_data, shutdown_pygame

configure_game_imports()

import pygame

from input_adapter import mouse_down, mouse_move, mouse_up
from progress import decode_progress, read_progress, write_progress


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
        shutdown_pygame()

    def setUp(self):
        game = self.game
        game._level_transition_phase = None
        game._level_transition_alpha = 0
        game._level_transition_target = None
        game.load_level(0)
        game.lives = 5
        game.shield = 0
        game.items.counts = {}
        game.ranged_unlocked = False
        game.dialogue.close()

    def finish_level_transition(self):
        updates = 0
        while self.game._level_transition_phase is not None:
            self.game._update_level_transition()
            updates += 1
            self.assertLess(updates, 100)

    def test_microscope_drag_order_and_resume(self):
        from minigame import MICROSCOPE_ORDER, MicroscopeMinigame
        game = self.game
        state = dict.fromkeys(MICROSCOPE_ORDER, False)
        def create():
            return MicroscopeMinigame(1920, 1080, game.puzzles.microscope_sprites_by_identity(),
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

    def test_microscope_drag_art_is_scaled_and_columns_are_separated(self):
        from minigame import MICROSCOPE_DRAG_SCALE, MICROSCOPE_ORDER, MicroscopeMinigame
        game = self.game
        mini = MicroscopeMinigame(
            1920, 1080,
            game.puzzles.microscope_sprites_by_identity(),
            game.assets.puzzle_sprites["microscope_complete"],
            dict.fromkeys(MICROSCOPE_ORDER, False),
        )
        for piece in mini.field.pieces:
            original = mini.sprites[piece["key"]]
            self.assertEqual(
                piece["image"].get_size(),
                (
                    original.get_width() * MICROSCOPE_DRAG_SCALE,
                    original.get_height() * MICROSCOPE_DRAG_SCALE,
                ),
            )
        self.assertGreater(
            min(piece["home"].left for piece in mini.field.pieces),
            max(slot["rect"].right for slot in mini.field.slots) + 300,
        )

    def test_animated_fog_keeps_visual_fringe_outside_collision(self):
        from fog import FogBarrier
        frame = pygame.Surface((480, 270), pygame.SRCALPHA).convert_alpha()
        frame.fill((90, 40, 120, 255))
        barrier = FogBarrier(pygame.Rect(210, 0, 400, 100), "teste")
        barrier.frames = [frame]
        surface = pygame.Surface((200, 100), pygame.SRCALPHA).convert_alpha()

        barrier.draw(surface, 0, 0)

        self.assertEqual(surface.get_at((170, 50)).a, 0)
        self.assertGreater(surface.get_at((180, 50)).a, 0)
        self.assertEqual(barrier.rect.x, 210)
        self.assertTrue(barrier.solid())

    def test_puzzle_progress_survives_rooms_and_resets_on_new_phase(self):
        game = self.game
        puzzles = game.puzzles
        old_slots = puzzles.microscope_slots
        old_wires = puzzles.energy_box_wires
        puzzles.microscope_slots["base"] = True
        puzzles.microscope_collected.add(0)
        puzzles.energy_box_state["screws_removed"] = True
        puzzles.lever_on = True
        game.interactions._dialogue_queue = [("Lia", "próxima fala")]
        game.enter_room("laboratorio_secreto")
        game.exit_room()
        self.assertIs(puzzles.microscope_slots, old_slots)
        self.assertIs(puzzles.energy_box_wires, old_wires)
        self.assertTrue(puzzles.microscope_slots["base"])
        self.assertEqual(puzzles.microscope_collected, {0})
        self.assertTrue(puzzles.energy_box_state["screws_removed"])
        self.assertEqual(game.interactions._dialogue_queue, [("Lia", "próxima fala")])
        game.load_level(1)
        self.assertIs(game.puzzles, puzzles)
        self.assertIsNot(puzzles.microscope_slots, old_slots)
        self.assertIsNot(puzzles.energy_box_wires, old_wires)
        self.assertFalse(any(puzzles.microscope_slots.values()))
        self.assertEqual(puzzles.microscope_collected, set())
        self.assertEqual(puzzles.energy_box_state, {"screws_removed": False, "wired": False})
        self.assertFalse(puzzles.lever_on)
        self.assertEqual(game.interactions._dialogue_queue, [])

    def test_elevator_lab_microscope_is_the_phase_one_requirement(self):
        from minigame import MICROSCOPE_ORDER
        game = self.game
        game.load_level(0)
        base_level = game.level
        game.collected = set(range(len(base_level.research)))
        game.player.x = base_level.world_width - 90

        game._advance_level_if_ready(game.player)

        self.assertEqual(game.level.index, 0)
        self.assertIn("laboratório acessado pelo elevador", game.message)

        game.enter_room("laboratorio_secreto")
        release_key = game.level.lab_bench["libera"]
        barrier = next(item for item in base_level.fog_barriers if item.chave == release_key)
        for item, _name in game.level.lab_microscope_parts:
            game.player.reset(item.x, item.y)
            game.puzzles.collect_lab_microscope_parts(game.player)

        self.assertEqual(len(game.puzzles.microscope_collected), len(MICROSCOPE_ORDER))
        game.puzzles.finish_minigame("microscope", "completed")
        self.assertTrue(game.puzzles.microscope_assembled)
        self.assertTrue(barrier._dissipating)

    def test_phase_one_lab_elevator_is_marked_to_require_the_panel(self):
        game = self.game
        game.load_level(0)

        elevator = next(
            item
            for item in game.level.secret_elevators
            if item["destino"] == "laboratorio_secreto"
        )

        self.assertTrue(elevator["requer_painel"])

    def test_elevator_lab_loose_parts_are_enlarged_and_bob(self):
        game = self.game
        game.load_level(0)
        game.enter_room("laboratorio_secreto")
        level = game.level
        pickup_rects = [item.copy() for item, _name in level.lab_microscope_parts]
        surface = pygame.Surface((1920, 1080), pygame.SRCALPHA).convert_alpha()

        game._draw_world(surface)

        for original, scaled in zip(
            game.assets.puzzle_sprites["microscope_parts"],
            level._scaled_lab_microscope_parts,
        ):
            self.assertEqual(
                scaled.get_size(),
                (
                    original.get_width() * level.LAB_MICROSCOPE_PART_SCALE,
                    original.get_height() * level.LAB_MICROSCOPE_PART_SCALE,
                ),
            )
        self.assertEqual(
            [item for item, _name in level.lab_microscope_parts],
            pickup_rects,
        )
        level.npc_animation = 0
        first_y = level._lab_microscope_bob(0)
        level.npc_animation = 18
        self.assertNotEqual(level._lab_microscope_bob(0), first_y)

    def test_elevator_cutscene_lia_is_doubled_and_grounded_behind_frame(self):
        cutscene = self.game.elevator_cutscene
        visible = cutscene.lia_visible_rect
        x, y = cutscene._lia_position()

        self.assertEqual(cutscene.lia_frame.get_size(), (288, 288))
        self.assertEqual(y + visible.bottom, cutscene.LIA_FLOOR_Y)
        self.assertEqual(x + visible.centerx, 1920 // 2)

    def test_contextual_prompts_describe_elevator_energy_box_and_microscope(self):
        game = self.game
        surface = pygame.Surface((1920, 1080), pygame.SRCALPHA).convert_alpha()

        with patch("game.draw_text") as draw:
            game.load_level(0)
            elevator = game.level.secret_elevators[0]["rect"]
            game.player.reset(elevator.x, elevator.y)
            game._draw_puzzle_prompts(surface)

            game.enter_room("laboratorio_secreto")
            exit_elevator = game.level.secret_elevators[0]["rect"]
            game.player.reset(exit_elevator.x, exit_elevator.y)
            game._draw_puzzle_prompts(surface)
            bench = game.level.lab_bench["rect"]
            game.player.reset(bench.x, bench.y)
            game._draw_puzzle_prompts(surface)

            game.load_level(1)
            game.enter_room("laboratorio")
            energy_box = game.level.energy_box
            game.player.reset(energy_box.x, energy_box.y)
            game._draw_puzzle_prompts(surface)

        labels = [call.args[1] for call in draw.call_args_list]
        self.assertIn("APERTE [E] PARA DESCER NO ELEVADOR", labels)
        self.assertIn("APERTE [E] PARA SUBIR NO ELEVADOR", labels)
        self.assertIn("APERTE [E] PARA MONTAR O MICROSCÓPIO", labels)
        self.assertIn("APERTE [E] PARA ACESSAR A CAIXA DE ENERGIA", labels)

    def test_secret_lab_elevators_use_full_object_width(self):
        game = self.game
        game.load_level(0)
        game.enter_room("laboratorio_secreto")

        self.assertEqual(
            [tuple(item["rect"]) for item in game.level.secret_elevators],
            [(40, 464, 80, 80), (2888, 464, 80, 80)],
        )

    def test_web_entrypoint_dispatches_events_and_exits(self):
        import asyncio
        namespace = {"__name__": "web_smoke", "__file__": "main_web.py"}
        source = (GAME_DIR / "main_web.py").read_text(encoding="utf-8")
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
        with patch(
            "pygame.event.get",
            side_effect=[events, [pygame.event.Event(pygame.QUIT)]],
        ), patch("pygame.quit") as quit_game, patch(
            "audio.use_pygame_mixer"
        ) as configure_audio, patch("audio.reset_backend") as reset_audio:
            asyncio.run(namespace["main"]())
        configure_audio.assert_called_once_with()
        reset_audio.assert_called_once_with()
        quit_game.assert_called_once_with()

    def test_new_phase_save_contains_ranged_unlock(self):
        game = self.game
        game.collected = set(range(len(game.level.research)))
        game.puzzles.microscope_assembled = True
        game.items.counts = {"essencia_slime": 1}
        game.player.x = game.level.world_width - 90
        game._advance_level_if_ready(game.player)

        self.assertEqual(game.level.index, 0)
        self.assertEqual(game._level_transition_phase, "fade_out")
        while game._level_transition_phase == "fade_out":
            game._update_level_transition()
        self.assertEqual(game._level_transition_alpha, 255)
        self.assertEqual(game.level.index, 1)
        self.finish_level_transition()

        saved = json.loads(game.SAVE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(saved["level"], 1)
        self.assertTrue(saved["ranged_unlocked"])
        self.assertTrue(game.ranged_unlocked)

    def test_phase_two_requires_the_energy_box_before_advancing(self):
        game = self.game
        game.load_level(1)
        game.collected = set(range(len(game.level.research)))
        game.items.counts = {"livro_magico": 1, "amostra_especime": 1}
        game.player.x = game.level.world_width - 90

        game._advance_level_if_ready(game.player)

        self.assertIsNone(game._level_transition_phase)
        self.assertIn("caixa de energia", game.message)

        game.puzzles.energy_box_state["wired"] = True
        game.player.x = game.level.world_width - 90
        game._advance_level_if_ready(game.player)

        self.assertEqual(game._level_transition_phase, "fade_out")
        self.assertEqual(game._level_transition_target, 2)

    def test_village_transition_saves_school_checkpoint(self):
        game = self.game
        game.load_level("vila")
        game.collected = set(range(len(game.level.research)))
        game.player.x = game.level.world_width - 90
        game._advance_level_if_ready(game.player)
        self.finish_level_transition()
        saved = json.loads(game.SAVE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(saved["level"], 0)
        self.assertEqual(saved["checkpoint"], list(game.level.spawn))

    def test_last_phase_fades_to_completion(self):
        from game_data import COMPLETE, PLAYING

        game = self.game
        game.load_level(2)
        game.collected = set(range(len(game.level.research)))
        game.player.x = game.level.world_width - 90

        game._advance_level_if_ready(game.player)

        self.assertEqual(game.state, PLAYING)
        self.assertEqual(game._level_transition_phase, "fade_out")
        while game._level_transition_phase == "fade_out":
            game._update_level_transition()
        self.assertEqual(game.state, COMPLETE)
        self.assertEqual(game._level_transition_alpha, 255)
        self.finish_level_transition()
        self.assertIsNone(game._level_transition_phase)

    def test_phase_one_uses_bosque_do_conhecimento_name(self):
        from level import PHASES

        self.assertEqual(PHASES[0]["name"], "Fase 1 — Bosque do Conhecimento")

    def test_trimmed_village_parallax_matches_full_layers_pixel_for_pixel(self):
        from assets import Assets
        from settings import ASSET_DIR, HEIGHT, WIDTH

        game = self.game
        game.load_level("vila")
        # Com a arte nova instalada, o GrassLand não fica residente; ainda
        # validamos aqui o carregador que serve de fallback se ela faltar.
        fallback_layers = game.assets._load_village_parallax_layers()
        game.camera_x = 937
        reference = pygame.Surface((WIDTH, HEIGHT)).convert()
        optimized = pygame.Surface((WIDTH, HEIGHT)).convert()

        for spec, layer in zip(Assets.VILLAGE_PARALLAX_LAYERS, fallback_layers):
            filename, parallax, has_alpha = spec
            if has_alpha:
                path = ASSET_DIR / Assets.VILLAGE_BACKGROUND_DIR / filename
                raw = pygame.image.load(path).convert_alpha()
                scale = HEIGHT / raw.get_height()
                image = pygame.transform.scale(
                    raw, (round(raw.get_width() * scale), HEIGHT)
                )
            else:
                image = layer["variants"]["normal"]
            game._draw_repeating_background(reference, image, parallax=parallax)

        resident_layers = game.assets.village_layers
        game.assets.village_layers = fallback_layers
        try:
            game._draw_village_parallax(optimized, "normal")
        finally:
            game.assets.village_layers = resident_layers
        self.assertEqual(
            pygame.image.tostring(optimized, "RGBA"),
            pygame.image.tostring(reference, "RGBA"),
        )
        for layer in fallback_layers[1:]:
            self.assertLess(layer["variants"]["normal"].get_height(), HEIGHT)
            self.assertGreater(layer["draw_offset"][1], 0)

    def test_campo_uses_the_approved_parallax_composition(self):
        from settings import HEIGHT, WIDTH

        game = self.game
        game.load_level("vila")
        self.assertEqual(game._background_key(), "campo")
        self.assertEqual(len(game.assets.campo_layers), 5)
        self.assertEqual(
            [layer["parallax"] for layer in game.assets.campo_layers],
            [spec[1] for spec in game.assets.CAMPO_PARALLAX_LAYERS],
        )
        # As velocidades aumentam conforme o plano se aproxima da câmera.
        speeds = [layer["parallax"] for layer in game.assets.campo_layers]
        self.assertEqual(speeds, sorted(speeds))

        start = pygame.Surface((WIDTH, HEIGHT)).convert()
        end = pygame.Surface((WIDTH, HEIGHT)).convert()
        game.camera_x = 0
        game._draw_background(start)
        game.camera_x = game.level.world_width - WIDTH
        game._draw_background(end)

        # O céu opaco mantém a tela coberta, enquanto os outros quatro planos
        # mudam de posição em velocidades diferentes durante o percurso.
        self.assertEqual(start.get_at((0, 0)).a, 255)
        self.assertEqual(end.get_at((WIDTH - 1, HEIGHT - 1)).a, 255)
        self.assertNotEqual(
            pygame.image.tostring(start, "RGB"),
            pygame.image.tostring(end, "RGB"),
        )

    def test_school_does_not_reuse_campo_background(self):
        from settings import HEIGHT, WIDTH

        game = self.game
        game.load_level(0)
        self.assertEqual(game._background_key(), "school")
        self.assertEqual(len(game.assets.school_layers), 3)
        self.assertEqual(
            [layer["name"] for layer in game.assets.school_layers],
            ["sky", "giant_trees", "fog"],
        )

        surface_view = pygame.Surface((WIDTH, HEIGHT)).convert()
        deep_view = pygame.Surface((WIDTH, HEIGHT)).convert()
        game.camera_x = 0
        game.camera_y = 0
        game._draw_background(surface_view)
        game.camera_x = game.level.world_width - WIDTH
        game.camera_y = game.level.world_height - HEIGHT
        game._draw_background(deep_view)

        # O céu opaco cobre os cantos e a descida altera a composição sem
        # depender da antiga troca súbita de fundo em UNDERGROUND_Y.
        self.assertEqual(surface_view.get_at((0, 0)).a, 255)
        self.assertEqual(deep_view.get_at((WIDTH - 1, HEIGHT - 1)).a, 255)
        self.assertNotEqual(
            pygame.image.tostring(surface_view, "RGB"),
            pygame.image.tostring(deep_view, "RGB"),
        )

        fog = next(
            layer for layer in game.assets.school_layers if layer["name"] == "fog"
        )
        self.assertGreater(fog["scroll_speed_x"], 5.0)

        trees = next(
            layer
            for layer in game.assets.school_layers
            if layer["name"] == "giant_trees"
        )
        self.assertGreater(trees["variants"]["normal"].get_height(), HEIGHT)
        for camera_y in (game.level.world_top, game.level.world_height - HEIGHT):
            origin_y = round(
                trees["draw_offset"][1]
                - (camera_y - trees["reference_y"]) * trees["parallax_y"]
            )
            self.assertLessEqual(origin_y, 0)
            self.assertGreaterEqual(
                origin_y + trees["variants"]["normal"].get_height(), HEIGHT
            )

        sky = game.assets.school_layers[0]["variants"]["normal"]
        lower_sky = sky.subsurface(pygame.Rect(0, HEIGHT - 16, WIDTH, 16))
        red, green, blue, _alpha = pygame.transform.average_color(lower_sky)
        self.assertGreater(blue, red)
        self.assertGreater(blue, green)

    def test_school_fog_moves_while_camera_is_still(self):
        game = self.game
        game.load_level(0)
        fog = next(
            layer for layer in game.assets.school_layers if layer["name"] == "fog"
        )
        before = round(
            fog["base_offset"][0]
            + fog["draw_offset"][0]
            - game.camera_x * fog["parallax_x"]
            - game._background_elapsed * fog["scroll_speed_x"]
        )
        game._background_elapsed += 1.0
        after = round(
            fog["base_offset"][0]
            + fog["draw_offset"][0]
            - game.camera_x * fog["parallax_x"]
            - game._background_elapsed * fog["scroll_speed_x"]
        )
        self.assertNotEqual(before, after)

    def test_all_villager_idle_sheets_are_loaded_without_chroma_green(self):
        from assets import Assets

        expected_counts = {
            "Dona Marta": 9,
            "Cadu": 8,
            "Zeca": 4,
            "Seu Joaquim": 9,
            "Sra. Amélia": 9,
            "Bento": 9,
        }
        expected_size = (round(48 * Assets.NPC_SCALE),) * 2
        for name, count in expected_counts.items():
            frames = self.game.assets.npc_frames[name]
            self.assertEqual(len(frames), count, name)
            self.assertTrue(any(frame.get_bounding_rect().size != (0, 0) for frame in frames))
            for frame in frames:
                self.assertEqual(frame.get_size(), expected_size, name)
                self.assertEqual(frame.get_at((0, 0)).a, 0, name)
                self.assertFalse(
                    any(
                        color.a
                        and color.g >= 245
                        and color.r <= 10
                        and color.b <= 10
                        for color in (
                            frame.get_at((x, y))
                            for y in range(frame.get_height())
                            for x in range(frame.get_width())
                        )
                    ),
                    name,
                )

            npc_rect = pygame.Rect(100, 50, 48, 48)
            original_npcs = self.game.level.npcs
            self.game.level.npcs = [{
                "name": name,
                "rect": npc_rect,
                "ground_y": npc_rect.bottom,
            }]
            try:
                preview = pygame.Surface((220, 160), pygame.SRCALPHA)
                self.game.level._draw_npcs(
                    preview, 0, 0, self.game.assets.npc_frames
                )
            finally:
                self.game.level.npcs = original_npcs
            self.assertEqual(
                preview.get_bounding_rect().bottom,
                npc_rect.bottom + self.game.level.NPC_GROUND_EMBED,
                name,
            )

        self.game.load_level("vila")
        for npc in self.game.level.npcs:
            frame = self.game.assets.npc_frames[npc["name"]][0]
            visible = frame.get_bounding_rect()
            drawn_top = (
                npc["ground_y"]
                + self.game.level.NPC_GROUND_EMBED
                - visible.bottom
            )
            self.assertEqual(
                drawn_top + visible.bottom - npc["ground_y"],
                5,
                npc["name"],
            )

    def test_zoom_one_draws_directly_without_allocating_world_buffer(self):
        import game as game_module

        game = self.game
        screen = SimpleNamespace(surface=pygame.Surface((1920, 1080)).convert())
        game._world_surface = None
        with patch.object(game_module, "CAMERA_ZOOM", 1):
            game.draw(screen)
        self.assertIsNone(game._world_surface)

    def test_dash_trail_reuses_layers_without_changing_pixels(self):
        game = self.game
        game.player.dash_timer = 1
        game.player.dash_direction = 1
        actual = pygame.Surface((1920, 1080), pygame.SRCALPHA)
        expected = pygame.Surface((1920, 1080), pygame.SRCALPHA)
        game.draw_dash_trail(actual)

        start_x = game.player.x - game.camera_x + game.player.rect.width // 2 - 12
        center_y = game.player.y - game.camera_y + game.player.rect.height // 2
        for offset, alpha in ((0, 150), (12, 95), (24, 45)):
            layer = pygame.Surface((42, 8), pygame.SRCALPHA)
            layer.fill((91, 220, 255, alpha))
            expected.blit(layer, (int(start_x - offset), int(center_y - 4)))

        self.assertEqual(
            pygame.image.tostring(actual, "RGBA"),
            pygame.image.tostring(expected, "RGBA"),
        )
        before = tuple(map(id, game.assets.dash_trail_layers))
        game.draw_dash_trail(actual)
        self.assertEqual(tuple(map(id, game.assets.dash_trail_layers)), before)

    def test_rewritten_dialogues_fit_and_keep_the_story_contract(self):
        from cutscene import IntroCutscene
        from game_data import (
            NPC_DIALOGUES,
            NPC_REPEAT,
            ROOM_LORE,
            SCIENCE_FACTS,
            SCIENCE_REACTIONS,
        )

        game = self.game
        sequences = [(name, content) for name, content in NPC_DIALOGUES.items()]
        sequences.extend((name, text) for name, text in NPC_REPEAT.items())
        sequences.extend(("Lia", content) for content in ROOM_LORE.values())
        sequences.extend(
            (
                "Ciência Delas",
                (("Ciência Delas", fact), ("Lia", SCIENCE_REACTIONS[name])),
            )
            for name, fact in SCIENCE_FACTS.items()
        )
        sequences.append(("Mãe", IntroCutscene.BEATS))

        lia_cancer_mentions = 0
        for default_speaker, content in sequences:
            for speaker, text in game.interactions.dialogue_beats(default_speaker, content):
                with self.subTest(speaker=speaker, text=text):
                    _lines, size, _line_height = game.dialogue._fit_text(text)
                    self.assertEqual(size, game.dialogue.TEXT_SIZE)
                if speaker == "Lia" and "câncer" in text.lower():
                    lia_cancer_mentions += 1

        self.assertEqual(len(IntroCutscene.BEATS), 12)
        self.assertEqual(lia_cancer_mentions, 2)
        cadu_text = " ".join(text for _speaker, text in NPC_DIALOGUES["Cadu"])
        self.assertIn("F", cadu_text)
        self.assertIn("clique esquerdo", cadu_text)

    def test_intro_energy_frames_share_one_canvas_and_swap_at_black(self):
        from cutscene import IntroCutscene

        paths = (IntroCutscene.BACKGROUND_PATH, *IntroCutscene.ENERGY_FRAME_PATHS)
        self.assertTrue(all(path.is_file() for path in paths))
        self.assertEqual(
            {pygame.image.load(path).get_size() for path in paths},
            {(1672, 941)},
        )

        intro = self.game.intro
        intro.done = False
        intro._start_energy_sequence()
        swapped_at = []
        previous_index = -1
        with patch.object(intro, "_load_energy_frame") as load_frame:
            for _tick in range(1000):
                intro.update(False)
                if intro.energy_frame_index != previous_index:
                    swapped_at.append(intro.fade_alpha)
                    previous_index = intro.energy_frame_index
                if not intro.active:
                    break

        self.assertEqual(load_frame.call_count, 6)
        self.assertEqual(swapped_at, [255] * 6)
        self.assertTrue(intro.finished_on_black)
        self.assertEqual(intro.fade_alpha, 255)

    def test_cadu_teaches_attack_before_the_first_village_slime(self):
        from level import VILLAGE

        game = self.game
        game.load_level(VILLAGE)
        cadu = next(npc for npc in game.level.npcs if npc["name"] == "Cadu")
        slime = next(enemy for enemy in game.level.enemies if type(enemy).__name__ == "Slime")
        self.assertLess(cadu["rect"].right, slime.rect.left)
        self.assertTrue(
            any(
                ground.top == cadu["ground_y"]
                and ground.left < cadu["rect"].right
                and ground.right > cadu["rect"].left
                for ground in game.level.grounds
            )
        )

    def test_phase_one_has_no_legacy_bench_or_return_route(self):
        game = self.game
        game.load_level(0)
        self.assertIsNone(game.level.bench)
        self.assertEqual(game.level.return_route_platforms, [])
        self.assertFalse(game.level.return_route_active)

    def test_research_and_room_lore_use_the_shared_dialogue_queue(self):
        from game_data import ROOM_LORE, SCIENCE_FACTS, SCIENCE_REACTIONS

        game = self.game
        research_rect, research_name = game.level.research[0]
        self.assertTrue(game._collect_research(SimpleNamespace(rect=research_rect.copy())))
        self.assertEqual(
            game.dialogue.current,
            ("Ciência Delas", SCIENCE_FACTS[research_name]),
        )
        self.assertEqual(
            game.interactions._dialogue_queue,
            [("Lia", SCIENCE_REACTIONS[research_name])],
        )
        game.dialogue.reveal_all()
        game.interactions.update_dialogue(True)
        self.assertEqual(game.dialogue.current, ("Lia", SCIENCE_REACTIONS[research_name]))

        game.load_level(1)
        game.enter_room("biblioteca")
        artifact_rect, artifact_name = game.level.artifacts[0]
        self.assertTrue(game._collect_artifacts(SimpleNamespace(rect=artifact_rect.copy())))
        expected = list(ROOM_LORE[artifact_name])
        self.assertEqual(game.dialogue.current, expected[0])
        self.assertEqual(game.interactions._dialogue_queue, expected[1:])

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
        game.items.counts = {"gororoba": 2}
        game.save_progress()
        before = game.SAVE_PATH.read_bytes()
        game.enter_room("laboratorio_secreto")
        game.save_progress()
        self.assertEqual(game.SAVE_PATH.read_bytes(), before)
        game.lives = 1
        self.assertTrue(game.load_progress())
        self.assertEqual(game.lives, 3.5)
        self.assertEqual(game.items.counts, {"gororoba": 2})
        self.assertIsNone(game.level.room)


if __name__ == "__main__":
    unittest.main()
