import pygame

from settings import ASSET_DIR, FONT_PATH, HEIGHT, WIDTH


class DialogueBox:
    """Caixa de diálogo com revelação gradual de texto."""

    CHARACTERS_PER_FRAME = 0.65
    WIDTH_RATIO = 0.64
    HEIGHT_RATIO = 0.50
    BOTTOM_MARGIN = 15
    HORIZONTAL_PADDING = 140
    TEXT_SIZE = 17
    LINE_HEIGHT = 23

    # A arte de dialogue_box.png é um cartucho ornamentado bem mais baixo
    # que o retângulo overlay_width x overlay_height inteiro (a moldura tem
    # uma borda grossa e um respiro grande acima/abaixo) — o miolo bege
    # realmente pintado (onde o texto precisa caber) ocupa só essa faixa
    # vertical, medida direto na imagem (~38.7% a ~66% da altura crua).
    # BODY_TOP/BODY_BOTTOM reservam a faixa abaixo do nome do locutor
    # (desenhado em overlay_y+210) até pouco antes da borda inferior.
    BODY_TOP = 225
    BODY_BOTTOM = 280
    # Se o texto revelado até agora não couber no tamanho padrão dentro
    # dessa faixa, cai pra um preset menor (nessa ordem) até caber — em vez
    # de simplesmente vazar por baixo da moldura (issue original: falas de
    # 4 linhas furavam a borda inferior do cartucho).
    SIZE_PRESETS = ((17, 23), (15, 19), (13, 16), (11, 14))

    def __init__(self):
        self.current = None
        self.visible_characters = 0.0
        self.characters_per_frame = self.CHARACTERS_PER_FRAME

        raw_background = pygame.image.load(
            ASSET_DIR / "ui" / "dialogue_box.png"
        ).convert_alpha()
        self.overlay_width = int(WIDTH * self.WIDTH_RATIO)
        self.overlay_height = int(HEIGHT * self.HEIGHT_RATIO)
        self.overlay_x = (WIDTH - self.overlay_width) // 2
        self.overlay_y = HEIGHT - self.overlay_height - self.BOTTOM_MARGIN
        self.background = pygame.transform.scale(
            raw_background,
            (self.overlay_width, self.overlay_height),
        )
        self.text_max_width = self.overlay_width - self.HORIZONTAL_PADDING
        self.text_measure_font = pygame.font.Font(str(FONT_PATH), self.TEXT_SIZE)
        # Uma fonte de medição por preset de tamanho (ver _fit_text) — os
        # pontos de quebra de linha mudam com o tamanho da fonte, então cada
        # tentativa precisa medir com a fonte do tamanho que vai usar.
        self._measure_fonts = {
            size: pygame.font.Font(str(FONT_PATH), size) for size, _ in self.SIZE_PRESETS
        }

    @property
    def active(self):
        return self.current is not None

    @property
    def finished(self):
        return self.active and self.visible_characters >= len(self.current[1])

    def start(self, speaker, text):
        self.current = (speaker, text)
        self.visible_characters = 0.0

    def close(self):
        self.current = None

    def reveal_all(self):
        """Mostra a fala inteira sem fechar a caixa."""
        if self.current:
            self.visible_characters = len(self.current[1])

    def update(self):
        """Avança a fala em etapas, como o texto de Undertale."""
        if self.active and not self.finished:
            self.visible_characters = min(
                len(self.current[1]),
                self.visible_characters + self.characters_per_frame,
            )

    def wrap_text(self, text, font=None):
        """Quebra a fala por palavras sem exceder a área interna da caixa."""
        lines = []
        for paragraph in text.split("\n"):
            lines.extend(self._wrap_paragraph(paragraph, font or self.text_measure_font))
        return lines

    def _wrap_paragraph(self, paragraph, font):
        lines = []
        current_line = ""
        for word in paragraph.split(" "):
            candidate = word if not current_line else f"{current_line} {word}"
            if current_line and font.size(candidate)[0] > self.text_max_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = candidate
        lines.append(current_line)
        return lines

    def _fit_text(self, visible_text):
        """Escolhe o menor preset de SIZE_PRESETS que ainda cabe dentro da
        faixa BODY_TOP..BODY_BOTTOM pro número de linhas que aquele tamanho
        gera — falas curtas ficam no tamanho padrão (17/23); só falas
        longas encolhem, em vez de vazar pela borda inferior da moldura."""
        available = self.BODY_BOTTOM - self.BODY_TOP
        best = None
        for size, line_height in self.SIZE_PRESETS:
            font = self._measure_fonts[size]
            lines = self.wrap_text(visible_text, font)
            block_height = (len(lines) - 1) * line_height + size
            best = (lines, size, line_height)  # se nada couber, sobra o último (o menor) tentado
            if block_height <= available:
                return lines, size, line_height
        # Nem o menor preset coube (fala excepcionalmente longa) — usa o
        # menor mesmo assim; ele lê melhor do que insistir no tamanho grande.
        return best

    def draw(self, surface, text_fn):
        if not self.current:
            return

        speaker, text = self.current
        visible_text = text[:int(self.visible_characters)]
        center_x = self.overlay_x + self.overlay_width // 2
        lines, text_size, line_height = self._fit_text(visible_text)

        surface.blit(self.background, (self.overlay_x, self.overlay_y))
        text_fn(surface, speaker, (center_x, self.overlay_y + 210), 18, "#173a62", True)

        block_height = (len(lines) - 1) * line_height
        available = self.BODY_BOTTOM - self.BODY_TOP
        first_line_y = self.overlay_y + self.BODY_TOP + max(0, (available - block_height) // 2)
        for line_number, line in enumerate(lines):
            text_fn(
                surface,
                line,
                (center_x, first_line_y + line_number * line_height),
                text_size,
                "#2b1a12",
                True,
            )

        instruction = (
            "[E / ENTER para continuar]"
            if self.finished
            else "Aguarde a fala terminar..."
        )
        text_fn(surface, instruction, (center_x, self.overlay_y + 350), 12, "#3b281b", True)
