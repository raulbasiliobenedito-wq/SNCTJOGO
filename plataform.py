import math

import pygame


class Platform:
    """Plataforma fixa ou móvel. A plataforma leva Lia quando ela está sobre ela."""

    HEIGHT = 32
    TILE_SIZE = 32

    def __init__(self, x, y, width, image_index=0, travel=0, period=0, axis="x"):
        self.x = self.base_x = x
        self.y = self.base_y = y
        self.width, self.image_index = width, image_index
        self.travel, self.period, self.axis = travel, period, axis
        self.time = self.dx = self.dy = 0

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.width, self.HEIGHT)

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
        tile_count = self.width // self.TILE_SIZE
        for tile in range(tile_count):
            image = self._tile_image(images, tile, tile_count)
            surface.blit(
                image,
                (self.x + tile * self.TILE_SIZE - camera_x, self.y - camera_y),
            )

    @staticmethod
    def _tile_image(images, tile, tile_count):
        """Escolhe ponta esquerda, miolo alternado ou ponta direita."""
        if tile == 0:
            return images[0]
        if tile == tile_count - 1:
            return images[3]
        return images[1 + (tile - 1) % 2]
