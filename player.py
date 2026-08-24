import pygame

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

    DASH_SPEED = 14.0
    DASH_DURATION = 10
    DASH_COOLDOWN = 90
    WALL_SLIDE_SPEED = 3.2
    WALL_JUMP_SPEED = -14.0
    WALL_JUMP_PUSH = 9.0

    # --- Mecânica de natação (água da Fase 3) ---
    SWIM_SPEED = 2.6
    SWIM_SINK_GRAVITY = 0.16
    SWIM_MAX_SINK = 2.0
    SWIM_RISE_ACCEL = 0.55
    SWIM_MAX_RISE = -2.5
    # Fôlego: 7 segundos debaixo d'água (com a cabeça submersa) antes de
    # começar a se afogar. Respirar (cabeça fora d'água) recarrega mais
    # rápido do que consome, pra não punir mergulhos rápidos.
    OXYGEN_MAX_FRAMES = 7 * FPS
    OXYGEN_DRAIN_PER_FRAME = 1
    OXYGEN_REFILL_PER_FRAME = 3
    HEAD_HEIGHT = 10

    ACCELERATION = 0.55
    DECELERATION = 0.70
    JUMP_BUFFER_DURATION = 7

    # Índices na sheet nova (14 quadros, ver player_sheet.png):
    # 0 idle · 1-4 andar · 5-7 pulo (subindo/no ar/caindo) · 8-11 combo de
    # ataque corpo a corpo (Game cuida de exibir esses, ver
    # Game._apply_attack_frame) · 12-13 morte (ver Game._apply_death_frame).
    FRAME_COUNT = 14
    # O arquivo em disco vem 64x96 por quadro — o dobro do tamanho final em
    # jogo (PLAYER_WIDTH/HEIGHT, ver settings.py). _load_frames recorta
    # nesse tamanho e reduz pela metade, porque em tela ela ficava enorme
    # (pedido do Raul) sem precisar mudar resolução nem hitbox.
    SHEET_FRAME_WIDTH = 64
    SHEET_FRAME_HEIGHT = 96
    IDLE_FRAME = 0
    WALK_FRAMES = (1, 2, 3, 4)
    JUMP_RISE_FRAME = 5
    JUMP_APEX_FRAME = 6
    JUMP_FALL_FRAME = 7
    # Zona "no ar" (quase parada verticalmente) em vez de só subindo/caindo
    # — abaixo desse módulo de vy ela tá perto do ápice do pulo.
    JUMP_APEX_VY_THRESHOLD = 1.5
    # Índice = combo_count - 1 (Game._apply_attack_frame); 4 quadros, o
    # último (combo_count==4) é o golpe de finalização com dano em dobro.
    ATTACK_FRAMES = (8, 9, 10, 11)
    # Índice = quantos quadros já se passaram desde a morte // (duração /
    # len) (Game._apply_death_frame).
    DEATH_FRAMES = (12, 13)

    def __init__(self):
        self.frames = self._load_frames()
        self.facing_right = True
        self.frame = 0
        self.animation = 0
        self.reset(100, 602)

    @staticmethod
    def _load_frames():
        """Recorta cada quadro no tamanho real do arquivo (64x96) e reduz
        pela metade pro tamanho final em jogo (PLAYER_WIDTH/HEIGHT,
        32x48) — pygame.transform.scale (sem suavizar) mantém a arte
        chapada, sem borrar; como é exatamente metade, não sobra pixel
        quebrado."""
        sheet_path = ASSET_DIR / "player" / "player_sheet.png"
        sheet = pygame.image.load(sheet_path).convert_alpha()
        frames = []
        for frame in range(Player.FRAME_COUNT):
            raw = sheet.subsurface(
                pygame.Rect(
                    frame * Player.SHEET_FRAME_WIDTH, 0,
                    Player.SHEET_FRAME_WIDTH, Player.SHEET_FRAME_HEIGHT,
                )
            )
            frames.append(pygame.transform.scale(raw, (PLAYER_WIDTH, PLAYER_HEIGHT)))
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
        self.wall_side = 0
        self.wall_jump_used = False
        # Tolerância (em quadros) após soltar o encosto na parede em que o
        # wall jump ainda conta — evita que soltar a direção pra preparar o
        # pulo derrube o "grude" um quadro antes do pulo registrar.
        self.wall_coyote_time = 0
        self.last_wall_side = 0
        # Natação: Game.move_player() atualiza `swimming` a cada quadro
        # (colisão com Level.water_zones); `up_held` reflete a tecla de
        # subir sendo segurada (não é um pulso único como o jump_buffer).
        self.swimming = False
        self.up_held = False
        self.oxygen = self.OXYGEN_MAX_FRAMES

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

    def read_controls(self, keyboard):
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
            return True
        if self.wall_coyote_time and not self.wall_jump_used:
            # Um salto por parede antes de tocar o chão novamente. Usa
            # last_wall_side (persiste durante a tolerância) em vez de
            # wall_side (que já pode ter voltado a 0 nesse quadro).
            self.vy = self.WALL_JUMP_SPEED
            self.vx = -self.last_wall_side * self.WALL_JUMP_PUSH
            self.facing_right = self.vx > 0
            self.wall_jump_used = True
            self.jump_buffer = 0
            self.wall_coyote_time = 0
            self.cancel_dash()
            return True
        return False

    def animate(self):
        """Sobreposto por fora quando ela ataca ou morre (ver
        Game._apply_attack_frame/_apply_death_frame, chamados depois desse
        método) — aqui só cobre parada/andando/pulando."""
        self.animation += 1
        if not self.grounded:
            # Pulo de 3 fases (pedido do Raul): subindo rápido, "flutuando"
            # perto do ápice, e caindo — sem o `grounded` isso ia disparar
            # também parada no chão, já que vy fica pertinho de 0 ali também
            # (ver Player.grounded, atualizado por Game.move_player).
            if self.vy < -self.JUMP_APEX_VY_THRESHOLD:
                self.frame = self.JUMP_RISE_FRAME
            elif self.vy > self.JUMP_APEX_VY_THRESHOLD:
                self.frame = self.JUMP_FALL_FRAME
            else:
                self.frame = self.JUMP_APEX_FRAME
        elif self.vx:
            self.frame = 1 + (self.animation // 7) % 4
        else:
            self.frame = self.IDLE_FRAME

    def draw(self, surface, camera_x, camera_y):
        """Sem contorno gerado por máscara (a arte nova já vem com contorno
        desenhado à mão — ver player_sheet.png/LEIA-ME correspondente —,
        dobrar por cima ficaria com uma borda grossa/errada)."""
        image = self.frames[self.frame]
        if not self.facing_right:
            image = pygame.transform.flip(image, True, False)

        draw_x = self.x - camera_x
        draw_y = self.y - camera_y
        surface.blit(image, (draw_x, draw_y))
