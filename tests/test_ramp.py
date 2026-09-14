"""Regressões da colisão pixel a pixel das rampas."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from test_support import (
    GAME_DIR,
    configure_game_imports,
    isolated_game_data,
    shutdown_pygame,
)

configure_game_imports()

import pygame

from level import Level
from ramp import Ramp
from tiled_map import TiledMap


def _right_ramp_mask(size=32):
    """Mesmo contorno 2x2 usado pelos tiles de grama atuais."""
    collision_mask = pygame.Mask((size, size))
    for x in range(2, size):
        top = size - 2 * (x // 2)
        for y in range(top, size):
            collision_mask.set_at((x, y))
    return collision_mask


class RampCollisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        shutdown_pygame()

    def test_climbing_follows_pixels_without_horizontal_pushback(self):
        ramp = Ramp(0, 0, 32, 32, True, _right_ramp_mask())
        bottom = 32
        for left in range(-20, 9, 4):
            bottom += 1  # gravidade aplicada antes da resolução
            player = pygame.Rect(left, bottom - 48, 24, 48)
            resolution = ramp.resolve(player, vx=4, vy=0.65, was_grounded=True)

            self.assertIsNotNone(resolution)
            dx, dy, on_surface = resolution
            self.assertEqual(dx, 0)
            self.assertTrue(on_surface)
            bottom += dy
            self.assertEqual(bottom, ramp._surface_y(player.left, player.right))

    def test_descending_snaps_to_each_pixel_step(self):
        ramp = Ramp(0, 0, 32, 32, True, _right_ramp_mask())
        bottom = ramp._surface_y(8, 32)
        for left in range(4, -21, -4):
            bottom += 1
            player = pygame.Rect(left, bottom - 48, 24, 48)
            dx, dy, on_surface = ramp.resolve(
                player,
                vx=-4,
                vy=0.65,
                was_grounded=True,
            )

            self.assertEqual(dx, 0)
            self.assertGreaterEqual(dy, 0)
            self.assertTrue(on_surface)
            bottom += dy
            self.assertEqual(bottom, ramp._surface_y(player.left, player.right))

    def test_high_edge_stays_a_wall_and_underside_stays_solid(self):
        ramp = Ramp(0, 0, 32, 32, True, _right_ramp_mask())

        side = ramp.resolve(
            pygame.Rect(31, -16, 24, 48),
            vx=-4,
            vy=0.65,
            was_grounded=True,
        )
        self.assertEqual(side, (1, 0, False))

        underside = ramp.resolve(
            pygame.Rect(8, 20, 24, 48),
            vx=0,
            vy=-5,
            was_grounded=False,
        )
        self.assertEqual(underside, (0, 12, False))

    def test_game_walks_over_real_village_ramp_and_reaches_plateau(self):
        with isolated_game_data():
            from game import Game, PLAYING
            from level import VILLAGE

            game = Game()
            game.load_level(VILLAGE)
            game.state = PLAYING
            game.level.enemies = []
            player = game.player
            player.x = 644
            player.y = 400
            player.vx = 4
            player.vy = 0
            game.player_grounded = True

            positions = []
            for _frame in range(34):
                previous_x = player.x
                game.move_player()
                positions.append((player.x, player.y, player.grounded))
                self.assertEqual(player.x, previous_x + 4)
                player.vx = 4

            self.assertEqual(player.x, 780)
            self.assertEqual(player.y, 304)
            self.assertTrue(all(grounded for _x, _y, grounded in positions))

    def test_real_tiles_supply_alpha_masks_and_merge_without_seams(self):
        tiled = TiledMap(GAME_DIR / "maps" / "vila.tmx")
        self.assertEqual(len(tiled.tile_ramps), 37)
        self.assertTrue(all(len(item) == 6 for item in tiled.tile_ramps))

        first_mask = tiled.tile_ramps[0][5]
        self.assertFalse(first_mask.get_at((0, 31)))
        self.assertTrue(first_mask.get_at((2, 30)))
        self.assertFalse(first_mask.get_at((2, 29)))

        merged = Level._merge_ramp_tiles(tiled.tile_ramps)
        long_ramp = next(item for item in merged if item[:4] == (2240, 256, 192, 192))
        self.assertEqual(long_ramp[5].get_size(), (192, 192))
        self.assertEqual(long_ramp[5].count(), sum(
            item[5].count()
            for item in tiled.tile_ramps
            if 2240 <= item[0] < 2432 and 256 <= item[1] < 448
        ))


if __name__ == "__main__":
    unittest.main()
