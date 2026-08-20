"""Constantes compartilhadas e caminhos do projeto."""

from pathlib import Path


# Canvas lógico fixo: a janela apenas amplia esta área de jogo em 16:9.
WIDTH = 1920
HEIGHT = 1080
TITLE = "Echoes of Life"
FPS = 60

# Movimento da personagem. Estes valores definem a jogabilidade e não devem
# ser alterados durante ajustes exclusivamente visuais.
GRAVITY = 0.72
MAX_FALL_SPEED = 17
MOVE_SPEED = 5.4
JUMP_SPEED = -15.5
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 48

# A arte da Lia tem margem transparente nas laterais; a colisão acompanha o corpo.
PLAYER_HITBOX_OFFSET_X = 4
PLAYER_HITBOX_WIDTH = 24

ROOT_DIR = Path(__file__).resolve().parent
ASSET_DIR = ROOT_DIR / "images"
FONT_PATH = ROOT_DIR / "fonts" / "minha_fonte.ttf"

MOTIVATION = "Todo experimento pode falhar. Levante-se e tente novamente!"
