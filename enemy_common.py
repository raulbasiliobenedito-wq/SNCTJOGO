"""Ciclo comum dos inimigos de chão e patrulha com pausas.

Os parâmetros de balanceamento ficam nas classes concretas em enemy.py.
Os temporizadores continuam medidos em quadros, com a mesma ordem de atualização.
"""

import pygame

from sprites import flipped


class GroundEnemy:
    """Posição, dano, morte e respawn dos inimigos permanentes de chão."""

    WALK = "walk"
    HURT = "hurt"
    DYING = "dying"
    DEAD = "dead"
    ACTIVE_STATES = (WALK, HURT)

    def __init__(self, platform):
        self.platform = platform
        self.x = platform.rect.centerx - self.WIDTH // 2
        self.y = platform.rect.top - self.HEIGHT
        self.direction = 1
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

    def _update_hurt(self):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK

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
            self.state_timer = self.RESPAWN_TIME

    def _update_respawn(self):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.health = self.HEALTH
            self.state = self.WALK
            self.death_frame = 0
            self.x = self.platform.rect.centerx - self.WIDTH // 2
            self.y = self.platform.rect.top - self.HEIGHT


class PausingGroundEnemy(GroundEnemy):
    """Patrulha com repouso nas bordas e desenho alinhado ao chão."""

    IDLE = "idle"
    ACTIVE_STATES = (IDLE, GroundEnemy.WALK, GroundEnemy.HURT)

    def update(self):
        self.animation += 1
        if self.state == self.DYING:
            self._update_death()
        elif self.state == self.DEAD:
            self._update_respawn()
        elif self.state == self.HURT:
            self._update_hurt()
        elif self.state == self.IDLE:
            self._update_idle()
        else:
            self._patrol()

    def _update_idle(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK

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
                self.state = self.IDLE
                self.state_timer = self.IDLE_DURATION
        self.y = self.platform.rect.top - self.HEIGHT

    def draw(self, surface, camera_x, camera_y, sprites):
        if self.state == self.DEAD:
            return
        key = "dead" if self.state == self.DYING else self.state
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
        if self.state == self.IDLE:
            return frames[(self.animation // 10) % len(frames)]
        return frames[(self.animation // 6) % len(frames)]
