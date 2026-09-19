"""Contratos de itens, capturados antes da extração de Game."""

import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from test_support import configure_game_imports, isolated_game_data, shutdown_pygame

configure_game_imports()

import pygame
from game_data import BOSS_DROP_TABLE, COMPLETE, ENEMY_DROP_TABLE, GAME_OVER, MAX_LIVES


class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1920, 1080))
        cls.isolation = isolated_game_data()
        cls.isolation.__enter__()
        from game import Game
        cls.game = Game()

    @classmethod
    def tearDownClass(cls):
        cls.isolation.__exit__(None, None, None)
        shutdown_pygame()

    def setUp(self):
        game = self.game
        game.load_level(0)
        game.player.reset(100, 100)
        game.lives = MAX_LIVES
        game.shield = 0
        game.items.counts.clear()
        game.dialogue.close()

    def test_full_health_keeps_healing_item_without_effect(self):
        game = self.game
        game.items.counts["gororoba"] = 1
        with patch.object(game.vfx, "spawn") as effect, patch.object(game, "show_message") as message:
            game.items.use_item("gororoba")
        self.assertEqual(game.items.counts, {"gororoba": 1})
        self.assertEqual(game.lives, MAX_LIVES)
        message.assert_called_once_with("Vidas já estão cheias.")
        effect.assert_not_called()

    def test_healing_caps_fractional_health_and_removes_last_item(self):
        game = self.game
        game.items.counts["gororoba"] = 1
        game.lives = MAX_LIVES - 0.5
        with patch.object(game.vfx, "spawn") as effect:
            game.items.use_item("gororoba")
        self.assertEqual(game.lives, MAX_LIVES)
        self.assertEqual(game.items.counts, {})
        effect.assert_called_once_with("dust", game.player.rect.centerx, game.player.rect.centery)

    def test_simultaneous_keys_keep_effect_order_and_stack_shield(self):
        game = self.game
        game.lives = MAX_LIVES - 1
        game.shield = 2
        game.items.counts.update(gororoba=1, carcaca_robo=1, dark_crystal=1)
        with patch.object(game, "show_message") as message:
            game.items.read_item_use(SimpleNamespace(k_1=True, k_2=True, k_3=True))
        self.assertEqual(game.lives, MAX_LIVES)
        self.assertEqual(game.shield, 4)
        self.assertEqual(game.items.counts, {})
        self.assertEqual([c.args[0] for c in message.call_args_list],
                         ["Gororoba usado!", "Carcaça de Robô usado!", "Dark Crystal usado!"])

    def test_quest_tools_and_absent_items_are_not_consumed(self):
        game = self.game
        expected = {"essencia_slime": 1, "chave_fenda": 2}
        game.items.counts.update(expected)
        with patch.object(game, "show_message") as message:
            for key in (*expected, "gororoba", "inexistente"):
                game.items.use_item(key)
        self.assertEqual(game.items.counts, expected)
        message.assert_not_called()

    def test_held_key_requires_release_and_input_reset_allows_new_use(self):
        game = self.game
        game.items.counts["carcaca_robo"] = 4
        key = SimpleNamespace(k_2=True)
        for _ in range(4):
            game.items.read_item_use(key)
        self.assertEqual((game.shield, game.items.counts["carcaca_robo"]), (1, 3))
        game.items.read_item_use(SimpleNamespace())
        game.items.read_item_use(key)
        self.assertEqual((game.shield, game.items.counts["carcaca_robo"]), (2, 2))
        game._reset_input_state()
        game.items.read_item_use(key)
        self.assertEqual((game.shield, game.items.counts["carcaca_robo"]), (3, 1))

    def enemy(self, name):
        return type(name, (), {"rect": pygame.Rect(40, 60, 20, 20)})()

    def test_boss_drops_are_guaranteed_without_random_draw(self):
        game = self.game
        with patch("random.random") as chance, patch("audio.play_sfx") as sound:
            for name in BOSS_DROP_TABLE:
                game.items.on_enemy_defeated(self.enemy(name))
        chance.assert_not_called()
        self.assertEqual(game.items.drops, [dict(item=key, x=50, y=70) for key in BOSS_DROP_TABLE.values()])
        self.assertEqual([c.args[0] for c in sound.call_args_list], ["boss_death_sound"] * 3)

    def test_golem_is_a_boss_but_does_not_create_an_extra_quest_item(self):
        game = self.game
        with patch("random.random") as chance, patch("audio.play_sfx") as sound:
            game.items.on_enemy_defeated(self.enemy("AncientGolem"))
        chance.assert_not_called()
        sound.assert_called_once_with("boss_death_sound")
        self.assertEqual(game.items.drops, [])
        self.assertEqual(game.message, "O caminho para o Bosque do Conhecimento foi liberado!")

    def test_common_drop_thresholds_and_unlisted_enemy(self):
        game = self.game
        with patch("audio.play_sfx") as sound:
            for name, (key, probability) in ENEMY_DROP_TABLE.items():
                with self.subTest(name=name), patch("random.random", side_effect=[probability - 0.001, probability]) as chance:
                    before = len(game.items.drops)
                    game.items.on_enemy_defeated(self.enemy(name))
                    game.items.on_enemy_defeated(self.enemy(name))
                    self.assertEqual(len(game.items.drops), before + 1)
                    self.assertEqual(game.items.drops[-1]["item"], key)
                    self.assertEqual(chance.call_count, 2)
            with patch("random.random") as chance:
                game.items.on_enemy_defeated(self.enemy("SmallSlime"))
            chance.assert_not_called()
        self.assertTrue(all(c.args == ("enemy_death_sound",) for c in sound.call_args_list))

    def test_pickup_overlap_stacks_items_once_and_preserves_outside_order(self):
        game = self.game
        player = SimpleNamespace(rect=pygame.Rect(100, 100, 20, 20))
        for key, x in [("gororoba", 78), ("gororoba", 79), ("gororoba", 110), ("dark_crystal", 500)]:
            game.items.spawn_drop(key, x, 110)
        game.items.counts["gororoba"] = 1
        with patch("audio.play_sfx") as sound, patch.object(game.vfx, "spawn") as effect:
            game.items.collect_drops(player)
            game.items.collect_drops(player)
        self.assertEqual(game.items.counts, {"gororoba": 3})
        self.assertEqual([d["x"] for d in game.items.drops], [78, 500])
        self.assertEqual(sound.call_count, 2)
        self.assertEqual([c.args for c in effect.call_args_list], [("dust", 79, 110), ("dust", 110, 110)])

    def test_tools_are_collected_once_per_index_only_on_overlap(self):
        game = self.game
        rect = pygame.Rect(100, 100, 20, 20)
        game.level.tool_pickups = [(rect, "chave_fenda"), (rect.copy(), "chave_fenda"),
                                   (rect.move(500, 0), "chave_fenda")]
        with patch("audio.play_sfx") as sound:
            for _ in range(2):
                game.items.collect_tools(SimpleNamespace(rect=rect))
        self.assertEqual(game.items.counts, {"chave_fenda": 2})
        self.assertEqual(game.tools_collected, {0, 1})
        self.assertEqual(sound.call_count, 2)

    def test_phase_and_room_changes_keep_inventory_but_clear_drops(self):
        game = self.game
        game.items.counts.update(gororoba=2, chave_fenda=1)
        game.shield = 3
        for transition in (lambda: game.load_level(1), lambda: game.enter_room("laboratorio"), game.exit_room):
            game.items.spawn_drop("gororoba", 100, 100)
            transition()
            self.assertEqual(game.items.counts, {"gororoba": 2, "chave_fenda": 1})
            self.assertEqual(game.shield, 3)
            self.assertEqual(game.items.drops, [])

    def test_restart_after_defeat_keeps_inventory_completion_clears_it(self):
        game = self.game
        for state, expected in ((GAME_OVER, {"gororoba": 2}), (COMPLETE, {})):
            game.items.counts.clear()
            game.items.counts["gororoba"] = 2
            game.state, game.lives, game.shield = state, 0, 3
            game.items.spawn_drop("gororoba", 100, 100)
            with patch("audio.play_sfx"):
                game._update_end_state(SimpleNamespace(r=True))
            self.assertEqual(game.items.counts, expected)
            self.assertEqual(game.items.drops, [])
            self.assertEqual((game.lives, game.shield), (5, 0))

    def test_save_roundtrip_keeps_v1_counts_and_discards_transient_drops(self):
        game = self.game
        expected = {"gororoba": 2, "livro_magico": 1, "chave_fenda": 1}
        game.items.counts.update(expected)
        game.shield = 3
        game.items.spawn_drop("dark_crystal", 100, 100)
        game.save_progress()
        saved = json.loads(game.SAVE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(saved["version"], 1)
        self.assertEqual(saved["inventory"], expected)
        self.assertNotIn("drops", saved)
        game.items.counts.clear()
        self.assertTrue(game.load_progress())
        self.assertEqual(game.items.counts, expected)
        self.assertEqual(game.shield, 3)
        self.assertEqual(game.items.drops, [])
