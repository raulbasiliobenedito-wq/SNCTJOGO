"""Contratos do Golem Ancião e de sua arena na vila/campo."""

import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from test_support import configure_game_imports, shutdown_pygame

configure_game_imports()

import pygame

from assets import Assets
from enemy_ancient_golem import AncientGolem
from game_data import BOSS_NAMES
from level import Level, VILLAGE


class AncientGolemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((320, 180))

    @classmethod
    def tearDownClass(cls):
        shutdown_pygame()

    def setUp(self):
        self.platform = SimpleNamespace(rect=pygame.Rect(5600, 480, 576, 32))
        self.golem = AncientGolem(self.platform)

    def advance(self, count):
        for _ in range(count):
            self.golem.update()

    def start_pattern_attack(self, index, player_x=6100):
        self.golem.wake_up()
        self.golem.attack_index = index
        self.golem.face_player(player_x)
        self.golem._start_attack()

    def test_village_map_builds_golem_and_locked_arena(self):
        level = Level(VILLAGE)
        golem = next(enemy for enemy in level.enemies if isinstance(enemy, AncientGolem))

        self.assertEqual(tuple(golem.platform.rect), (5600, 480, 576, 32))
        arena = next(entry for entry in level.boss_arenas if entry["enemy"] is golem)
        self.assertEqual(tuple(arena["zone"]), (5568, 0, 640, 640))
        self.assertEqual(golem.state, golem.DORMANT)
        self.assertIn("AncientGolem", BOSS_NAMES)

    def test_slam_spawns_local_impact_then_sequential_waves(self):
        self.start_pattern_attack(0)
        self.assertEqual(self.golem.state, self.golem.SLAM)

        self.advance(self.golem.SLAM_IMPACT_FRAME * self.golem.SLAM_FRAME_TICKS - 1)
        self.assertEqual(self.golem.effects, [])
        self.golem.update()

        self.assertEqual(
            [effect["kind"] for effect in self.golem.effects],
            ["ground_slam_impact", "rock_shockwave"],
        )
        self.assertEqual(len(self.golem.shockwave_queue), 3)
        hazards = self.golem.active_hazards()
        self.assertEqual(len(hazards), 2)
        self.assertEqual(
            {(hazard.width, hazard.height) for hazard in hazards},
            {(66, 34), (51, 34)},
        )

        self.advance(self.golem.SHOCKWAVE_INTERVAL)
        self.assertEqual(
            sum(effect["kind"] == "rock_shockwave" for effect in self.golem.effects),
            2,
        )

    def test_charge_locks_direction_moves_and_leaves_dust(self):
        self.start_pattern_attack(1, player_x=6200)
        self.assertEqual(self.golem.state, self.golem.CHARGE_TELEGRAPH)
        self.assertEqual(self.golem.direction, 1)

        self.advance(self.golem.CHARGE_TELEGRAPH_FRAMES * self.golem.CHARGE_TELEGRAPH_FRAME_TICKS)
        self.assertEqual(self.golem.state, self.golem.CHARGE_ACTIVE)
        x_before = self.golem.x
        self.golem.face_player(5000)  # execução não pode virar para perseguir.
        self.golem.update()

        self.assertGreater(self.golem.x, x_before)
        self.assertEqual(self.golem.direction, 1)
        self.assertIn("charge_dust", [effect["kind"] for effect in self.golem.effects])

    def test_throw_releases_ballistic_boulder_on_frame_thirteen(self):
        self.start_pattern_attack(2)
        self.advance(self.golem.THROW_RELEASE_FRAME * self.golem.THROW_FRAME_TICKS - 1)
        self.assertEqual(self.golem.boulders, [])
        self.golem.update()

        self.assertEqual(len(self.golem.boulders), 1)
        boulder = self.golem.boulders[0]
        self.assertGreater(boulder["vx"], 0)
        self.assertLess(boulder["vy"], 0)
        self.assertEqual(len(self.golem.active_hazards()), 1)

    def test_hurt_uses_debris_and_death_clears_every_hazard(self):
        self.assertTrue(self.golem.take_hit())
        self.assertEqual(self.golem.state, self.golem.HURT)
        self.assertEqual(self.golem.effects[0]["kind"], "damage_debris")

        self.golem.health = 1
        self.assertTrue(self.golem.take_hit(1, allow_hurt=True))
        self.assertEqual(self.golem.state, self.golem.DYING)
        self.assertFalse(self.golem.alive)
        self.assertEqual(self.golem.effects, [])
        self.assertEqual(self.golem.boulders, [])
        self.assertEqual(self.golem.active_hazards(), [])

        self.advance(self.golem.DEATH_FRAMES * self.golem.DEATH_FRAME_TIME)
        self.assertEqual(self.golem.state, self.golem.DEAD)
        self.assertEqual(self.golem.death_frame, self.golem.DEATH_FRAMES - 1)

    def test_sprite_loader_uses_all_body_and_vfx_frames(self):
        sprites = Assets.__new__(Assets)._load_ancient_golem_sprites()
        self.assertEqual(
            {key: len(sprites[key]) for key in ("idle", "walk", "charge", "slam", "throw", "hurt", "dead")},
            {"idle": 11, "walk": 8, "charge": 16, "slam": 17, "throw": 16, "hurt": 7, "dead": 17},
        )
        self.assertEqual(
            {
                frame.get_size()
                for key in ("idle", "walk", "charge", "slam", "throw", "hurt", "dead")
                for frame in sprites[key]
            },
            {(138, 138)},
        )
        self.assertEqual(
            {key: len(value) for key, value in sprites["vfx"].items()},
            {
                "rock_shockwave": 9,
                "ground_slam_impact": 7,
                "charge_dust": 7,
                "charge_impact": 9,
                "projectile": 9,
                "boulder_explosion": 9,
                "damage_debris": 8,
            },
        )
        self.assertEqual(
            {
                key: {frame.get_size() for frame in frames}
                for key, frames in sprites["vfx"].items()
            },
            {
                "rock_shockwave": {(96, 96)},
                "ground_slam_impact": {(96, 96)},
                "charge_dust": {(72, 72)},
                "charge_impact": {(96, 96)},
                "projectile": {(96, 96)},
                "boulder_explosion": {(96, 96)},
                "damage_debris": {(96, 96)},
            },
        )


if __name__ == "__main__":
    unittest.main()
