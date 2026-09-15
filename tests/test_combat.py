"""Contrato do combate, executado antes e depois da extração de Game."""

import hashlib
import json
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
from enemy import AncientGolem, Librarian, Slime
from game_data import (
    ATTACK_COOLDOWN,
    ATTACK_DURATION,
    ATTACK_FRAME_TICKS,
    GAME_OVER,
    PLAYING,
)
from projectile import Projectile


def combat_state(game):
    """Permite capturar a referência também na versão anterior à extração."""
    return getattr(game, "combat", game)


def call_combat(game, name, *args):
    if hasattr(game, "combat"):
        return getattr(game.combat, name)(*args)
    legacy = name if name == "check_enemies" else "_" + name
    return getattr(game, legacy)(*args)


def attack_sequence(game):
    game.load_level(0)
    game.level.enemies = []
    game.player.reset(100, 100)
    game.ranged_unlocked = False
    combat = combat_state(game)
    trace = hashlib.sha256()
    with patch("audio.play_sfx") as sound:
        for tick in range(240):
            game.player.dash_timer = int(30 <= tick < 45)
            game.player.facing_right = tick < 145
            if tick == 5:
                game.ranged_unlocked = True
            call_combat(game, "update_attack", tick in (0, 1, 20, 40, 60, 80, 150))
            call_combat(game, "update_ranged_attack", tick in (0, 5, 6, 74, 75, 145))
            call_combat(game, "apply_attack_frame")
            call_combat(game, "update_projectiles")
            state = [combat.attack_timer, combat.attack_cooldown, combat.attack_power,
                     combat.combo_count, combat.attack_animation_index(),
                     combat.attack_hit_index(), combat.ranged_cooldown,
                     game.player.frame,
                     [[p.x, p.y, p.direction, p.traveled, p.alive] for p in combat.projectiles]]
            trace.update(json.dumps(state, separators=(",", ":")).encode())
        return {"ticks": 240, "trace_sha256": trace.hexdigest(),
                "sounds": [c.args[0] for c in sound.call_args_list], "final": state}


