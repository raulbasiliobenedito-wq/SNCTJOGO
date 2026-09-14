"""Comportamento específico da entidade sombria flutuante."""

import math
import random

import pygame

from sprites import flipped


class DarkWraith:
    """Entidade sombria flutuante: boia devagar (com balanço vertical) dentro
    de uma faixa e, periodicamente, faz uma investida rápida e telegrafada
    (antecipação -> arranco -> recuperação) na direção em que está voltada."""

    # Ampliado 1.6x ao carregar (ver game.py _load_wraith_sprites); a hitbox
    # aqui é um pouco menor que o quadro desenhado (77x77) pra manter o
    # combate justo.
    WIDTH = 48
    HEIGHT = 54
    GROUND_LIFT = 0
    HEALTH = 3
    FLOAT_SPEED = 0.5
    BOB_AMPLITUDE = 6
    BOB_PERIOD = 90
    ZONE_MARGIN = 10
    ATTACK_COOLDOWN_MIN = 190
    ATTACK_COOLDOWN_MAX = 280
    ANTICIPATION_DURATION = 24
    LUNGE_DURATION = 10
    LUNGE_DISTANCE = 130
    RECOVER_DURATION = 26
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 20
    DEATH_FRAME_TIME = 5
    DEATH_FRAMES = 14

    FLOAT = "float"
    ANTICIPATION = "anticipation"
    LUNGE = "lunge"
    RECOVER = "recover"
    HURT = "hurt"
    DYING = "dying"
    DEAD = "dead"
    ACTIVE_STATES = (FLOAT, ANTICIPATION, LUNGE, RECOVER, HURT)

    def __init__(self, zone):
        self.zone = zone
        rect = zone.rect
        self.anchor_x = rect.centerx - self.WIDTH // 2
        self.anchor_y = rect.centery - self.HEIGHT // 2
        self.x = self.anchor_x
        self.y = self.anchor_y
        self.direction = 1
        self.health = self.HEALTH
        self.state = self.FLOAT
        self.state_timer = self._next_attack_delay()
        self.death_frame = 0
        self.animation = 0
        self.lunge_start_x = self.x
        self.half_range = max(0, rect.width // 2 - self.WIDTH // 2 - self.ZONE_MARGIN)

    @staticmethod
    def _next_attack_delay():
        return random.randint(DarkWraith.ATTACK_COOLDOWN_MIN, DarkWraith.ATTACK_COOLDOWN_MAX)

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.WIDTH, self.HEIGHT)

    @property
    def alive(self):
        return self.state in self.ACTIVE_STATES

    def update(self):
        self.animation += 1
        if self.state == self.DYING:
            self._update_death()
        elif self.state == self.DEAD:
            self._update_respawn()
        elif self.state == self.HURT:
            self._update_hurt()
        elif self.state == self.ANTICIPATION:
            self._update_anticipation()
        elif self.state == self.LUNGE:
            self._update_lunge()
        elif self.state == self.RECOVER:
            self._update_recover()
        else:
            self._update_float()

    def _update_float(self):
        if self.half_range > 0:
            self.x += self.FLOAT_SPEED * self.direction
            offset = self.x - self.anchor_x
            if offset <= -self.half_range or offset >= self.half_range:
                self.x = self.anchor_x + max(-self.half_range, min(offset, self.half_range))
                self.direction *= -1
        self.y = self.anchor_y + math.sin(self.animation / self.BOB_PERIOD * 2 * math.pi) * self.BOB_AMPLITUDE
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.ANTICIPATION
            self.state_timer = self.ANTICIPATION_DURATION

    def _update_anticipation(self):
        self.y = self.anchor_y + math.sin(self.animation / self.BOB_PERIOD * 2 * math.pi) * self.BOB_AMPLITUDE
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.LUNGE
            self.state_timer = self.LUNGE_DURATION
            self.lunge_start_x = self.x

    def _update_lunge(self):
        self.state_timer -= 1
        progress = 1 - self.state_timer / self.LUNGE_DURATION
        self.x = self.lunge_start_x + self.direction * self.LUNGE_DISTANCE * progress
        if self.state_timer <= 0:
            self.state = self.RECOVER
            self.state_timer = self.RECOVER_DURATION

    def _update_recover(self):
        self.state_timer -= 1
        self.x += (self.anchor_x + max(-self.half_range, min(self.x - self.anchor_x, self.half_range)) - self.x) * 0.08
        if self.state_timer <= 0:
            self.direction *= -1
            self.state = self.FLOAT
            self.state_timer = self._next_attack_delay()

    def _update_hurt(self):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.FLOAT
            self.state_timer = self._next_attack_delay()

    def take_hit(self, damage=1, allow_hurt=False):
        if not self.alive or (self.state == self.HURT and not allow_hurt):
            return False
        self.health -= damage
        if self.health <= 0:
            self._start_dying()
        else:
            self.state = self.HURT
            self.state_timer = self.HURT_DURATION
        return True

    def stomp(self):
        if not self.alive:
            return False
        self.health = 0
        self._start_dying()
        return True

    def _start_dying(self):
        self.state = self.DYING
        self.state_timer = self.DEATH_FRAMES * self.DEATH_FRAME_TIME
        self.death_frame = 0

    def _update_death(self):
        self.state_timer -= 1
        self.death_frame = min(
            self.DEATH_FRAMES - 1,
            self.death_frame + int(self.state_timer % self.DEATH_FRAME_TIME == 0),
        )
        if self.state_timer <= 0:
            self.state = self.DEAD
            self.state_timer = self.RESPAWN_TIME

    def _update_respawn(self):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.health = self.HEALTH
            self.state = self.FLOAT
            self.state_timer = self._next_attack_delay()
            self.death_frame = 0
            self.x = self.anchor_x
            self.y = self.anchor_y
            self.direction = 1

    def draw(self, surface, camera_x, camera_y, sprites):
        if self.state == self.DEAD:
            return
        key = self._sprite_key()
        frames = sprites[key]
        frame = self._animation_frame(frames)
        if self.direction < 0:
            frame = flipped(frame)
        frame_w, frame_h = frame.get_size()
        offset_x = (frame_w - self.WIDTH) // 2
        offset_y = (frame_h - self.HEIGHT) // 2
        surface.blit(frame, (self.x - offset_x - camera_x, self.y - offset_y - camera_y))

    def _sprite_key(self):
        if self.state == self.DYING:
            return "dead"
        if self.state == self.HURT:
            return "hurt"
        if self.state in (self.ANTICIPATION, self.LUNGE, self.RECOVER):
            return "lunge"
        return "idle"

    def _animation_frame(self, frames):
        if self.state == self.DYING:
            return frames[min(self.death_frame, len(frames) - 1)]
        if self.state == self.ANTICIPATION:
            # Antecipação lenta: prende nos 2 primeiros quadros da investida,
            # a marca de aviso, por mais tempo que o resto do ciclo.
            slot = min(1, self.animation // 12 % 2)
            return frames[slot]
        if self.state == self.LUNGE:
            slot = 2 + (self.animation // 2 % max(1, len(frames) - 2))
            return frames[min(slot, len(frames) - 1)]
        if self.state == self.RECOVER:
            slot = min(len(frames) - 1, 4 + self.animation // 6 % 3)
            return frames[slot]
        if self.state == self.HURT:
            return frames[(self.animation // 5) % len(frames)]
        return frames[(self.animation // 8) % len(frames)]
