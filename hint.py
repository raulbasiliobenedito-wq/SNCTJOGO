"""Sistema de dicas contextuais: escurece a tela ao redor de um "holofote"
radial (vinheta) que aparece aos poucos, com um título e uma explicação —
baseado numa referência que o Raul mandou (dica de outro jogo com esse
mesmo efeito). Pausa a jogabilidade enquanto ativa, do mesmo jeito que a
DialogueBox já faz (ver Game.update: dialogue.active tem prioridade sobre
_update_playing) — aqui vale o mesmo padrão, só que sem revelação de texto
character a character (dicas são objetivas, aparecem inteiras de uma vez).
"""

import math

import pygame

from settings import HEIGHT, WIDTH


class Hint:
    VIGNETTE_COLOR = (2, 5, 11)
    VIGNETTE_MAX_ALPHA = 240
    # Fração da distância até a borda (normalizada por eixo, não em pixels —
    # ver _build_vignette) onde a vinheta começa a escurecer e onde ela já
    # chega na opacidade máxima. Terminar em 0.72 (bem antes de 1.0, que é o
    # meio de cada lado da tela) garante que topo/base/laterais fiquem tão
    # escuros quanto os cantos — a primeira versão usava distância euclidiana
    # simples a partir do centro, que só chegava no alpha máximo nos 4 cantos
    # (os pontos mais distantes) e deixava topo/base quase sem escurecer.
    CLEAR_START = 0.18
    FULL_DARK_AT = 0.72

    FADE_IN_FRAMES = 28
    # A vinheta escurece bem antes do texto ficar legível — evita o título
    # "piscando" em cima de um fundo ainda claro demais nos primeiros quadros.
    TEXT_REVEAL_THRESHOLD = 0.35

    def __init__(self):
        self._vignette = self._build_vignette()
        self.active = False
        self.timer = 0
        self.title = ""
        self.lines = ()

    @classmethod
    def _build_vignette(cls):
        """Constrói a vinheta cheia (WIDTH x HEIGHT) uma única vez, na
        inicialização. Calcula pixel a pixel numa superfície pequena
        (160x90, mesma proporção 16:9 da tela) e amplia com smoothscale —
        rodar o laço 1600x900 vezes em Python puro seria caro demais pra
        repetir a cada dica; numa grade pequena é ~14 mil iterações, uma
        vez só, e o smoothscale suaviza o resultado ao ampliar."""
        small_w, small_h = 160, 90
        small = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
        cx, cy = small_w / 2, small_h / 2
        span = cls.FULL_DARK_AT - cls.CLEAR_START
        for y in range(small_h):
            ny = (y - cy) / cy
            for x in range(small_w):
                nx = (x - cx) / cx
                # Distância normalizada por eixo: 1.0 é o meio de cada lado
                # da tela (não o canto) — assim topo/base/laterais escurecem
                # no mesmo ritmo que os cantos, em vez de só os cantos.
                dist = math.hypot(nx, ny)
                t = min(1.0, max(0.0, (dist - cls.CLEAR_START) / span))
                alpha = int((t ** 1.3) * cls.VIGNETTE_MAX_ALPHA)
                small.set_at((x, y), (*cls.VIGNETTE_COLOR, alpha))
        return pygame.transform.smoothscale(small, (WIDTH, HEIGHT))

    @property
    def finished_fade(self):
        return self.timer >= self.FADE_IN_FRAMES

    def show(self, title, lines):
        """`lines`: tupla de strings já curtas/pré-quebradas — dicas são
        textos objetivos, não precisam do wrap automático da DialogueBox."""
        self.title = title
        self.lines = lines
        self.active = True
        self.timer = 0

    def close(self):
        self.active = False

    def update(self):
        if self.active and not self.finished_fade:
            self.timer += 1

    def draw(self, surface, text_fn):
        if not self.active:
            return
        progress = min(1.0, self.timer / self.FADE_IN_FRAMES)
        eased = 1 - (1 - progress) ** 2  # ease-out: escurece rápido, suaviza no fim

        if progress >= 1.0:
            vignette = self._vignette
        else:
            # Técnica já usada em level.py (_draw_lab, sombreamento de peça
            # do microscópio): copiar e multiplicar pelo alpha desejado via
            # BLEND_RGBA_MULT escala a opacidade inteira da superfície sem
            # depender de Surface.set_alpha() combinado com alpha por pixel
            # (comportamento inconsistente entre versões do pygame).
            vignette = self._vignette.copy()
            vignette.fill(
                (255, 255, 255, int(255 * eased)),
                special_flags=pygame.BLEND_RGBA_MULT,
            )
        surface.blit(vignette, (0, 0))

        if eased < self.TEXT_REVEAL_THRESHOLD:
            return

        text_fn(surface, self.title, (WIDTH // 2, 110), 32, "#f4e4a5", True)
        line_height = 26
        block_top = HEIGHT - 90 - (len(self.lines) - 1) * line_height
        for index, line in enumerate(self.lines):
            text_fn(
                surface, line,
                (WIDTH // 2, block_top + index * line_height),
                21, "#e7edf5", True,
            )
        text_fn(surface, "[E / ENTER para fechar]", (WIDTH // 2, HEIGHT - 40), 13, "#9aa6b5", True)
