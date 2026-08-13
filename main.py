"""Execute este jogo com: pgzrun main.py."""
import pygame
import pgzrun
from game import Game
from settings import HEIGHT as GAME_HEIGHT, TITLE, WIDTH as GAME_WIDTH

# Resolução de exibição. Em um monitor Full HD, ocupa a tela inteira;
# a lógica continua usando o canvas interno de 1600x900.
WIDTH, HEIGHT = 1600, 900
FULLSCREEN = True


class LogicalScreen:
    """Adaptador para o Game desenhar em uma superfície interna fixa."""
    def __init__(self):
        self.surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT)).convert()


game = Game()
logical_screen = LogicalScreen()


def update():
    game.update(keyboard)


def draw():
    game.draw(logical_screen)
    # 1600x900 -> 1920x1080 preserva exatamente a proporção 16:9.
    enlarged = pygame.transform.smoothscale(logical_screen.surface, (WIDTH, HEIGHT))
    screen.surface.blit(enlarged, (0, 0))


def on_mouse_down(pos, button):
    if button == mouse.LEFT:
        game.request_mouse_attack()


pgzrun.go()
