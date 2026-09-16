"""Contratos de portas, diálogos e puzzles anteriores à extração."""

import os
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from test_support import configure_game_imports

configure_game_imports()

import pygame
from game import Game
from puzzles import PuzzleSystem
from interactions import InteractionSystem
from game_data import NPC_DIALOGUES, NPC_REPEAT
from minigame import MICROSCOPE_ORDER, WIRE_COLORS


class InteractionTests(unittest.TestCase):
    def setUp(self):
        game = self.game = Game.__new__(Game)
        game.puzzles = PuzzleSystem(game)
        game.interactions = InteractionSystem(game)
        rect = pygame.Rect(100, 100, 20, 20)
        game.player = SimpleNamespace(rect=rect)
        game.dialogue = Mock(finished=False)
        game.elevator_cutscene = Mock(active=False)
        game.minigame = Mock()
        game.items = SimpleNamespace(counts={})
        game.assets = SimpleNamespace(energy_box_sprites={"test": True}, puzzle_sprites={
            "microscope_parts": ["lens", "base", "light", "ocular"],
            "microscope_complete": "complete", "microscope_body": "body",
            "lab_bench_assembled": "bench",
        })
        game.level = SimpleNamespace(
            room=None, is_underground=True, doors=[], secret_elevators=[], npcs=[],
            fog_barriers=[], energy_box=rect.copy(), panel_lever=rect.copy(),
            buttons=[rect.move(i * 200, 0) for i in range(4)],
            lab_bench={"rect": rect.copy(), "libera": "laboratorio"},
            lab_microscope_parts=[(rect.copy(), "parte")],
            set_lever_active=Mock(), activate_return_route=Mock(), update_lever_animations=Mock(),
        )
        game.interact_pressed = True
        game.interactions._dialogue_queue = []
        game.puzzles._minigame_escape_was_down = False
        game.puzzles.lever_on = False
        game.puzzles.sequence_solved = False
        game.puzzles.sequence_progress = 0
        game.puzzles.microscope_assembled = False
        game.puzzles.microscope_collected = set()
        game.puzzles.microscope_slots = dict.fromkeys(MICROSCOPE_ORDER, False)
        game.puzzles.energy_box_state = {"screws_removed": False, "wired": False}
        game.puzzles.energy_box_wires = dict.fromkeys(WIRE_COLORS, False)
        self.sound = self.enterContext(patch("audio.play_sfx"))

    def test_interaction_priority_stops_at_first_handler(self):
        game = self.game
        names = ["_use_doors", "_use_secret_elevator", "_talk_to_npc",
                 "_use_panel_lever", "_use_sequence_button"]
        for stop in range(len(names)):
            calls = []
            with self.subTest(stop=names[stop]), ExitStack() as stack:
                for i, name in enumerate(names):
                    def handler(*args, i=i, name=name):
                        calls.append(name)
                        return i == stop
                    stack.enter_context(patch.object(game.interactions if hasattr(game.interactions, name[1:]) else game.puzzles, name[1:], side_effect=handler))
                game.interactions.handle_interactions()
            self.assertEqual(calls, names[:stop + 1])
        game.interact_pressed = False
        with patch.object(game.interactions, "use_doors") as door:
            game.interactions.handle_interactions()
        door.assert_not_called()

    def test_secondary_rooms_do_not_use_corridor_puzzles(self):
        game = self.game
        for room, handler in (("laboratorio", "_use_energy_box"),
                              ("laboratorio_secreto", "_use_lab_microscope_bench")):
            game.level.room = room
            with patch.object(game.puzzles, handler[1:], return_value=False) as use, patch.object(game.puzzles, "use_panel_lever") as panel:
                game.interactions.handle_interactions()
            use.assert_called_once_with(game.player)
            panel.assert_not_called()

    def test_door_uses_first_nearby_target_and_exit(self):
        game = self.game
        rect = game.player.rect
        game.level.doors = [{"rect": rect.move(500, 0), "target": "longe"},
                            {"rect": rect.copy(), "target": "biblioteca"},
                            {"rect": rect.copy(), "target": "laboratorio"}]
        with patch.object(game, "enter_room") as enter:
            self.assertTrue(game.interactions.use_doors())
        enter.assert_called_once_with("biblioteca")
        game.level.doors[1]["target"] = "sair"
        with patch.object(game, "exit_room") as leave:
            self.assertTrue(game.interactions.use_doors())
        leave.assert_called_once_with()
        self.assertEqual([c.args[0] for c in self.sound.call_args_list], ["door_sound", "door_sound"])

    def test_elevator_gate_and_delayed_transition(self):
        game = self.game
        barrier = SimpleNamespace(chave="lab", encountered=False)
        game.level.fog_barriers = [barrier]
        elevator = {"rect": game.player.rect.copy(), "chave": "lab", "destino": "laboratorio_secreto"}
        game.level.secret_elevators = [elevator]
        with patch.object(game, "enter_room") as enter:
            self.assertTrue(game.interactions.use_secret_elevator())
            game.elevator_cutscene.start.assert_not_called()
            barrier.encountered = True
            self.assertTrue(game.interactions.use_secret_elevator())
            enter.assert_not_called()
            kwargs = game.elevator_cutscene.start.call_args.kwargs
            self.assertFalse(kwargs["reverse"])
            kwargs["on_finish"]()
        enter.assert_called_once_with("laboratorio_secreto")

    def test_elevator_exit_reverse_and_active_guard(self):
        game = self.game
        game.level.secret_elevators = [{"rect": game.player.rect.copy(), "chave": "", "destino": "sair"}]
        with patch.object(game, "exit_room") as leave:
            self.assertTrue(game.interactions.use_secret_elevator())
            kwargs = game.elevator_cutscene.start.call_args.kwargs
            self.assertTrue(kwargs["reverse"])
            leave.assert_not_called()
            kwargs["on_finish"]()
        leave.assert_called_once_with()
        game.elevator_cutscene.active = True
        game.elevator_cutscene.start.reset_mock()
        self.assertFalse(game.interactions.use_secret_elevator())
        game.elevator_cutscene.start.assert_not_called()

    def test_npc_reveal_queue_then_close_and_repeat(self):
        game = self.game
        game.level.npcs = [{"rect": game.player.rect.copy(), "name": "Teste"}]
        beats = (("Teste", "primeira"), ("Lia", "segunda"), ("Teste", "terceira"))
        with patch.dict(NPC_DIALOGUES, Teste=beats), patch.dict(NPC_REPEAT, Teste="lembrete"):
            self.assertTrue(game.interactions.talk_to_npc())
            game.dialogue.start.assert_called_with("Teste", "primeira")
            game.interactions.update_dialogue(True)
            game.dialogue.reveal_all.assert_called_once_with()
            self.assertEqual(
                game.interactions._dialogue_queue,
                [("Lia", "segunda"), ("Teste", "terceira")],
            )
            game.dialogue.finished = True
            game.interactions.update_dialogue(True)
            game.dialogue.start.assert_called_with("Lia", "segunda")
            game.interactions.update_dialogue(True)
            game.dialogue.start.assert_called_with("Teste", "terceira")
            game.interactions.update_dialogue(True)
            game.dialogue.close.assert_called_once_with()
            self.assertTrue(game.interactions.talk_to_npc())
            game.dialogue.start.assert_called_with("Teste", "lembrete")
        self.assertEqual(game.level.update_lever_animations.call_count, 4)

    def test_single_npc_clears_old_queue_and_idle_dialogue_updates(self):
        game = self.game
        game.interactions._dialogue_queue = [("Antigo", "antiga")]
        game.level.npcs = [{"rect": game.player.rect.copy(), "name": "Teste"}]
        with patch.dict(NPC_DIALOGUES, Teste="fala única"):
            self.assertTrue(game.interactions.talk_to_npc())
        self.assertEqual(game.interactions._dialogue_queue, [])
        game.interactions.update_dialogue(False)
        game.dialogue.update.assert_called_once_with()

    def test_dialogue_sequence_accepts_legacy_and_alternating_formats(self):
        interactions = self.game.interactions
        cases = (
            ("fala única", [("Teste", "fala única")]),
            (("primeira", "segunda"), [("Teste", "primeira"), ("Teste", "segunda")]),
            ((("Teste", "primeira"), ("Lia", "segunda")), [("Teste", "primeira"), ("Lia", "segunda")]),
        )
        for content, expected in cases:
            with self.subTest(content=content):
                self.game.dialogue.reset_mock()
                self.assertTrue(interactions.start_dialogue_sequence("Teste", content))
                self.game.dialogue.start.assert_called_once_with(*expected[0])
                self.assertEqual(interactions._dialogue_queue, expected[1:])

        with self.assertRaises(ValueError):
            interactions.start_dialogue_sequence("Teste", (("sem texto",),))

    def test_dialogue_reset_can_preserve_or_clear_repeat_history(self):
        interactions = self.game.interactions
        interactions._visited_npcs.add("Teste")
        interactions.reset_dialogue()
        self.assertEqual(interactions._visited_npcs, {"Teste"})
        interactions.reset_dialogue(clear_visits=True)
        self.assertEqual(interactions._visited_npcs, set())

    def test_panel_off_resets_progress_but_keeps_solved_state(self):
        game = self.game
        self.assertTrue(game.puzzles.use_panel_lever(game.player))
        self.assertTrue(game.puzzles.lever_on)
        game.puzzles.sequence_progress, game.puzzles.sequence_solved = 3, True
        self.assertTrue(game.puzzles.use_panel_lever(game.player))
        self.assertFalse(game.puzzles.lever_on)
        self.assertEqual(game.puzzles.sequence_progress, 0)
        self.assertTrue(game.puzzles.sequence_solved)
        self.assertEqual([c.args for c in game.level.set_lever_active.call_args_list], [("panel", True), ("panel", False)])

    def test_sequence_requires_power_resets_on_error_then_completes(self):
        game = self.game
        self.assertTrue(game.puzzles.use_sequence_button(game.player))
        self.assertEqual(game.puzzles.sequence_progress, 0)
        game.puzzles.lever_on = True
        game.player.rect = game.level.buttons[1].copy()
        self.assertTrue(game.puzzles.use_sequence_button(game.player))
        self.assertEqual(game.puzzles.sequence_progress, 0)
        for index, rect in enumerate(game.level.buttons):
            game.player.rect = rect.copy()
            self.assertTrue(game.puzzles.use_sequence_button(game.player))
            self.assertEqual(game.puzzles.sequence_progress, index + 1)
        self.assertTrue(game.puzzles.sequence_solved)
        self.sound.assert_called_with("correct_sequence_sound")
        game.puzzles.use_sequence_button(game.player)
        self.assertEqual(game.puzzles.sequence_progress, 4)

    def test_elevator_lab_parts_are_the_phase_one_microscope_parts(self):
        game = self.game
        game.puzzles.collect_lab_microscope_parts(game.player)
        self.assertEqual(game.puzzles.microscope_collected, {0})
        game.puzzles.collect_lab_microscope_parts(game.player)
        self.assertEqual(self.sound.call_count, 1)

    def test_elevator_lab_bench_waits_for_parts_and_does_not_reopen(self):
        game = self.game
        with patch.object(game.puzzles, "open_lab_microscope_minigame") as lab:
            self.assertTrue(game.puzzles.use_lab_microscope_bench(game.player))
            lab.assert_not_called()
            game.puzzles.microscope_collected.add(0)
            game.puzzles.use_lab_microscope_bench(game.player)
            lab.assert_called_once_with()
            game.puzzles.microscope_assembled = True
            game.puzzles.use_lab_microscope_bench(game.player)
            self.assertEqual(lab.call_count, 1)

    def test_absent_or_distant_elevator_lab_bench_does_not_open(self):
        game = self.game
        game.level.lab_bench = None
        self.assertFalse(game.puzzles.use_lab_microscope_bench(game.player))
        game.level.lab_bench = {"rect": game.player.rect.move(500, 0)}
        self.assertFalse(game.puzzles.use_lab_microscope_bench(game.player))

    def test_elevator_lab_minigame_uses_canonical_phase_one_progress(self):
        game = self.game
        with patch("puzzles.MicroscopeMinigame") as constructor:
            game.puzzles.open_lab_microscope_minigame()
            args, kwargs = constructor.call_args
            self.assertIs(args[4], game.puzzles.microscope_slots)
            self.assertEqual(args[2], {"objetiva": "lens", "base": "base", "iluminador": "light", "ocular": "ocular"})
            self.assertEqual(args[3], "bench")
            self.assertEqual(kwargs, {})

    def test_energy_box_requires_tool_unless_lid_removed_and_reuses_progress(self):
        game = self.game
        with patch("puzzles.EnergyBoxMinigame") as constructor:
            self.assertTrue(game.puzzles.use_energy_box(game.player))
            constructor.assert_not_called()
            game.items.counts["chave_fenda"] = 1
            self.assertTrue(game.puzzles.use_energy_box(game.player))
            args = constructor.call_args.args
            self.assertIs(args[3], game.puzzles.energy_box_state)
            self.assertIs(args[4], game.puzzles.energy_box_wires)
            self.assertEqual(game.items.counts, {"chave_fenda": 1})
            game.items.counts.clear()
            game.puzzles.energy_box_state["screws_removed"] = True
            game.puzzles.use_energy_box(game.player)
            self.assertEqual(constructor.call_count, 2)
            game.puzzles.energy_box_state["wired"] = True
            game.puzzles.use_energy_box(game.player)
            self.assertEqual(constructor.call_count, 2)

    def test_absent_art_or_far_energy_box_does_not_handle_interaction(self):
        game = self.game
        game.level.energy_box = None
        self.assertFalse(game.puzzles.use_energy_box(game.player))
        game.level.energy_box = game.player.rect.copy()
        game.assets.energy_box_sprites = None
        self.assertFalse(game.puzzles.use_energy_box(game.player))
        game.assets.energy_box_sprites = {}
        game.level.energy_box = game.player.rect.move(500, 0)
        self.assertFalse(game.puzzles.use_energy_box(game.player))
        game.minigame.open.assert_not_called()

    def test_escape_closes_without_updating_and_preserves_slots(self):
        game = self.game
        game.puzzles.microscope_slots["base"] = True
        game.puzzles.update_minigame(SimpleNamespace(escape=True), 1 / 60)
        game.minigame.close.assert_called_once_with()
        game.minigame.update.assert_not_called()
        self.assertTrue(game.puzzles.microscope_slots["base"])
        game.minigame.drain_sfx.return_value = []
        game.minigame.pop_result.return_value = None
        game.puzzles.update_minigame(SimpleNamespace(escape=True), 1 / 60)
        game.minigame.update.assert_called_once_with(1 / 60)
        self.assertEqual(game.minigame.close.call_count, 1)

    def test_minigame_sounds_precede_completion_without_removed_return_route(self):
        game = self.game
        calls = []
        self.sound.side_effect = lambda name: calls.append(name)
        game.minigame.drain_sfx.return_value = ["piece_sound"]
        game.minigame.pop_result.return_value = ("microscope", "completed")
        with patch.object(game, "_release_fog_barrier", side_effect=lambda key: calls.append(key)):
            game.puzzles.update_minigame(SimpleNamespace(escape=False), 0.1)
        self.assertTrue(game.puzzles.microscope_assembled)
        self.assertEqual(calls, ["piece_sound", "microscope_sound", "laboratorio"])
        game.level.activate_return_route.assert_not_called()

    def test_energy_results_do_not_open_routes_or_mark_unfinished_puzzles(self):
        game = self.game
        for result in ("wired", "closed_mistakes"):
            game.puzzles.finish_minigame("energy_box", result)
        self.assertEqual(game.dialogue.start.call_count, 2)
        game.level.activate_return_route.assert_not_called()
        game.puzzles.finish_minigame("microscope", "cancelled")
        self.assertFalse(game.puzzles.microscope_assembled)
