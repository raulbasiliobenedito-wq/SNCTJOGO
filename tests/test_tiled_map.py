"""Regressões da ordem e do recorte do desenho dos mapas."""

import json
import os
from pathlib import Path
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from test_support import configure_game_imports, shutdown_pygame

configure_game_imports()

import pygame
from map_render_scenarios import CASES, record_map_renderings
from tiled_map import TiledMap


class _RecordingSurface:
    def __init__(self, size):
        self.surface = pygame.Surface(size, pygame.SRCALPHA)
        self.calls = []

    def get_width(self):
        return self.surface.get_width()

    def get_height(self):
        return self.surface.get_height()

    def blit(self, image, position):
        self.calls.append((image, position))
        return self.surface.blit(image, position)


class TiledMapRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        shutdown_pygame()

    def test_real_maps_match_camera_references(self):
        path = Path(__file__).with_name("fixtures") / "map_rendering.json"
        reference = json.loads(path.read_text(encoding="utf-8"))
        actual = record_map_renderings()
        self.assertEqual(set(actual), set(CASES))
        self.assertEqual(actual, reference["cases"])

    def test_binary_alpha_cross_chunk_tile_is_drawn_once_without_pixel_change(self):
        tiled = self._synthetic_map()
        crossing = pygame.Surface((96, 64), pygame.SRCALPHA)
        crossing.fill((0, 0, 0, 0))
        pygame.draw.rect(crossing, (32, 96, 224, 255), (0, 0, 48, 64))
        pygame.draw.rect(crossing, (32, 96, 224, 255), (64, 0, 32, 64))
        overlay = pygame.Surface((24, 64), pygame.SRCALPHA)
        overlay.fill((240, 64, 48, 255))
        entries = [
            (224, 24, crossing, 96, 64),
            (232, 24, overlay, 24, 64),
        ]
        chunks = tiled._build_chunks(entries)

        expected = self._legacy_draw(tiled, chunks)
        actual = _RecordingSurface((360, 128))
        tiled._draw_chunks(actual, 0, 0, chunks, {})

        self.assertEqual(
            pygame.image.tostring(actual.surface, "RGBA"),
            pygame.image.tostring(expected.surface, "RGBA"),
        )
        crossing_calls = sum(image is crossing for image, _position in actual.calls)
        self.assertEqual(crossing_calls, 1)
        self.assertEqual(len(expected.calls), 3)
        self.assertEqual(len(actual.calls), 2)

    def test_partial_alpha_cross_chunk_tile_keeps_legacy_repetitions(self):
        tiled = self._synthetic_map()
        crossing = pygame.Surface((96, 64), pygame.SRCALPHA)
        crossing.fill((32, 96, 224, 128))
        overlay = pygame.Surface((24, 64), pygame.SRCALPHA)
        overlay.fill((240, 64, 48, 255))
        entries = [
            (224, 24, crossing, 96, 64),
            (232, 24, overlay, 24, 64),
        ]
        chunks = tiled._build_chunks(entries)

        expected = self._legacy_draw(tiled, chunks)
        actual = _RecordingSurface((360, 128))
        tiled._draw_chunks(actual, 0, 0, chunks, {})

        self.assertEqual(
            pygame.image.tostring(actual.surface, "RGBA"),
            pygame.image.tostring(expected.surface, "RGBA"),
        )
        crossing_calls = sum(image is crossing for image, _position in actual.calls)
        self.assertEqual(crossing_calls, 2)
        self.assertEqual(len(actual.calls), len(expected.calls))

    @staticmethod
    def _synthetic_map():
        tiled = TiledMap.__new__(TiledMap)
        tiled.tile_width = 32
        tiled.tile_height = 32
        tiled._binary_alpha_cache = {}
        tiled._current_frames = {}
        return tiled

    @staticmethod
    def _legacy_draw(tiled, chunks):
        surface = _RecordingSurface((360, 128))
        right = surface.get_width()
        bottom = surface.get_height()
        chunk_w = tiled.CHUNK_TILES * tiled.tile_width
        chunk_h = tiled.CHUNK_TILES * tiled.tile_height
        for chunk_row in range(-1, int(bottom // chunk_h) + 2):
            for chunk_col in range(-1, int(right // chunk_w) + 2):
                for x, y, image, width, height in chunks.get(
                    (chunk_col, chunk_row), ()
                ):
                    if x + width < 0 or x > right:
                        continue
                    if y + height < 0 or y > bottom:
                        continue
                    surface.blit(image, (x, y))
        return surface


if __name__ == "__main__":
    unittest.main()
