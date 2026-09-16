"""Prólogo de Lia e sua mãe sobre o projeto escolar ``Ciência Delas``.

O diálogo usa uma ilustração estática. Depois da última fala, seis quadros
mostram o caderno reagindo à energia coral. Cada troca acontece no preto
total: isso dá ritmo de história ilustrada e também esconde as diferenças
pequenas que a IA deixou entre uma imagem completa e outra.
"""

import pygame

from sprites import load_optional
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
    """Apresenta o tema central antes de Lia atravessar o Campo.

    A doença da mãe continua sendo a motivação emocional, mas o objetivo de
    Lia nasce de seu projeto sobre mulheres na ciência. As páginas do caderno
    conectam o prólogo aos itens de pesquisa e às cientistas encontradas nas
    fases seguintes.
    """

    BEATS = (
        ("Mãe", "Ainda acordada por causa da feira de ciências?"),
        ("Lia", "Meu trabalho chama Ciência Delas. Só não sei como terminar."),
        (
            "Mãe",
            "Talvez com uma pergunta. É assim que toda pesquisa começa.",
        ),
        (
            "Lia",
            "Então me ajuda: por que essas cientistas precisaram lutar tanto para serem ouvidas?",
        ),
        (
            "Mãe",
            "Porque muita gente usou as descobertas delas e esqueceu de contar quem abriu o caminho.",
        ),
        ("Lia", "Eu não vou esquecer."),
        (
            "Mãe",
            "Tem outra coisa que você precisa saber. Os médicos encontraram um câncer em mim.",
        ),
        ("Lia", "Mas existe tratamento, não existe?"),
        (
            "Mãe",
            "Existe porque muita gente continuou pesquisando, errando, registrando e compartilhando.",
        ),
        ("Lia", "Então eu quero descobrir quem tornou esse caminho possível."),
        (
            "Mãe",
            "Comece por quem quase ficou fora dos livros. E lembre: ciência nunca se faz sozinha.",
        ),
        ("Lia", "Vou levar o caderno para a escola. Cada pista vai entrar nessa pesquisa."),
    )

    BACKGROUND_PATH = ASSET_DIR / "cutscenes" / "prologo_ciencia_delas.png"
    ENERGY_FRAME_PATHS = tuple(
        ASSET_DIR / "cutscenes" / f"energia_{index:02}.png"
        for index in range(1, 7)
    )
    FADE_STEP = 24
    FRAME_HOLD_TICKS = 8
    FINAL_HOLD_TICKS = 45

    def __init__(self, dialogue_box, lia_frame):
        # Reaproveita a MESMA DialogueBox usada pelos diálogos de NPC —
        # Game.update já dá prioridade ao estado INTRO antes de checar
        # dialogue.active, então não há conflito entre os dois usos.
        self.dialogue_box = dialogue_box
        self.index = -1
        self.done = True
        self.timer = 0
        self.sequence_active = False
        self.energy_frame_index = -1
        self.energy_frame = None
        self.energy_frame_offset = (0, 0)
        self.transition_phase = None
        self.fade_alpha = 0
        self.hold_timer = 0
        self.finished_on_black = False
        self.fade_surface = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.fade_surface.fill("black")

        self.background = None
        self.background_offset = (0, 0)
        raw = load_optional(self.BACKGROUND_PATH, alpha=False)
        if raw is not None:
            self.background, self.background_offset = _scale_cover(raw, (WIDTH, HEIGHT))
        else:
            # Fallback só pra não travar o jogo caso a ilustração ainda não
            # tenha sido colocada em images/cutscenes/.
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
        self.sequence_active = False
        self.energy_frame_index = -1
        self.energy_frame = None
        self.transition_phase = None
        self.fade_alpha = 0
        self.hold_timer = 0
        self.finished_on_black = False
        self._advance()

    def _advance(self):
        self.index += 1
        if self.index >= len(self.BEATS):
            self.dialogue_box.close()
            self._start_energy_sequence()
            return
        speaker, text = self.BEATS[self.index]
        self.dialogue_box.start(speaker, text)

    def skip(self):
        self.done = True
        self.sequence_active = False
        self.energy_frame = None
        self.fade_alpha = 0
        self.finished_on_black = False
        self.dialogue_box.close()

    def update(self, advance_pressed):
        if not self.active:
            return
        self.timer += 1
        if self.sequence_active:
            self._update_energy_sequence()
            return
        if advance_pressed:
            if not self.dialogue_box.finished:
                self.dialogue_box.reveal_all()
            else:
                self._advance()
        else:
            self.dialogue_box.update()

    def _start_energy_sequence(self):
        self.sequence_active = True
        self.energy_frame_index = -1
        self.energy_frame = None
        self.transition_phase = "fade_out"
        self.fade_alpha = 0
        self.hold_timer = 0

    def _load_energy_frame(self, index):
        """Mantém somente o quadro atual escalado, evitando ~50 MB extras."""
        raw = load_optional(self.ENERGY_FRAME_PATHS[index], alpha=False)
        if raw is None:
            self.energy_frame = self.background
            self.energy_frame_offset = self.background_offset
            return
        self.energy_frame, self.energy_frame_offset = _scale_cover(
            raw, (WIDTH, HEIGHT)
        )

    def _update_energy_sequence(self):
        if self.transition_phase == "fade_out":
            self.fade_alpha = min(255, self.fade_alpha + self.FADE_STEP)
            if self.fade_alpha < 255:
                return
            next_index = self.energy_frame_index + 1
            if next_index >= len(self.ENERGY_FRAME_PATHS):
                self.done = True
                self.sequence_active = False
                self.energy_frame = None
                self.finished_on_black = True
                return
            self.energy_frame_index = next_index
            self._load_energy_frame(next_index)
            self.transition_phase = "fade_in"
            return

        if self.transition_phase == "fade_in":
            self.fade_alpha = max(0, self.fade_alpha - self.FADE_STEP)
            if self.fade_alpha == 0:
                self.transition_phase = "hold"
                self.hold_timer = (
                    self.FINAL_HOLD_TICKS
                    if self.energy_frame_index == len(self.ENERGY_FRAME_PATHS) - 1
                    else self.FRAME_HOLD_TICKS
                )
            return

        if self.transition_phase == "hold":
            self.hold_timer -= 1
            if self.hold_timer <= 0:
                self.transition_phase = "fade_out"

    def draw(self, surface, text_fn):
        image = self.energy_frame or self.background
        image_offset = (
            self.energy_frame_offset if self.energy_frame is not None
            else self.background_offset
        )
        if image is not None:
            surface.blit(image, image_offset)
        else:
            self._draw_fallback_room(surface)
            self._draw_lia(surface)
        if not self.sequence_active:
            self.dialogue_box.draw(surface, text_fn)
        text_fn(
            surface,
            "[ESC pula a introdução]",
            (WIDTH - 190, 30),
            14,
            "#cbd6e6",
            True,
        )
        if self.fade_alpha:
            self.fade_surface.set_alpha(self.fade_alpha)
            surface.blit(self.fade_surface, (0, 0))

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
