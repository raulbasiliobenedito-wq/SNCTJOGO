import math
import random

import pygame


class Slime:
    """Inimigo que patrulha somente a plataforma onde nasceu."""

    WIDTH = 52
    HEIGHT = 34
    # Pequeno ajuste pra cima: o tileset novo tem uma leve textura/borda no
    # topo do tile de rocha que fazia os inimigos parecerem com os pés
    # afundados na pedra quando alinhados exatamente na linha do chão.
    GROUND_LIFT = 3
    HEALTH = 2
    SPEED = 1.15
    PLATFORM_MARGIN = 8
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 20
    DEATH_FRAME_TIME = 4
    DEATH_FRAMES = 9

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

    def update(self):
        self.animation += 1
        if self.state == self.DYING:
            self._update_death()
        elif self.state == self.DEAD:
            self._update_respawn()
        elif self.state == self.HURT:
            self._update_hurt()
        else:
            self._patrol()

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

    def _update_hurt(self):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK

    def _patrol(self):
        left = self.platform.rect.left + self.PLATFORM_MARGIN
        right = self.platform.rect.right - self.WIDTH - self.PLATFORM_MARGIN
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
        """Pulo sobre o slime derrota-o imediatamente."""
        if not self.alive:
            return False
        self.health = 0
        self._start_dying()
        return True

    def _start_dying(self):
        self.state = self.DYING
        self.state_timer = self.DEATH_FRAMES * self.DEATH_FRAME_TIME
        self.death_frame = 0

    def draw(self, surface, camera_x, camera_y, sprites):
        if self.state == self.DEAD:
            return

        frames = sprites["dead" if self.state == self.DYING else self.state]
        frame = self._animation_frame(frames)
        if self.direction < 0:
            frame = pygame.transform.flip(frame, True, False)
        draw_y = self.y - camera_y + (14 if self.state == self.DYING else 2) - self.GROUND_LIFT
        surface.blit(frame, (self.x - 6 - camera_x, draw_y))

    def _animation_frame(self, frames):
        if self.state == self.DYING:
            return frames[min(self.death_frame, len(frames) - 1)]
        return frames[(self.animation // 8) % len(frames)]


class CrystalStag:
    """Cervo de cristal: patrulha o chão como o Slime, mas para (repouso) em
    cada ponta antes de virar, e sua morte é uma mineralização de 14 quadros
    em vez do encolhimento simples do slime."""

    # Hitbox um pouco menor que o quadro desenhado (72x61, ver game.py
    # _load_stag_sprites) — WIDTH/HEIGHT maiores que o quadro cru original
    # (40x34) porque o sprite é ampliado 1.8x ao carregar, pra não ficar
    # pequeno demais perto da Lia/slime.
    WIDTH = 52
    HEIGHT = 46
    # Levanta o desenho alguns pixels em relação ao alinhamento "encostado no
    # chão" ingênuo — o tileset novo tem uma leve borda de textura no topo do
    # tile de rocha que fazia os pés parecerem afundados na pedra.
    GROUND_LIFT = 5
    HEALTH = 3
    SPEED = 1.5
    PLATFORM_MARGIN = 6
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 22
    DEATH_FRAME_TIME = 5
    DEATH_FRAMES = 14
    IDLE_DURATION = 55

    IDLE = "idle"
    WALK = "walk"
    HURT = "hurt"
    DYING = "dying"
    DEAD = "dead"
    ACTIVE_STATES = (IDLE, WALK, HURT)

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

    def draw(self, surface, camera_x, camera_y, sprites):
        if self.state == self.DEAD:
            return
        key = "dead" if self.state == self.DYING else self.state
        frames = sprites[key]
        frame = self._animation_frame(frames)
        if self.direction < 0:
            frame = pygame.transform.flip(frame, True, False)
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
            frame = pygame.transform.flip(frame, True, False)
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
