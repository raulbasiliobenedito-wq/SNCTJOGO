import pygame
from settings import ASSET_DIR, FONT_PATH, HEIGHT, WIDTH


class DialogueBox:
    def __init__(self):
        self.current = None
        self.visible_characters = 0.0
        self.characters_per_frame = 0.65
        raw_background = pygame.image.load(ASSET_DIR / "ui" / "dialogue_box.png").convert_alpha()
        # Usa 80% da tela: mantém a arte legível sem esconder demais o jogo.
        self.overlay_width = int(WIDTH * 0.64)
        self.overlay_height = int(HEIGHT * 0.50)
        self.overlay_x = (WIDTH - self.overlay_width) // 2
        self.overlay_y = HEIGHT - self.overlay_height - 15
        self.background = pygame.transform.scale(
            raw_background, (self.overlay_width, self.overlay_height)
        )
        self.text_max_width = self.overlay_width - 140
        self.text_measure_font = pygame.font.Font(str(FONT_PATH), 17)

    @property
    def active(self):
        return self.current is not None

    def start(self, speaker, text):
        self.current = (speaker, text)
        self.visible_characters = 0.0

    def close(self):
        self.current = None

    def reveal_all(self):
        """Mostra a fala inteira sem fechar a caixa; o próximo toque avança."""
        if self.current:
            self.visible_characters = len(self.current[1])

    @property
    def finished(self):
        return self.active and self.visible_characters >= len(self.current[1])

    def update(self):
        """Mostra a fala em etapas, como o texto de Undertale."""
        if self.active and not self.finished:
            self.visible_characters = min(
                len(self.current[1]), self.visible_characters + self.characters_per_frame
            )

    def wrap_text(self, text):
        """Quebra a fala por palavras, sem ultrapassar a área interna da caixa."""
        lines = []
        for paragraph in text.split("\n"):
            current_line = ""
            for word in paragraph.split(" "):
                candidate = word if not current_line else f"{current_line} {word}"
                if current_line and self.text_measure_font.size(candidate)[0] > self.text_max_width:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = candidate
            lines.append(current_line)
        return lines

    def draw(self, surface, text_fn):
        if not self.current:
            return
        speaker, text = self.current
        visible_text = text[:int(self.visible_characters)]
        surface.blit(self.background, (self.overlay_x, self.overlay_y))
        center_x = self.overlay_x + self.overlay_width // 2
        text_fn(surface, speaker, (center_x, self.overlay_y + 210), 18, "#173a62", True)
        lines = self.wrap_text(visible_text)
        first_line_y = self.overlay_y + 262 - (len(lines) - 1) * 12
        for line_number, line in enumerate(lines):
            text_fn(surface, line, (center_x, first_line_y + line_number * 23), 17, "#2b1a12", True)
        instruction = "[E / ENTER para continuar]" if self.finished else "Aguarde a fala terminar..."
        text_fn(surface, instruction, (center_x, self.overlay_y + 350), 12, "#3b281b", True)
