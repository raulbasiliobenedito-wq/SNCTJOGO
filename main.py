"""Ponto de entrada do Pygame Zero.

Execute com pgzrun main.py. A janela abre em tela cheia, na resolução
lógica do próprio jogo (GAME_WIDTH x GAME_HEIGHT, ver settings.py) — o
Windows/driver de vídeo escala isso pra caber na tela de verdade sozinho,
sem o jogo precisar descobrir a resolução do monitor.

IMPORTANTE sobre como a tela cheia é ligada: o pgzero (o pacote em si) NÃO
tem suporte de verdade a um `FULLSCREEN = True` no módulo — é um pedido de
feature aberto no repositório deles desde 2022, nunca implementado (só
WIDTH/HEIGHT/TITLE são lidos de fato). Um `FULLSCREEN = True` aqui não
fazia nada; a janela sempre abria no modo normal.

O jeito que funciona de verdade: deixar o pgzero criar a janela do jeito
dele (como sempre fez) e, UMA ÚNICA VEZ, no primeiro quadro, trocar pra
tela cheia chamando pygame.display.set_mode(..., pygame.FULLSCREEN) de
novo e atualizando screen.surface na mão (ver _apply_fullscreen). Fazer
isso TODO quadro (uma versão antiga deste arquivo fazia isso dentro de
update(), tentando recriar a janela em SCALED a cada quadro) é o que
causava "pygame.error: failed to create renderer" — a maioria dos drivers
de vídeo não gosta de recriar a janela/renderer repetidamente. Uma vez só,
no primeiro quadro, não tem esse problema.

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


class LogicalScreen:
    """Adaptador para o Game desenhar em uma superfície interna fixa."""

    def __init__(self):
        self.surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT)).convert()


game = Game()
logical_screen = LogicalScreen()

# Ver docstring do arquivo — troca pra tela cheia uma única vez, no
# primeiro quadro (não no import, porque o `screen` que o pgzero injeta só
# existe depois que pgzrun.go() começa a rodar o laço).
_fullscreen_applied = False
# F11 alterna cheia/janela (pedido do Raul: tela cheia bloqueia print
# screen em alguns sistemas). Troca só acontece na tecla — never dentro de
# update()/draw() — pelo mesmo motivo do _apply_fullscreen acima: recriar a
# janela todo quadro é o que gerava o "failed to create renderer".
_is_fullscreen = True


def _apply_fullscreen():
    global _fullscreen_applied
    if _fullscreen_applied:
        return
    _fullscreen_applied = True
    screen.surface = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption(TITLE)


def _toggle_fullscreen():
    global _is_fullscreen
    _is_fullscreen = not _is_fullscreen
    flags = pygame.FULLSCREEN if _is_fullscreen else 0
    screen.surface = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption(TITLE)


def update(dt):
    _apply_fullscreen()
    game.update(keyboard, dt)


def draw():
    game.draw(logical_screen)
    enlarged = pygame.transform.smoothscale(logical_screen.surface, (WIDTH, HEIGHT))
    screen.surface.blit(enlarged, (0, 0))


def on_mouse_down(pos, button):
    if button == mouse.LEFT:
        game.request_mouse_attack()


def on_key_down(key):
    if key == keys.F11:
        _toggle_fullscreen()


pgzrun.go()
