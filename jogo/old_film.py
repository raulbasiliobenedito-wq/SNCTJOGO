"""Efeito leve de poeira e riscos de filme sobre a cena."""

from pathlib import Path

import pygame


class OldFilmOverlay:
    """Reproduz uma spritesheet curta sem decodificar vídeo durante o jogo.

    Os pixels pretos da arte são neutros no ``BLEND_RGB_ADD``. Assim, só a
    poeira e os riscos claros chegam à cena, sem criar um retângulo preto nem
    alterar a leitura das cores do cenário.
    """

    FRAME_SIZE = (640, 360)
    FRAME_COLUMNS = 8
    FRAME_COUNT = 32
    FRAME_RATE = 10.0

    def __init__(self, path):
        self.elapsed = 0.0
        self.frame_index = 0
        self._sheet = None
        self._frames = ()
        self._scaled_frame = None
        self._scaled_key = None

        path = Path(path)
        if not path.is_file():
            return

        try:
            sheet = pygame.image.load(path).convert()
        except (OSError, pygame.error):
            return

        frame_width, frame_height = self.FRAME_SIZE
        rows = (self.FRAME_COUNT + self.FRAME_COLUMNS - 1) // self.FRAME_COLUMNS
        expected_size = (frame_width * self.FRAME_COLUMNS, frame_height * rows)
        if sheet.get_size() != expected_size:
            return

        self._sheet = sheet
        self._frames = tuple(
            sheet.subsurface(
                pygame.Rect(
                    (index % self.FRAME_COLUMNS) * frame_width,
                    (index // self.FRAME_COLUMNS) * frame_height,
                    frame_width,
                    frame_height,
                )
            )
            for index in range(self.FRAME_COUNT)
        )

    @property
    def available(self):
        return bool(self._frames)

    def update(self, dt):
        if not self.available:
            return
        # Evita saltos enormes ao voltar de uma janela suspensa.
        elapsed = max(0.0, min(float(dt), 0.1))
        self.elapsed = (self.elapsed + elapsed) % (self.FRAME_COUNT / self.FRAME_RATE)
        next_index = int(self.elapsed * self.FRAME_RATE) % self.FRAME_COUNT
        if next_index != self.frame_index:
            self.frame_index = next_index
            self._scaled_frame = None
            self._scaled_key = None

    def draw(self, surface):
        if not self.available:
            return

        target_size = surface.get_size()
        cache_key = (self.frame_index, target_size)
        if cache_key != self._scaled_key:
            frame = self._frames[self.frame_index]
            self._scaled_frame = (
                frame
                if frame.get_size() == target_size
                else pygame.transform.scale(frame, target_size)
            )
            self._scaled_key = cache_key

        surface.blit(
            self._scaled_frame,
            (0, 0),
            special_flags=pygame.BLEND_RGB_ADD,
        )
