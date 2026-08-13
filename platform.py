import math
import pygame


class Platform:
    """Plataforma fixa ou móvel. A plataforma leva Lia quando ela está sobre ela."""
    def __init__(self, x, y, width, image_index=0, travel=0, period=0, axis="x"):
        self.x = self.base_x = x
        self.y = self.base_y = y
        self.width, self.image_index = width, image_index
        self.travel, self.period, self.axis = travel, period, axis
        self.time = self.dx = self.dy = 0

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.width, 32)

    def update(self):
        old_x, old_y = self.x, self.y
        if self.period:
            self.time += 1
            movement = math.sin(self.time * math.tau / self.period) * self.travel / 2
            if self.axis == "x":
                self.x = self.base_x + movement
            else:
                self.y = self.base_y + movement
        self.dx, self.dy = self.x - old_x, self.y - old_y

    def draw(self, surface, camera_x, camera_y, images):
        """Monta a plataforma: ponta esquerda, miolo alternado e ponta direita."""
        tile_count = self.width // 32
        for tile in range(tile_count):
            if tile == 0:
                image = images[0]              # platform1: extremidade esquerda
            elif tile == tile_count - 1:
                image = images[3]              # platform4: extremidade direita
            else:
                image = images[1 + ((tile - 1) % 2)] # platform2 e platform3 alternados no centro
            surface.blit(image, (self.x + tile * 32 - camera_x, self.y - camera_y))
