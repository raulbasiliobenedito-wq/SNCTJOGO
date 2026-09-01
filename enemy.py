import math
import random

import pygame


class Slime:
    """Inimigo que patrulha somente a plataforma onde nasceu."""

    WIDTH = 40
    HEIGHT = 22
    # Pedido do Raul (Fase 1: slime afundando no chão da escola): o quadro
    # desenhado (_load_enemy_sheet recorta e AMPLIA cada frame pra 64x32,
    # sempre preenchendo a altura toda, mesmo já cortando a moldura
    # transparente via get_bounding_rect) é bem mais alto que a hitbox
    # (32px vs HEIGHT=22px) — draw() ancora o desenho em
    # "self.y + 2 - GROUND_LIFT", então com GROUND_LIFT=3 a base do
    # desenho ficava 9px ABAIXO da base de verdade da hitbox (34-3=31 de
    # desenho contra 22 da hitbox). No tileset antigo (rocha) isso não
    # aparecia porque a própria borda/textura do topo do tile escondia a
    # sobra; no chão liso da escola nova ficou visível. GROUND_LIFT=9
    # deixa só ~3px de sobreposição (efeito "pé apoiado", igual à
    # calibragem original), em vez de 9.
    GROUND_LIFT = 9
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
            # Pedido do Raul: chefe morto fica morto pra sempre, sem
            # respawn (ver docstring de _update_death) — nenhuma ação aqui.
            pass
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
        """Pedido do Raul: chefe derrotado fica morto pra sempre — sem
        RESPAWN_TIME/_update_respawn (removidos), DEAD é estado terminal,
        ver update() acima."""
        self.state_timer -= 1
        self.death_frame = min(
            self.DEATH_FRAMES - 1,
            self.death_frame + int(self.state_timer % self.DEATH_FRAME_TIME == 0),
        )
        if self.state_timer <= 0:
            self.state = self.DEAD

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
            # Pedido do Raul: chefe morto fica morto pra sempre, sem
            # respawn (ver docstring de _update_death) — nenhuma ação aqui.
            pass
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
        """Pedido do Raul: chefe derrotado fica morto pra sempre — sem
        RESPAWN_TIME/_update_respawn (removidos), DEAD é estado terminal,
        ver update() acima."""
        self.state_timer -= 1
        self.death_frame = min(
            self.DEATH_FRAMES - 1,
            self.death_frame + int(self.state_timer % self.DEATH_FRAME_TIME == 0),
        )
        if self.state_timer <= 0:
            self.state = self.DEAD

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
            # Pedido do Raul: chefe morto fica morto pra sempre, sem
            # respawn (ver docstring de _update_death) — nenhuma ação aqui.
            pass
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
        """Pedido do Raul: chefe derrotado fica morto pra sempre — sem
        RESPAWN_TIME/_update_respawn (removidos), DEAD é estado terminal,
        ver update() acima."""
        self.state_timer -= 1
        self.death_frame = min(
            self.DEATH_FRAMES - 1,
            self.death_frame + int(self.state_timer % self.DEATH_FRAME_TIME == 0),
        )
        if self.state_timer <= 0:
            self.state = self.DEAD

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

    Refeito do zero (pedido do Raul, com a folha de sprite nova dele,
    9 quadros de 324x265 desenhados à mão — ver game._load_dragon_sprites):
    luta estilo Cuphead de verdade agora. Ele fica PARADO no mesmo lugar o
    tempo todo (nunca mais anda — sem WALK/_patrol) e é PERMANENTEMENTE
    imune a corpo a corpo (ver melee_vulnerable: sempre False, não muda
    mais por estado) — só o ataque à distância da Lia (Game.
    _update_projectiles, que nunca olha essa propriedade) causa dano nele;
    tocar nele continua doendo na Lia normalmente (Game.check_enemies,
    ramo de contato). Também ficou BEM maior (ver DRAGON_SCALE em
    game.py) pra "ler" como o chefe final do jogo.

    Dois ataques telegrafados, direto da folha nova:
    - SOPRO (quadros 2-3 da folha, "já desenhei" — jato de fogo na Lia):
      mesma mecânica de sempre, jato rasteiro à frente — resposta certa:
      pular por cima ou manter distância.
    - TERREMOTO (quadros 4-6 voando + 7-9 batendo no chão): ele voa (fica
      no ar, parado no eixo X mesmo assim) e desce batendo — o impacto
      sacode a câmera por uns 5 segundos (ver Game._check_boss_shake_
      events/consume_shake_event) enquanto MUITOS pedaços da caverna vão
      caindo aos poucos ao longo desse tremor todo (reaproveita o sistema
      de pedras da antiga Brasas — ver _update_rocks, roda todo quadro,
      independente do estado; pedido do Raul: "o ataque brasas com
      pedras fará parte do terremoto também"). O antigo Voo da Fúria
      (meteoros mirados no chão) saiu de cena — virou este ataque único
      aqui.

    Sem quadros próprios de dano/morte na folha nova (só idle, sopro e
    voo/terremoto) — HURT reaproveita o quadro parado (o hit já é sentido
    pela barra de vida + boss_hit_sound) e DYING esmaece esse mesmo quadro
    até sumir (ver draw/_current_frame)."""

    # Hitbox BEM maior que antes (era 150x132) — pedido explícito do Raul:
    # "ele será BEM maior do que o atual já é... enorme". O visual (ver
    # DRAGON_SCALE em game.py) fica ainda maior que isso, mesmo padrão
    # "sprite maior que a hitbox" já usado no resto do jogo.
    WIDTH = 360
    HEIGHT = 300
    # Pedido do Raul (2026-08-27): "um pouco afundado no chão" com 32 —
    # reduzido bastante (positivo = sprite desce, negativo = sprite sobe;
    # ver Slime.GROUND_LIFT acima pra mesma conta). Ainda é chute (não dá
    # pra calibrar o pixel exato sem rodar o jogo) — se continuar afundado
    # ou passar a flutuar, é só me avisar que ajusto de novo.
    GROUND_LIFT = -8
    HEALTH = 16
    HURT_DURATION = 20
    DEATH_FRAME_TIME = 6
    DEATH_FRAMES = 14

    # Ventre em brasa (LEIA-ME: "a luz da fase 3 vem de baixo, o ventre é a
    # área clara") — pinta o jato e os pedaços de pedra com o mesmo acento
    # alaranjado.
    HAZARD_COLOR = (235, 140, 70, 140)

    ATTACK_COOLDOWN_MIN = 190
    ATTACK_COOLDOWN_MAX = 260
    # Só 2 ataques agora (Sopro/Terremoto) — alterna entre os dois.
    ATTACK_PATTERN = ("A", "B")

    # Sopro (quadros 2-3 da folha nova): sem quadros próprios de
    # antecipação/recuperação — TELEGRAPH e RECOVER seguram o quadro 2
    # (boca carregando/fechando), BREATH mostra o quadro 3 (jato ativo).
    SOPRO_TELEGRAPH_DURATION = 28
    SOPRO_BREATH_DURATION = 16
    SOPRO_RECOVER_DURATION = 10
    SOPRO_RANGE = 360
    SOPRO_HEIGHT = 30
    # Fração aproximada de onde fica a boca dentro do quadro cru (a cabeça
    # sempre nasce do lado ESQUERDO da arte, ver correção de flip em draw)
    # — chute de olho na arte, não dá pra medir o pixel exato sem rodar o
    # jogo. X medido a partir da borda de trás (rabo); Y do topo do quadro.
    # Usado só pro VISUAL do jato/faísca (ver _mouth_position/
    # _draw_sopro_fire) — o retângulo que realmente causa dano continua
    # _sopro_breath_rect, sem mudar (baseado na hitbox, não na arte).
    SOPRO_MOUTH_X_FRACTION = 0.14
    SOPRO_MOUTH_Y_FRACTION = 0.38

    # Terremoto (quadros 4-6 voando + 7-9 batendo): TELEGRAPH segura o
    # quadro parado (idle) antes de decolar, FLY alterna os 3 quadros de
    # voo em loop, SLAM segura os quadros de impacto (anima rápido os 3 e
    # trava no último — ver _frame_index) durante TODO o tremor de ~5s
    # (pedido do Raul), soltando um pedaço novo da caverna a cada
    # TERREMOTO_ROCK_INTERVAL quadros até bater TERREMOTO_ROCK_TOTAL —
    # "MUITOS meteoros" caindo ao longo do tremor, não uma leva só de
    # início. RECOVER volta pro quadro parado até assentar de vez.
    TERREMOTO_TELEGRAPH_DURATION = 24
    TERREMOTO_FLY_DURATION = 70
    # 300 quadros = ~5s a 60fps (ver EARTHQUAKE_SHAKE_DURATION em game.py,
    # mesma duração pra tremor de câmera e chuva de pedras terminarem
    # juntos).
    TERREMOTO_SLAM_DURATION = 300
    # Só os 3 quadros de impacto animam rápido (ver _frame_index) — o
    # resto dos 300 quadros do SLAM segura no último quadro (poeira
    # assentada) enquanto os pedaços continuam caindo.
    TERREMOTO_SLAM_FRAME_DURATION = 24
    TERREMOTO_RECOVER_DURATION = 14
    TERREMOTO_ROCK_INTERVAL = 16
    TERREMOTO_ROCK_TOTAL = 18
    # Margem lateral pra sortear onde cada pedaço nasce (mesma ideia do
    # antigo PLATFORM_MARGIN, mas não precisa mais de patrulha nenhuma).
    ROCK_SPAWN_MARGIN = 20

    # Sistema de queda reaproveitado tal e qual da antiga Brasas (dragon_
    # rock.png, 8 quadros: queda/impacto/explosão) — só a origem (um
    # pedaço novo a cada TERREMOTO_ROCK_INTERVAL quadros ao longo de todo
    # o tremor, não uma leva só no instante do impacto) mudou, ver
    # _update_terremoto_slam/_spawn_terremoto_rock/_update_rocks.
    # ROCK_SIZE agora bate com o sprite visual de verdade (24 * Game.
    # ROCK_SPRITE_SCALE=2.2 = 52.8, arredondado pro mesmo 53 que
    # pygame.transform.scale gera lá — ver _load_grid_sheet) — pedido do
    # Raul: "aumente a hitbox dos meteoros para ficarem iguais ao tamanho
    # deles". Se o Raul mudar ROCK_SPRITE_SCALE de novo, este número
    # precisa acompanhar pra continuar batendo.
    ROCK_FALL_SPEED = 4.2
    ROCK_START_HEIGHT = 260
    ROCK_IMPACT_DURATION = 4
    ROCK_EXPLOSION_DURATION = 46
    ROCK_SIZE = 53

    IDLE = "idle"
    HURT = "hurt"
    DYING = "dying"
    DEAD = "dead"
    # Dormente até o player chegar perto (estilo Silksong, ver Game.
    # _maybe_wake_bosses) — mesmo padrão do SlimeKing/Librarian/Specimen.
    DORMANT = "dormant"
    SOPRO_TELEGRAPH = "sopro_telegraph"
    SOPRO_BREATH = "sopro_breath"
    SOPRO_RECOVER = "sopro_recover"
    TERREMOTO_TELEGRAPH = "terremoto_telegraph"
    TERREMOTO_FLY = "terremoto_fly"
    TERREMOTO_SLAM = "terremoto_slam"
    TERREMOTO_RECOVER = "terremoto_recover"
    ATTACK_STATES = (
        SOPRO_TELEGRAPH, SOPRO_BREATH, SOPRO_RECOVER,
        TERREMOTO_TELEGRAPH, TERREMOTO_FLY, TERREMOTO_SLAM, TERREMOTO_RECOVER,
    )
    # IDLE aqui já é o "parado esperando o próximo ataque" — não existe
    # mais WALK (ele nunca anda, ver docstring da classe).
    ACTIVE_STATES = (IDLE, HURT, DORMANT) + ATTACK_STATES
    # Ver SlimeKing.FACING_STATES — mesma regra: só vira pra Lia parado ou
    # ainda na antecipação, nunca no meio de um ataque em execução.
    FACING_STATES = (IDLE, DORMANT, SOPRO_TELEGRAPH, TERREMOTO_TELEGRAPH)

    def __init__(self, platform):
        self.platform = platform
        # Posição fixa pra sempre (ver docstring: ele nunca mais se move em
        # X) — nasce encostado na extremidade DIREITA do retângulo do Tiled
        # (pedido do Raul), não centralizado (ver Level._make_boss_arenas,
        # ramo Fase 3).
        self.x = platform.rect.right - self.WIDTH
        self.y = platform.rect.top - self.HEIGHT
        self.direction = 1
        self.health = self.HEALTH
        self.state = self.DORMANT
        self.state_timer = 0
        self.animation = 0
        self.attack_cooldown = self._next_attack_delay()
        self.attack_index = 0
        # Pedaços de pedra já soltos: atualizados todo quadro independente
        # do estado (ver _update_rocks), pra continuarem caindo/queimando
        # mesmo depois dele já ter voltado a esperar o próximo ataque.
        self.rocks = []
        # Quantos pedaços já nasceram no tremor do Terremoto em andamento
        # (ver _update_terremoto_slam) — reseta a cada novo Terremoto em
        # _start_terremoto_slam.
        self.terremoto_rocks_spawned = 0
        # Vira True por 1 quadro no instante do impacto do Terremoto (ver
        # _start_terremoto_slam) — Game._check_boss_shake_events consome
        # isso pra disparar o shake de tela + earthquake_dragon_sound.
        self._shake_pending = False

    @property
    def melee_vulnerable(self):
        """Pedido do Raul: luta estilo Cuphead — corpo a corpo NUNCA causa
        dano nele (permanente, não depende mais do estado). Só o ataque à
        distância funciona (Game._update_projectiles não olha essa
        propriedade); tocar nele continua doendo na Lia normalmente (ramo
        de contato de Game.check_enemies, sem relação com isso)."""
        return False

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
        if self.state == self.DYING:
            self._update_death()
        elif self.state == self.DEAD:
            # Pedido do Raul: chefe morto fica morto pra sempre, sem
            # respawn (ver docstring de _update_death) — nenhuma ação aqui.
            pass
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
        elif self.state == self.TERREMOTO_TELEGRAPH:
            self._start_terremoto_fly()
        elif self.state == self.TERREMOTO_FLY:
            self._update_terremoto_fly()
        elif self.state == self.TERREMOTO_SLAM:
            self._update_terremoto_slam()
        elif self.state == self.TERREMOTO_RECOVER:
            self._update_attack_recover()

    def _update_phase(self, next_state, next_duration):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = next_state
            self.state_timer = next_duration

    def _update_idle(self):
        """Parado esperando o próximo ataque — não existe mais transição
        pra WALK (ver docstring da classe: ele nunca anda), então IDLE
        dura até attack_cooldown zerar."""
        self.y = self.platform.rect.top - self.HEIGHT
        self.attack_cooldown -= 1
        if self.attack_cooldown <= 0:
            self._start_attack()

    def _update_dormant(self):
        self.y = self.platform.rect.top - self.HEIGHT

    def wake_up(self):
        if self.state == self.DORMANT:
            self.state = self.IDLE

    def _start_attack(self):
        kind = self.ATTACK_PATTERN[self.attack_index % len(self.ATTACK_PATTERN)]
        self.attack_index += 1
        if kind == "A":
            self.state = self.SOPRO_TELEGRAPH
            self.state_timer = self.SOPRO_TELEGRAPH_DURATION
        else:
            self.state = self.TERREMOTO_TELEGRAPH
            self.state_timer = self.TERREMOTO_TELEGRAPH_DURATION

    def _update_attack_recover(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.IDLE
            self.attack_cooldown = self._next_attack_delay()

    def _start_terremoto_fly(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.TERREMOTO_FLY
            self.state_timer = self.TERREMOTO_FLY_DURATION

    def _update_terremoto_fly(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        if self.state_timer <= 0:
            self._start_terremoto_slam()

    def _start_terremoto_slam(self):
        """Bate no chão: dispara o tremor de tela de ~5s (ver
        consume_shake_event, lido por Game._check_boss_shake_events, que
        também toca earthquake_dragon_sound) e zera a contagem de pedaços
        — eles nascem aos poucos em _update_terremoto_slam, não todos de
        uma vez (pedido do Raul: "que caia MUITOS meteoros" ao longo do
        tremor, não uma leva só no instante do tranco)."""
        self.state = self.TERREMOTO_SLAM
        self.state_timer = self.TERREMOTO_SLAM_DURATION
        self.terremoto_rocks_spawned = 0
        self._shake_pending = True

    def _update_terremoto_slam(self):
        self.y = self.platform.rect.top - self.HEIGHT
        self.state_timer -= 1
        elapsed = self.TERREMOTO_SLAM_DURATION - self.state_timer
        expected = min(self.TERREMOTO_ROCK_TOTAL, 1 + elapsed // self.TERREMOTO_ROCK_INTERVAL)
        while self.terremoto_rocks_spawned < expected:
            self._spawn_terremoto_rock()
            self.terremoto_rocks_spawned += 1
        if self.state_timer <= 0:
            self.state = self.TERREMOTO_RECOVER
            self.state_timer = self.TERREMOTO_RECOVER_DURATION

    def _spawn_terremoto_rock(self):
        """Um pedaço da caverna por vez (reaproveita o sistema de queda da
        antiga Brasas — ver _update_rocks, roda todo quadro, independente
        do estado, então os pedaços continuam caindo/explodindo mesmo
        depois do tremor já ter passado)."""
        left = self.platform.rect.left + self.ROCK_SPAWN_MARGIN
        right = self.platform.rect.right - self.ROCK_SPAWN_MARGIN
        x = random.uniform(left, right) if right > left else self.rect.centerx
        self.rocks.append({
            "x": x,
            "y": self.platform.rect.top - self.ROCK_START_HEIGHT,
            "phase": "falling",
            "timer": 0,
        })

    def consume_shake_event(self):
        """Lido uma vez só por Game._check_boss_shake_events — True no
        primeiro quadro depois de um impacto do Terremoto, daí volta a
        False sozinho (evita disparar o shake de novo todo quadro
        seguinte enquanto ele ainda está no estado SLAM)."""
        if self._shake_pending:
            self._shake_pending = False
            return True
        return False

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

    def _sopro_breath_rect(self):
        width, height = self.SOPRO_RANGE, self.SOPRO_HEIGHT
        y = self.platform.rect.top - height
        x = self.rect.right if self.direction > 0 else self.rect.left - width
        return pygame.Rect(round(x), round(y), width, height)

    def active_hazards(self):
        """Jato do Sopro enquanto varre o chão e pedaços de pedra caídos do
        Terremoto (caindo/no impacto) — continuam valendo mesmo depois do
        estado de ataque que os originou (ver _update_rocks, roda todo
        quadro, incondicional). Sem mais meteoros: o antigo Voo da Fúria
        (marca no chão + meteoro mirado) saiu de cena, ver docstring da
        classe. Isso aqui é o que REALMENTE causa dano (ver Game.
        _check_enemy_attack_hazards) — Level._draw_enemy_attack_hazards usa
        essa mesma lista como aviso pintado, não precisa mais de um
        overlay_hazards à parte (não tem mais nada especial pra excluir)."""
        hazards = []
        if self.state == self.SOPRO_BREATH:
            hazards.append(self._sopro_breath_rect())
        size = self.ROCK_SIZE
        for rock in self.rocks:
            hazards.append(pygame.Rect(round(rock["x"] - size / 2), round(rock["y"] - size / 2), size, size))
        return hazards

    def overlay_hazards(self):
        """Sem retângulo laranja translúcido genérico pra NENHUM hazard do
        Dragão agora (Level._draw_enemy_attack_hazards) — dragon_fire.png
        deu arte de verdade ao Sopro (ver _draw_sopro_fire) e os pedaços de
        pedra do Terremoto já têm sprite própria (dragon_rock.png, maior
        agora — ver Game.ROCK_SPRITE_SCALE, pedido do Raul: "retire isso e
        deixe apenas a sprite dos meteoros"). O dano de ambos continua
        intacto (active_hazards, sem mudança) — isso aqui é só o aviso
        pintado por cima, que agora fica sempre vazio."""
        return []

    def parryable_hazards(self):
        """Sopro enquanto varre e pedaços de pedra do Terremoto — só
        enquanto ainda estão "voando" (fase "falling"); depois de
        "impact"/"explosion" já caíram, não tem mais o que aparar (pedido
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
        return pairs

    def _update_hurt(self):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.IDLE

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

    def _update_death(self):
        """Sem quadros de morte próprios na folha nova (ver docstring da
        classe) — esmaece o quadro parado até sumir (ver draw/
        _current_frame, que aplica o alpha proporcional a state_timer).
        Pedido do Raul: chefe derrotado fica morto pra sempre — sem
        RESPAWN_TIME/_update_respawn (removidos), DEAD é estado terminal,
        ver update() acima."""
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.DEAD

    def _sprite_key(self):
        """4 chaves só (ver game._load_dragon_sprites): "idle" (1 quadro,
        cobre parado/dormente/dano/morte também — sem arte própria pra
        essas, ver docstring da classe), "sopro" (2 quadros), "voo" (3
        quadros, fase TERREMOTO_FLY) e "terremoto" (3 quadros, fase
        TERREMOTO_SLAM)."""
        if self.state in (self.SOPRO_TELEGRAPH, self.SOPRO_BREATH, self.SOPRO_RECOVER):
            return "sopro"
        if self.state == self.TERREMOTO_FLY:
            return "voo"
        if self.state == self.TERREMOTO_SLAM:
            return "terremoto"
        return "idle"

    def _frame_index(self, key, count):
        if key == "sopro":
            # 2 quadros só: o 1º cobre antecipação/recuperação (boca
            # carregando/fechando), o 2º é o jato ativo.
            return 1 if self.state == self.SOPRO_BREATH else 0
        if key == "voo":
            # Bate asas em loop enquanto sobe/paira (duração de sobra pra
            # não ficar rápido demais, ~0.4s por ciclo a 60fps).
            return (self.animation // 8) % count
        if key == "terremoto":
            # Percorre os 3 quadros de impacto rápido (TERREMOTO_SLAM_
            # FRAME_DURATION, bem menor que o SLAM inteiro de ~5s) e
            # segura o último (poeira assentada) pro resto do tremor,
            # enquanto os pedaços continuam caindo — ver TERREMOTO_SLAM_
            # FRAME_DURATION.
            elapsed = self.TERREMOTO_SLAM_DURATION - self.state_timer
            if elapsed >= self.TERREMOTO_SLAM_FRAME_DURATION:
                return count - 1
            return max(0, min(count - 1, elapsed * count // self.TERREMOTO_SLAM_FRAME_DURATION))
        return 0

    def _rock_frame_index(self, rock):
        if rock["phase"] == "falling":
            return (self.animation // 5) % 4
        if rock["phase"] == "impact":
            return 4
        elapsed = self.ROCK_EXPLOSION_DURATION - rock["timer"]
        return 5 + min(2, elapsed // 4)

    def _current_frame(self, sprites):
        key = self._sprite_key()
        frames = sprites[key]
        index = self._frame_index(key, len(frames))
        return frames[min(index, len(frames) - 1)]

    def draw(self, surface, camera_x, camera_y, sprites):
        if self.state != self.DEAD:
            frame = self._current_frame(sprites)
            # A arte nova (dragon.png) já nasce olhando pra ESQUERDA em
            # todo quadro (cabeça/chifres sempre do lado esquerdo da tira —
            # diferente da folha antiga). Por isso o flip é invertido aqui
            # (direction > 0, não < 0): direction=1 (Lia à direita) precisa
            # virar o desenho pra ele passar a olhar pra direita; direction
            # =-1 (Lia à esquerda) já sai certo sem flip nenhum. Bug real
            # do Raul (2026-08-27): com o sinal antigo o Dragão sempre
            # ficava olhando pro lado ERRADO — se ela ficasse parada de um
            # lado só (comum numa luta à distância parada), parecia
            # "travado" sempre olhando pro mesmo lado.
            if self.direction > 0:
                frame = pygame.transform.flip(frame, True, False)
            if self.state == self.DYING:
                # Sem quadros de morte próprios (ver docstring) — esmaece o
                # quadro parado até sumir de vez.
                frame = frame.copy()
                total = self.DEATH_FRAMES * self.DEATH_FRAME_TIME
                alpha = max(0, min(255, round(255 * self.state_timer / total)))
                frame.set_alpha(alpha)
            frame_w, frame_h = frame.get_size()
            offset_x = (frame_w - self.WIDTH) // 2
            offset_y = frame_h - self.HEIGHT - self.GROUND_LIFT
            surface.blit(frame, (self.x - offset_x - camera_x, self.y - offset_y - camera_y))
        self._draw_sopro_fire(surface, camera_x, camera_y, sprites)
        rock_frames = sprites.get("rock")
        if rock_frames:
            for rock in self.rocks:
                frame = rock_frames[min(self._rock_frame_index(rock), len(rock_frames) - 1)]
                surface.blit(
                    frame,
                    (rock["x"] - camera_x - frame.get_width() / 2, rock["y"] - camera_y - frame.get_height() / 2),
                )

    def _mouth_position(self, frame_w, frame_h):
        """Posição aproximada da boca dele em coordenadas de mundo, pra o
        jato/faísca nascerem ali em vez de na borda da hitbox (pedido do
        Raul: "que o sopro saia da boca dele"). Usa o mesmo offset_x/
        offset_y do corpo (ver draw) pra achar a borda do sprite VISUAL
        (bem maior que a hitbox) e desloca pra dentro pelas frações
        SOPRO_MOUTH_X/Y_FRACTION. Como a cabeça nasce sempre do lado
        ESQUERDO do quadro cru, direction=-1 (olhando pra esquerda, sem
        flip) usa a fração direto; direction=1 (flipado) espelha a fração
        (1 - fração) pra continuar caindo em cima da cabeça depois de
        virada."""
        offset_x = (frame_w - self.WIDTH) // 2
        offset_y = frame_h - self.HEIGHT - self.GROUND_LIFT
        sprite_left = self.x - offset_x
        sprite_top = self.y - offset_y
        x_fraction = (
            self.SOPRO_MOUTH_X_FRACTION if self.direction < 0
            else 1 - self.SOPRO_MOUTH_X_FRACTION
        )
        mouth_x = sprite_left + x_fraction * frame_w
        mouth_y = sprite_top + self.SOPRO_MOUTH_Y_FRACTION * frame_h
        return mouth_x, mouth_y

    def _draw_sopro_fire(self, surface, camera_x, camera_y, sprites):
        """Chama de verdade (dragon_fire.png, ver game._load_dragon_fire_
        sprites) nascendo da boca dele (ver _mouth_position) — o hitbox
        real não muda (_sopro_breath_rect continua sendo o que
        active_hazards usa pra dano, baseado na hitbox, não na arte), isso
        aqui é só o visual. TELEGRAPH mostra uma faísca crescendo na boca
        (carregando o jato); BREATH estica a chama grande a partir dela
        até cobrir o alcance do jato (SOPRO_RANGE)."""
        sopro_frames = sprites.get("sopro")
        if not sopro_frames:
            return
        frame_w, frame_h = sopro_frames[0].get_size()
        mouth_x, mouth_y = self._mouth_position(frame_w, frame_h)
        ember = sprites.get("sopro_ember")
        flame = sprites.get("sopro_flame")
        if self.state == self.SOPRO_TELEGRAPH and ember:
            progress = 1 - self.state_timer / self.SOPRO_TELEGRAPH_DURATION
            scale = 0.4 + 0.6 * progress
            size = (max(1, round(ember.get_width() * scale)), max(1, round(ember.get_height() * scale)))
            spark = pygame.transform.scale(ember, size)
            surface.blit(spark, (mouth_x - camera_x - size[0] / 2, mouth_y - camera_y - size[1] / 2))
        elif self.state == self.SOPRO_BREATH and flame:
            width, height = self.SOPRO_RANGE, self.SOPRO_HEIGHT
            stretched = pygame.transform.scale(flame, (width, height))
            # Espelha igual ao corpo (ver draw) — não dá pra garantir sem
            # rodar o jogo que bate certo com a arte crua do dragon_fire.png;
            # avise se a chama sair virada pro lado errado que eu ajusto.
            if self.direction > 0:
                stretched = pygame.transform.flip(stretched, True, False)
            rect_x = mouth_x if self.direction > 0 else mouth_x - width
            surface.blit(stretched, (rect_x - camera_x, mouth_y - height / 2 - camera_y))
