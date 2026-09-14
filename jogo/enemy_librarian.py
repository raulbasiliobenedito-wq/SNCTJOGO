"""Chefe da biblioteca e seus ataques específicos."""

import math
import random

import pygame

from sprites import flipped


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
    # classe) — mesmo mecanismo do Dragão (CombatSystem.check_enemies confere isso
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
        CombatSystem.check_parries testa o attack_box da Lia contra esse rect e,
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
                frame = flipped(frame)
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
