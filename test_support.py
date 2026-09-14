"""Isolamento de disco para verificações; não é importado pelo jogo."""

from contextlib import contextmanager
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch


GAME_DIR = Path(__file__).resolve().parent / "jogo"


def configure_game_imports():
    """Expõe os módulos de jogo/ aos testes e ferramentas da raiz."""
    directory = str(GAME_DIR)
    if directory not in sys.path:
        sys.path.insert(0, directory)


@contextmanager
def isolated_game_data():
    """Redireciona saves e preferências durante testes, inclusive no import."""
    configure_game_imports()
    with TemporaryDirectory(prefix="echoes-test-") as directory:
        with patch.dict("os.environ", {"ECHOES_DATA_DIR": directory}):
            import settings

            path = Path(directory)
            with patch.object(settings, "DATA_DIR", path):
                import audio
                from game import Game
            with patch.object(Game, "SAVE_PATH", path / "save.json"), patch.object(
                audio, "_SETTINGS_PATH", path / "audio_settings.json"
            ):
                yield path


def shutdown_pygame():
    """Libera fontes antes de encerrar SDL; os testes podem iniciá-lo novamente.

    Reutilizar um Font cacheado após pygame.quit() pode causar uma falha
    nativa do SDL_ttf no Windows, sem levantar uma exceção Python.
    """
    import pygame
    from hud import get_font

    get_font.cache_clear()
    pygame.quit()
