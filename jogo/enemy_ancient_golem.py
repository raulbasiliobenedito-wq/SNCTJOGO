"""Golem Ancião, chefe intermediário da vila/campo."""

import random

import pygame

import audio
from sprites import flipped


class AncientGolem:
    """Chefe terrestre com três ataques legíveis e VFX próprios.

    O corpo lógico é menor que os quadros 92x92. Os 14 pixels transparentes
    abaixo da arte são compensados por ``GROUND_LIFT``; assim os pés encostam
    no piso sem recortar as animações de ataque e morte.

    O ciclo de todos os ataques é preparação -> execução -> recuperação:

    * impacto no chão: golpeia e cria erupções sucessivas na direção da Lia;
    * investida: trava a direção, cruza parte da arena e deixa poeira;
    * pedregulho: arremessa uma pedra em arco que explode ao cair.
    """

    WIDTH = 46
    HEIGHT = 64
    VFX_SCALE = 1.5
    # A spritesheet é desenhada a 1,5x. A margem transparente inferior
    # original de 14px acompanha a mesma escala para os pés permanecerem
    # exatamente no piso.
    GROUND_LIFT = 21
    HEALTH = 36
    SPEED = 0.75
    PLATFORM_MARGIN = 12
    WAKE_RADIUS = 300
    uses_custom_hit_vfx = True

    HURT_FRAME_TICKS = 3
    HURT_FRAMES = 7
    HURT_DURATION = HURT_FRAME_TICKS * HURT_FRAMES
    DEATH_FRAME_TIME = 5
    DEATH_FRAMES = 17
    IDLE_DURATION = 65

    ATTACK_COOLDOWN_MIN = 105
    ATTACK_COOLDOWN_MAX = 155
    INITIAL_ATTACK_DELAY = 90
    ATTACK_PATTERN = ("slam", "charge", "throw", "slam", "throw", "charge")

    SLAM_FRAME_TICKS = 4
    SLAM_FRAMES = 17
    SLAM_IMPACT_FRAME = 14  # índice zero; quadro 15 no Aseprite
    SLAM_RECOVERY_SEQUENCE = (16, 13, 12, 10, 5, 2, 0)
    SLAM_RECOVERY_FRAME_TICKS = 4
    SHOCKWAVE_DISTANCES = (72, 136, 200, 264)
    SHOCKWAVE_INTERVAL = 7
    SHOCKWAVE_HAZARD_FRAMES = 14

    CHARGE_TELEGRAPH_FRAMES = 5
    CHARGE_TELEGRAPH_FRAME_TICKS = 5
    CHARGE_ACTIVE_START_FRAME = 5
    CHARGE_ACTIVE_FRAMES = 11
    CHARGE_ACTIVE_FRAME_TICKS = 3
    CHARGE_SPEED = 6.8
    CHARGE_RECOVERY_DURATION = 30
    CHARGE_DUST_INTERVAL = 6

    THROW_FRAME_TICKS = 4
    THROW_FRAMES = 16
    THROW_RELEASE_FRAME = 12  # índice zero; transição Q12 -> Q13
    THROW_RECOVERY_DURATION = 24
    BOULDER_SPEED_X = 7.5
    BOULDER_SPEED_Y = -5.5
    BOULDER_GRAVITY = 0.30
    BOULDER_RADIUS = round(15 * VFX_SCALE)
    BOULDER_RANGE = 460

    EFFECT_FRAME_TICKS = 4
    EFFECT_FRAME_COUNTS = {
        "rock_shockwave": 9,
        "ground_slam_impact": 7,
        "charge_dust": 7,
        "charge_impact": 9,
        "boulder_explosion": 9,
        "damage_debris": 8,
    }

    DORMANT = "dormant"
    IDLE = "idle"
    WALK = "walk"
    HURT = "hurt"
    DYING = "dying"
    DEAD = "dead"
    SLAM = "slam"
    SLAM_RECOVER = "slam_recover"
    CHARGE_TELEGRAPH = "charge_telegraph"
    CHARGE_ACTIVE = "charge_active"
    CHARGE_RECOVER = "charge_recover"
    THROW = "throw"
    THROW_RECOVER = "throw_recover"

    ATTACK_STATES = (
        SLAM,
        SLAM_RECOVER,
        CHARGE_TELEGRAPH,
        CHARGE_ACTIVE,
        CHARGE_RECOVER,
        THROW,
        THROW_RECOVER,
    )
    ACTIVE_STATES = (DORMANT, IDLE, WALK, HURT) + ATTACK_STATES
    FACING_STATES = (DORMANT, IDLE)

    def __init__(self, platform):
        self.platform = platform
        self.x = platform.rect.centerx - self.WIDTH // 2
        self.y = platform.rect.top - self.HEIGHT
        self.direction = -1
        self.speed = self.SPEED
        self.health = self.HEALTH
        self.state = self.DORMANT
        self.state_timer = 0
        self.state_elapsed = 0
        self.animation = 0
        self.death_frame = 0
        self.attack_cooldown = self.INITIAL_ATTACK_DELAY
        self.attack_index = 0
        self.player_x = self.rect.centerx
        self.effects = []
        self.boulders = []
        self.shockwave_queue = []
        self._slam_triggered = False
        self._throw_released = False

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.WIDTH, self.HEIGHT)

    @property
    def alive(self):
        return self.state in self.ACTIVE_STATES

    @property
    def melee_vulnerable(self):
        # A primeira versão não possui escudo ou imunidade sem sinal visual.
        return True

    @staticmethod
    def _next_attack_delay():
        return random.randint(
            AncientGolem.ATTACK_COOLDOWN_MIN,
            AncientGolem.ATTACK_COOLDOWN_MAX,
        )

    def face_player(self, player_x):
        # Guarda a posição mesmo durante estados que não podem virar. O valor
        # mais recente trava a direção exatamente quando o próximo ataque começa.
        self.player_x = player_x
        if self.state in self.FACING_STATES:
            self.direction = 1 if player_x >= self.rect.centerx else -1

    def wake_up(self):
        if self.state == self.DORMANT:
            self._set_state(self.WALK)

    def update(self):
        self.animation += 1
        self.state_elapsed += 1
        self._update_effects()
        self._update_shockwave_queue()
        self._update_boulders()

        if self.state == self.DYING:
            self._update_death()
        elif self.state == self.DEAD:
            return
        elif self.state == self.DORMANT:
            self._ground()
        elif self.state == self.HURT:
            self._update_hurt()
        elif self.state == self.IDLE:
            self._update_idle()
        elif self.state == self.SLAM:
            self._update_slam()
        elif self.state == self.SLAM_RECOVER:
            self._update_recovery()
        elif self.state == self.CHARGE_TELEGRAPH:
            self._update_charge_telegraph()
        elif self.state == self.CHARGE_ACTIVE:
            self._update_charge_active()
        elif self.state == self.CHARGE_RECOVER:
            self._update_recovery()
        elif self.state == self.THROW:
            self._update_throw()
        elif self.state == self.THROW_RECOVER:
            self._update_recovery()
        else:
            self._patrol()

    def _set_state(self, state, duration=0):
        self.state = state
        self.state_timer = duration
        self.state_elapsed = 0

    def _ground(self):
        self.y = self.platform.rect.top - self.HEIGHT

    def _update_idle(self):
        self._ground()
        self.state_timer -= 1
        self.attack_cooldown -= 1
        if self.attack_cooldown <= 0:
            self._start_attack()
        elif self.state_timer <= 0:
            self._set_state(self.WALK)

    def _patrol(self):
        left = self.platform.rect.left + self.PLATFORM_MARGIN
        right = self.platform.rect.right - self.WIDTH - self.PLATFORM_MARGIN
        self.x += self.speed * self.direction
        if self.x <= left or self.x >= right:
            self.x = max(left, min(self.x, right))
            self.direction *= -1
            self._set_state(self.IDLE, self.IDLE_DURATION)
        self._ground()
        self.attack_cooldown -= 1
        if self.attack_cooldown <= 0:
            self._start_attack()

    def _lock_direction_to_player(self):
        self.direction = 1 if self.player_x >= self.rect.centerx else -1

    def _start_attack(self):
        self._lock_direction_to_player()
        attack = self.ATTACK_PATTERN[self.attack_index % len(self.ATTACK_PATTERN)]
        self.attack_index += 1
        if attack == "slam":
            self._slam_triggered = False
            self._set_state(self.SLAM, self.SLAM_FRAMES * self.SLAM_FRAME_TICKS)
        elif attack == "charge":
            duration = self.CHARGE_TELEGRAPH_FRAMES * self.CHARGE_TELEGRAPH_FRAME_TICKS
            self._set_state(self.CHARGE_TELEGRAPH, duration)
        else:
            self._throw_released = False
            self._set_state(self.THROW, self.THROW_FRAMES * self.THROW_FRAME_TICKS)

    def _tick_state(self):
        self._ground()
        self.state_timer -= 1
        return self.state_timer <= 0

    def _update_slam(self):
        if not self._slam_triggered and self.state_elapsed >= self.SLAM_IMPACT_FRAME * self.SLAM_FRAME_TICKS:
            self._slam_triggered = True
            self._start_slam_effects()
            audio.play_sfx("golem_ground_slam_sound")
        if self._tick_state():
            duration = len(self.SLAM_RECOVERY_SEQUENCE) * self.SLAM_RECOVERY_FRAME_TICKS
            self._set_state(self.SLAM_RECOVER, duration)

    def _start_slam_effects(self):
        floor_y = self.platform.rect.top
        impact_x = self.rect.centerx + self.direction * 24
        self._spawn_effect("ground_slam_impact", impact_x, floor_y, "bottom")

        positions = []
        for distance in self.SHOCKWAVE_DISTANCES:
            x = self.rect.centerx + self.direction * distance
            x = max(self.platform.rect.left + 28, min(x, self.platform.rect.right - 28))
            if not positions or x != positions[-1]:
                positions.append(x)
        if positions:
            self._spawn_effect("rock_shockwave", positions[0], floor_y, "bottom")
        self.shockwave_queue.extend(
            {"delay": index * self.SHOCKWAVE_INTERVAL, "x": x, "y": floor_y}
            for index, x in enumerate(positions[1:], start=1)
        )

    def _update_shockwave_queue(self):
        pending = []
        for wave in self.shockwave_queue:
            wave["delay"] -= 1
            if wave["delay"] <= 0:
                self._spawn_effect("rock_shockwave", wave["x"], wave["y"], "bottom")
            else:
                pending.append(wave)
        self.shockwave_queue = pending

    def _update_charge_telegraph(self):
        if self._tick_state():
            duration = self.CHARGE_ACTIVE_FRAMES * self.CHARGE_ACTIVE_FRAME_TICKS
            self._set_state(self.CHARGE_ACTIVE, duration)

    def _update_charge_active(self):
        left = self.platform.rect.left + self.PLATFORM_MARGIN
        right = self.platform.rect.right - self.WIDTH - self.PLATFORM_MARGIN
        target = self.x + self.direction * self.CHARGE_SPEED
        hit_edge = target <= left or target >= right
        self.x = max(left, min(target, right))
        self._ground()

        if self.state_elapsed == 1 or self.state_elapsed % self.CHARGE_DUST_INTERVAL == 0:
            dust_x = self.rect.centerx - self.direction * (self.WIDTH // 2)
            self._spawn_effect("charge_dust", dust_x, self.platform.rect.top, "bottom")

        self.state_timer -= 1
        if hit_edge or self.state_timer <= 0:
            impact_x = self.rect.centerx + self.direction * (self.WIDTH // 2)
            self._spawn_effect("charge_impact", impact_x, self.platform.rect.top, "bottom")
            audio.play_sfx("golem_charge_impact_sound")
            self._set_state(self.CHARGE_RECOVER, self.CHARGE_RECOVERY_DURATION)

    def _update_throw(self):
        if not self._throw_released and self.state_elapsed >= self.THROW_RELEASE_FRAME * self.THROW_FRAME_TICKS:
            self._throw_released = True
            self._spawn_boulder()
            audio.play_sfx("golem_boulder_throw_sound")
        if self._tick_state():
            self._set_state(self.THROW_RECOVER, self.THROW_RECOVERY_DURATION)

    def _spawn_boulder(self):
        self.boulders.append({
            "x": float(self.rect.centerx + self.direction * 30),
            "y": float(self.rect.top + 27),
            "vx": self.direction * self.BOULDER_SPEED_X,
            "vy": self.BOULDER_SPEED_Y,
            "origin_x": float(self.rect.centerx),
            "age": 0,
        })

    def _update_boulders(self):
        active = []
        floor_y = self.platform.rect.top
        left = self.platform.rect.left
        right = self.platform.rect.right
        for boulder in self.boulders:
            boulder["x"] += boulder["vx"]
            boulder["y"] += boulder["vy"]
            boulder["vy"] += self.BOULDER_GRAVITY
            boulder["age"] += 1
            landed = boulder["y"] + self.BOULDER_RADIUS >= floor_y
            out = boulder["x"] <= left or boulder["x"] >= right
            expired = abs(boulder["x"] - boulder["origin_x"]) >= self.BOULDER_RANGE
            if landed or out or expired:
                x = max(left + self.BOULDER_RADIUS, min(boulder["x"], right - self.BOULDER_RADIUS))
                self._spawn_effect("boulder_explosion", x, floor_y, "bottom")
                audio.play_sfx("golem_boulder_explosion_sound")
            else:
                active.append(boulder)
        self.boulders = active

    def _update_recovery(self):
        if self._tick_state():
            self.attack_cooldown = self._next_attack_delay()
            self._set_state(self.WALK)

    def _update_hurt(self):
        if self._tick_state():
            self.attack_cooldown = max(self.attack_cooldown, 35)
            self._set_state(self.WALK)

    def take_hit(self, damage=1, allow_hurt=False):
        if not self.alive or (self.state == self.HURT and not allow_hurt):
            return False
        self.health -= damage
        self._spawn_effect("damage_debris", self.rect.centerx, self.rect.centery, "center")
        if self.health <= 0:
            self._start_dying()
        elif self.state not in self.ATTACK_STATES:
            self._set_state(self.HURT, self.HURT_DURATION)
        return True

    def stomp(self):
        # Defesa adicional: CombatSystem já exclui chefes do pisão, mas o
        # próprio Golem também nunca deve morrer instantaneamente por ele.
        return False

    def _start_dying(self):
        self.health = 0
        self.effects.clear()
        self.boulders.clear()
        self.shockwave_queue.clear()
        self.death_frame = 0
        self._set_state(self.DYING, self.DEATH_FRAMES * self.DEATH_FRAME_TIME)

    def _update_death(self):
        self._ground()
        self.state_timer -= 1
        self.death_frame = min(
            self.DEATH_FRAMES - 1,
            self.state_elapsed // self.DEATH_FRAME_TIME,
        )
        if self.state_timer <= 0:
            self.death_frame = self.DEATH_FRAMES - 1
            self._set_state(self.DEAD)

    def _spawn_effect(self, kind, x, y, anchor):
        self.effects.append({"kind": kind, "x": float(x), "y": float(y), "anchor": anchor, "age": 0})

    def _update_effects(self):
        for effect in self.effects:
            effect["age"] += 1
        self.effects = [
            effect
            for effect in self.effects
            if effect["age"] < self.EFFECT_FRAME_COUNTS[effect["kind"]] * self.EFFECT_FRAME_TICKS
        ]

    def active_hazards(self):
        if not self.alive or self.state == self.DORMANT:
            return []
        hazards = []
        for effect in self.effects:
            if effect["kind"] == "rock_shockwave" and effect["age"] <= self.SHOCKWAVE_HAZARD_FRAMES:
                hazards.append(self._scaled_effect_hazard(effect, 34, 23, 25))
            elif effect["kind"] == "ground_slam_impact" and effect["age"] <= 11:
                hazards.append(self._scaled_effect_hazard(effect, 44, 23, 25))
            elif effect["kind"] == "charge_impact" and effect["age"] <= 10:
                hazards.append(self._scaled_effect_hazard(effect, 40, 26, 28))
            elif effect["kind"] == "boulder_explosion" and effect["age"] <= 11:
                hazards.append(self._scaled_effect_hazard(effect, 44, 26, 28))
        hazards.extend(self._boulder_rect(boulder) for boulder in self.boulders)
        return hazards

    def _scaled_effect_hazard(self, effect, width, height, bottom_offset):
        """Amplia a área perigosa junto do VFX, preservando sua âncora."""
        scaled_width = round(width * self.VFX_SCALE)
        scaled_height = round(height * self.VFX_SCALE)
        scaled_bottom_offset = round(bottom_offset * self.VFX_SCALE)
        return pygame.Rect(
            round(effect["x"] - scaled_width / 2),
            round(effect["y"] - scaled_bottom_offset),
            scaled_width,
            scaled_height,
        )

    def overlay_hazards(self):
        # A arte comunica todas as áreas perigosas; não desenhar retângulos
        # translúcidos por cima dos VFX.
        return []

    def _boulder_rect(self, boulder):
        radius = self.BOULDER_RADIUS
        return pygame.Rect(round(boulder["x"] - radius), round(boulder["y"] - radius), radius * 2, radius * 2)

    def _body_frame(self, sprites):
        if self.state == self.DORMANT:
            frames = sprites["idle"]
            return frames[(self.animation // 8) % len(frames)]
        if self.state == self.WALK:
            frames = sprites["walk"]
            return frames[(self.animation // 5) % len(frames)]
        if self.state == self.HURT:
            frames = sprites["hurt"]
            return frames[min(len(frames) - 1, self.state_elapsed // self.HURT_FRAME_TICKS)]
        if self.state in (self.DYING, self.DEAD):
            return sprites["dead"][min(self.death_frame, len(sprites["dead"]) - 1)]
        if self.state == self.SLAM:
            index = min(self.SLAM_FRAMES - 1, self.state_elapsed // self.SLAM_FRAME_TICKS)
            return sprites["slam"][index]
        if self.state == self.SLAM_RECOVER:
            sequence_index = min(
                len(self.SLAM_RECOVERY_SEQUENCE) - 1,
                self.state_elapsed // self.SLAM_RECOVERY_FRAME_TICKS,
            )
            return sprites["slam"][self.SLAM_RECOVERY_SEQUENCE[sequence_index]]
        if self.state == self.CHARGE_TELEGRAPH:
            index = min(
                self.CHARGE_TELEGRAPH_FRAMES - 1,
                self.state_elapsed // self.CHARGE_TELEGRAPH_FRAME_TICKS,
            )
            return sprites["charge"][index]
        if self.state == self.CHARGE_ACTIVE:
            relative = min(
                self.CHARGE_ACTIVE_FRAMES - 1,
                self.state_elapsed // self.CHARGE_ACTIVE_FRAME_TICKS,
            )
            return sprites["charge"][self.CHARGE_ACTIVE_START_FRAME + relative]
        if self.state == self.CHARGE_RECOVER:
            return sprites["charge"][-1] if self.state_elapsed < 8 else sprites["throw"][0]
        if self.state == self.THROW:
            index = min(self.THROW_FRAMES - 1, self.state_elapsed // self.THROW_FRAME_TICKS)
            return sprites["throw"][index]
        # IDLE/THROW_RECOVER: primeiro quadro lateral neutro, nunca o idle
        # frontal reservado ao estado dormente.
        return sprites["throw"][0]

    def draw(self, surface, camera_x, camera_y, sprites):
        self._draw_effects(surface, camera_x, camera_y, sprites, foreground=False)

        frame = self._body_frame(sprites)
        if self.direction < 0 and self.state != self.DORMANT:
            frame = flipped(frame)
        frame_w, frame_h = frame.get_size()
        offset_x = (frame_w - self.WIDTH) // 2
        offset_y = frame_h - self.HEIGHT - self.GROUND_LIFT
        surface.blit(frame, (self.x - offset_x - camera_x, self.y - offset_y - camera_y))

        self._draw_boulders(surface, camera_x, camera_y, sprites)
        self._draw_effects(surface, camera_x, camera_y, sprites, foreground=True)

    def _draw_boulders(self, surface, camera_x, camera_y, sprites):
        frames = sprites["vfx"]["projectile"]
        for boulder in self.boulders:
            frame = frames[(boulder["age"] // self.EFFECT_FRAME_TICKS) % len(frames)]
            surface.blit(
                frame,
                (
                    boulder["x"] - camera_x - frame.get_width() / 2,
                    boulder["y"] - camera_y - frame.get_height() / 2,
                ),
            )

    def _draw_effects(self, surface, camera_x, camera_y, sprites, foreground):
        foreground_kinds = {"damage_debris", "charge_impact", "boulder_explosion"}
        for effect in self.effects:
            if (effect["kind"] in foreground_kinds) != foreground:
                continue
            frames = sprites["vfx"][effect["kind"]]
            index = min(len(frames) - 1, effect["age"] // self.EFFECT_FRAME_TICKS)
            frame = frames[index]
            x = effect["x"] - camera_x - frame.get_width() / 2
            if effect["anchor"] == "bottom":
                y = effect["y"] - camera_y - frame.get_height()
            else:
                y = effect["y"] - camera_y - frame.get_height() / 2
            surface.blit(frame, (x, y))
