"""Ponto de entrada do Pygame Zero.

Execute com pgzrun main.py. A janela abre em tela cheia (FULLSCREEN=True)
na resolução lógica do próprio jogo (GAME_WIDTH x GAME_HEIGHT, ver
settings.py) — o Windows/driver de vídeo escala isso pra caber na tela de
verdade sozinho, sem o jogo precisar descobrir a resolução do monitor.

IMPORTANTE: a janela é criada UMA VEZ SÓ, pelo próprio Pygame Zero, a
partir de WIDTH/HEIGHT/FULLSCREEN definidos aqui embaixo (é assim que o
pgzero sabe pra abrir direto em tela cheia). Chamar pygame.display.set_mode
de novo depois, na mão (como uma versão anterior deste arquivo fazia
dentro de update(), tentando recriar a janela em SCALED todo quadro) é o
que causava o "pygame.error: failed to create renderer" — a maioria dos
drivers de vídeo não gosta de recriar a janela/renderer depois que ela já
existe, ainda mais toda vez que o loop passa por ali.

WIDTH/HEIGHT usam a resolução lógica do jogo (não a do monitor): tentar
detectar a resolução real via pygame.display.Info() antes do Pygame Zero
criar a janela se mostrou instável (abriu uma janela minúscula em vez de
tela cheia) — trocar pra um modo exclusivo de tela cheia numa resolução
"estranha" costuma ser o que dá errado. Ficar na resolução do próprio jogo
é o modo mais confiável de abrir em tela cheia sem esse risco.
"""

import pygame
import pgzrun

from game import Game
from settings import HEIGHT as GAME_HEIGHT, TITLE, WIDTH as GAME_WIDTH

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
