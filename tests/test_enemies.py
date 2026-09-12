"""Compara comportamento e desenho com referências anteriores à extração."""

import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import enemy
from enemy_scenarios import ENEMY_NAMES, SCENARIOS, record_scenario


class EnemyCharacterizationTests(unittest.TestCase):
    def test_original_tick_traces_and_pixels(self):
        path = Path(__file__).with_name("fixtures") / "ground_enemies.json"
        reference = json.loads(path.read_text(encoding="utf-8"))
        for name in ENEMY_NAMES:
            for scenario in SCENARIOS:
                with self.subTest(enemy=name, scenario=scenario):
                    actual = record_scenario(getattr(enemy, name), scenario)
                    self.assertEqual(actual, reference["cases"][f"{name}/{scenario}"])

    def test_hit_immunity_and_respawn_timing(self):
        for name in ENEMY_NAMES:
            with self.subTest(enemy=name):
                actor = getattr(enemy, name)(SimpleNamespace(rect=pygame.Rect(20, 140, 240, 30)))
                self.assertTrue(actor.take_hit())
                self.assertEqual(actor.health, actor.HEALTH - 1)
                self.assertFalse(actor.take_hit())
                for _ in range(actor.HURT_DURATION - 1):
                    actor.update()
                self.assertEqual(actor.state, actor.HURT)
                actor.update()
                self.assertEqual(actor.state, actor.WALK)
                self.assertTrue(actor.take_hit(100))
                self.assertFalse(actor.alive)
                for _ in range(actor.DEATH_FRAMES * actor.DEATH_FRAME_TIME):
                    actor.update()
                self.assertEqual(actor.state, actor.DEAD)
                self.assertFalse(actor.stomp())
                for _ in range(actor.RESPAWN_TIME - 1):
                    actor.update()
                self.assertEqual(actor.state, actor.DEAD)
                actor.update()
                self.assertTrue(actor.alive)
                self.assertEqual(actor.health, actor.HEALTH)
                self.assertEqual(actor.state, actor.WALK)
                self.assertEqual(actor.x, actor.platform.rect.centerx - actor.WIDTH // 2)

    def test_stomp_during_hurt_still_kills(self):
        for name in ENEMY_NAMES:
            with self.subTest(enemy=name):
                actor = getattr(enemy, name)(SimpleNamespace(rect=pygame.Rect(0, 100, 200, 30)))
                actor.take_hit()
                self.assertTrue(actor.stomp())
                self.assertEqual(actor.health, 0)
                self.assertEqual(actor.state, actor.DYING)
                self.assertFalse(actor.stomp())


if __name__ == "__main__":
    unittest.main()
