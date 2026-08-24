"""Cutscene inicial: Lia e a mãe no hospital, antes da Fase 1.

Usa uma ilustração única (images/cutscenes/hospital.png) como cenário —
ela já traz cama, monitor e as duas personagens desenhadas, então o código
só entra pra dar um pouco de vida em cima disso (o brilho coral pulsante)
e pra tocar as falas na mesma DialogueBox ornamentada usada pelas
cientistas-NPC (mesmo cartucho, mesma revelação gradual de texto, mesmo
"[E/ENTER para continuar]").

Se o arquivo da ilustração não existir ainda, cai num cenário simples
desenhado por código (gradiente + formas), só pra não travar o jogo.
"""

import math

import pygame

from settings import ASSET_DIR, HEIGHT, WIDTH


def _lerp_color(start, end, t):
    return tuple(int(start[i] + (end[i] - start[i]) * t) for i in range(3))


def _scale_cover(image, target_size):
    """Redimensiona `image` pra cobrir target_size inteiro (sem distorcer,
    cortando o excesso) — mesma lógica de `background-size: cover` do CSS.
    Devolve a imagem escalada e o deslocamento (geralmente negativo) onde
    ela deve ser desenhada pra ficar centralizada."""
    target_w, target_h = target_size
    src_w, src_h = image.get_size()
    scale = max(target_w / src_w, target_h / src_h)
    new_size = (round(src_w * scale), round(src_h * scale))
    scaled = pygame.transform.smoothscale(image, new_size)
    offset = ((target_w - new_size[0]) // 2, (target_h - new_size[1]) // 2)
    return scaled, offset


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

    CORAL_GLOW = (216, 134, 166)
    # Posição do brilho, em fração (0..1) da ILUSTRAÇÃO original — perto do
    # rosto/ombro de Lia, bem acima de onde a caixa de diálogo cobre a tela
    # (ela começa em y=435 de 900, ver dialogue.py). Ajuste fino aqui se a
    # posição não bater com a arte depois de ver rodando de verdade.
    GLOW_ANCHOR = (0.70, 0.32)

    BACKGROUND_PATH = ASSET_DIR / "cutscenes" / "hospital.png"

    def __init__(self, dialogue_box, lia_frame):
        # Reaproveita a MESMA DialogueBox usada pelos diálogos de NPC —
        # Game.update já dá prioridade ao estado INTRO antes de checar
        # dialogue.active, então não há conflito entre os dois usos.
        self.dialogue_box = dialogue_box
        self.index = -1
        self.done = True
        self.timer = 0

        self.background = None
        self.background_offset = (0, 0)
        self.glow_pos = (WIDTH * self.GLOW_ANCHOR[0], HEIGHT * self.GLOW_ANCHOR[1])
        if self.BACKGROUND_PATH.exists():
            raw = pygame.image.load(str(self.BACKGROUND_PATH)).convert_alpha()
            self.background, self.background_offset = _scale_cover(raw, (WIDTH, HEIGHT))
            self.glow_pos = (
                self.background_offset[0] + self.background.get_width() * self.GLOW_ANCHOR[0],
                self.background_offset[1] + self.background.get_height() * self.GLOW_ANCHOR[1],
            )
        else:
            # Fallback só pra não travar o jogo caso a ilustração ainda não
            # tenha sido colocada em images/cutscenes/hospital.png.
            self.lia_frame = pygame.transform.scale(
                lia_frame, (lia_frame.get_width() * 3, lia_frame.get_height() * 3)
            )

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
        if self.background is not None:
            surface.blit(self.background, self.background_offset)
        else:
            self._draw_fallback_room(surface)
            self._draw_lia(surface)
        if self.index == len(self.BEATS) - 1:
            self._draw_coral_glow(surface)
        self.dialogue_box.draw(surface, text_fn)
        text_fn(surface, "[ESC pula a introdução]", (WIDTH - 190, 30), 14, "#cbd6e6", True)

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
        x, y = self.glow_pos
        surface.blit(glow, (x - size // 2, y - size // 2))

    # --- Fallback (só usado se images/cutscenes/hospital.png não existir) ---

    def _draw_fallback_room(self, surface):
        top = (16, 24, 40)
        bottom = (58, 70, 92)
        band = 6
        for y in range(0, HEIGHT, band):
            t = y / HEIGHT
            surface.fill(_lerp_color(top, bottom, t), (0, y, WIDTH, band))
        bed_rect = pygame.Rect(230, 180, 560, 150)
        pygame.draw.rect(surface, (214, 224, 236), bed_rect, border_radius=26)
        pillow_rect = pygame.Rect(258, 156, 150, 74)
        pygame.draw.rect(surface, (230, 236, 244), pillow_rect, border_radius=28)
        blanket_rect = pygame.Rect(230, 220, 560, 110)
        pygame.draw.rect(surface, (110, 142, 158), blanket_rect, border_radius=22)

    def _draw_lia(self, surface):
        rect = self.lia_frame.get_rect()
        rect.midbottom = (1060, 330)
        surface.blit(self.lia_frame, rect)
