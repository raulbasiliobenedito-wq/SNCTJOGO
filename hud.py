from functools import lru_cache

import pygame

from settings import FONT_PATH, FONT_SCALE, HEIGHT, WIDTH


ABILITY_PANEL_WIDTH = 232
# +34 pra caber a linha do ataque à distância (ver draw_ability_ui) sem
# espremer o pulo de parede — o painel cresce um pouco mesmo antes do
# ataque desbloquear, já que a linha reserva espaço desde o início.
ABILITY_PANEL_HEIGHT = 176
ABILITY_PANEL_MARGIN = 20


@lru_cache(maxsize=None)
def get_font(size, bold):
    """Carrega cada tamanho da fonte apenas uma vez. `size` é sempre o
    tamanho "lógico" pedido pelo código (ex.: 17 numa fala de diálogo) —
    FONT_SCALE (settings.py) amplia isso na hora de carregar a fonte de
    verdade. dialogue.py também passa por aqui pra medir quebra de linha
    (ver DialogueBox), então HUD e diálogo sempre escalam juntos e em
    sincronia — mudar só o FONT_SCALE redimensiona o jogo inteiro de uma vez."""
    font = pygame.font.Font(str(FONT_PATH), round(size * FONT_SCALE))
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
    shield=0,
):
    """Desenha informações persistentes da fase e a mensagem temporária."""
    draw_text(surface, level_name, (24, 20), 27)
    hearts = "♥ " * lives
    draw_text(surface, "Vidas: " + hearts, (24, 55), 25, "#ff6379")
    if shield:
        shield_x = 24 + get_font(25, True).size("Vidas: " + hearts)[0] + 14
        draw_text(surface, "◆ " * shield, (shield_x, 55), 25, "#7cd6ff")
    draw_text(surface, f"Pesquisa: {found}/{total}", (24, 88), 22, "#ffe47a")

    if microscope_total:
        status = "montado" if microscope_assembled else f"{microscope_parts}/{microscope_total}"
        draw_text(surface, f"Microscópio: {status}", (24, 121), 19, "#9de3bb")
    if oxygen_ratio is not None:
        _draw_oxygen_bar(surface, oxygen_ratio)
    if message_timer:
        _draw_message(surface, message)


ITEM_KEY_LABELS = {"gororoba": "1", "carcaca_robo": "2", "dark_crystal": "3"}


def draw_inventory(surface, inventory, item_icons, item_order):
    """Barra de itens no canto inferior esquerdo: um slot por tipo já
    coletado (consumíveis mostram a tecla de uso; itens de pesquisa não têm
    tecla — eles só destravam o avanço de fase ao serem obtidos)."""
    owned = [key for key in item_order if inventory.get(key, 0) > 0]
    if not owned:
        return
    slot = 46
    gap = 8
    x = 24
    y = HEIGHT - 90
    for key in owned:
        icon = item_icons.get(key)
        pygame.draw.rect(surface, (12, 25, 43), (x, y, slot, slot), border_radius=8)
        pygame.draw.rect(surface, (74, 96, 122), (x, y, slot, slot), 2, border_radius=8)
        if icon:
            surface.blit(icon, (x + slot // 2 - icon.get_width() // 2, y + slot // 2 - icon.get_height() // 2 - 4))
        count = inventory.get(key, 0)
        draw_text(surface, f"x{count}", (x + slot - 4, y + slot - 6), 13, "#ffffff", False)
        key_label = ITEM_KEY_LABELS.get(key)
        if key_label:
            draw_text(surface, f"[{key_label}]", (x + slot // 2, y - 12), 12, "#ffe47a", True)
        x += slot + gap


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
    ranged_unlocked,
    ranged_remaining,
    ranged_total,
):
    """Desenha o painel de habilidades, com rótulos e barras de recarga.
    A linha de ataque à distância (ver game.RANGED_*) sempre reserva o
    espaço, mesmo antes de desbloquear (Fase 1 completa) — assim ela não
    "pula" pra dentro do painel de repente quando desbloqueia; só troca de
    "BLOQUEADO" pra uma barra de recarga normal."""
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

    if ranged_unlocked:
        _draw_cooldown_row(
            surface, x, "DISTÂNCIA", "R", y + 98, ranged_remaining, ranged_total, (95, 201, 255)
        )
    else:
        draw_text(surface, "[R] DISTÂNCIA", (x + 12, y + 102), 13, "#5a6472")
        draw_text(surface, "BLOQUEADO", (x + ABILITY_PANEL_WIDTH - 82, y + 102), 11, "#5a6472")

    wall_color = "#9cf0ad" if wall_jump_ready else "#7e8a98"
    wall_state = "PRONTO" if wall_jump_ready else "USADO"
    draw_text(surface, "PULO PAREDE", (x + 12, y + 134), 13, "#ffffff")
    draw_text(surface, wall_state, (x + ABILITY_PANEL_WIDTH - 42, y + 140), 11, wall_color, True)


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
