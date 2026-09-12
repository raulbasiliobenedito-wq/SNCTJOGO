"""Isolamento de disco para verificações; não é importado pelo jogo."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


@contextmanager
def isolated_game_data():
    """Redireciona saves e preferências durante testes, inclusive no import."""
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
