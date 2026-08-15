"""Ponto de entrada do Pygame Zero.

Execute com pgzrun main.py. A lógica usa um canvas interno para manter a
mesma proporção e a mesma jogabilidade em qualquer resolução de tela.
"""

import pygame
import pgzrun

from game import Game
from settings import HEIGHT as GAME_HEIGHT, TITLE, WIDTH as GAME_WIDTH


# Resolução de exibição. A lógica continua usando o canvas interno.
WIDTH = GAME_WIDTH
HEIGHT = GAME_HEIGHT
FULLSCREEN = True


class LogicalScreen:
    """Adaptador para o Game desenhar em uma superfície interna fixa."""

    def __init__(self):
        self.surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT)).convert()


game = Game()
logical_screen = LogicalScreen()


def update(dt):
    game.update(keyboard, dt)


def draw():
    game.draw(logical_screen)
    enlarged = pygame.transform.smoothscale(logical_screen.surface, (WIDTH, HEIGHT))
    screen.surface.blit(enlarged, (0, 0))


def on_mouse_down(pos, button):
    if button == mouse.LEFT:
        game.request_mouse_attack()


pgzrun.go()
