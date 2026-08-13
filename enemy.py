import pygame


class Slime:
    """Inimigo simples que patrulha somente a plataforma onde nasceu."""
    WIDTH, HEIGHT = 52, 34
    RESPAWN_TIME = 20 * 60
    DEATH_FRAME_TIME = 4
    DEATH_FRAMES = 9

    def __init__(self, platform):
        self.platform = platform
        self.x = platform.rect.centerx - self.WIDTH // 2
        self.y = platform.rect.top - self.HEIGHT
        self.direction = 1
        self.speed = 1.15
        self.health = 2
        self.state = "walk"
        self.state_timer = 0
        self.death_frame = 0
        self.animation = 0

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.WIDTH, self.HEIGHT)

    @property
    def alive(self):
        return self.state in ("walk", "hurt")

    def update(self):
        self.animation += 1
        if self.state == "dying":
            self.state_timer -= 1
            self.death_frame = min(
                self.DEATH_FRAMES - 1,
                self.death_frame + int(self.state_timer % self.DEATH_FRAME_TIME == 0)
            )
            if self.state_timer <= 0:
                self.state, self.state_timer = "dead", self.RESPAWN_TIME
            return
        if self.state == "dead":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.health = 2
                self.state = "walk"
                self.death_frame = 0
                self.x = self.platform.rect.centerx - self.WIDTH // 2
                self.y = self.platform.rect.top - self.HEIGHT
            return
        if self.state == "hurt":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "walk"
            return
        left = self.platform.rect.left + 8
        right = self.platform.rect.right - self.WIDTH - 8
        self.x += self.speed * self.direction
        if self.x <= left or self.x >= right:
            self.x = max(left, min(self.x, right))
            self.direction *= -1
        self.y = self.platform.rect.top - self.HEIGHT

    def take_hit(self, damage=1):
        if not self.alive or self.state == "hurt":
            return False
        self.health -= damage
        if self.health <= 0:
            self.state = "dying"
            self.state_timer = self.DEATH_FRAMES * self.DEATH_FRAME_TIME
            self.death_frame = 0
        else:
            self.state, self.state_timer = "hurt", 20
        return True

    def stomp(self):
        """Pulo sobre o slime derrota-o imediatamente, como nos plataformas clássicos."""
        if not self.alive:
            return False
        self.health = 0
        self.state = "dying"
        self.state_timer = self.DEATH_FRAMES * self.DEATH_FRAME_TIME
        self.death_frame = 0
        return True

    def draw(self, surface, camera_x, camera_y, sprites):
        # Depois da animação, o slime fica fora da tela até reaparecer após 20 segundos.
        if self.state == "dead":
            return
        frames = sprites["dead" if self.state == "dying" else self.state]
        # A morte percorre os quadros uma vez; as demais animações ficam em loop.
        frame = (frames[min(self.death_frame, len(frames) - 1)] if self.state == "dying"
                 else frames[(self.animation // 8) % len(frames)])
        if self.direction < 0:
            frame = pygame.transform.flip(frame, True, False)
        draw_y = self.y - camera_y + (14 if self.state == "dying" else 2)
        surface.blit(frame, (self.x - 6 - camera_x, draw_y))
