import pygame

import audio
from hud import get_font
from settings import ASSET_DIR, HEIGHT, WIDTH


class DialogueBox:
    """Caixa de diálogo com revelação gradual de texto."""

    CHARACTERS_PER_FRAME = 0.65
    WIDTH_RATIO = 0.64
    BOTTOM_MARGIN = 15
    TEXT_SIZE = 17
    TEXT_COLOR = "#e94f48"
    PORTRAIT_FRAME_TICKS = 8

    # Proporções medidas na nova dialogue_box.png de 1536x420. O espaço à
    # esquerda fica reservado ao personagem e o texto ocupa somente o
    # painel claro, sem atravessar a divisória.
    PORTRAIT_X_RATIO = 0.035
    PORTRAIT_Y_RATIO = 0.15
    PORTRAIT_WIDTH_RATIO = 0.185
    PORTRAIT_HEIGHT_RATIO = 0.65
    TEXT_LEFT_RATIO = 0.255
    TEXT_RIGHT_RATIO = 0.955
    SPEAKER_Y_RATIO = 0.27
    BODY_TOP_RATIO = 0.30
    BODY_BOTTOM_RATIO = 0.66
    INSTRUCTION_Y_RATIO = 0.79
    # Se o texto revelado até agora não couber no tamanho padrão dentro
    # dessa faixa, cai pra um preset menor (nessa ordem) até caber — em vez
    # de simplesmente vazar por baixo da moldura (issue original: falas de
    # 4 linhas furavam a borda inferior do cartucho).
    SIZE_PRESETS = ((17, 23), (15, 19), (13, 16), (11, 14))

    def __init__(self, portraits=None):
        self.current = None
        self.visible_characters = 0.0
        self.characters_per_frame = self.CHARACTERS_PER_FRAME
        self.portrait_tick = 0

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
        self.background = pygame.transform.scale(
            raw_background,
            (self.overlay_width, self.overlay_height),
        )
        self.portrait_rect = pygame.Rect(
            round(self.overlay_width * self.PORTRAIT_X_RATIO),
            round(self.overlay_height * self.PORTRAIT_Y_RATIO),
            round(self.overlay_width * self.PORTRAIT_WIDTH_RATIO),
            round(self.overlay_height * self.PORTRAIT_HEIGHT_RATIO),
        )
        self.text_left = round(self.overlay_width * self.TEXT_LEFT_RATIO)
        self.text_right = round(self.overlay_width * self.TEXT_RIGHT_RATIO)
        self.text_center_x = (self.text_left + self.text_right) // 2
        self.speaker_y = round(self.overlay_height * self.SPEAKER_Y_RATIO)
        self.body_top = round(self.overlay_height * self.BODY_TOP_RATIO)
        self.body_bottom = round(self.overlay_height * self.BODY_BOTTOM_RATIO)
        self.instruction_y = round(self.overlay_height * self.INSTRUCTION_Y_RATIO)
        self.text_max_width = self.text_right - self.text_left
        self.portraits = self._prepare_portraits(portraits or {})
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
        self.portrait_tick = 0

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
        if self.active:
            self.portrait_tick += 1
        if self.active and not self.finished:
            speed = audio.text_speed
            if speed <= 0:
                self.visible_characters = len(self.current[1])
                return
            self.visible_characters = min(
                len(self.current[1]),
                self.visible_characters + speed,
            )

    def _prepare_portraits(self, portraits):
        """Recorta a margem vazia do idle e o amplia sem suavização.

        O mesmo retângulo de recorte é usado em todos os quadros de cada
        personagem; assim a animação não fica pulando dentro da janela.
        """
        prepared = {}
        available_width = max(1, self.portrait_rect.width - 20)
        available_height = max(1, self.portrait_rect.height - 14)
        for speaker, source_frames in portraits.items():
            frames = [frame for frame in source_frames if frame is not None]
            if not frames:
                continue
            bounds = [frame.get_bounding_rect(min_alpha=8) for frame in frames]
            bounds = [rect for rect in bounds if rect.width and rect.height]
            if not bounds:
                continue
            content = bounds[0].copy()
            for rect in bounds[1:]:
                content.union_ip(rect)
            scale = min(
                available_width / content.width,
                available_height / content.height,
            )
            size = (
                max(1, round(content.width * scale)),
                max(1, round(content.height * scale)),
            )
            prepared[speaker] = [
                pygame.transform.scale(frame.subsurface(content), size)
                for frame in frames
            ]
        return prepared

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
        center_x = self.overlay_x + self.text_center_x
        lines, text_size, line_height = self._fit_text(visible_text)

        surface.blit(self.background, (self.overlay_x, self.overlay_y))
        self._draw_portrait(surface, speaker)
        text_fn(
            surface,
            speaker,
            (center_x, self.overlay_y + self.speaker_y),
            18,
            self.TEXT_COLOR,
            True,
        )

        block_height = (len(lines) - 1) * line_height
        available = self.body_bottom - self.body_top
        first_line_y = self.overlay_y + self.body_top + max(0, (available - block_height) // 2)
        for line_number, line in enumerate(lines):
            text_fn(
                surface,
                line,
                (center_x, first_line_y + line_number * line_height),
                text_size,
                self.TEXT_COLOR,
                True,
            )

        instruction = (
            "[E / ENTER para continuar]"
            if self.finished
            else "Aguarde a fala terminar..."
        )
        text_fn(
            surface,
            instruction,
            (center_x, self.overlay_y + self.instruction_y),
            12,
            self.TEXT_COLOR,
            True,
        )

    def _draw_portrait(self, surface, speaker):
        rect = self.portrait_rect.move(self.overlay_x, self.overlay_y)
        frames = self.portraits.get(speaker)
        if not frames:
            return
        frame = frames[(self.portrait_tick // self.PORTRAIT_FRAME_TICKS) % len(frames)]
        frame_rect = frame.get_rect(midbottom=(rect.centerx, rect.bottom - 4))
        previous_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.blit(frame, frame_rect)
        surface.set_clip(previous_clip)
