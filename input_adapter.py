"""Tela lógica e roteamento de entrada compartilhados por desktop e web."""

import pygame

from game_data import PAUSED, SETTINGS, TITLE
from settings import HEIGHT, WIDTH


class LogicalScreen:
    """Superfície de resolução fixa em que Game desenha."""

    def __init__(self):
        self.surface = pygame.Surface((WIDTH, HEIGHT)).convert()


class KeyboardState:
    """Substitui o objeto `keyboard` que o pgzero injeta automaticamente.
    Mesmos nomes de atributo que game.py/player.py já esperam (e.RETURN,
    space, f, q, r, left/right/up/down, a/d/w, k_1/k_2/k_3 — ver
    game._read_input, game._read_item_use, player._read_horizontal/
    _read_jump)."""

    _KEYS = {
        "left": pygame.K_LEFT, "right": pygame.K_RIGHT, "up": pygame.K_UP,
        "down": pygame.K_DOWN, "space": pygame.K_SPACE,
        "a": pygame.K_a, "d": pygame.K_d, "w": pygame.K_w,
        "e": pygame.K_e, "f": pygame.K_f, "q": pygame.K_q, "r": pygame.K_r,
        "RETURN": pygame.K_RETURN, "escape": pygame.K_ESCAPE,
        "k_1": pygame.K_1, "k_2": pygame.K_2, "k_3": pygame.K_3,
    }

    def __init__(self):
        for name in self._KEYS:
            setattr(self, name, False)

    def refresh(self, pressed):
        for name, code in self._KEYS.items():
            setattr(self, name, bool(pressed[code]))


def mouse_down(game, pos):
    """Recebe apenas o botão principal, já filtrado pela plataforma."""
    if game.minigame.active:
        game.handle_minigame_click(pos)
    elif game.state in (TITLE, SETTINGS, PAUSED):
        game.handle_menu_click(pos)
    else:
        game.request_mouse_attack()


def mouse_move(game, pos):
    if game.minigame.active:
        game.handle_minigame_drag(pos)
    elif game.state in (SETTINGS, PAUSED):
        game.handle_menu_drag(pos)


def mouse_up(game, pos):
    if game.minigame.active:
        game.handle_minigame_release(pos)
    else:
        game.handle_menu_release()
