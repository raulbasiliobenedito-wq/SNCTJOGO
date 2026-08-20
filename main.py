"""Ponto de entrada do Pygame Zero.

Execute com pgzrun main.py. A lógica usa um canvas interno para manter a
mesma proporção e a mesma jogabilidade em qualquer resolução de tela.
"""

import pygame
import pgzrun

from game import Game
from settings import HEIGHT as GAME_HEIGHT, TITLE, WIDTH as GAME_WIDTH

# 1. Mantemos a resolução lógica original de 1920x1080 para o Pygame Zero criar a base
WIDTH = GAME_WIDTH
HEIGHT = GAME_HEIGHT

# Controla se a tela cheia já foi aplicada para não repetir o comando toda hora
_fullscreen_setup_done = False


class LogicalScreen:
    """Adaptador para o Game desenhar em uma superfície interna fixa."""

    def __init__(self):
        self.surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT)).convert()


game = Game()
logical_screen = LogicalScreen()


def update(dt):
    global _fullscreen_setup_done
    
    # 2. Quando o jogo começar, forçamos o Pygame Zero a mudar para Tela Cheia Escalada
    if not _fullscreen_setup_done:
        # pygame.SCALED garante que o Pygame cuide da proporção e do clique do mouse sozinho!
        flags = pygame.FULLSCREEN | pygame.SCALED
        screen.surface = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT), flags)
        _fullscreen_setup_done = True

    # Tecla de emergência: Fecha o jogo em tela cheia se apertar ESC
    if keyboard.escape:
        pygame.quit()
        import sys
        sys.exit()

    game.update(keyboard, dt)


def draw():
    # Desenha o seu jogo normalmente no canvas lógico
    game.draw(logical_screen)
    
    # O Pygame Zero joga o canvas para a tela do computador
    screen.surface.blit(logical_screen.surface, (0, 0))


def on_mouse_down(pos, button):
    if button == mouse.LEFT:
        # Graças ao pygame.SCALED, a variável 'pos' já vem corrigida no tamanho certo!
        game.request_mouse_attack()


pgzrun.go()
