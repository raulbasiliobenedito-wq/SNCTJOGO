"""Filtro azul sincronizado com a respiração da Lia."""

import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from test_support import configure_game_imports, shutdown_pygame

configure_game_imports()

import pygame

from game import Game


class UnderwaterOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        shutdown_pygame()

    def setUp(self):
        self.game = Game.__new__(Game)
        self.game.level = SimpleNamespace(
            water_zones=[pygame.Rect(0, 100, 200, 100)]
        )
        self.game._underwater_overlay = None

    @staticmethod
    def player_with_head(rect):
        return SimpleNamespace(
            head_rect=rect,
            oxygen=100,
            OXYGEN_MAX_FRAMES=100,
            OXYGEN_DRAIN_PER_FRAME=1,
            OXYGEN_REFILL_PER_FRAME=2,
        )

    def test_head_must_clear_surface_before_filter_disappears(self):
        submerged = self.player_with_head(pygame.Rect(50, 105, 24, 10))
        breathing = self.player_with_head(pygame.Rect(50, 90, 24, 10))

        self.assertTrue(self.game._player_head_submerged(submerged))
        self.assertFalse(self.game._player_head_submerged(breathing))

    def test_overlay_tints_only_while_head_is_submerged_and_is_reused(self):
        original = pygame.Color(200, 160, 120)
        surface = pygame.Surface((64, 48), pygame.SRCALPHA).convert_alpha()
        self.game.player = self.player_with_head(pygame.Rect(50, 105, 24, 10))
        surface.fill(original)

        self.game._draw_underwater_overlay(surface)

        self.assertNotEqual(surface.get_at((0, 0)), original)
        cached_overlay = self.game._underwater_overlay
        self.game._draw_underwater_overlay(surface)
        self.assertIs(self.game._underwater_overlay, cached_overlay)

        self.game.player.head_rect = pygame.Rect(50, 90, 24, 10)
        surface.fill(original)
        self.game._draw_underwater_overlay(surface)
        self.assertEqual(surface.get_at((0, 0)), original)

    def test_oxygen_uses_the_same_head_condition(self):
        player = self.player_with_head(pygame.Rect(50, 105, 24, 10))
        self.game.invuln_timer = 0
        self.game.take_damage = lambda _damage: None

        self.assertFalse(self.game._update_oxygen(player))
        self.assertEqual(player.oxygen, 99)

        player.head_rect = pygame.Rect(50, 90, 24, 10)
        self.assertFalse(self.game._update_oxygen(player))
        self.assertEqual(player.oxygen, 100)


if __name__ == "__main__":
    unittest.main()
