"""Chefe do laboratório e seus ataques específicos."""

import random

import pygame

from sprites import flipped


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
    # mesmo mecanismo do Dragão/Bibliotecário: CombatSystem.check_enemies confere
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

    def take_hit(self, damage=1, allow_hurt=False):
        if not self.alive or (self.state == self.HURT and not allow_hurt):
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
                frame = flipped(frame)
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
        Assets._load_specimen_sprites), sem animação própria."""
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
