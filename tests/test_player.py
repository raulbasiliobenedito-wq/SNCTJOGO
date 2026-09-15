"""Mapeamento e transições da spritesheet completa da Lia."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from test_support import configure_game_imports, shutdown_pygame

configure_game_imports()

import pygame

from player import Player


class PlayerAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        shutdown_pygame()

    def setUp(self):
        self.player = Player()

    def test_sheet_has_97_unscaled_frames_and_reference_is_excluded(self):
        self.assertEqual(len(self.player.frames), 97)
        self.assertEqual({frame.get_size() for frame in self.player.frames}, {(48, 48)})
        self.assertEqual(
            {frame.get_size() for frame in self.player.render_frames},
            {(60, 60)},
        )
        used = set().union(
            self.player.IDLE_FRAMES,
            self.player.WALK_START_FRAMES,
            self.player.JUMP_UP_FRAMES,
            self.player.JUMP_FALL_FRAMES,
            self.player.LAND_FRAMES,
            self.player.DASH_FRAMES,
            self.player.SWIM_START_FRAMES,
            self.player.SWIM_LOOP_FRAMES,
            self.player.ATTACK_FRAMES,
            self.player.HURT_FRAMES,
            self.player.DEATH_FRAMES,
            self.player.RANGED_FRAMES,
            self.player.SWIM_IDLE_FRAMES,
        )
        self.assertNotIn(self.player.REFERENCE_FRAME, used)
        self.assertEqual(used, set(range(96)))

    def test_walk_plays_9_to_22_then_loops_13_to_22(self):
        self.player.grounded = True
        self.player.vx = 1
        frames = []
        for _ in range(len(self.player.WALK_START_FRAMES) * self.player.WALK_FRAME_TICKS):
            self.player.animate()
            frames.append(self.player.frame)
        expected = [frame for frame in self.player.WALK_START_FRAMES for _ in range(5)]
        self.assertEqual(frames, expected)
        for _ in range(len(self.player.WALK_LOOP_FRAMES) * self.player.WALK_FRAME_TICKS):
            self.player.animate()
            frames.append(self.player.frame)
        self.assertEqual(
            frames[-len(self.player.WALK_LOOP_FRAMES) * self.player.WALK_FRAME_TICKS:],
            [frame for frame in self.player.WALK_LOOP_FRAMES for _ in range(5)],
        )

    def test_fall_loops_28_29_and_landing_ends_on_34(self):
        self.player.grounded = False
        self.player.vy = 3
        falling = []
        for _ in range(2 * self.player.FALL_FRAME_TICKS):
            self.player.animate()
            falling.append(self.player.frame)
        self.assertEqual(falling, [27] * 6 + [28] * 6)

        self.player.grounded = True
        self.player.start_landing()
        landing = []
        for _ in range(len(self.player.LAND_FRAMES) * self.player.LAND_FRAME_TICKS):
            self.player.animate()
            landing.append(self.player.frame)
        self.assertEqual(landing[-1], 33)

    def test_swim_stops_in_reverse_then_enters_idle_swim(self):
        self.player.swimming = True
        self.player.vx = 1
        for _ in range(len(self.player.SWIM_START_FRAMES) * self.player.SWIM_FRAME_TICKS):
            self.player.animate()
        self.assertEqual(self.player.swim_phase, "loop")

        self.player.vx = 0
        self.player.up_held = False
        reverse = []
        for _ in range(len(self.player.SWIM_START_FRAMES) * self.player.SWIM_FRAME_TICKS):
            self.player.animate()
            reverse.append(self.player.frame)
        expected = [frame for frame in self.player.SWIM_START_FRAMES[::-1] for _ in range(6)]
        self.assertEqual(reverse, expected)
        self.player.animate()
        self.assertEqual(self.player.frame, self.player.SWIM_IDLE_FRAMES[0])

    def test_death_mapping_ends_on_ground_pose(self):
        frames = [
            self.player.DEATH_FRAMES[
                min(
                    len(self.player.DEATH_FRAMES) - 1,
                    tick // self.player.DEATH_FRAME_TICKS,
                )
            ]
            for tick in range(len(self.player.DEATH_FRAMES) * self.player.DEATH_FRAME_TICKS)
        ]
        self.assertEqual(frames[0], 74)
        self.assertEqual(frames[-1], 81)


if __name__ == "__main__":
    unittest.main()