class CombatTests(unittest.TestCase):
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
        game.level.enemies = []
        game.player.reset(100, 100)
        game.player.facing_right = True
        game.dialogue.close()
        game.lives = 5
        game.shield = 0
        game.ranged_unlocked = False
        self.combat = combat_state(game)

    def enemy(self, kind=Slime, x=140, y=100):
        actor = kind(SimpleNamespace(rect=pygame.Rect(0, 148, 400, 32)))
        actor.x, actor.y = x, y
        self.game.level.enemies.append(actor)
        return actor

    def test_attack_sequence_matches_current_contract(self):
        expected = json.loads((Path(__file__).with_name("fixtures") / "combat_sequence.json").read_text(encoding="utf-8"))
        self.assertEqual(attack_sequence(self.game), expected["sequence"])

    def test_one_click_runs_four_hit_combo_then_half_second_cooldown(self):
        frames = []
        hit_powers = []
        seen_hits = set()
        with patch("audio.play_sfx") as sound:
            call_combat(self.game, "update_attack", True)
            self.assertEqual(self.combat.attack_timer, ATTACK_DURATION)
            self.assertEqual(self.combat.attack_cooldown, 0)
            for _ in range(ATTACK_DURATION):
                call_combat(self.game, "apply_attack_frame")
                frames.append(self.game.player.frame)
                hit = self.combat.attack_hit_index()
                if hit is not None and hit not in seen_hits:
                    seen_hits.add(hit)
                    hit_powers.append(self.combat.attack_power)
                call_combat(self.game, "update_attack", False)

        expected_frames = [
            frame
            for frame in self.game.player.ATTACK_FRAMES
            for _ in range(ATTACK_FRAME_TICKS)
        ]
        self.assertEqual(frames, expected_frames)
        self.assertEqual(seen_hits, {0, 1, 2, 3})
        self.assertEqual(hit_powers, [1, 1, 1, 2])
        self.assertEqual(
            [call.args[0] for call in sound.call_args_list],
            ["punch.punch_1", "punch.punch_2", "punch.punch_3", "punch.punch_4"],
        )
        self.assertEqual((self.combat.attack_timer, self.combat.attack_cooldown), (0, ATTACK_COOLDOWN))
        for _ in range(ATTACK_COOLDOWN - 1):
            call_combat(self.game, "update_attack", False)
        call_combat(self.game, "update_attack", True)
        self.assertTrue(self.combat.attacking)

    def test_attack_box_direction_and_dash(self):
        self.assertIsNone(call_combat(self.game, "attack_box"))
        for facing, dash, expected in [(True, False, (117, 99, 46, 58)), (False, False, (47, 99, 46, 58)),
                                       (True, True, (110, 99, 60, 58)), (False, True, (26, 99, 60, 58))]:
            self.game.player.facing_right = facing
            self.combat.attack_started_dashing = dash
            impact_frame = 4 if dash else 14
            self.combat.attack_timer = ATTACK_DURATION - impact_frame * ATTACK_FRAME_TICKS
            self.assertEqual(tuple(call_combat(self.game, "attack_box")), expected)

    def test_each_punch_can_damage_same_target_once(self):
        target = self.enemy(Librarian, x=140)
        call_combat(self.game, "update_attack", True)
        for _ in range(ATTACK_DURATION):
            call_combat(self.game, "check_enemies")
            call_combat(self.game, "update_attack", False)
        self.assertEqual(target.health, target.HEALTH - 5)

    def test_golem_uses_its_own_damage_debris_without_generic_impact(self):
        target = self.enemy(AncientGolem, x=140)
        self.combat.attack_timer = 5
        with patch.object(self.game.vfx, "spawn") as spawn:
            call_combat(self.game, "check_enemies")
        self.assertEqual(target.health, target.HEALTH - 1)
        self.assertEqual(target.effects[0]["kind"], "damage_debris")
        spawn.assert_not_called()

    def test_ranged_unlock_direction_and_cooldown(self):
        call_combat(self.game, "update_ranged_attack", True)
        self.assertEqual(self.combat.projectiles, [])
        self.game.ranged_unlocked = True
        self.game.player.facing_right = False
        call_combat(self.game, "update_ranged_attack", True)
        shot = self.combat.projectiles[0]
        self.assertEqual((shot.x, shot.y, shot.direction), (96, 120, -1))
        self.assertEqual(
            self.game.player.ranged_timer,
            len(self.game.player.RANGED_FRAMES) * self.game.player.RANGED_FRAME_TICKS,
        )
        call_combat(self.game, "update_ranged_attack", True)
        self.assertEqual(len(self.combat.projectiles), 1)
        self.assertEqual(self.combat.ranged_cooldown, 69)

    def test_projectile_consumed_even_when_target_rejects_hit(self):
        target = self.enemy(x=160)
        target.take_hit()
        health = target.health
        self.combat.projectiles = [Projectile(150, 120, 1, 14, 1, 500)]
        call_combat(self.game, "update_projectiles")
        self.assertEqual(target.health, health)
        self.assertEqual(self.combat.projectiles, [])

    def test_projectile_expiration_precedes_collision(self):
        target = self.enemy(x=160)
        self.combat.projectiles = [Projectile(150, 120, 1, 14, 1, 14)]
        call_combat(self.game, "update_projectiles")
        self.assertEqual(target.health, target.HEALTH)
        self.assertEqual(self.combat.projectiles, [])

    def test_projectile_defeat_reports_drop_once(self):
        target = self.enemy(x=160)
        target.health = 1
        self.combat.projectiles = [Projectile(150, 120, 1, 14, 1, 500)]
        with patch.object(self.game.items, "on_enemy_defeated") as defeated:
            call_combat(self.game, "update_projectiles")
            call_combat(self.game, "update_projectiles")
        defeated.assert_called_once_with(target)

    def test_melee_checks_remaining_targets_after_contact(self):
        self.enemy(x=65)  # Contato à esquerda, fora do alcance da espada.
        target = self.enemy(x=140)
        self.combat.attack_timer = 5
        call_combat(self.game, "check_enemies")
        self.assertEqual(target.health, target.HEALTH - 1)
        self.assertEqual(self.game.lives, 4.5)
        self.assertEqual(self.game.hitstop_timer, 2)

    def test_boss_shield_blocks_melee_but_allows_projectile(self):
        boss = self.enemy(Librarian, x=108)
        boss.state = boss.ESCUDO_ACTIVE
        self.combat.attack_timer = 5
        call_combat(self.game, "check_enemies")
        self.assertEqual(boss.health, boss.HEALTH)
        self.assertEqual(self.game.lives, 4)
        self.combat.projectiles = [Projectile(96, 120, 1, 14, 1, 500)]
        call_combat(self.game, "update_projectiles")
        self.assertEqual(boss.health, boss.HEALTH - 1)

    def test_stomp_bounces_on_common_enemy_and_skips_boss(self):
        target = self.enemy(x=105, y=140)
        self.game.player.vy = 3
        self.assertTrue(call_combat(self.game, "stomp_enemy_if_possible", self.game.player, 140))
        self.assertFalse(target.alive)
        self.assertEqual((self.game.player.y, self.game.player.vy), (92, -10.5))
        self.game.level.enemies = []
        boss = self.enemy(Librarian, x=105, y=140)
        self.game.player.reset(100, 100)
        self.game.player.vy = 3
        self.assertFalse(call_combat(self.game, "stomp_enemy_if_possible", self.game.player, 140))
        self.assertEqual(boss.health, boss.HEALTH)

    def test_parry_cancels_hazard_before_damage_and_grants_drop(self):
        boss = self.enemy(Librarian, x=300)
        boss.health = 1
        hazards = [pygame.Rect(120, 110, 20, 20)]
        cancelled = Mock(side_effect=hazards.clear)
        boss.parryable_hazards = lambda: [(rect, cancelled) for rect in hazards]
        boss.active_hazards = lambda: hazards
        self.combat.attack_timer = 5
        self.game.level.room = "teste"
        self.game.check_events()
        cancelled.assert_called_once_with()
        self.assertEqual(self.game.lives, 5)
        self.assertEqual(self.game.invuln_timer, 60)
        self.assertEqual(self.game.hitstop_timer, 3)
        self.assertEqual(self.game.shake_timer, 14)
        self.assertEqual([d["item"] for d in self.game.items.drops], ["livro_magico"])

    def test_hitstop_freezes_combat_timers_but_updates_shake(self):
        self.game.hitstop_timer = 2
        self.game.shake_timer = 4
        self.combat.attack_timer = 5
        self.combat.attack_cooldown = 12
        with patch.object(self.game.level, "update") as update_level:
            self.game._update_playing(SimpleNamespace(), True, True, True, 1 / 60)
        update_level.assert_not_called()
        self.assertEqual((self.combat.attack_timer, self.combat.attack_cooldown), (5, 12))
        self.assertEqual((self.game.hitstop_timer, self.game.shake_timer), (1, 3))

    def test_hurt_interrupts_combo_and_death_holds_last_frame(self):
        call_combat(self.game, "update_attack", True)
        self.assertTrue(self.combat.attacking)
        self.game.take_damage(0.5)
        self.assertFalse(self.combat.attacking)
        self.assertEqual(self.combat.attack_cooldown, ATTACK_COOLDOWN)
        self.assertEqual(self.game.player.frame, self.game.player.HURT_FRAMES[0])

        self.game.lives = 0.5
        self.game.take_damage(0.5)
        self.assertEqual(self.game.state, GAME_OVER)
        for _ in range(self.game.DEATH_POSE_DURATION + 3):
            self.game._update_end_state(SimpleNamespace(r=False))
        self.assertEqual(self.game.player.frame, self.game.player.DEATH_FRAMES[-1])

    def test_level_reset_clears_transient_combat_only(self):
        self.combat.attack_timer = 5
        self.combat.combo_count = 3
        self.combat.projectiles = [Projectile(150, 120, 1, 14, 1, 500)]
        self.game.ranged_unlocked = True
        self.game.items.counts = {"gororoba": 2}
        self.game.load_level(1)
        self.combat = combat_state(self.game)
        self.assertEqual((self.combat.attack_timer, self.combat.combo_count, self.combat.projectiles), (0, 0, []))
        self.assertTrue(self.game.ranged_unlocked)
        self.assertEqual(self.game.items.counts, {"gororoba": 2})


if __name__ == "__main__":
    unittest.main()
