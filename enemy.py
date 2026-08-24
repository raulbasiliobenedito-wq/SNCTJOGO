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


class PossessedStudent:
    """Estudante possuído da Fase 2: mesma patrulha com pausas do cervo de
    cristal (anda até a borda, para um instante, vira), parente visual da
    entidade sombria da Fase 3 (mesmo vocabulário de olhos que acendem antes
    do "ataque" — aqui só cosmético, o dano é por contato como os outros
    inimigos de chão)."""

    WIDTH = 26
    HEIGHT = 44
    GROUND_LIFT = 3
    HEALTH = 2
    SPEED = 1.3
    PLATFORM_MARGIN = 6
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 20
    DEATH_FRAME_TIME = 5
    DEATH_FRAMES = 12
    IDLE_DURATION = 50

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


class JanitorGuardian:
    """Zelador guardião: mini-chefe da Fase 2. Mesma patrulha com pausas do
    estudante, só que maior, mais resistente e mais lento — a leitura de
    "chefe" vem da escala e do peso, não de um ataque à distância novo (ver
    LEIA-ME_fase2.md, seção Notas de Design)."""

    WIDTH = 34
    HEIGHT = 54
    GROUND_LIFT = 4
    HEALTH = 4
    SPEED = 0.9
    PLATFORM_MARGIN = 6
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 22
    DEATH_FRAME_TIME = 5
    DEATH_FRAMES = 12
    IDLE_DURATION = 60

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


