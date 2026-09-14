import pygame

import audio
from hud import get_font
from settings import ASSET_DIR, HEIGHT, WIDTH


class DialogueBox:
    """Caixa de diálogo com revelação gradual de texto."""

    CHARACTERS_PER_FRAME = 0.65
    WIDTH_RATIO = 0.64
    # HEIGHT_RATIO removido: a altura vem da proporção do cartucho recortado.
    BOTTOM_MARGIN = 15
    HORIZONTAL_PADDING = 140
    TEXT_SIZE = 17

    # dialogue_box.png é 1536x1024, mas o cartucho DESENHADO é só uma faixa
    # de 1492x386 (proporção 3.865) no meio — o resto do arquivo é
    # transparente. O código antigo esticava o arquivo INTEIRO pra
    # 1228x540: dentro disso a faixa virava 1193x204, proporção 5.85, ou
    # seja, o cartucho aparecia 51% mais achatado do que foi desenhado.
    # Agora a moldura é recortada no carregamento (_crop_to_content) e
    # escalada mantendo a proporção dela — sem distorção e sem carregar
    # 64% de pixel transparente pra tela.
    #
    # As posições de texto eram pixels absolutos calibrados em cima da
    # caixa achatada. Viraram frações da faixa RECORTADA, convertidas a
    # partir de onde caíam dentro da faixa antiga (que ia de y=164 a y=367
    # dentro dos 540px): 210 -> 0.224, 225 -> 0.298, 280 -> 0.569,
    # 350 -> 0.914. O texto continua no mesmo ponto DO DESENHO.
    SPEAKER_Y_RATIO = 0.224
    BODY_TOP_RATIO = 0.298
    BODY_BOTTOM_RATIO = 0.569
    # 0.914 caía em cima da moldura escura do rodapé (baixo contraste — o
    # mesmo defeito existia na versão antiga, com o valor absoluto 350).
    # 0.84 põe a instrução dentro do miolo bege, abaixo do texto.
    INSTRUCTION_Y_RATIO = 0.84
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
        raw_background = self._crop_to_content(raw_background)
        # A LARGURA manda; a altura acompanha a proporção real do cartucho.
        self.overlay_width = int(WIDTH * self.WIDTH_RATIO)
        aspect = raw_background.get_height() / raw_background.get_width()
        self.overlay_height = round(self.overlay_width * aspect)
        self.overlay_x = (WIDTH - self.overlay_width) // 2
        self.overlay_y = HEIGHT - self.overlay_height - self.BOTTOM_MARGIN
        self.background = pygame.transform.smoothscale(
            raw_background,
            (self.overlay_width, self.overlay_height),
        )
        # Posições de texto derivadas da altura real da caixa (ver *_RATIO).
        self.speaker_y = round(self.overlay_height * self.SPEAKER_Y_RATIO)
        self.body_top = round(self.overlay_height * self.BODY_TOP_RATIO)
        self.body_bottom = round(self.overlay_height * self.BODY_BOTTOM_RATIO)
        self.instruction_y = round(self.overlay_height * self.INSTRUCTION_Y_RATIO)
        self.text_max_width = self.overlay_width - self.HORIZONTAL_PADDING
        # Medir com hud.get_font (em vez de instanciar a fonte na mão) é
        # essencial: é o mesmo helper que desconto o texto de verdade (via
        # text_fn=draw_text), com o mesmo FONT_SCALE aplicado — se a medição
        # usasse um tamanho "cru" desencontrado do que é desenhado, a quebra
        # de linha calculada aqui não bateria com o texto realmente maior/
        # menor renderizado depois, estourando a caixa.
        self.text_measure_font = get_font(self.TEXT_SIZE, self.TEXT_SIZE >= 30)
        # Uma fonte de medição por preset de tamanho (ver _fit_text) — os
        # pontos de quebra de linha mudam com o tamanho da fonte, então cada
        # tentativa precisa medir com a fonte do tamanho que vai usar.
        self._measure_fonts = {
            size: get_font(size, size >= 30) for size, _ in self.SIZE_PRESETS
        }

    @staticmethod
    def _crop_to_content(image):
        """Descarta a moldura transparente ao redor do cartucho.

        min_alpha=8 em vez de 1 porque a arte tem uma franja de alpha
        quase-zero (resíduo de exportação) que cobre o arquivo inteiro e
        faria o recorte não recortar nada. Se um dia a arte for reexportada
        já sem sobra, isto vira um no-op."""
        content = image.get_bounding_rect(min_alpha=8)
        if content.width <= 0 or content.height <= 0:
            return image
        return image.subsurface(content).copy()

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
        """Avança a fala em etapas, como o texto de Undertale. A velocidade
        vem das Configurações (audio.text_speed) — 0 revela a fala inteira
        de uma vez, pra quem prefere ler no próprio ritmo."""
        if self.active and not self.finished:
            speed = audio.text_speed
            if speed <= 0:
                self.visible_characters = len(self.current[1])
                return
            self.visible_characters = min(
                len(self.current[1]),
                self.visible_characters + speed,
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
        faixa body_top..body_bottom pro número de linhas que aquele tamanho
        gera — falas curtas ficam no tamanho padrão (17/23); só falas
        longas encolhem, em vez de vazar pela borda inferior da moldura."""
        available = self.body_bottom - self.body_top
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
        text_fn(surface, speaker, (center_x, self.overlay_y + self.speaker_y), 18, "#173a62", True)

        block_height = (len(lines) - 1) * line_height
        available = self.body_bottom - self.body_top
        first_line_y = self.overlay_y + self.body_top + max(0, (available - block_height) // 2)
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
        text_fn(surface, instruction, (center_x, self.overlay_y + self.instruction_y), 12, "#3b281b", True)
