import pygame
from settings import (ASSET_DIR, GRAVITY, JUMP_SPEED, MAX_FALL_SPEED, MOVE_SPEED,
                      PLAYER_HEIGHT, PLAYER_HITBOX_OFFSET_X, PLAYER_HITBOX_WIDTH, PLAYER_WIDTH)


class Player:
    DASH_SPEED = 14.0
    DASH_DURATION = 10
    DASH_COOLDOWN = 90
    WALL_SLIDE_SPEED = 3.2
    WALL_JUMP_SPEED = -14.0
    WALL_JUMP_PUSH = 9.0

    def __init__(self):
        sheet = pygame.image.load(ASSET_DIR / "player" / "player_sheet.png").convert_alpha()
        self.frames = [sheet.subsurface(pygame.Rect(i * PLAYER_WIDTH, 0, PLAYER_WIDTH, PLAYER_HEIGHT)) for i in range(7)]
        self.outlines = []
        for frame in self.frames:
            mask = pygame.mask.from_surface(frame)
            outline = mask.to_surface(setcolor=(14, 23, 42, 255), unsetcolor=(0, 0, 0, 0)).convert_alpha()
            self.outlines.append(outline)
        self.facing_right, self.frame, self.animation = True, 0, 0
        self.reset(100, 602)

    @property
    def rect(self):
        return pygame.Rect(
            round(self.x) + PLAYER_HITBOX_OFFSET_X, round(self.y),
            PLAYER_HITBOX_WIDTH, PLAYER_HEIGHT
        )

    def reset(self, x, y):
        self.x, self.y = x, y
        self.vx = self.vy = 0
        self.coyote_time = self.jump_buffer = 0
        self.dash_timer = self.dash_cooldown = 0
        self.dash_direction = 1
        self.wall_side = 0
        self.wall_jump_used = False

    @property
    def dashing(self):
        return self.dash_timer > 0

    def update_abilities(self):
        """Atualiza recarga e duração do dash em cada quadro."""
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
        acceleration = 0.55
        deceleration = 0.70
        target_speed = direction * MOVE_SPEED
        if direction:
            # Acelera gradualmente até a velocidade máxima.
            if self.vx < target_speed:
                self.vx = min(target_speed, self.vx + acceleration)
            elif self.vx > target_speed:
                self.vx = max(target_speed, self.vx - acceleration)
        elif self.vx > 0:
            self.vx = max(0, self.vx - deceleration)
        elif self.vx < 0:
            self.vx = min(0, self.vx + deceleration)
        if direction:
            self.facing_right = direction > 0
        if keyboard.space or keyboard.up or keyboard.w:
            self.jump_buffer = 7
        self.jump_buffer = max(0, self.jump_buffer - 1)

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
        draw_x, draw_y = self.x - camera_x, self.y - camera_y
        # Contorno escuro de 1 px: mantém Lia visível em fundos claros ou escuros.
        for offset_x, offset_y in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            surface.blit(outline, (draw_x + offset_x, draw_y + offset_y))
        surface.blit(image, (draw_x, draw_y))
