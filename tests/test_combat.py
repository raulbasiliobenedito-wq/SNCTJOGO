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
from enemy import Librarian, Slime
from game_data import PLAYING
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
                     combat.combo_count, combat.combo_timer, combat.ranged_cooldown,
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

    def test_attack_sequence_matches_original(self):
        expected = json.loads((Path(__file__).with_name("fixtures") / "combat_sequence.json").read_text(encoding="utf-8"))
        self.assertEqual(attack_sequence(self.game), expected["sequence"])

    def test_combo_cooldown_finisher_and_expiration(self):
        counts, powers = [], []
        for tick in range(81):
            call_combat(self.game, "update_attack", tick % 20 == 0)
            if tick % 20 == 0:
                counts.append(self.combat.combo_count)
                powers.append(self.combat.attack_power)
                self.assertEqual(self.combat.attack_timer, 10)
                self.assertEqual(self.combat.attack_cooldown, 20)
        self.assertEqual(counts, [1, 2, 3, 4, 1])
        self.assertEqual(powers, [1, 1, 1, 2, 1])
        for _ in range(40):
            call_combat(self.game, "update_attack", False)
        call_combat(self.game, "update_attack", True)
        self.assertEqual(self.combat.combo_count, 1)

    def test_attack_box_direction_and_dash(self):
        self.assertIsNone(call_combat(self.game, "attack_box"))
        self.combat.attack_timer = 5
        for facing, dash, expected in [(True, 0, (117, 99, 46, 58)), (False, 0, (47, 99, 46, 58)),
                                       (True, 1, (110, 99, 60, 58)), (False, 1, (26, 99, 60, 58))]:
            self.game.player.facing_right = facing
            self.game.player.dash_timer = dash
            self.assertEqual(tuple(call_combat(self.game, "attack_box")), expected)

    def test_ranged_unlock_direction_and_cooldown(self):
        call_combat(self.game, "update_ranged_attack", True)
        self.assertEqual(self.combat.projectiles, [])
        self.game.ranged_unlocked = True
        self.game.player.facing_right = False
        call_combat(self.game, "update_ranged_attack", True)
        shot = self.combat.projectiles[0]
        self.assertEqual((shot.x, shot.y, shot.direction), (96, 120, -1))
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
