from functools import lru_cache

import pygame

from settings import FONT_PATH, WIDTH


ABILITY_PANEL_WIDTH = 232
ABILITY_PANEL_HEIGHT = 142
ABILITY_PANEL_MARGIN = 20


@lru_cache(maxsize=None)
def get_font(size, bold):
    """Carrega cada tamanho da fonte apenas uma vez."""
    font = pygame.font.Font(str(FONT_PATH), size)
    font.set_bold(bold)
    return font


def draw_text(surface, value, position, size=28, color="white", center=False):
    font = get_font(size, size >= 30)
    image = font.render(value, True, pygame.Color(color))
    rect = image.get_rect(center=position) if center else image.get_rect(topleft=position)
    surface.blit(image, rect)


def draw_hud(
    surface,
    level_name,
    lives,
    found,
    total,
    message,
    message_timer,
    microscope_parts=0,
    microscope_total=0,
    microscope_assembled=False,
    oxygen_ratio=None,
):
    """Desenha informações persistentes da fase e a mensagem temporária."""
    draw_text(surface, level_name, (24, 20), 27)
    draw_text(surface, "Vidas: " + "♥ " * lives, (24, 55), 25, "#ff6379")
    draw_text(surface, f"Pesquisa: {found}/{total}", (24, 88), 22, "#ffe47a")

    if microscope_total:
        status = "montado" if microscope_assembled else f"{microscope_parts}/{microscope_total}"
        draw_text(surface, f"Microscópio: {status}", (24, 121), 19, "#9de3bb")
    if oxygen_ratio is not None:
        _draw_oxygen_bar(surface, oxygen_ratio)
    if message_timer:
        _draw_message(surface, message)


def _draw_oxygen_bar(surface, ratio):
    """Barra de fôlego, exibida enquanto a Lia está na água (ou logo após
    sair). Fica vermelha nos últimos instantes pra avisar do afogamento."""
    x, y, width, height = 24, 150, 220, 16
    pygame.draw.rect(surface, (12, 25, 43), (x - 3, y - 3, width + 6, height + 6), border_radius=8)
    color = "#5fc9ff" if ratio > 0.3 else "#ff5c5c"
    pygame.draw.rect(surface, (30, 45, 66), (x, y, width, height), border_radius=6)
    pygame.draw.rect(surface, pygame.Color(color), (x, y, int(width * max(0, ratio)), height), border_radius=6)
    draw_text(surface, "FÔLEGO", (x + width // 2, y + 8), 12, "#0b1420", True)


def _draw_message(surface, message):
    left = 220
    box_width = WIDTH - 440
    pygame.draw.rect(
        surface,
        (17, 34, 58),
        (left, 18, box_width, 48),
        border_radius=12,
    )
    draw_text(surface, message, (WIDTH // 2, 42), 19, "white", True)


def draw_ability_ui(
    surface,
    dash_remaining,
    dash_total,
    attack_remaining,
    attack_total,
    wall_jump_ready,
):
    """Desenha o painel de habilidades, com rótulos e barras de recarga."""
    x = WIDTH - ABILITY_PANEL_WIDTH - ABILITY_PANEL_MARGIN
    y = 22
    pygame.draw.rect(
        surface,
        (12, 25, 43),
        (x, y, ABILITY_PANEL_WIDTH, ABILITY_PANEL_HEIGHT),
        border_radius=10,
    )
    pygame.draw.rect(
        surface,
        (101, 184, 228),
        (x, y, ABILITY_PANEL_WIDTH, ABILITY_PANEL_HEIGHT),
        2,
        border_radius=10,
    )
    draw_text(surface, "HABILIDADES", (x + ABILITY_PANEL_WIDTH // 2, y + 10), 14, "#d9f3ff", True)

    _draw_cooldown_row(
        surface, x, "DASH", "Q", y + 34, dash_remaining, dash_total, (83, 211, 255)
    )
    _draw_cooldown_row(
        surface, x, "ATAQUE", "F", y + 66, attack_remaining, attack_total, (255, 186, 78)
    )

    wall_color = "#9cf0ad" if wall_jump_ready else "#7e8a98"
    wall_state = "PRONTO" if wall_jump_ready else "USADO"
    draw_text(surface, "PULO PAREDE", (x + 12, y + 102), 13, "#ffffff")
    draw_text(surface, wall_state, (x + ABILITY_PANEL_WIDTH - 42, y + 108), 11, wall_color, True)


def _draw_cooldown_row(surface, x, label, key, top, remaining, total, color):
    ratio = 1 - remaining / total if total else 1
    draw_text(surface, f"[{key}] {label}", (x + 12, top), 13, "#ffffff")
    bar = pygame.Rect(x + 12, top + 17, ABILITY_PANEL_WIDTH - 24, 8)
    pygame.draw.rect(surface, (43, 58, 77), bar, border_radius=4)
    pygame.draw.rect(
        surface,
        color,
        (bar.x, bar.y, int(bar.width * ratio), bar.height),
        border_radius=4,
    )
