"""Cutscene inicial: Lia e a mãe no hospital, antes da Fase 1.

Não depende de nenhuma arte nova — o quarto de hospital (gradiente, cama,
monitor cardíaco animado) é desenhado por código, e as falas usam a mesma
DialogueBox ornamentada já usada pelas cientistas-NPC (mesmo cartucho,
mesma revelação gradual de texto, mesmo "[E/ENTER para continuar]"), pra
manter o mesmo estilo visual do resto do jogo sem precisar de nenhum PNG
novo. A sprite de Lia também é reaproveitada do sheet do jogador (Player.
frames[0]), só ampliada.
"""

import math

import pygame

from settings import HEIGHT, WIDTH


def _lerp_color(start, end, t):
    return tuple(int(start[i] + (end[i] - start[i]) * t) for i in range(3))


class IntroCutscene:
    """Toca uma vez, entre a tela de título e a Fase 1: a mãe de Lia conta
    que está com câncer, e Lia decide sair atrás de respostas — as "pistas"
    que ela persegue nas três fases são, a partir daqui, literalmente isso:
    uma pesquisa por algo que possa ajudar. A frase "Todo experimento pode
    falhar. Levante-se e tente novamente" (settings.MOTIVATION, reaproveitada
    na tela de derrota) nasce aqui como algo que a própria mãe diz pra ela."""

    BEATS = (
        ("Mãe", "Lia... vem sentar aqui pertinho de mim um minutinho?"),
        (
            "Mãe",
            "Os médicos encontraram uma coisa chamada câncer no meu corpo. "
            "Vou fazer um tratamento, e vai ter dias mais difíceis pela frente.",
        ),
        ("Lia", "Isso tem cura, mãe? Tem alguma coisa que eu possa fazer?"),
        (
            "Mãe",
            "Tem gente estudando isso o tempo todo — em laboratórios, "
            "universidades, centros de pesquisa. Ninguém descobre nada sozinho.",
        ),
        (
            "Mãe",
            "Todo experimento pode falhar. Levante-se e tente de novo, minha "
            "filha — isso vale pra ciência, e vale pra vida.",
        ),
        (
            "Lia",
            "Então é isso que eu vou fazer. Vou atrás de cada pista, cada "
            "pesquisa, cada resposta que existir por aí. Por você.",
        ),
    )

    BED_COLOR = (214, 224, 236)
    BLANKET_COLOR = (110, 142, 158)
    PILLOW_COLOR = (230, 236, 244)
    MONITOR_BODY = (8, 14, 24)
    MONITOR_FRAME = (54, 66, 86)
    MONITOR_LINE = (110, 226, 196)
    CORAL_GLOW = (216, 134, 166)

    def __init__(self, dialogue_box, lia_frame):
        # Reaproveita a MESMA DialogueBox usada pelos diálogos de NPC —
        # Game.update já dá prioridade ao estado INTRO antes de checar
        # dialogue.active, então não há conflito entre os dois usos.
        self.dialogue_box = dialogue_box
        self.lia_frame = pygame.transform.scale(
            lia_frame, (lia_frame.get_width() * 3, lia_frame.get_height() * 3)
        )
        self.index = -1
        self.done = True
        self.timer = 0

    @property
    def active(self):
        return not self.done

    def start(self):
        self.index = -1
        self.done = False
        self.timer = 0
        self._advance()

    def _advance(self):
        self.index += 1
        if self.index >= len(self.BEATS):
            self.done = True
            self.dialogue_box.close()
            return
        speaker, text = self.BEATS[self.index]
        self.dialogue_box.start(speaker, text)

    def skip(self):
        self.done = True
        self.dialogue_box.close()

    def update(self, advance_pressed):
        if not self.active:
            return
        self.timer += 1
        if advance_pressed:
            if not self.dialogue_box.finished:
                self.dialogue_box.reveal_all()
            else:
                self._advance()
        else:
            self.dialogue_box.update()

    def draw(self, surface, text_fn):
        self._draw_room(surface)
        self._draw_monitor(surface)
        self._draw_lia(surface)
        if self.index == len(self.BEATS) - 1:
            self._draw_coral_glow(surface)
        self.dialogue_box.draw(surface, text_fn)
        text_fn(surface, "[ESC pula a introdução]", (WIDTH - 190, 30), 14, "#cbd6e6", True)

    # A DialogueBox ocupa a metade DE BAIXO da tela inteira (HEIGHT_RATIO=
    # 0.50 em dialogue.py, então ela começa em y=435 numa tela de 900px) —
    # bem mais alto do que os ~140px que uma caixa de diálogo comum ocupa
    # no resto do jogo. Por isso a cena (cama, monitor, Lia) inteira fica
    # comprimida acima de y=~330: qualquer elemento novo aqui precisa
    # continuar acima dessa linha pra não ficar atrás da caixa.
    def _draw_room(self, surface):
        top = (16, 24, 40)
        bottom = (58, 70, 92)
        band = 6
        for y in range(0, HEIGHT, band):
            t = y / HEIGHT
            surface.fill(_lerp_color(top, bottom, t), (0, y, WIDTH, band))

        bed_rect = pygame.Rect(230, 180, 560, 150)
        pygame.draw.rect(surface, self.BED_COLOR, bed_rect, border_radius=26)
        pillow_rect = pygame.Rect(258, 156, 150, 74)
        pygame.draw.rect(surface, self.PILLOW_COLOR, pillow_rect, border_radius=28)
        blanket_rect = pygame.Rect(230, 220, 560, 110)
        pygame.draw.rect(surface, self.BLANKET_COLOR, blanket_rect, border_radius=22)

    def _draw_monitor(self, surface):
        stand = pygame.Rect(900, 180, 14, 150)
        pygame.draw.rect(surface, (30, 36, 48), stand)
        body = pygame.Rect(840, 40, 210, 140)
        pygame.draw.rect(surface, self.MONITOR_BODY, body, border_radius=12)
        pygame.draw.rect(surface, self.MONITOR_FRAME, body, 3, border_radius=12)

        segment_count = 40
        points = []
        for i in range(segment_count):
            x = body.x + 14 + i * ((body.width - 28) / (segment_count - 1))
            phase = self.timer * 0.12 + i * 0.6
            spike = -34 if i % 13 == 6 else 0
            y = body.y + body.height / 2 + math.sin(phase) * 6 + spike
            points.append((x, y))
        pygame.draw.lines(surface, self.MONITOR_LINE, False, points, 2)

    def _draw_lia(self, surface):
        rect = self.lia_frame.get_rect()
        rect.midbottom = (1060, 330)
        surface.blit(self.lia_frame, rect)

    def _draw_coral_glow(self, surface):
        """Um brilho coral discreto que pulsa perto de Lia na última fala —
        a mesma cor reservada à anomalia no resto do jogo (ver
        LEIA-ME_bosses_e_itens.md §4), plantada aqui como o primeiro sinal
        de que a pesquisa dela vai cruzar com algo maior."""
        pulse = (math.sin(self.timer * 0.05) + 1) / 2
        radius = int(10 + pulse * 6)
        size = radius * 6
        glow = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size // 2, size // 2)
        for r, alpha in ((radius * 3, 30), (radius * 2, 70), (radius, 160)):
            pygame.draw.circle(glow, (*self.CORAL_GLOW, alpha), center, r)
        surface.blit(glow, (1060 - size // 2, 258 - size // 2))
