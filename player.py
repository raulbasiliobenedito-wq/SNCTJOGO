import pygame

from settings import (
    ASSET_DIR,
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

    ACCELERATION = 0.55
    DECELERATION = 0.70
    JUMP_BUFFER_DURATION = 7
    OUTLINE_COLOR = (14, 23, 42, 255)
    OUTLINE_OFFSETS = (
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (1, -1), (-1, 1), (1, 1),
    )

    def __init__(self):
        self.frames = self._load_frames()
        self.outlines = [self._make_outline(frame) for frame in self.frames]
        self.facing_right = True
        self.frame = 0
        self.animation = 0
        self.reset(100, 602)

    @staticmethod
    def _load_frames():
        sheet_path = ASSET_DIR / "player" / "player_sheet.png"
        sheet = pygame.image.load(sheet_path).convert_alpha()
        return [
            sheet.subsurface(
                pygame.Rect(frame * PLAYER_WIDTH, 0, PLAYER_WIDTH, PLAYER_HEIGHT)
            )
            for frame in range(7)
        ]

    @classmethod
    def _make_outline(cls, frame):
        mask = pygame.mask.from_surface(frame)
        return mask.to_surface(
            setcolor=cls.OUTLINE_COLOR,
            unsetcolor=(0, 0, 0, 0),
        ).convert_alpha()

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
        self.coyote_time = self.jump_buffer = 0
        self.dash_timer = self.dash_cooldown = 0
        self.dash_direction = 1
        self.wall_side = 0
        self.wall_jump_used = False

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
        if self.dashing:
            # O dash conserva a direção escolhida até terminar.
            self.vx = self.dash_direction * self.DASH_SPEED
            return

        self._update_horizontal_speed(direction)
        if direction:
            self.facing_right = direction > 0
        if keyboard.space or keyboard.up or keyboard.w:
            self.jump_buffer = self.JUMP_BUFFER_DURATION
        self.jump_buffer = max(0, self.jump_buffer - 1)

    def _update_horizontal_speed(self, direction):
        target_speed = direction * MOVE_SPEED
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

    def try_jump(self):
        if not self.jump_buffer:
            return False
        if self.coyote_time:
            self.vy, self.coyote_time, self.jump_buffer = JUMP_SPEED, 0, 0
            return True
        if self.wall_side and not self.wall_jump_used:
            # Um salto por parede antes de tocar o chão novamente.
            self.vy = self.WALL_JUMP_SPEED
            self.vx = -self.wall_side * self.WALL_JUMP_PUSH
            self.facing_right = self.vx > 0
            self.wall_jump_used = True
            self.jump_buffer = 0
            self.cancel_dash()
            return True
        return False

    def animate(self):
        self.animation += 1
        if abs(self.vy) > 1:
            self.frame = 5 if self.vy < 0 else 6
        elif self.vx:
            self.frame = 1 + (self.animation // 7) % 4
        else:
            self.frame = 0

    def draw(self, surface, camera_x, camera_y):
        image = self.frames[self.frame]
        outline = self.outlines[self.frame]
        if not self.facing_right:
            image = pygame.transform.flip(image, True, False)
            outline = pygame.transform.flip(outline, True, False)

        draw_x = self.x - camera_x
        draw_y = self.y - camera_y
        for offset_x, offset_y in self.OUTLINE_OFFSETS:
            surface.blit(outline, (draw_x + offset_x, draw_y + offset_y))
        surface.blit(image, (draw_x, draw_y))
