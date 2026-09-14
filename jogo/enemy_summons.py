"""Invocações transitórias criadas por ataques de chefes."""

import random

import pygame

from sprites import flipped


class SmallSlime:
    """Slime pequeno cuspido pelo Rei Slime no ataque Cisão (slime_common.png,
    32x32 — o mesmo corpo do Rei, sem coroa nem núcleo coral). Vive numa
    zona curta ao redor do ponto onde nasceu (ver Level.update, que drena
    SlimeKing.pending_spawns). Diferente dos outros inimigos do jogo, não
    respawna: uma vez morto fica morto (é ameaça transitória da arena do
    chefe, não um inimigo permanente do mapa) e não larga item — só o Rei
    larga a Essência de Slime (LEIA-ME_bosses_e_itens.md, §2.2)."""

    WIDTH = 24
    HEIGHT = 20
    GROUND_LIFT = 2
    HEALTH = 1
    SPEED = 0.8
    PLATFORM_MARGIN = 4
    HURT_DURATION = 12
    DEATH_FRAME_TIME = 6
    DEATH_FRAMES = 6

    WALK = "walk"
    HURT = "hurt"
    DYING = "dying"
    DEAD = "dead"
    ACTIVE_STATES = (WALK, HURT)

    def __init__(self, platform):
        self.platform = platform
        self.x = platform.rect.centerx - self.WIDTH // 2
        self.y = platform.rect.top - self.HEIGHT
        self.direction = random.choice((-1, 1))
        self.speed = self.SPEED
        self.health = self.HEALTH
        self.state = self.WALK
        self.state_timer = 0
        self.death_frame = 0
        self.animation = 0

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
            return
        elif self.state == self.HURT:
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = self.WALK
        else:
            self._patrol()

    def _patrol(self):
        left = self.platform.rect.left + self.PLATFORM_MARGIN
        right = self.platform.rect.right - self.WIDTH - self.PLATFORM_MARGIN
        if left >= right:
            self.x = left
        else:
            self.x += self.speed * self.direction
            if self.x <= left or self.x >= right:
                self.x = max(left, min(self.x, right))
                self.direction *= -1
        self.y = self.platform.rect.top - self.HEIGHT

    def take_hit(self, damage=1):
        if not self.alive or self.state == self.HURT:
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

    def draw(self, surface, camera_x, camera_y, sprites):
        if self.state == self.DEAD:
            return
        key = "dead" if self.state == self.DYING else ("hurt" if self.state == self.HURT else "walk")
        frames = sprites[key]
        frame = self._animation_frame(frames)
        if self.direction < 0:
            frame = flipped(frame)
        frame_w, frame_h = frame.get_size()
        offset_x = (frame_w - self.WIDTH) // 2
        offset_y = frame_h - self.HEIGHT - self.GROUND_LIFT
        surface.blit(frame, (self.x - offset_x - camera_x, self.y - offset_y - camera_y))

    def _animation_frame(self, frames):
        if self.state == self.DYING:
            return frames[min(self.death_frame, len(frames) - 1)]
        if self.state == self.HURT:
            return frames[(self.animation // 4) % len(frames)]
        return frames[(self.animation // 5) % len(frames)]
