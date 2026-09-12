"""Roteiros determinísticos para caracterizar os inimigos antes de refatorar."""

import hashlib
import json
from types import SimpleNamespace

import pygame


ENEMY_NAMES = ("Slime", "CrystalStag", "PossessedStudent", "JanitorGuardian")
SCENARIOS = {"patrol": 420, "narrow_platform": 100, "damage_respawn": 1600, "stomp_while_hurt": 1400}


def _sprites(enemy):
    result = {}
    for row, state in enumerate(("walk", "idle", "hurt", "dead")):
        result[state] = []
        for index in range(enemy.DEATH_FRAMES):
            image = pygame.Surface((enemy.WIDTH + 13, enemy.HEIGHT + 17), pygame.SRCALPHA)
            image.fill(((row * 51 + 17) % 256, (index * 19 + 31) % 256, 123, 173))
            # Marca assimétrica: um espelhamento incorreto muda os pixels.
            pygame.draw.rect(image, (250, 20, 47, 255), (2, 3, 5 + index, 7))
            result[state].append(image)
    return result


def record_scenario(enemy_class, scenario):
    platform = SimpleNamespace(rect=pygame.Rect(-45, 140, 220, 24))
    if scenario == "narrow_platform":
        platform.rect.width = 12
    enemy = enemy_class(platform)
    sprites = _sprites(enemy)
    trace = hashlib.sha256()
    pixels = hashlib.sha256()
    surface = pygame.Surface((360, 220), pygame.SRCALPHA)
    transitions = []
    actions = []
    drawn_frames = 0
    previous = None
    for tick in range(SCENARIOS[scenario]):
        if scenario == "patrol" and tick in (120, 180):
            platform.rect.move_ip(35 if tick == 120 else -35, -12 if tick == 120 else 12)
        if scenario == "damage_respawn":
            if tick in (80, 81, 140, 141):
                result = enemy.take_hit(1 if tick < 140 else 100)
                actions.append([tick, "hit", result])
            if tick == 300:
                platform.rect.move_ip(20, -16)
        if scenario == "stomp_while_hurt":
            if tick == 1:
                actions.append([tick, "hit", enemy.take_hit()])
            if tick in (2, 3):
                actions.append([tick, "stomp", enemy.stomp()])
        enemy.update()
        values = [enemy.x, enemy.y, enemy.direction, enemy.speed, enemy.health,
                  enemy.state, enemy.state_timer, enemy.death_frame, enemy.animation,
                  list(enemy.rect), enemy.alive]
        trace.update(json.dumps(values, separators=(",", ":")).encode("utf-8"))
        # Todas as transições e todos os quadros de morte entram no registro visual.
        changed = (enemy.state, enemy.direction, enemy.death_frame) != previous
        if changed:
            transitions.append([tick, enemy.state, enemy.direction, enemy.death_frame])
        if changed or tick % 13 == 0:
            surface.fill((25, 42, 60, 255))
            enemy.draw(surface, platform.rect.left - 45.5, 3.25, sprites)
            pixels.update(pygame.image.tostring(surface, "RGBA"))
            drawn_frames += 1
        previous = (enemy.state, enemy.direction, enemy.death_frame)
    return {"ticks": SCENARIOS[scenario], "trace_sha256": trace.hexdigest(),
            "pixels_sha256": pixels.hexdigest(), "drawn_frames": drawn_frames,
            "transitions": transitions, "actions": actions, "final": values}
