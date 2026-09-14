import pygame

from sprites import flipped
from settings import (
    ASSET_DIR,
    FPS,
    GRAVITY,
    JUMP_SPEED,
    MAX_FALL_SPEED,
    MOVE_SPEED,
    PLAYER_HEIGHT,
    PLAYER_HITBOX_OFFSET_X,
    PLAYER_HITBOX_WIDTH,
    PLAYER_WIDTH,
)


class Player:
    """Estado, movimentação e animação da Lia."""

    DASH_SPEED = 12.0
    DASH_DURATION = 8
    DASH_COOLDOWN = 10

    # --- Mecânica de natação (água da Fase 3) ---
    SWIM_SPEED = 2.9
    SWIM_SINK_GRAVITY = 0.16
    SWIM_MAX_SINK = 2.0
    SWIM_RISE_ACCEL = 0.6
    SWIM_MAX_RISE = -2.5
    # Fôlego: 7 segundos debaixo d'água (com a cabeça submersa) antes de
    # começar a se afogar. Respirar (cabeça fora d'água) recarrega mais
    # rápido do que consome, pra não punir mergulhos rápidos.
    OXYGEN_MAX_FRAMES = 7 * FPS
    OXYGEN_DRAIN_PER_FRAME = 1
    OXYGEN_REFILL_PER_FRAME = 2
    HEAD_HEIGHT = 10

    ACCELERATION = 0.6
    DECELERATION = 0.70
    JUMP_BUFFER_DURATION = 7

    # LIA_ALL_ANIMATIONS-Sheet.png: 97 quadros de 48x48 em uma única linha.
    # As faixas abaixo usam índices Python (começam em zero); a numeração que
    # aparece no arquivo de arte começa em 1. O quadro 97 é só referência.
    FRAME_COUNT = 97
    SHEET_FRAME_WIDTH = 48
    SHEET_FRAME_HEIGHT = 48

    IDLE_FRAMES = tuple(range(0, 8))            # arte 1-8
    WALK_START_FRAMES = tuple(range(8, 22))     # arte 9-22
    WALK_LOOP_FRAMES = tuple(range(12, 22))     # arte 13-22
    JUMP_UP_FRAMES = tuple(range(22, 28))       # arte 23-28
    JUMP_FALL_FRAMES = (27, 28)                 # arte 28-29
    LAND_FRAMES = tuple(range(29, 34))          # arte 30-34
    DASH_FRAMES = tuple(range(34, 42))          # arte 35-42
    SWIM_START_FRAMES = tuple(range(42, 52))    # arte 43-52
    SWIM_LOOP_FRAMES = tuple(range(47, 52))     # arte 48-52
    ATTACK_FRAMES = tuple(range(52, 68))        # arte 53-68
    HURT_FRAMES = tuple(range(68, 74))          # arte 69-74
    DEATH_FRAMES = tuple(range(74, 82))         # arte 75-82
    RANGED_FRAMES = tuple(range(82, 88))        # arte 83-88
    SWIM_IDLE_FRAMES = tuple(range(88, 96))     # arte 89-96
    REFERENCE_FRAME = 96                        # arte 97, nunca exibido

    IDLE_FRAME_TICKS = 7
    WALK_FRAME_TICKS = 5
    JUMP_FRAME_TICKS = 3
    FALL_FRAME_TICKS = 6
    LAND_FRAME_TICKS = 4
    SWIM_FRAME_TICKS = 6
    HURT_FRAME_TICKS = 4
    DEATH_FRAME_TICKS = 6
    RANGED_FRAME_TICKS = 4

    # Zona "no ar" (quase parada verticalmente) em vez de só subindo/caindo
    # — abaixo desse módulo de vy ela tá perto do ápice do pulo.
    JUMP_APEX_VY_THRESHOLD = 1.5

    def __init__(self):
        self.frames = self._load_frames()
        self.facing_right = True
        self.frame = 0
        self.animation = 0
        self.reset(100, 602)

    @staticmethod
    def _load_frames():
        """Recorta os 97 quadros 48x48 sem redimensionar o pixel art."""
        sheet_path = ASSET_DIR / "player" / "player_sheet.png"
        sheet = pygame.image.load(sheet_path).convert_alpha()
        expected_width = Player.FRAME_COUNT * Player.SHEET_FRAME_WIDTH
        if sheet.get_size() != (expected_width, Player.SHEET_FRAME_HEIGHT):
            raise ValueError(
                "player_sheet.png deve ter "
                f"{expected_width}x{Player.SHEET_FRAME_HEIGHT}px; "
                f"recebido {sheet.get_width()}x{sheet.get_height()}px"
            )
        frames = []
        for frame in range(Player.FRAME_COUNT):
            frames.append(sheet.subsurface(
                pygame.Rect(
                    frame * Player.SHEET_FRAME_WIDTH, 0,
                    Player.SHEET_FRAME_WIDTH, Player.SHEET_FRAME_HEIGHT,
                )
            ).copy())
        return frames

    @property
    def rect(self):
        return pygame.Rect(
            round(self.x) + PLAYER_HITBOX_OFFSET_X,
            round(self.y),
            PLAYER_HITBOX_WIDTH,
            PLAYER_HEIGHT,
        )

    @property
    def dashing(self):
        return self.dash_timer > 0

    def reset(self, x, y):
        """Restaura apenas o estado transitório da personagem."""
        self.x, self.y = x, y
        self.vx = self.vy = 0
        # Atualizado de fora por Game.move_player logo antes de animate()
        # rodar (ver comentário lá) — usado só pra decidir entre os 3
        # frames de pulo e o idle/andar, então começa "no chão" por padrão.
        self.grounded = True
        self.coyote_time = self.jump_buffer = 0
        self.dash_timer = self.dash_cooldown = 0
        self.dash_direction = 1
        # Natação: Game.move_player() atualiza `swimming` a cada quadro
        # (colisão com Level.water_zones); `up_held` reflete a tecla de
        # subir sendo segurada (não é um pulso único como o jump_buffer).
        self.swimming = False
        self.up_held = False
        self.oxygen = self.OXYGEN_MAX_FRAMES
        self.animation = 0
        self.frame = self.IDLE_FRAMES[0]
        self.idle_tick = 0
        self.walk_tick = 0
        self.was_walking = False
        self.jump_tick = 0
        self.fall_tick = 0
        self.landing_tick = None
        self.swim_phase = None
        self.swim_tick = 0
        self.hurt_timer = 0
        self.ranged_timer = 0

    def update_abilities(self):
        """Atualiza recarga e duração do dash a cada quadro."""
        self.dash_cooldown = max(0, self.dash_cooldown - 1)
        if self.dash_timer:
            self.dash_timer -= 1
            self.vx = self.dash_direction * self.DASH_SPEED

    def start_dash(self):
        if self.dash_cooldown:
            return False
        self.dash_direction = 1 if self.facing_right else -1
        self.dash_timer = self.DASH_DURATION
        self.dash_cooldown = self.DASH_COOLDOWN
        self.vx = self.dash_direction * self.DASH_SPEED
        return True

    def cancel_dash(self):
        self.dash_timer = 0

    def read_controls(self, keyboard, movement_locked=False):
        if movement_locked:
            self.vx = 0
            self.up_held = False
            self.jump_buffer = 0
            return

        direction = int(keyboard.right or keyboard.d) - int(keyboard.left or keyboard.a)
        up_down = keyboard.space or keyboard.up or keyboard.w
        self.up_held = up_down

        if self.dashing and not self.swimming:
            # O dash conserva a direção escolhida até terminar.
            self.vx = self.dash_direction * self.DASH_SPEED
            return

        speed_limit = self.SWIM_SPEED if self.swimming else MOVE_SPEED
        self._update_horizontal_speed(direction, speed_limit)
        if direction:
            self.facing_right = direction > 0

        if self.swimming:
            # Debaixo d'água não há pulo por impulso: subir é contínuo
            # enquanto a tecla é segurada (ver apply_swim_gravity).
            self.jump_buffer = 0
            return
        if up_down:
            self.jump_buffer = self.JUMP_BUFFER_DURATION
        self.jump_buffer = max(0, self.jump_buffer - 1)

    def _update_horizontal_speed(self, direction, speed_limit=MOVE_SPEED):
        target_speed = direction * speed_limit
        if direction:
            self.vx = self._approach(self.vx, target_speed, self.ACCELERATION)
        elif self.vx > 0:
            self.vx = max(0, self.vx - self.DECELERATION)
        elif self.vx < 0:
            self.vx = min(0, self.vx + self.DECELERATION)

    @staticmethod
    def _approach(current, target, step):
        if current < target:
            return min(target, current + step)
        if current > target:
            return max(target, current - step)
        return current

    def apply_gravity(self):
        self.vy = min(self.vy + GRAVITY, MAX_FALL_SPEED)

    def apply_swim_gravity(self):
        """Debaixo d'água a gravidade normal dá lugar a um afundar suave;
        segurar a tecla de subir (up_held) inverte isso em uma subida
        contínua, em vez do impulso único de um pulo."""
        if self.up_held:
            self.vy = max(self.SWIM_MAX_RISE, self.vy - self.SWIM_RISE_ACCEL)
        else:
            self.vy = min(self.SWIM_MAX_SINK, self.vy + self.SWIM_SINK_GRAVITY)

    @property
    def head_rect(self):
        """Fatia fina no topo do hitbox: usada para checar se a cabeça está
        para fora d'água (respirando) ou submersa (consumindo oxigênio)."""
        body = self.rect
        return pygame.Rect(body.x, round(self.y), body.width, self.HEAD_HEIGHT)

    def try_jump(self):
        if not self.jump_buffer:
            return False
        if self.coyote_time:
            self.vy, self.coyote_time, self.jump_buffer = JUMP_SPEED, 0, 0
            self.jump_tick = 0
            self.fall_tick = 0
            self.landing_tick = None
            return True
        return False

    def animate(self):
        """Escolhe a pose base; ataque e morte têm prioridade em Game."""
        self.animation += 1

        if self.hurt_timer > 0:
            self.frame = self._timed_frame(
                self.HURT_FRAMES,
                len(self.HURT_FRAMES) * self.HURT_FRAME_TICKS - self.hurt_timer,
                self.HURT_FRAME_TICKS,
            )
            self.hurt_timer -= 1
            return

        if self.ranged_timer > 0:
            self.frame = self._timed_frame(
                self.RANGED_FRAMES,
                len(self.RANGED_FRAMES) * self.RANGED_FRAME_TICKS - self.ranged_timer,
                self.RANGED_FRAME_TICKS,
            )
            self.ranged_timer -= 1
            return

        if self.dashing and not self.swimming:
            dash_index = min(len(self.DASH_FRAMES) - 1, self.DASH_DURATION - self.dash_timer)
            self.frame = self.DASH_FRAMES[dash_index]
            self._reset_ground_animation()
            return

        if self.swimming:
            self._animate_swimming()
            self._reset_ground_animation()
            return
        self.swim_phase = None
        self.swim_tick = 0

        if not self.grounded:
            if self.vy < -self.JUMP_APEX_VY_THRESHOLD:
                self.frame = self._timed_frame(
                    self.JUMP_UP_FRAMES, self.jump_tick, self.JUMP_FRAME_TICKS
                )
                self.jump_tick += 1
            else:
                self.frame = self._loop_frame(
                    self.JUMP_FALL_FRAMES, self.fall_tick, self.FALL_FRAME_TICKS
                )
                self.fall_tick += 1
            self.landing_tick = None
            self._reset_ground_animation()
        elif self.landing_tick is not None:
            self.frame = self._timed_frame(
                self.LAND_FRAMES, self.landing_tick, self.LAND_FRAME_TICKS
            )
            self.landing_tick += 1
            if self.landing_tick >= len(self.LAND_FRAMES) * self.LAND_FRAME_TICKS:
                self.landing_tick = None
            self._reset_ground_animation()
        elif abs(self.vx) > 0.2:
            if not self.was_walking:
                self.walk_tick = 0
            intro_duration = len(self.WALK_START_FRAMES) * self.WALK_FRAME_TICKS
            if self.walk_tick < intro_duration:
                self.frame = self._timed_frame(
                    self.WALK_START_FRAMES, self.walk_tick, self.WALK_FRAME_TICKS
                )
            else:
                self.frame = self._loop_frame(
                    self.WALK_LOOP_FRAMES,
                    self.walk_tick - intro_duration,
                    self.WALK_FRAME_TICKS,
                )
            self.walk_tick += 1
            self.was_walking = True
            self.idle_tick = 0
        else:
            self.was_walking = False
            self.walk_tick = 0
            self.frame = self._loop_frame(
                self.IDLE_FRAMES, self.idle_tick, self.IDLE_FRAME_TICKS
            )
            self.idle_tick += 1

    @staticmethod
    def _timed_frame(frames, tick, ticks_per_frame):
        index = min(len(frames) - 1, max(0, tick) // ticks_per_frame)
        return frames[index]

    @staticmethod
    def _loop_frame(frames, tick, ticks_per_frame):
        return frames[(max(0, tick) // ticks_per_frame) % len(frames)]

    def _reset_ground_animation(self):
        self.was_walking = False
        self.walk_tick = 0
        self.idle_tick = 0

    def _animate_swimming(self):
        moving = abs(self.vx) > 0.2 or self.up_held
        if self.swim_phase is None:
            self.swim_phase = "start" if moving else "idle"
            self.swim_tick = 0

        if moving and self.swim_phase not in ("start", "loop"):
            self.swim_phase = "start"
            self.swim_tick = 0
        elif not moving and self.swim_phase in ("start", "loop"):
            self.swim_phase = "stop"
            self.swim_tick = 0

        if self.swim_phase == "start":
            self.frame = self._timed_frame(
                self.SWIM_START_FRAMES, self.swim_tick, self.SWIM_FRAME_TICKS
            )
            self.swim_tick += 1
            if self.swim_tick >= len(self.SWIM_START_FRAMES) * self.SWIM_FRAME_TICKS:
                self.swim_phase = "loop"
                self.swim_tick = 0
        elif self.swim_phase == "loop":
            self.frame = self._loop_frame(
                self.SWIM_LOOP_FRAMES, self.swim_tick, self.SWIM_FRAME_TICKS
            )
            self.swim_tick += 1
        elif self.swim_phase == "stop":
            reverse_frames = self.SWIM_START_FRAMES[::-1]
            self.frame = self._timed_frame(
                reverse_frames, self.swim_tick, self.SWIM_FRAME_TICKS
            )
            self.swim_tick += 1
            if self.swim_tick >= len(reverse_frames) * self.SWIM_FRAME_TICKS:
                self.swim_phase = "idle"
                self.swim_tick = 0
        else:
            self.frame = self._loop_frame(
                self.SWIM_IDLE_FRAMES, self.swim_tick, self.SWIM_FRAME_TICKS
            )
            self.swim_tick += 1

    def start_landing(self):
        self.landing_tick = 0

    def start_hurt(self):
        self.hurt_timer = len(self.HURT_FRAMES) * self.HURT_FRAME_TICKS
        self.ranged_timer = 0
        self.frame = self.HURT_FRAMES[0]

    def start_ranged_attack(self):
        if self.hurt_timer <= 0:
            self.ranged_timer = len(self.RANGED_FRAMES) * self.RANGED_FRAME_TICKS

    def lock_for_attack(self):
        """Trava apenas o controle; a gravidade continua agindo no ar."""
        self.vx = 0
        self.up_held = False
        self.jump_buffer = 0
        self.cancel_dash()

    def draw(self, surface, camera_x, camera_y):
        """Sem contorno gerado por máscara (a arte nova já vem com contorno
        desenhado à mão — ver player_sheet.png/LEIA-ME correspondente —,
        dobrar por cima ficaria com uma borda grossa/errada)."""
        image = self.frames[self.frame]
        if not self.facing_right:
            # Espelho cacheado (sprites.flipped): antes era um Surface novo por
            # quadro só pra virar a Lia pra esquerda.
            image = flipped(image)

        draw_x = self.x - camera_x + (PLAYER_WIDTH - image.get_width()) / 2
        draw_y = self.y - camera_y + (PLAYER_HEIGHT - image.get_height())
        surface.blit(image, (round(draw_x), round(draw_y)))