class Librarian:
    """Bibliotecário Silente: chefe da sala secundária da biblioteca. Mesma
    patrulha com pausas dos outros guardiões de sala (zona fixa via
    _StaticZone), com bem mais vida — é o "chefe" das duas salas novas.

    Os dois ataques telegrafados do LEIA-ME_biblioteca.md:
    - SILÊNCIO: longa antecipação (4 sinais em escada) e depois uma onda
      rasteira (13px de altura) que corre pro chão nos dois sentidos —
      resposta certa: pular.
    - ERRATA: 4 tomos brotam do chão, orbitam o chefe e mergulham em
      direções diferentes; ao contrário da onda, os tomos CONTINUAM se
      movendo depois da animação do chefe acabar — resposta certa: andar/
      reposicionar, não pular (no ar você não escolhe pra onde vai).
    - ESCUDO DE PÁGINA (novo, estilo Cuphead — pedido do Raul): ele levanta
      o livro-escudo e fica IMUNE a corpo a corpo (ver melee_vulnerable)
      enquanto solta um leque de lâminas de página — resposta certa: usar o
      ataque à distância, já que a espada não funciona nessa janela.
    O jogo alterna os três ataques num ritmo A→B→C→A→B→C, então o padrão
    fica legível depois de um combate."""

    WIDTH = 46
    HEIGHT = 58
    GROUND_LIFT = 4
    HEALTH = 12
    SPEED = 1.1
    PLATFORM_MARGIN = 6
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 20
    DEATH_FRAME_TIME = 6
    DEATH_FRAMES = 14
    IDLE_DURATION = 55

    # Acento coral do "olho" do chefe (LEIA-ME_biblioteca.md) — usado pra
    # pintar a onda do Silêncio e os tomos do Errata com a mesma cor da
    # ameaça, em vez de um hitbox invisível.
    HAZARD_COLOR = (200, 90, 80, 130)

    ATTACK_COOLDOWN_MIN = 150
    ATTACK_COOLDOWN_MAX = 220
    # "C" = Escudo de Página, novo (pedido do Raul: estilo Cuphead nos
    # chefes da Fase 2) — o Bibliotecário fica imune a corpo a corpo
    # enquanto o escudo está de pé, então só o ataque à distância machuca
    # nessa janela.
    ATTACK_PATTERN = ("A", "B", "C", "A", "B", "C")

    # attack_a.png (Silêncio, 9 quadros): Q1-4 antecipação[0..3] 8fps,
    # Q5 estouro[4] 24fps, Q6-8 onda corre[5..7] 14fps, Q9 recup[8] 10fps.
    SILENCE_TELEGRAPH_DURATION = 30
    SILENCE_BURST_DURATION = 3
    SILENCE_WAVE_DURATION = 13
    SILENCE_RECOVER_DURATION = 6
    SILENCE_RANGE = 260

    # attack_b.png (Errata, 10 quadros): Q1-3 brotam[0..2] 9fps,
    # Q4-6 órbita[3..5] 12fps, Q7-9 mergulho[6..8] 16fps, Q10 recup[9] 10fps.
    # Endurecido a pedido do Raul: mais tomos (4->6) girando bem mais rápido
    # (ver ERRATA_ORBIT_REVOLUTIONS) antes de mergulharem.
    ERRATA_RISE_DURATION = 21
    ERRATA_ORBIT_DURATION = 15
    ERRATA_DIVE_DURATION = 12
    ERRATA_RECOVER_DURATION = 6
    ERRATA_ORBIT_RADIUS = 42
    ERRATA_DIVE_SPEED = 3.4
    ERRATA_TOME_LIFETIME = 46  # continua se movendo depois da animação acabar
    ERRATA_TOME_SIZE = 20
    ERRATA_TOME_COUNT = 6
    # Voltas completas dadas durante a órbita inteira (ERRATA_ORBIT_DURATION
    # quadros) — era 0.9 (menos de uma volta); agora gira bem mais rápido.
    ERRATA_ORBIT_REVOLUTIONS = 2.4

    # attack_c (Escudo de Página, novo — sem spritesheet própria: o corpo
    # reaproveita a pose parada de "idle" enquanto livro_escudo.png é
    # desenhado por cima, mesmo espírito dos indicadores/meteoros estáticos
    # do Dragão em vez de uma animação nova quadro a quadro).
    # Endurecido a pedido do Raul: imunidade mais longa (ACTIVE_DURATION
    # maior) e as 5 lâminas agora saem uma de cada vez, todas retas na
    # direção que ele está olhando (> > > > >) em vez de um leque de uma
    # vez só — ver _update_escudo_active/_fire_blade.
    ESCUDO_TELEGRAPH_DURATION = 24
    ESCUDO_ACTIVE_DURATION = 76
    ESCUDO_RECOVER_DURATION = 14
    BLADE_SPEED = 4.2
    BLADE_LIFETIME = 70
    BLADE_COUNT = 5
    BLADE_FIRE_INTERVAL = 11  # quadros entre cada lâmina disparada
    BLADE_SIZE = 20

    IDLE = "idle"
    WALK = "walk"
    HURT = "hurt"
    DYING = "dying"
    DEAD = "dead"
    # Estilo Silksong: nasce parado até a Lia chegar perto (ver __init__/
    # wake_up/Game._maybe_wake_bosses) — mesmo padrão do SlimeKing.
    DORMANT = "dormant"
    SILENCE_TELEGRAPH = "silence_telegraph"
    SILENCE_BURST = "silence_burst"
    SILENCE_WAVE = "silence_wave"
    SILENCE_RECOVER = "silence_recover"
    ERRATA_RISE = "errata_rise"
    ERRATA_ORBIT = "errata_orbit"
    ERRATA_DIVE = "errata_dive"
    ERRATA_RECOVER = "errata_recover"
    ESCUDO_TELEGRAPH = "escudo_telegraph"
    ESCUDO_ACTIVE = "escudo_active"
    ESCUDO_RECOVER = "escudo_recover"
    ATTACK_STATES = (
        SILENCE_TELEGRAPH, SILENCE_BURST, SILENCE_WAVE, SILENCE_RECOVER,
        ERRATA_RISE, ERRATA_ORBIT, ERRATA_DIVE, ERRATA_RECOVER,
        ESCUDO_TELEGRAPH, ESCUDO_ACTIVE, ESCUDO_RECOVER,
    )
    ACTIVE_STATES = (IDLE, WALK, HURT, DORMANT) + ATTACK_STATES
    # Imune a corpo a corpo enquanto o escudo está de pé (ver docstring da
    # classe) — mesmo mecanismo do Dragão (Game.check_enemies confere isso
    # antes do dano de espada; o ataque à distância nunca olha pra isso).
    MELEE_IMMUNE_STATES = (ESCUDO_TELEGRAPH, ESCUDO_ACTIVE)
    # Ver SlimeKing.FACING_STATES — mesma regra: só vira pra Lia parado ou
    # ainda na antecipação, nunca no meio de WALK/ataque em execução.
    FACING_STATES = (IDLE, DORMANT, SILENCE_TELEGRAPH, ERRATA_RISE, ESCUDO_TELEGRAPH)

    def __init__(self, platform):
        self.platform = platform
        self.x = platform.rect.centerx - self.WIDTH // 2
        self.y = platform.rect.top - self.HEIGHT
        self.direction = 1
        self.speed = self.SPEED
        self.health = self.HEALTH
        self.state = self.DORMANT
        self.state_timer = 0
        self.death_frame = 0
        self.animation = 0
        self.attack_cooldown = self._next_attack_delay()
        self.attack_index = 0
        self.tomes = []
        self.blades = []
        self.blade_shots_fired = 0

    @staticmethod
    def _next_attack_delay():
        return random.randint(Librarian.ATTACK_COOLDOWN_MIN, Librarian.ATTACK_COOLDOWN_MAX)

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.WIDTH, self.HEIGHT)

    @property
    def alive(self):
        return self.state in self.ACTIVE_STATES

    @property
    def melee_vulnerable(self):
        return self.state not in self.MELEE_IMMUNE_STATES

    def face_player(self, player_x):
        if self.state not in self.FACING_STATES:
            return
        self.direction = 1 if player_x >= self.rect.centerx else -1

    def update(self):
        self.animation += 1
        self._update_tomes()
        self._update_blades()
        if self.state == self.DYING:
            self._update_death()
        elif self.state == self.DEAD:
            self._update_respawn()
        elif self.state == self.HURT:
            self._update_hurt()
        elif self.state == self.DORMANT:
            self._update_dormant()
        elif self.state == self.IDLE:
            self._update_idle()
        elif self.state == self.SILENCE_TELEGRAPH:
            self._update_phase(self.SILENCE_BURST, self.SILENCE_BURST_DURATION)
        elif self.state == self.SILENCE_BURST:
            self._update_phase(self.SILENCE_WAVE, self.SILENCE_WAVE_DURATION)
        elif self.state == self.SILENCE_WAVE:
            self._update_phase(self.SILENCE_RECOVER, self.SILENCE_RECOVER_DURATION)
        elif self.state == self.SILENCE_RECOVER:
            self._update_attack_recover()
        elif self.state == self.ERRATA_RISE:
            self._update_phase(self.ERRATA_ORBIT, self.ERRATA_ORBIT_DURATION)
        elif self.state == self.ERRATA_ORBIT:
            self._start_errata_dive()
        elif self.state == self.ERRATA_DIVE:
            self._update_phase(self.ERRATA_RECOVER, self.ERRATA_RECOVER_DURATION)
        elif self.state == self.ERRATA_RECOVER:
            self._update_attack_recover()
        elif self.state == self.ESCUDO_TELEGRAPH:
            self._update_escudo_telegraph()
        elif self.state == self.ESCUDO_ACTIVE:
            self._update_escudo_active()
        elif self.state == self.ESCUDO_RECOVER:
            self._update_attack_recover()
        else:
            self._patrol()

    def _update_phase(self, next_state, next_duration):
        """Só passa pro próximo trecho do ataque quando o timer zera —
        usado pelos estágios que não têm lógica própria além de esperar."""
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = next_state
            self.state_timer = next_duration

    def _update_idle(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK

    def _update_dormant(self):
        self.y = self.platform.rect.top - self.HEIGHT

    def wake_up(self):
        if self.state == self.DORMANT:
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
        self.attack_cooldown -= 1
        if self.attack_cooldown <= 0:
            self._start_attack()

    def _start_attack(self):
        kind = self.ATTACK_PATTERN[self.attack_index % len(self.ATTACK_PATTERN)]
        self.attack_index += 1
        if kind == "A":
            self.state = self.SILENCE_TELEGRAPH
            self.state_timer = self.SILENCE_TELEGRAPH_DURATION
        elif kind == "B":
            self.state = self.ERRATA_RISE
            self.state_timer = self.ERRATA_RISE_DURATION
        else:
            self.state = self.ESCUDO_TELEGRAPH
            self.state_timer = self.ESCUDO_TELEGRAPH_DURATION

    def _update_attack_recover(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK
            self.attack_cooldown = self._next_attack_delay()

    def _update_escudo_telegraph(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self._start_escudo_active()

    def _start_escudo_active(self):
        self.blade_shots_fired = 0
        self.state = self.ESCUDO_ACTIVE
        self.state_timer = self.ESCUDO_ACTIVE_DURATION

    def _update_escudo_active(self):
        """Uma lâmina de cada vez, sempre reta na direção que ele está
        olhando (> > > > >, pedido do Raul) — a direção fica travada desde
        o telegraph (ver FACING_STATES), então as 5 saem todas na mesma
        linha. O escudo continua de pé (imune) até o fim da janela, mesmo
        depois da última lâmina já ter partido."""
        self.y = self.platform.rect.top - self.HEIGHT
        elapsed = self.ESCUDO_ACTIVE_DURATION - self.state_timer
        if (
            self.blade_shots_fired < self.BLADE_COUNT
            and elapsed >= self.blade_shots_fired * self.BLADE_FIRE_INTERVAL
        ):
            self._fire_blade()
            self.blade_shots_fired += 1
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.ESCUDO_RECOVER
            self.state_timer = self.ESCUDO_RECOVER_DURATION

    def _fire_blade(self):
        self.blades.append({
            "x": self.rect.centerx, "y": self.rect.centery,
            "vx": self.BLADE_SPEED * self.direction, "vy": 0.0,
            "life": self.BLADE_LIFETIME,
        })

    def _update_blades(self):
        """Roda todo quadro, independente do estado do chefe — mesma lógica
        de _update_tomes: as lâminas continuam voando depois da animação."""
        remaining = []
        for blade in self.blades:
            blade["x"] += blade["vx"]
            blade["y"] += blade["vy"]
            blade["life"] -= 1
            if blade["life"] > 0:
                remaining.append(blade)
        self.blades = remaining

    def _silence_wave_rects(self):
        elapsed = self.SILENCE_WAVE_DURATION - self.state_timer
        progress = max(0.0, min(1.0, elapsed / self.SILENCE_WAVE_DURATION))
        width = max(1, round(self.SILENCE_RANGE * progress))
        height = 13
        y = self.platform.rect.top - height
        center = self.rect.centerx
        return [
            pygame.Rect(center - width, y, width, height),
            pygame.Rect(center, y, width, height),
        ]

    def _start_errata_dive(self):
        """A órbita acabou: cada tomo ganha velocidade na direção em que
        estava naquele instante (o espalhamento natural da órbita vira o
        "mergulho em direções diferentes" descrito no LEIA-ME)."""
        for tome in self.tomes:
            tome["diving"] = True
            tome["vx"] = math.cos(tome["angle"]) * self.ERRATA_DIVE_SPEED
            tome["vy"] = math.sin(tome["angle"]) * self.ERRATA_DIVE_SPEED
            tome["life"] = self.ERRATA_TOME_LIFETIME
        self.state = self.ERRATA_DIVE
        self.state_timer = self.ERRATA_DIVE_DURATION

    def _update_tomes(self):
        """Roda todo quadro, independente do estado do chefe — é assim que
        os tomos continuam voando depois dele já ter voltado a patrulhar."""
        if self.state == self.ERRATA_RISE:
            progress = max(0.0, min(1.0, 1 - self.state_timer / self.ERRATA_RISE_DURATION))
            if not self.tomes:
                base_angle = math.tau / 8
                count = self.ERRATA_TOME_COUNT
                self.tomes = [
                    {"angle": base_angle + i * (math.tau / count), "radius": 0.0,
                     "x": self.rect.centerx, "y": self.rect.centery,
                     "diving": False, "vx": 0.0, "vy": 0.0, "life": 0}
                    for i in range(count)
                ]
            for tome in self.tomes:
                tome["radius"] = self.ERRATA_ORBIT_RADIUS * progress
        elif self.state == self.ERRATA_ORBIT:
            for tome in self.tomes:
                tome["radius"] = self.ERRATA_ORBIT_RADIUS

        remaining = []
        for tome in self.tomes:
            if tome["diving"]:
                tome["x"] += tome["vx"]
                tome["y"] += tome["vy"]
                tome["life"] -= 1
                if tome["life"] > 0:
                    remaining.append(tome)
            else:
                if self.state == self.ERRATA_ORBIT:
                    tome["angle"] += math.tau * self.ERRATA_ORBIT_REVOLUTIONS / self.ERRATA_ORBIT_DURATION
                tome["x"] = self.rect.centerx + math.cos(tome["angle"]) * tome["radius"]
                tome["y"] = self.rect.centery + math.sin(tome["angle"]) * tome["radius"]
                remaining.append(tome)
        self.tomes = remaining

    def active_hazards(self):
        """Retângulos perigosos AGORA (fora da hitbox do próprio corpo,
        que já causa dano por contato normal): a onda do Silêncio enquanto
        corre, e os tomos do Errata a partir do momento em que mergulham."""
        hazards = []
        if self.state == self.SILENCE_WAVE:
            hazards.extend(self._silence_wave_rects())
        size = self.ERRATA_TOME_SIZE
        for tome in self.tomes:
            if tome["diving"]:
                hazards.append(pygame.Rect(round(tome["x"] - size / 2), round(tome["y"] - size / 2), size, size))
        blade_size = self.BLADE_SIZE
        for blade in self.blades:
            hazards.append(
                pygame.Rect(round(blade["x"] - blade_size / 2), round(blade["y"] - blade_size / 2), blade_size, blade_size)
            )
        return hazards

    def parryable_hazards(self):
        """Só o que voa de verdade — tomos já mergulhando e lâminas do
        Escudo — nunca a onda do Silêncio (ela corre pelo chão, não é algo
        pra "aparar" no ar; pedido do Raul). Cada item é (rect, cancel):
        Game._check_parries testa o attack_box da Lia contra esse rect e,
        se acertar, chama cancel() pra tirar só aquele hazard específico da
        lista — os outros continuam voando normalmente."""
        pairs = []
        size = self.ERRATA_TOME_SIZE
        for tome in self.tomes:
            if not tome["diving"]:
                continue
            rect = pygame.Rect(round(tome["x"] - size / 2), round(tome["y"] - size / 2), size, size)
            pairs.append((rect, lambda t=tome: self.tomes.remove(t) if t in self.tomes else None))
        blade_size = self.BLADE_SIZE
        for blade in self.blades:
            rect = pygame.Rect(round(blade["x"] - blade_size / 2), round(blade["y"] - blade_size / 2), blade_size, blade_size)
            pairs.append((rect, lambda b=blade: self.blades.remove(b) if b in self.blades else None))
        return pairs

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
            self.tomes = []
            self.blades = []

    def _sprite_key(self):
        if self.state == self.DYING:
            return "dead"
        if self.state in (self.SILENCE_TELEGRAPH, self.SILENCE_BURST, self.SILENCE_WAVE, self.SILENCE_RECOVER):
            return "attack_a"
        if self.state in (self.ERRATA_RISE, self.ERRATA_ORBIT, self.ERRATA_DIVE, self.ERRATA_RECOVER):
            return "attack_b"
        if self.state in (self.DORMANT, self.ESCUDO_TELEGRAPH, self.ESCUDO_ACTIVE, self.ESCUDO_RECOVER):
            return self.IDLE
        return self.state

    def _attack_frame_index(self):
        if self.state == self.SILENCE_TELEGRAPH:
            return self._phase_frame(0, 4, self.SILENCE_TELEGRAPH_DURATION)
        if self.state == self.SILENCE_BURST:
            return 4
        if self.state == self.SILENCE_WAVE:
            return self._phase_frame(5, 3, self.SILENCE_WAVE_DURATION)
        if self.state == self.SILENCE_RECOVER:
            return 8
        if self.state == self.ERRATA_RISE:
            return self._phase_frame(0, 3, self.ERRATA_RISE_DURATION)
        if self.state == self.ERRATA_ORBIT:
            return self._phase_frame(3, 3, self.ERRATA_ORBIT_DURATION)
        if self.state == self.ERRATA_DIVE:
            return self._phase_frame(6, 3, self.ERRATA_DIVE_DURATION)
        return 9

    def _phase_frame(self, start, count, duration):
        elapsed = duration - self.state_timer
        return start + max(0, min(count - 1, elapsed * count // duration))

    def draw(self, surface, camera_x, camera_y, sprites):
        if self.state != self.DEAD:
            key = self._sprite_key()
            frames = sprites[key]
            if key in ("attack_a", "attack_b"):
                frame = frames[min(self._attack_frame_index(), len(frames) - 1)]
            else:
                frame = self._animation_frame(frames)
            if self.direction < 0:
                frame = pygame.transform.flip(frame, True, False)
            frame_w, frame_h = frame.get_size()
            offset_x = (frame_w - self.WIDTH) // 2
            offset_y = frame_h - self.HEIGHT - self.GROUND_LIFT
            surface.blit(frame, (self.x - offset_x - camera_x, self.y - offset_y - camera_y))
        tome_image = sprites.get("tome")
        if tome_image:
            for tome in self.tomes:
                surface.blit(
                    tome_image,
                    (
                        tome["x"] - camera_x - tome_image.get_width() / 2,
                        tome["y"] - camera_y - tome_image.get_height() / 2,
                    ),
                )
        shield_image = sprites.get("shield")
        if shield_image and self.state in (self.ESCUDO_TELEGRAPH, self.ESCUDO_ACTIVE):
            offset = self.WIDTH / 2 + 6
            shield_x = self.rect.centerx + (offset if self.direction > 0 else -offset)
            surface.blit(
                shield_image,
                (
                    shield_x - camera_x - shield_image.get_width() / 2,
                    self.rect.centery - camera_y - shield_image.get_height() / 2,
                ),
            )
        blade_image = sprites.get("blade")
        if blade_image:
            for blade in self.blades:
                surface.blit(
                    blade_image,
                    (
                        blade["x"] - camera_x - blade_image.get_width() / 2,
                        blade["y"] - camera_y - blade_image.get_height() / 2,
                    ),
                )

    def _animation_frame(self, frames):
        if self.state == self.DYING:
            return frames[min(self.death_frame, len(frames) - 1)]
        if self.state in (self.IDLE, self.DORMANT):
            return frames[(self.animation // 10) % len(frames)]
        return frames[(self.animation // 6) % len(frames)]


class Specimen:
    """Guardião do laboratório velho: a coisa que estava no tanque de
    contenção. Mesma patrulha com pausas dos outros inimigos de chão (zona
    fixa via _StaticZone, já que o laboratório também tem um piso contínuo).

    Três ataques telegrafados (os dois primeiros do LEIA-ME_laboratorio.md,
    desenhados como opostos — mesmo espírito do bibliotecário; o terceiro é
    novo, estilo Cuphead):
    - JATO ÁCIDO: fica parado, encolhe e verticaliza (o *tell*), depois
      cospe um feixe reto na altura do núcleo — resposta certa: sair da
      linha de tiro (mudar de altura/posição, não corpo a corpo).
    - INVESTIDA: comprime e se lança na horizontal, cobrindo distância —
      resposta certa: pular por cima (recuar em linha reta não escapa).
    - CASULO ÁCIDO (novo, pedido do Raul): ele se enrola num casulo e fica
      IMUNE a corpo a corpo (ver melee_vulnerable) enquanto solta 3 esporos
      que caem e viram poça de ácido no chão — resposta certa: ataque à
      distância, já que a espada não funciona nessa janela."""

    WIDTH = 40
    HEIGHT = 34
    GROUND_LIFT = 3
    HEALTH = 12
    SPEED = 1.0
    PLATFORM_MARGIN = 6
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 18
    DEATH_FRAME_TIME = 6
    DEATH_FRAMES = 12
    IDLE_DURATION = 55

    # Verde-ácido (LEIA-ME_laboratorio.md, "o acento único saturado — ele só
    # aparece onde machuca") — pinta o feixe do jato com a mesma cor que já
    # identifica perigo químico no resto da sala.
    HAZARD_COLOR = (121, 181, 151, 140)

    ATTACK_COOLDOWN_MIN = 130
    ATTACK_COOLDOWN_MAX = 200

    # attack_jet (7 quadros): Q1-2 recolhe[0,1] 8fps, Q3-4 jato[2,3] 20fps,
    # Q5-7 retorno[4,5,6] 12fps.
    JET_TELEGRAPH_DURATION = 15
    JET_ACTIVE_DURATION = 6
    JET_RECOVER_DURATION = 15
    JET_BEAM_WIDTH = 170
    JET_BEAM_HEIGHT = 18

    # attack_lunge (8 quadros): Q1-2 comprime[0,1] 9fps, Q3 disparo[2] 24fps,
    # Q4-5 em voo[3,4] 18fps (disparo+voo = investida ativa), Q6 impacto[5]
    # 20fps, Q7-8 recompõe[6,7] 11fps (impacto+recompõe = recuperação).
    LUNGE_TELEGRAPH_DURATION = 14
    LUNGE_ACTIVE_DURATION = 9
    LUNGE_RECOVER_DURATION = 13
    LUNGE_DISTANCE = 120

    # attack_cocoon (novo — o corpo padrão SOME enquanto o casulo está de
    # pé, ver draw(); casulo_acido.png é a única coisa visível ali, mesmo
    # espírito do escudo do Bibliotecário e dos indicadores/meteoros
    # estáticos do Dragão). Os 3 esporos nascem de uma vez (centro + duas
    # laterais) e caem até o chão da plataforma, virando poça que fica
    # queimando por um tempo — mesma ideia de aviso→impacto→dano-persistente
    # das pedras do Dragão. O casulo quebra cedo se levar COCOON_BREAK_HITS
    # tiros à distância (só ranged alcança — melee_vulnerable é False aqui),
    # ou no fim natural de COCOON_ACTIVE_DURATION, o que vier primeiro.
    COCOON_TELEGRAPH_DURATION = 22
    COCOON_ACTIVE_DURATION = 46
    COCOON_RECOVER_DURATION = 16
    COCOON_BREAK_HITS = 3
    SPORE_OFFSETS = (-70, 0, 70)
    SPORE_FALL_SPEED = 2.6
    SPORE_IMPACT_DURATION = 5
    PUDDLE_LIFETIME = 90
    PUDDLE_WIDTH = 46
    PUDDLE_HEIGHT = 14

    IDLE = "idle"
    WALK = "walk"
    HURT = "hurt"
    DYING = "dying"
    DEAD = "dead"
    # Dormente até o player chegar perto (estilo Silksong, ver Game.
    # _maybe_wake_bosses) — mesmo padrão do SlimeKing/Librarian: fica parado
    # preso ao chão da plataforma até wake_up() ser chamado de fora.
    DORMANT = "dormant"
    JET_TELEGRAPH = "jet_telegraph"
    JET_ACTIVE = "jet_active"
    JET_RECOVER = "jet_recover"
    LUNGE_TELEGRAPH = "lunge_telegraph"
    LUNGE_ACTIVE = "lunge_active"
    LUNGE_RECOVER = "lunge_recover"
    COCOON_TELEGRAPH = "cocoon_telegraph"
    COCOON_ACTIVE = "cocoon_active"
    COCOON_RECOVER = "cocoon_recover"
    ATTACK_STATES = (
        JET_TELEGRAPH, JET_ACTIVE, JET_RECOVER,
        LUNGE_TELEGRAPH, LUNGE_ACTIVE, LUNGE_RECOVER,
        COCOON_TELEGRAPH, COCOON_ACTIVE, COCOON_RECOVER,
    )
    ACTIVE_STATES = (IDLE, WALK, HURT, DORMANT) + ATTACK_STATES
    # Imune a corpo a corpo dentro do casulo (ver docstring da classe) —
    # mesmo mecanismo do Dragão/Bibliotecário: Game.check_enemies confere
    # isso antes do dano de espada; o ataque à distância nunca olha pra isso.
    MELEE_IMMUNE_STATES = (COCOON_TELEGRAPH, COCOON_ACTIVE)
    # Ver SlimeKing.FACING_STATES — mesma regra: só vira pra Lia parado ou
    # ainda na antecipação, nunca no meio de WALK/ataque em execução (a
    # Investida em particular DEPENDE da direção ficar travada, senão o
    # bote mudaria de sentido no ar).
    FACING_STATES = (IDLE, DORMANT, JET_TELEGRAPH, LUNGE_TELEGRAPH, COCOON_TELEGRAPH)

    def __init__(self, platform):
        self.platform = platform
        self.x = platform.rect.centerx - self.WIDTH // 2
        self.y = platform.rect.top - self.HEIGHT
        self.direction = 1
        self.speed = self.SPEED
        self.health = self.HEALTH
        self.state = self.DORMANT
        self.state_timer = 0
        self.death_frame = 0
        self.animation = 0
        self.attack_cooldown = self._next_attack_delay()
        self.lunge_start_x = self.x
        self.spores = []
        self.cocoon_hits = 0

    @staticmethod
    def _next_attack_delay():
        return random.randint(Specimen.ATTACK_COOLDOWN_MIN, Specimen.ATTACK_COOLDOWN_MAX)

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.WIDTH, self.HEIGHT)

    @property
    def alive(self):
        return self.state in self.ACTIVE_STATES

    @property
    def melee_vulnerable(self):
        return self.state not in self.MELEE_IMMUNE_STATES

    def face_player(self, player_x):
        if self.state not in self.FACING_STATES:
            return
        self.direction = 1 if player_x >= self.rect.centerx else -1

    def update(self):
        self.animation += 1
        self._update_spores()
        if self.state == self.DYING:
            self._update_death()
        elif self.state == self.DEAD:
            self._update_respawn()
        elif self.state == self.HURT:
            self._update_hurt()
        elif self.state == self.DORMANT:
            self._update_dormant()
        elif self.state == self.IDLE:
            self._update_idle()
        elif self.state == self.JET_TELEGRAPH:
            self._update_wait(self.JET_ACTIVE, self.JET_ACTIVE_DURATION)
        elif self.state == self.JET_ACTIVE:
            self._update_wait(self.JET_RECOVER, self.JET_RECOVER_DURATION)
        elif self.state == self.JET_RECOVER:
            self._update_attack_recover()
        elif self.state == self.LUNGE_TELEGRAPH:
            self._start_lunge_active()
        elif self.state == self.LUNGE_ACTIVE:
            self._update_lunge_active()
        elif self.state == self.LUNGE_RECOVER:
            self._update_attack_recover()
        elif self.state == self.COCOON_TELEGRAPH:
            self._update_cocoon_telegraph()
        elif self.state == self.COCOON_ACTIVE:
            self._update_wait(self.COCOON_RECOVER, self.COCOON_RECOVER_DURATION)
        elif self.state == self.COCOON_RECOVER:
            self._update_attack_recover()
        else:
            self._patrol()

    def _update_wait(self, next_state, next_duration):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = next_state
            self.state_timer = next_duration

    def _update_idle(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK

    def _update_dormant(self):
        self.y = self.platform.rect.top - self.HEIGHT

    def wake_up(self):
        if self.state == self.DORMANT:
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
        self.attack_cooldown -= 1
        if self.attack_cooldown <= 0:
            self._start_attack()

    def _start_attack(self):
        # Casulo é mais raro que os outros dois (deixa o chefe imune por
        # uma janela inteira, então usar demais tornaria a luta arrastada).
        roll = random.random()
        if roll < 0.4:
            self.state = self.JET_TELEGRAPH
            self.state_timer = self.JET_TELEGRAPH_DURATION
        elif roll < 0.75:
            self.state = self.LUNGE_TELEGRAPH
            self.state_timer = self.LUNGE_TELEGRAPH_DURATION
        else:
            self.state = self.COCOON_TELEGRAPH
            self.state_timer = self.COCOON_TELEGRAPH_DURATION

    def _update_cocoon_telegraph(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self._start_cocoon_active()

    def _start_cocoon_active(self):
        """3 esporos nascem de uma vez (centro + duas laterais) e caem até o
        chão da plataforma, virando poça de ácido — mesma ideia de aviso→
        impacto→dano-persistente das pedras do Dragão, só que aqui é o
        próprio Espécime que dispara, não algo que cai do céu."""
        floor_y = self.platform.rect.top
        for offset in self.SPORE_OFFSETS:
            self.spores.append({
                "x": self.rect.centerx + offset,
                "y": self.rect.centery - self.HEIGHT / 2,
                "target_y": floor_y,
                "phase": "falling",
                "timer": 0,
            })
        self.cocoon_hits = 0
        self.state = self.COCOON_ACTIVE
        self.state_timer = self.COCOON_ACTIVE_DURATION

    def _update_spores(self):
        """Roda todo quadro, independente do estado do chefe — mesma lógica
        das pedras/meteoros do Dragão: a poça continua queimando no chão
        mesmo depois dele já ter voltado a patrulhar."""
        for spore in self.spores:
            if spore["phase"] == "falling":
                spore["y"] += self.SPORE_FALL_SPEED
                if spore["y"] >= spore["target_y"]:
                    spore["y"] = spore["target_y"]
                    spore["phase"] = "impact"
                    spore["timer"] = self.SPORE_IMPACT_DURATION
            elif spore["phase"] == "impact":
                spore["timer"] -= 1
                if spore["timer"] <= 0:
                    spore["phase"] = "puddle"
                    spore["timer"] = self.PUDDLE_LIFETIME
            elif spore["phase"] == "puddle":
                spore["timer"] -= 1
        self.spores = [s for s in self.spores if not (s["phase"] == "puddle" and s["timer"] <= 0)]

    def _start_lunge_active(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.LUNGE_ACTIVE
            self.state_timer = self.LUNGE_ACTIVE_DURATION
            self.lunge_start_x = self.x

    def _update_lunge_active(self):
        left = self.platform.rect.left + self.PLATFORM_MARGIN
        right = self.platform.rect.right - self.WIDTH - self.PLATFORM_MARGIN
        self.state_timer -= 1
        progress = 1 - self.state_timer / self.LUNGE_ACTIVE_DURATION
        target = self.lunge_start_x + self.direction * self.LUNGE_DISTANCE * progress
        self.x = max(left, min(target, right))
        self.y = self.platform.rect.top - self.HEIGHT
        if self.state_timer <= 0:
            self.state = self.LUNGE_RECOVER
            self.state_timer = self.LUNGE_RECOVER_DURATION

    def _update_attack_recover(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK
            self.attack_cooldown = self._next_attack_delay()

    def _jet_beam_rect(self):
        width, height = self.JET_BEAM_WIDTH, self.JET_BEAM_HEIGHT
        core_y = self.y + self.HEIGHT / 2 - height / 2
        x = self.x + self.WIDTH if self.direction > 0 else self.x - width
        return pygame.Rect(round(x), round(core_y), width, height)

    def active_hazards(self):
        """Retângulo perigoso além do corpo (a investida já causa dano por
        contato normal — só o jato precisa de um hitbox à parte, já que o
        feixe alcança bem além do corpo do espécime). As poças de ácido do
        Casulo também entram aqui, e continuam valendo mesmo fora do estado
        de ataque (fase "impact"/"puddle" independem do state atual)."""
        hazards = [self._jet_beam_rect()] if self.state == self.JET_ACTIVE else []
        width, height = self.PUDDLE_WIDTH, self.PUDDLE_HEIGHT
        for spore in self.spores:
            if spore["phase"] in ("impact", "puddle"):
                hazards.append(
                    pygame.Rect(round(spore["x"] - width / 2), round(spore["target_y"] - height), width, height)
                )
        return hazards

    def parryable_hazards(self):
        """Só o jato (JET_ACTIVE) — a investida é corpo a corpo (não dá pra
        aparar) e o casulo já tem sua própria regra de 3 acertos pra quebrar
        (ver take_hit); nenhum dos dois entra aqui. Janela real de parry é a
        de JET_ACTIVE inteira (JET_ACTIVE_DURATION, só 6 quadros) — de
        propósito o aparo mais apertado do jogo."""
        if self.state != self.JET_ACTIVE:
            return []

        def cancel():
            self.state = self.JET_RECOVER
            self.state_timer = self.JET_RECOVER_DURATION

        return [(self._jet_beam_rect(), cancel)]

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
            return True
        if self.state == self.COCOON_ACTIVE:
            # Dentro do casulo ele não vacila em HURT a cada tiro (senão a
            # pose do casulo "piscaria" toda hora) — em vez disso, cada
            # acerto conta pra quebrar o casulo antes da hora.
            self.cocoon_hits += 1
            if self.cocoon_hits >= self.COCOON_BREAK_HITS:
                self._break_cocoon()
            return True
        self.state = self.HURT
        self.state_timer = self.HURT_DURATION
        return True

    def _break_cocoon(self):
        """3 tiros à distância racham o casulo antes do tempo normal — dá
        ao jogador uma saída ativa em vez de só esperar o timer."""
        self.state = self.COCOON_RECOVER
        self.state_timer = self.COCOON_RECOVER_DURATION

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
            self.spores = []

    def _sprite_key(self):
        if self.state == self.DYING:
            return "dead"
        if self.state in (self.JET_TELEGRAPH, self.JET_ACTIVE, self.JET_RECOVER):
            return "jet"
        if self.state in (self.LUNGE_TELEGRAPH, self.LUNGE_ACTIVE, self.LUNGE_RECOVER):
            return "lunge"
        if self.state in (self.DORMANT, self.COCOON_TELEGRAPH, self.COCOON_ACTIVE, self.COCOON_RECOVER):
            return self.IDLE
        return self.state

    def _attack_frame_index(self):
        if self.state == self.JET_TELEGRAPH:
            return self._phase_frame(0, 2, self.JET_TELEGRAPH_DURATION)
        if self.state == self.JET_ACTIVE:
            return self._phase_frame(2, 2, self.JET_ACTIVE_DURATION)
        if self.state == self.JET_RECOVER:
            return self._phase_frame(4, 3, self.JET_RECOVER_DURATION)
        if self.state == self.LUNGE_TELEGRAPH:
            return self._phase_frame(0, 2, self.LUNGE_TELEGRAPH_DURATION)
        if self.state == self.LUNGE_ACTIVE:
            return self._phase_frame(2, 3, self.LUNGE_ACTIVE_DURATION)
        if self.state == self.LUNGE_RECOVER:
            return self._phase_frame(5, 3, self.LUNGE_RECOVER_DURATION)
        return 0

    def _phase_frame(self, start, count, duration):
        elapsed = duration - self.state_timer
        return start + max(0, min(count - 1, elapsed * count // duration))

    def draw(self, surface, camera_x, camera_y, sprites):
        # Corpo padrão (rosa) some enquanto o casulo está de pé (pedido do
        # Raul) — só casulo_acido.png fica visível nessa janela.
        if self.state != self.DEAD and self.state not in (self.COCOON_TELEGRAPH, self.COCOON_ACTIVE):
            key = self._sprite_key()
            frames = sprites[key]
            if key in ("jet", "lunge"):
                frame = frames[min(self._attack_frame_index(), len(frames) - 1)]
            else:
                frame = self._animation_frame(frames)
            if self.direction < 0:
                frame = pygame.transform.flip(frame, True, False)
            frame_w, frame_h = frame.get_size()
            offset_x = (frame_w - self.WIDTH) // 2
            offset_y = frame_h - self.HEIGHT - self.GROUND_LIFT
            surface.blit(frame, (self.x - offset_x - camera_x, self.y - offset_y - camera_y))
        cocoon_image = sprites.get("cocoon")
        if cocoon_image and self.state in (self.COCOON_TELEGRAPH, self.COCOON_ACTIVE):
            surface.blit(
                cocoon_image,
                (
                    self.rect.centerx - camera_x - cocoon_image.get_width() / 2,
                    self.rect.centery - camera_y - cocoon_image.get_height() / 2,
                ),
            )
        self._draw_spores(surface, camera_x, camera_y, sprites)

    def _draw_spores(self, surface, camera_x, camera_y, sprites):
        """Esporo (fase "falling", caindo) e poça (fases "impact"/"puddle",
        parada no chão) — sprites únicos e estáticos (ver
        game._load_specimen_sprites), sem animação própria."""
        spore_image = sprites.get("spore")
        puddle_image = sprites.get("puddle")
        for spore in self.spores:
            if spore["phase"] == "falling" and spore_image:
                surface.blit(
                    spore_image,
                    (
                        spore["x"] - camera_x - spore_image.get_width() / 2,
                        spore["y"] - camera_y - spore_image.get_height() / 2,
                    ),
                )
            elif spore["phase"] in ("impact", "puddle") and puddle_image:
                surface.blit(
                    puddle_image,
                    (
                        spore["x"] - camera_x - puddle_image.get_width() / 2,
                        spore["target_y"] - camera_y - puddle_image.get_height(),
                    ),
                )

    def _animation_frame(self, frames):
        if self.state == self.DYING:
            return frames[min(self.death_frame, len(frames) - 1)]
        if self.state in (self.IDLE, self.DORMANT):
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
            frame = pygame.transform.flip(frame, True, False)
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


class SlimeKing:
    """Rei Slime: chefe da Fase 1 (LEIA-ME_bosses_e_itens.md, §2). Mesma
    patrulha com pausas dos outros chefes de zona fixa, com uma arena
    própria montada em código no fim da Fase 1 (ver Level._make_boss_arena
    e Game._active_boss_arena — a câmera trava nela e Lia não sai enquanto
    ele estiver vivo).

    Dois ataques telegrafados, desenhados como opostos (a silhueta muda em
    eixos diferentes, igual ao par Silêncio/Errata do Bibliotecário):
    - ESMAGAR: achata e alarga, dispara uma onda rasteira pros DOIS lados —
      resposta certa: pular (andar não resolve, a onda cobre os dois
      sentidos).
    - CISÃO: estica e afina, "cospe" 4 slimes menores que se espalham pelo
      chão e CONTINUAM ali depois da animação acabar — resposta certa:
      andar/limpar (pular te derruba no meio deles)."""

    WIDTH = 54
    HEIGHT = 48
    GROUND_LIFT = 6
    HEALTH = 12
    SPEED = 0.85
    PLATFORM_MARGIN = 10
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 20
    DEATH_FRAME_TIME = 6
    DEATH_FRAMES = 12
    IDLE_DURATION = 60

    # O núcleo coral (a mesma cor do olho do Bibliotecário/Espécime/estudante
    # possuído) — a primeira aparição da anomalia no jogo, por isso pinta a
    # onda do Esmagar e os filhotes da Cisão com o mesmo acento.
    HAZARD_COLOR = (215, 100, 95, 130)

    ATTACK_COOLDOWN_MIN = 170
    ATTACK_COOLDOWN_MAX = 240
    ATTACK_PATTERN = ("A", "B", "A", "A", "B")

    # attack_a.png (Esmagar, 9 quadros): Q1-3 antecipação[0-2] 8fps,
    # Q4-5 subida[3,4] 14fps, Q6 ápice[5] 10fps, Q7 impacto[6] 20fps
    # (dispara a onda), Q8-9 assentamento[7,8] 12fps. A onda em si (como a
    # do Silêncio do Bibliotecário) tem sua própria janela de duração,
    # separada do quadro de impacto que a dispara.
    ESMAGAR_TELEGRAPH_DURATION = 24
    ESMAGAR_RISE_DURATION = 8
    ESMAGAR_APEX_DURATION = 6
    ESMAGAR_IMPACT_DURATION = 3
    ESMAGAR_WAVE_DURATION = 13
    ESMAGAR_SETTLE_DURATION = 10
    ESMAGAR_RANGE = 340
    ESMAGAR_WAVE_HEIGHT = 16

    # attack_b.png (Cisão, 10 quadros): Q1-2 antecipação[0,1] 8fps,
    # Q3-5 convulsão[2-4] 12fps, Q6-8 expulsão[5-7] 16fps (nasce os 4
    # filhotes), Q9-10 recomposição[8,9] 10fps.
    CISAO_TELEGRAPH_DURATION = 16
    CISAO_CONVULSION_DURATION = 15
    CISAO_EXPULSION_DURATION = 12
    CISAO_RECOVER_DURATION = 12
    CISAO_SPAWN_OFFSETS = (-100, -35, 35, 100)

    IDLE = "idle"
    WALK = "walk"
    HURT = "hurt"
    DYING = "dying"
    DEAD = "dead"
    # Estilo Silksong: nasce parado (ver __init__/wake_up) até a Lia chegar
    # perto o bastante (Game._maybe_wake_bosses) — dá tempo de ver o
    # tamanho do chefe antes da luta começar de verdade, em vez de já vir
    # patrulhando/atacando assim que a câmera trava na arena.
    DORMANT = "dormant"
    ESMAGAR_TELEGRAPH = "esmagar_telegraph"
    ESMAGAR_RISE = "esmagar_rise"
    ESMAGAR_APEX = "esmagar_apex"
    ESMAGAR_IMPACT = "esmagar_impact"
    ESMAGAR_WAVE = "esmagar_wave"
    ESMAGAR_SETTLE = "esmagar_settle"
    CISAO_TELEGRAPH = "cisao_telegraph"
    CISAO_CONVULSION = "cisao_convulsion"
    CISAO_EXPULSION = "cisao_expulsion"
    CISAO_RECOVER = "cisao_recover"
    ATTACK_STATES = (
        ESMAGAR_TELEGRAPH, ESMAGAR_RISE, ESMAGAR_APEX, ESMAGAR_IMPACT, ESMAGAR_WAVE, ESMAGAR_SETTLE,
        CISAO_TELEGRAPH, CISAO_CONVULSION, CISAO_EXPULSION, CISAO_RECOVER,
    )
    ACTIVE_STATES = (IDLE, WALK, HURT, DORMANT) + ATTACK_STATES
    # Estados em que face_player pode virar o chefe pra Lia (ver
    # Game._face_bosses_at_player) — parado (IDLE/DORMANT) ou ainda na
    # antecipação de um ataque (TELEGRAPH); durante WALK a direção já é
    # quem comanda o próprio andar do patrulhamento (mexer nela ali
    # bagunçaria a patrulha), e durante a execução/recuperação do ataque
    # a direção fica travada pra não "virar no meio do golpe".
    FACING_STATES = (IDLE, DORMANT, ESMAGAR_TELEGRAPH, CISAO_TELEGRAPH)

    def __init__(self, platform):
        self.platform = platform
        self.x = platform.rect.centerx - self.WIDTH // 2
        self.y = platform.rect.top - self.HEIGHT
        self.direction = 1
        self.speed = self.SPEED
        self.health = self.HEALTH
        self.state = self.DORMANT
        self.state_timer = 0
        self.death_frame = 0
        self.animation = 0
        self.attack_cooldown = self._next_attack_delay()
        self.attack_index = 0
        # Level.update() drena essa fila todo quadro e cria os SmallSlime de
        # verdade — o próprio inimigo não tem referência à Level pra se
        # auto-inserir na lista de inimigos.
        self.pending_spawns = []

    @staticmethod
    def _next_attack_delay():
        return random.randint(SlimeKing.ATTACK_COOLDOWN_MIN, SlimeKing.ATTACK_COOLDOWN_MAX)

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.WIDTH, self.HEIGHT)

    @property
    def alive(self):
        return self.state in self.ACTIVE_STATES

    def face_player(self, player_x):
        """Vira o chefe pra Lia (pedido do Raul: "sempre olhem pra ela" +
        ataques sempre saindo na direção certa) — só quando isso não
        atrapalha um movimento já em curso, ver FACING_STATES."""
        if self.state not in self.FACING_STATES:
            return
        self.direction = 1 if player_x >= self.rect.centerx else -1

    def update(self):
        self.animation += 1
        if self.state == self.DYING:
            self._update_death()
        elif self.state == self.DEAD:
            self._update_respawn()
        elif self.state == self.HURT:
            self._update_hurt()
        elif self.state == self.DORMANT:
            self._update_dormant()
        elif self.state == self.IDLE:
            self._update_idle()
        elif self.state == self.ESMAGAR_TELEGRAPH:
            self._update_phase(self.ESMAGAR_RISE, self.ESMAGAR_RISE_DURATION)
        elif self.state == self.ESMAGAR_RISE:
            self._update_phase(self.ESMAGAR_APEX, self.ESMAGAR_APEX_DURATION)
        elif self.state == self.ESMAGAR_APEX:
            self._update_phase(self.ESMAGAR_IMPACT, self.ESMAGAR_IMPACT_DURATION)
        elif self.state == self.ESMAGAR_IMPACT:
            self._update_phase(self.ESMAGAR_WAVE, self.ESMAGAR_WAVE_DURATION)
        elif self.state == self.ESMAGAR_WAVE:
            self._update_phase(self.ESMAGAR_SETTLE, self.ESMAGAR_SETTLE_DURATION)
        elif self.state == self.ESMAGAR_SETTLE:
            self._update_attack_recover()
        elif self.state == self.CISAO_TELEGRAPH:
            self._update_phase(self.CISAO_CONVULSION, self.CISAO_CONVULSION_DURATION)
        elif self.state == self.CISAO_CONVULSION:
            self._start_cisao_expulsion()
        elif self.state == self.CISAO_EXPULSION:
            self._update_phase(self.CISAO_RECOVER, self.CISAO_RECOVER_DURATION)
        elif self.state == self.CISAO_RECOVER:
            self._update_attack_recover()
        else:
            self._patrol()

    def _update_phase(self, next_state, next_duration):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = next_state
            self.state_timer = next_duration

    def _update_idle(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK

    def _update_dormant(self):
        """Só fica parado, sem timer — quem tira dele desse estado é
        wake_up(), chamado de fora (Game._maybe_wake_bosses) quando a Lia
        chega perto o bastante."""
        self.y = self.platform.rect.top - self.HEIGHT

    def wake_up(self):
        if self.state == self.DORMANT:
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
        self.attack_cooldown -= 1
        if self.attack_cooldown <= 0:
            self._start_attack()

    def _start_attack(self):
        kind = self.ATTACK_PATTERN[self.attack_index % len(self.ATTACK_PATTERN)]
        self.attack_index += 1
        if kind == "A":
            self.state = self.ESMAGAR_TELEGRAPH
            self.state_timer = self.ESMAGAR_TELEGRAPH_DURATION
        else:
            self.state = self.CISAO_TELEGRAPH
            self.state_timer = self.CISAO_TELEGRAPH_DURATION

    def _update_attack_recover(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK
            self.attack_cooldown = self._next_attack_delay()

    def _esmagar_wave_rects(self):
        elapsed = self.ESMAGAR_WAVE_DURATION - self.state_timer
        progress = max(0.0, min(1.0, elapsed / self.ESMAGAR_WAVE_DURATION))
        width = max(1, round(self.ESMAGAR_RANGE * progress))
        height = self.ESMAGAR_WAVE_HEIGHT
        y = self.platform.rect.top - height
        center = self.rect.centerx
        return [
            pygame.Rect(center - width, y, width, height),
            pygame.Rect(center, y, width, height),
        ]

    def _start_cisao_expulsion(self):
        """4 nascimentos registrados em fila (ver pending_spawns) — Level.
        update() os drena em SmallSlime de verdade, espalhados pelo chão da
        arena, no instante em que a "expulsão" (Q6-8) começa."""
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer > 0:
            return
        center = self.rect.centerx
        left = self.platform.rect.left + self.PLATFORM_MARGIN
        right = self.platform.rect.right - self.PLATFORM_MARGIN
        for offset in self.CISAO_SPAWN_OFFSETS:
            spawn_x = max(left, min(center + offset, right))
            self.pending_spawns.append((spawn_x, self.platform.rect.top))
        self.state = self.CISAO_EXPULSION
        self.state_timer = self.CISAO_EXPULSION_DURATION

    def active_hazards(self):
        """Rasteira do Esmagar enquanto corre — os filhotes da Cisão são
        inimigos de verdade (SmallSlime), não hazards; o dano deles já vem
        do teste de colisão corpo-a-corpo normal de check_enemies."""
        if self.state == self.ESMAGAR_WAVE:
            return self._esmagar_wave_rects()
        return []

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

    def _sprite_key(self):
        if self.state == self.DYING:
            return "dead"
        if self.state in (
            self.ESMAGAR_TELEGRAPH, self.ESMAGAR_RISE, self.ESMAGAR_APEX,
            self.ESMAGAR_IMPACT, self.ESMAGAR_WAVE, self.ESMAGAR_SETTLE,
        ):
            return "attack_a"
        if self.state in (
            self.CISAO_TELEGRAPH, self.CISAO_CONVULSION, self.CISAO_EXPULSION, self.CISAO_RECOVER,
        ):
            return "attack_b"
        if self.state == self.DORMANT:
            # Sem quadro próprio (nunca dorme "de verdade" na spritesheet) —
            # reaproveita a pose de repouso normal, mesma ideia do
            # DORMANT->IDLE cadence em _animation_frame logo abaixo.
            return self.IDLE
        return self.state

    def _attack_frame_index(self):
        if self.state == self.ESMAGAR_TELEGRAPH:
            return self._phase_frame(0, 3, self.ESMAGAR_TELEGRAPH_DURATION)
        if self.state == self.ESMAGAR_RISE:
            return self._phase_frame(3, 2, self.ESMAGAR_RISE_DURATION)
        if self.state == self.ESMAGAR_APEX:
            return 5
        if self.state in (self.ESMAGAR_IMPACT, self.ESMAGAR_WAVE):
            return 6
        if self.state == self.ESMAGAR_SETTLE:
            return self._phase_frame(7, 2, self.ESMAGAR_SETTLE_DURATION)
        if self.state == self.CISAO_TELEGRAPH:
            return self._phase_frame(0, 2, self.CISAO_TELEGRAPH_DURATION)
        if self.state == self.CISAO_CONVULSION:
            return self._phase_frame(2, 3, self.CISAO_CONVULSION_DURATION)
        if self.state == self.CISAO_EXPULSION:
            return self._phase_frame(5, 3, self.CISAO_EXPULSION_DURATION)
        if self.state == self.CISAO_RECOVER:
            return self._phase_frame(8, 2, self.CISAO_RECOVER_DURATION)
        return 0

    def _phase_frame(self, start, count, duration):
        elapsed = duration - self.state_timer
        return start + max(0, min(count - 1, elapsed * count // duration))

    def draw(self, surface, camera_x, camera_y, sprites):
        if self.state == self.DEAD:
            return
        key = self._sprite_key()
        frames = sprites[key]
        if key in ("attack_a", "attack_b"):
            frame = frames[min(self._attack_frame_index(), len(frames) - 1)]
        else:
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
        if self.state in (self.IDLE, self.DORMANT):
            return frames[(self.animation // 10) % len(frames)]
        if self.state == self.HURT:
            return frames[(self.animation // 4) % len(frames)]
        return frames[(self.animation // 5) % len(frames)]


class Dragon:
    """Dragão: chefe da Fase 3 (LEIA-ME_bosses_e_itens.md, §3), numa arena
    própria montada em código perto do fim da caverna (ver
    Level._make_boss_arena / Game._active_boss_arena).

    Redesenhado maior e mais duro (pedido do Raul: luta estilo Cuphead —
    chefe enorme, jogador atacando de longe). Três ataques telegrafados
    agora:
    - SOPRO: o peito acende em degraus, depois um jato rasteiro varre o
      chão à frente — resposta certa: pular por cima.
    - BRASAS: as asas abrem, ele voa e solta pedras incandescentes em x
      aleatório; elas CONTINUAM caindo depois dele pousar — resposta
      certa: andar/reposicionar (pular te deixa mais tempo embaixo delas).
    - VOO DA FÚRIA (novo): voo bem mais longo que o de Brasas — ele MARCA
      o chão (indicador_perigo.png) antes de cada meteoro (meteoro.png)
      cair exatamente ali, um de cada vez. Ver melee_vulnerable: durante
      os dois voos (Brasas e Voo da Fúria) ele fica fora de alcance de
      corpo a corpo de propósito — só o ataque à distância (Game.
      _update_projectiles, sem essa checagem) continua causando dano."""

    # Hitbox bem maior que antes (era 78x70) — o visual (ver DRAGON_SCALE
    # em game.py, 2.4) fica ainda maior que isso, mesmo padrão "sprite
    # maior que a hitbox" já usado nos outros inimigos.
    WIDTH = 150
    HEIGHT = 132
    GROUND_LIFT = 14
    HEALTH = 16
    SPEED = 0.8
    PLATFORM_MARGIN = 20
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 20
    DEATH_FRAME_TIME = 6
    DEATH_FRAMES = 14
    IDLE_DURATION = 60

    # Ventre em brasa (LEIA-ME: "a luz da fase 3 vem de baixo, o ventre é a
    # área clara") — pinta o jato e as pedras com o mesmo acento alaranjado.
    HAZARD_COLOR = (235, 140, 70, 140)

    ATTACK_COOLDOWN_MIN = 190
    ATTACK_COOLDOWN_MAX = 260
    ATTACK_PATTERN = ("A", "B", "C", "A", "B", "C")

    # attack_a.png (Sopro, 10 quadros): Q1-4 carrega[0-3] 9fps, Q5-8
    # sopro[4-7] 16fps (jato ativo), Q9-10 recupera[8,9] ~12fps.
    SOPRO_TELEGRAPH_DURATION = 28
    SOPRO_BREATH_DURATION = 16
    SOPRO_RECOVER_DURATION = 10
    SOPRO_RANGE = 300
    SOPRO_HEIGHT = 26

    # attack_b.png (Brasas, 10 quadros): Q1-3 antecipação[0-2] 9fps, Q4-7
    # voo[3-6] 10fps (solta pedras), Q8 pouso[7] 14fps, Q9-10 assenta[8,9]
    # 12fps.
    BRASAS_TELEGRAPH_DURATION = 21
    BRASAS_FLIGHT_DURATION = 24
    BRASAS_LANDING_DURATION = 4
    BRASAS_RECOVER_DURATION = 10
    BRASAS_ROCK_INTERVAL = 8
    BRASAS_ROCK_COUNT = 3

    ROCK_FALL_SPEED = 4.2
    ROCK_START_HEIGHT = 260
    ROCK_IMPACT_DURATION = 4
    ROCK_EXPLOSION_DURATION = 46
    ROCK_SIZE = 24

    # Voo da Fúria (ataque "C", novo): reaproveita o sprite/animação do
    # attack_b (voo) — só a arte do CHÃO é nova (marca + meteoro), não
    # precisa de quadros próprios do corpo do Dragão. Voo bem mais longo
    # que o de Brasas (150 vs 24 quadros) e meteoros um de cada vez, com
    # aviso — dá tempo de reagir, mas o voo prolongado é o que força o
    # jogador a ficar no ataque à distância por mais tempo seguido.
    VOO_FURIA_TELEGRAPH_DURATION = 26
    VOO_FURIA_FLIGHT_DURATION = 150
    VOO_FURIA_LANDING_DURATION = 4
    VOO_FURIA_RECOVER_DURATION = 12
    METEOR_MARK_INTERVAL = 45
    METEOR_MARK_COUNT = 4
    METEOR_TELEGRAPH_DURATION = 40
    METEOR_FALL_SPEED = 7.5
    METEOR_START_HEIGHT = 340
    METEOR_IMPACT_DURATION = 5
    METEOR_EXPLOSION_DURATION = 30
    METEOR_SIZE = 32

    IDLE = "idle"
    WALK = "walk"
    HURT = "hurt"
    DYING = "dying"
    DEAD = "dead"
    # Dormente até o player chegar perto (estilo Silksong, ver Game.
    # _maybe_wake_bosses) — mesmo padrão do SlimeKing/Librarian/Specimen.
    DORMANT = "dormant"
    SOPRO_TELEGRAPH = "sopro_telegraph"
    SOPRO_BREATH = "sopro_breath"
    SOPRO_RECOVER = "sopro_recover"
    BRASAS_TELEGRAPH = "brasas_telegraph"
    BRASAS_FLIGHT = "brasas_flight"
    BRASAS_LANDING = "brasas_landing"
    BRASAS_RECOVER = "brasas_recover"
    VOO_FURIA_TELEGRAPH = "voo_furia_telegraph"
    VOO_FURIA = "voo_furia"
    VOO_FURIA_LANDING = "voo_furia_landing"
    VOO_FURIA_RECOVER = "voo_furia_recover"
    ATTACK_STATES = (
        SOPRO_TELEGRAPH, SOPRO_BREATH, SOPRO_RECOVER,
        BRASAS_TELEGRAPH, BRASAS_FLIGHT, BRASAS_LANDING, BRASAS_RECOVER,
        VOO_FURIA_TELEGRAPH, VOO_FURIA, VOO_FURIA_LANDING, VOO_FURIA_RECOVER,
    )
    ACTIVE_STATES = (IDLE, WALK, HURT, DORMANT) + ATTACK_STATES
    # Fora de alcance de corpo a corpo durante os voos (ver docstring da
    # classe) — Game.check_enemies confere isso antes de aplicar dano de
    # espada; o ataque à distância (Game._update_projectiles) nunca olha
    # pra essa propriedade, então continua funcionando sempre.
    MELEE_IMMUNE_STATES = (
        BRASAS_FLIGHT, BRASAS_LANDING,
        VOO_FURIA_TELEGRAPH, VOO_FURIA, VOO_FURIA_LANDING,
    )
    # Ver SlimeKing.FACING_STATES — mesma regra: só vira pra Lia parado ou
    # ainda na antecipação, nunca no meio de WALK/ataque em execução.
    FACING_STATES = (IDLE, DORMANT, SOPRO_TELEGRAPH, BRASAS_TELEGRAPH, VOO_FURIA_TELEGRAPH)

    def __init__(self, platform):
        self.platform = platform
        self.x = platform.rect.centerx - self.WIDTH // 2
        self.y = platform.rect.top - self.HEIGHT
        self.direction = 1
        self.speed = self.SPEED
        self.health = self.HEALTH
        self.state = self.DORMANT
        self.state_timer = 0
        self.death_frame = 0
        self.animation = 0
        self.attack_cooldown = self._next_attack_delay()
        self.attack_index = 0
        self.rocks_spawned = 0
        self.meteors_marked = 0
        # Pedras/meteoros já soltos: atualizados todo quadro independente
        # do estado (ver _update_rocks/_update_meteors), pra continuarem
        # caindo/queimando depois dele já ter pousado e voltado a patrulhar.
        self.rocks = []
        self.meteors = []

    @property
    def melee_vulnerable(self):
        return self.state not in self.MELEE_IMMUNE_STATES

    def face_player(self, player_x):
        if self.state not in self.FACING_STATES:
            return
        self.direction = 1 if player_x >= self.rect.centerx else -1

    @staticmethod
    def _next_attack_delay():
        return random.randint(Dragon.ATTACK_COOLDOWN_MIN, Dragon.ATTACK_COOLDOWN_MAX)

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.WIDTH, self.HEIGHT)

    @property
    def alive(self):
        return self.state in self.ACTIVE_STATES

    def update(self):
        self.animation += 1
        self._update_rocks()
        self._update_meteors()
        if self.state == self.DYING:
            self._update_death()
        elif self.state == self.DEAD:
            self._update_respawn()
        elif self.state == self.HURT:
            self._update_hurt()
        elif self.state == self.DORMANT:
            self._update_dormant()
        elif self.state == self.IDLE:
            self._update_idle()
        elif self.state == self.SOPRO_TELEGRAPH:
            self._update_phase(self.SOPRO_BREATH, self.SOPRO_BREATH_DURATION)
        elif self.state == self.SOPRO_BREATH:
            self._update_phase(self.SOPRO_RECOVER, self.SOPRO_RECOVER_DURATION)
        elif self.state == self.SOPRO_RECOVER:
            self._update_attack_recover()
        elif self.state == self.BRASAS_TELEGRAPH:
            self._start_brasas_flight()
        elif self.state == self.BRASAS_FLIGHT:
            self._update_brasas_flight()
        elif self.state == self.BRASAS_LANDING:
            self._update_phase(self.BRASAS_RECOVER, self.BRASAS_RECOVER_DURATION)
        elif self.state == self.BRASAS_RECOVER:
            self._update_attack_recover()
        elif self.state == self.VOO_FURIA_TELEGRAPH:
            self._start_voo_furia()
        elif self.state == self.VOO_FURIA:
            self._update_voo_furia()
        elif self.state == self.VOO_FURIA_LANDING:
            self._update_phase(self.VOO_FURIA_RECOVER, self.VOO_FURIA_RECOVER_DURATION)
        elif self.state == self.VOO_FURIA_RECOVER:
            self._update_attack_recover()
        else:
            self._patrol()

    def _update_phase(self, next_state, next_duration):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = next_state
            self.state_timer = next_duration

    def _update_idle(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK

    def _update_dormant(self):
        self.y = self.platform.rect.top - self.HEIGHT

    def wake_up(self):
        if self.state == self.DORMANT:
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
        self.attack_cooldown -= 1
        if self.attack_cooldown <= 0:
            self._start_attack()

    def _start_attack(self):
        kind = self.ATTACK_PATTERN[self.attack_index % len(self.ATTACK_PATTERN)]
        self.attack_index += 1
        if kind == "A":
            self.state = self.SOPRO_TELEGRAPH
            self.state_timer = self.SOPRO_TELEGRAPH_DURATION
        elif kind == "B":
            self.state = self.BRASAS_TELEGRAPH
            self.state_timer = self.BRASAS_TELEGRAPH_DURATION
        else:
            self.state = self.VOO_FURIA_TELEGRAPH
            self.state_timer = self.VOO_FURIA_TELEGRAPH_DURATION

    def _update_attack_recover(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.WALK
            self.attack_cooldown = self._next_attack_delay()

    def _start_brasas_flight(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.BRASAS_FLIGHT
            self.state_timer = self.BRASAS_FLIGHT_DURATION
            self.rocks_spawned = 0

    def _update_brasas_flight(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        elapsed = self.BRASAS_FLIGHT_DURATION - self.state_timer
        expected = min(self.BRASAS_ROCK_COUNT, 1 + elapsed // self.BRASAS_ROCK_INTERVAL)
        while self.rocks_spawned < expected:
            self._spawn_rock()
            self.rocks_spawned += 1
        if self.state_timer <= 0:
            self.state = self.BRASAS_LANDING
            self.state_timer = self.BRASAS_LANDING_DURATION

    def _spawn_rock(self):
        left = self.platform.rect.left + self.PLATFORM_MARGIN
        right = self.platform.rect.right - self.PLATFORM_MARGIN
        x = random.uniform(left, right) if right > left else self.rect.centerx
        self.rocks.append({
            "x": x,
            "y": self.platform.rect.top - self.ROCK_START_HEIGHT,
            "phase": "falling",
            "timer": 0,
        })

    def _update_rocks(self):
        floor_y = self.platform.rect.top
        remaining = []
        for rock in self.rocks:
            if rock["phase"] == "falling":
                rock["y"] += self.ROCK_FALL_SPEED
                if rock["y"] >= floor_y:
                    rock["y"] = floor_y
                    rock["phase"] = "impact"
                    rock["timer"] = self.ROCK_IMPACT_DURATION
            elif rock["phase"] == "impact":
                rock["timer"] -= 1
                if rock["timer"] <= 0:
                    rock["phase"] = "explosion"
                    rock["timer"] = self.ROCK_EXPLOSION_DURATION
            elif rock["phase"] == "explosion":
                rock["timer"] -= 1
                if rock["timer"] <= 0:
                    continue
            remaining.append(rock)
        self.rocks = remaining

    def _start_voo_furia(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.VOO_FURIA
            self.state_timer = self.VOO_FURIA_FLIGHT_DURATION
            self.meteors_marked = 0

    def _update_voo_furia(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        elapsed = self.VOO_FURIA_FLIGHT_DURATION - self.state_timer
        expected = min(self.METEOR_MARK_COUNT, 1 + elapsed // self.METEOR_MARK_INTERVAL)
        while self.meteors_marked < expected:
            self._mark_meteor()
            self.meteors_marked += 1
        if self.state_timer <= 0:
            self.state = self.VOO_FURIA_LANDING
            self.state_timer = self.VOO_FURIA_LANDING_DURATION

    def _mark_meteor(self):
        """Marca um ponto no chão (indicador_perigo.png) — só depois de
        METEOR_TELEGRAPH_DURATION quadros o meteoro de verdade nasce lá e
        começa a cair (ver _update_meteors). Um de cada vez, ao contrário
        das pedras de Brasas (que caem direto): aqui o aviso É o desafio,
        não a queda em si."""
        left = self.platform.rect.left + self.PLATFORM_MARGIN
        right = self.platform.rect.right - self.PLATFORM_MARGIN
        x = random.uniform(left, right) if right > left else self.rect.centerx
        self.meteors.append({
            "x": x,
            "y": self.platform.rect.top - self.METEOR_START_HEIGHT,
            "phase": "telegraph",
            "timer": self.METEOR_TELEGRAPH_DURATION,
        })

    def _update_meteors(self):
        """Roda todo quadro (igual _update_rocks), independente do estado
        — um meteoro marcado antes do Dragão pousar precisa continuar a
        contagem/queda mesmo se ele já estiver recuperando."""
        floor_y = self.platform.rect.top
        remaining = []
        for meteor in self.meteors:
            if meteor["phase"] == "telegraph":
                meteor["timer"] -= 1
                if meteor["timer"] <= 0:
                    meteor["phase"] = "falling"
            elif meteor["phase"] == "falling":
                meteor["y"] += self.METEOR_FALL_SPEED
                if meteor["y"] >= floor_y:
                    meteor["y"] = floor_y
                    meteor["phase"] = "impact"
                    meteor["timer"] = self.METEOR_IMPACT_DURATION
            elif meteor["phase"] == "impact":
                meteor["timer"] -= 1
                if meteor["timer"] <= 0:
                    meteor["phase"] = "explosion"
                    meteor["timer"] = self.METEOR_EXPLOSION_DURATION
            elif meteor["phase"] == "explosion":
                meteor["timer"] -= 1
                if meteor["timer"] <= 0:
                    continue
            remaining.append(meteor)
        self.meteors = remaining

    def _sopro_breath_rect(self):
        width, height = self.SOPRO_RANGE, self.SOPRO_HEIGHT
        y = self.platform.rect.top - height
        x = self.rect.right if self.direction > 0 else self.rect.left - width
        return pygame.Rect(round(x), round(y), width, height)

    def active_hazards(self):
        """Jato do Sopro enquanto varre o chão, pedras das Brasas e
        meteoros do Voo da Fúria (caindo/no impacto) — todos continuam
        valendo mesmo fora dos estados de ataque que os originaram, ver
        _update_rocks/_update_meteors (rodam todo quadro, incondicional).
        A MARCA no chão (fase "telegraph") não é um perigo em si — é só o
        aviso — por isso não entra aqui, só a partir de "falling"."""
        hazards = []
        if self.state == self.SOPRO_BREATH:
            hazards.append(self._sopro_breath_rect())
        size = self.ROCK_SIZE
        for rock in self.rocks:
            hazards.append(pygame.Rect(round(rock["x"] - size / 2), round(rock["y"] - size / 2), size, size))
        meteor_size = self.METEOR_SIZE
        for meteor in self.meteors:
            if meteor["phase"] in ("falling", "impact"):
                hazards.append(pygame.Rect(
                    round(meteor["x"] - meteor_size / 2), round(meteor["y"] - meteor_size / 2),
                    meteor_size, meteor_size,
                ))
        return hazards

    def parryable_hazards(self):
        """Sopro enquanto varre, pedras das Brasas e meteoros do Voo da
        Fúria — só enquanto ainda estão "voando" (fase "falling"); depois de
        "impact"/"explosion" já pousaram, não tem mais o que aparar (pedido
        do Raul: só projéteis/objetos que voam, nunca coisa que já caiu)."""
        pairs = []
        if self.state == self.SOPRO_BREATH:
            def cancel_breath():
                self.state = self.SOPRO_RECOVER
                self.state_timer = self.SOPRO_RECOVER_DURATION
            pairs.append((self._sopro_breath_rect(), cancel_breath))
        size = self.ROCK_SIZE
        for rock in self.rocks:
            if rock["phase"] == "falling":
                rect = pygame.Rect(round(rock["x"] - size / 2), round(rock["y"] - size / 2), size, size)
                pairs.append((rect, lambda r=rock: self.rocks.remove(r) if r in self.rocks else None))
        meteor_size = self.METEOR_SIZE
        for meteor in self.meteors:
            if meteor["phase"] == "falling":
                rect = pygame.Rect(
                    round(meteor["x"] - meteor_size / 2), round(meteor["y"] - meteor_size / 2),
                    meteor_size, meteor_size,
                )
                pairs.append((rect, lambda m=meteor: self.meteors.remove(m) if m in self.meteors else None))
        return pairs

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
            self.rocks = []
            self.meteors = []

    def _sprite_key(self):
        if self.state == self.DYING:
            return "dead"
        if self.state in (self.SOPRO_TELEGRAPH, self.SOPRO_BREATH, self.SOPRO_RECOVER):
            return "attack_a"
        if self.state in (
            self.BRASAS_TELEGRAPH, self.BRASAS_FLIGHT, self.BRASAS_LANDING, self.BRASAS_RECOVER,
            # Voo da Fúria reaproveita a animação de voo do attack_b — só o
            # que cai do céu é diferente (meteoro em vez de brasa), não o
            # corpo do Dragão, então não precisa de quadros próprios.
            self.VOO_FURIA_TELEGRAPH, self.VOO_FURIA, self.VOO_FURIA_LANDING, self.VOO_FURIA_RECOVER,
        ):
            return "attack_b"
        if self.state == self.DORMANT:
            return self.IDLE
        return self.state

    def _attack_frame_index(self):
        if self.state == self.SOPRO_TELEGRAPH:
            return self._phase_frame(0, 4, self.SOPRO_TELEGRAPH_DURATION)
        if self.state == self.SOPRO_BREATH:
            return self._phase_frame(4, 4, self.SOPRO_BREATH_DURATION)
        if self.state == self.SOPRO_RECOVER:
            return self._phase_frame(8, 2, self.SOPRO_RECOVER_DURATION)
        if self.state in (self.BRASAS_TELEGRAPH, self.VOO_FURIA_TELEGRAPH):
            duration = self.BRASAS_TELEGRAPH_DURATION if self.state == self.BRASAS_TELEGRAPH else self.VOO_FURIA_TELEGRAPH_DURATION
            return self._phase_frame(0, 3, duration)
        if self.state in (self.BRASAS_FLIGHT, self.VOO_FURIA):
            # Voo prolongado do Voo da Fúria: em vez de mapear a duração
            # inteira (150 quadros) num loop de 4 quadros só uma vez — o que
            # ia ficar devagar demais — repete o ciclo de bater asas a cada
            # BRASAS_FLIGHT_DURATION quadros, pra continuar com a mesma
            # cadência visual do voo curto de Brasas.
            elapsed = self.animation % self.BRASAS_FLIGHT_DURATION
            return 3 + max(0, min(3, elapsed * 4 // self.BRASAS_FLIGHT_DURATION))
        if self.state in (self.BRASAS_LANDING, self.VOO_FURIA_LANDING):
            return 7
        if self.state in (self.BRASAS_RECOVER, self.VOO_FURIA_RECOVER):
            duration = self.BRASAS_RECOVER_DURATION if self.state == self.BRASAS_RECOVER else self.VOO_FURIA_RECOVER_DURATION
            return self._phase_frame(8, 2, duration)
        return 0

    def _phase_frame(self, start, count, duration):
        elapsed = duration - self.state_timer
        return start + max(0, min(count - 1, elapsed * count // duration))

    def _rock_frame_index(self, rock):
        if rock["phase"] == "falling":
            return (self.animation // 5) % 4
        if rock["phase"] == "impact":
            return 4
        elapsed = self.ROCK_EXPLOSION_DURATION - rock["timer"]
        return 5 + min(2, elapsed // 4)

    def draw(self, surface, camera_x, camera_y, sprites):
        if self.state != self.DEAD:
            key = self._sprite_key()
            frames = sprites[key]
            if key in ("attack_a", "attack_b"):
                frame = frames[min(self._attack_frame_index(), len(frames) - 1)]
            else:
                frame = self._animation_frame(frames)
            if self.direction < 0:
                frame = pygame.transform.flip(frame, True, False)
            frame_w, frame_h = frame.get_size()
            offset_x = (frame_w - self.WIDTH) // 2
            offset_y = frame_h - self.HEIGHT - self.GROUND_LIFT
            surface.blit(frame, (self.x - offset_x - camera_x, self.y - offset_y - camera_y))
        rock_frames = sprites.get("rock")
        if rock_frames:
            for rock in self.rocks:
                frame = rock_frames[min(self._rock_frame_index(rock), len(rock_frames) - 1)]
                surface.blit(
                    frame,
                    (rock["x"] - camera_x - frame.get_width() / 2, rock["y"] - camera_y - frame.get_height() / 2),
                )
        self._draw_meteors(surface, camera_x, camera_y, sprites)

    def _draw_meteors(self, surface, camera_x, camera_y, sprites):
        """Marca (fase "telegraph", parada no chão) e meteoro (demais fases,
        caindo/no impacto/queimando) — sprites únicos e estáticos (ver
        game._load_dragon_sprites), sem animação própria."""
        marker_sprite = sprites.get("danger_marker")
        meteor_sprite = sprites.get("meteor")
        floor_y = self.platform.rect.top
        for meteor in self.meteors:
            if meteor["phase"] == "telegraph" and marker_sprite:
                surface.blit(
                    marker_sprite,
                    (
                        meteor["x"] - camera_x - marker_sprite.get_width() / 2,
                        floor_y - camera_y - marker_sprite.get_height() / 2,
                    ),
                )
            elif meteor["phase"] in ("falling", "impact") and meteor_sprite:
                surface.blit(
                    meteor_sprite,
                    (
                        meteor["x"] - camera_x - meteor_sprite.get_width() / 2,
                        meteor["y"] - camera_y - meteor_sprite.get_height() / 2,
                    ),
                )

    def _animation_frame(self, frames):
        if self.state == self.DYING:
            return frames[min(self.death_frame, len(frames) - 1)]
        if self.state in (self.IDLE, self.DORMANT):
            return frames[(self.animation // 10) % len(frames)]
        if self.state == self.HURT:
            return frames[(self.animation // 4) % len(frames)]
        return frames[(self.animation // 6) % len(frames)]
