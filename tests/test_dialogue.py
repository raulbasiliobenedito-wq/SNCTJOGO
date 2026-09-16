"""Layout da nova caixa de diálogo e retratos animados."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from test_support import configure_game_imports, shutdown_pygame

configure_game_imports()

import pygame

from dialogue import DialogueBox


class DialogueBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        shutdown_pygame()

    def make_frames(self):
        frames = []
        for offset in (0, 2):
            frame = pygame.Surface((48, 48), pygame.SRCALPHA).convert_alpha()
            pygame.draw.rect(frame, "white", (14 + offset, 8, 18, 38))
            frames.append(frame)
        return frames

    def test_portrait_and_text_areas_do_not_overlap(self):
        dialogue = DialogueBox({"Lia": self.make_frames()})

        self.assertEqual(dialogue.TEXT_COLOR, "#e94f48")
        self.assertLessEqual(dialogue.portrait_rect.right, dialogue.text_left)
        self.assertIn("Lia", dialogue.portraits)
        self.assertTrue(
            all(
                frame.get_width() <= dialogue.portrait_rect.width
                and frame.get_height() <= dialogue.portrait_rect.height
                for frame in dialogue.portraits["Lia"]
            )
        )

    def test_every_dialogue_label_uses_requested_coral(self):
        dialogue = DialogueBox({"Lia": self.make_frames()})
        dialogue.start("Lia", "Texto de teste.")
        dialogue.reveal_all()
        calls = []

        def record_text(_surface, value, position, size, color, center):
            calls.append((value, position, size, color, center))

        surface = pygame.Surface((1920, 1080)).convert()
        dialogue.draw(surface, record_text)

        self.assertGreaterEqual(len(calls), 3)
        self.assertTrue(all(call[3] == "#e94f48" for call in calls))
        portrait_right = dialogue.overlay_x + dialogue.portrait_rect.right
        self.assertTrue(all(call[1][0] > portrait_right for call in calls))

    def test_portrait_is_drawn_above_the_box_background(self):
        dialogue = DialogueBox({"Lia": self.make_frames()})
        dialogue.start("Lia", "Teste.")
        dialogue.reveal_all()
        surface = pygame.Surface((1920, 1080), pygame.SRCALPHA).convert_alpha()
        surface.fill((31, 73, 109))

        dialogue.draw(surface, lambda *_args: None)

        frame = dialogue.portraits["Lia"][0]
        portrait_rect = dialogue.portrait_rect.move(
            dialogue.overlay_x,
            dialogue.overlay_y,
        )
        frame_rect = frame.get_rect(
            midbottom=(portrait_rect.centerx, portrait_rect.bottom - 4)
        )
        self.assertEqual(surface.get_at(frame_rect.center), pygame.Color("white"))


if __name__ == "__main__":
    unittest.main()
