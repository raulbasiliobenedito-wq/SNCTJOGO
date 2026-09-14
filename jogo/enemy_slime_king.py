"""Rei Slime e seus ataques específicos."""

import random

import pygame

from sprites import flipped


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
            frame = flipped(frame)
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
