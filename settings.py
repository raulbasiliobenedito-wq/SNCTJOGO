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
# Sheet nova da Lia (player_sheet.png) vem em 64x96 por quadro no arquivo,
# mas isso ficava enorme em jogo (pedido do Raul) — Player._load_frames
# reduz cada quadro pela metade ao carregar (ver Player.SHEET_FRAME_WIDTH/
# HEIGHT lá), então esses dois aqui já são o tamanho final em tela/hitbox,
# de volta aos mesmos 32x48 de antes da troca de sheet.
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 48

# A arte da Lia tem margem transparente nas laterais; a colisão acompanha o corpo.
PLAYER_HITBOX_OFFSET_X = 4
PLAYER_HITBOX_WIDTH = 24

ROOT_DIR = Path(__file__).resolve().parent
ASSET_DIR = ROOT_DIR / "images"
FONT_PATH = ROOT_DIR / "fonts" / "minha_fonte.ttf"
# Multiplicador aplicado a TODO tamanho de fonte pedido no jogo (ver
# hud.get_font) — meche aqui pra redimensionar HUD, diálogos e menus de
# uma vez só, sem precisar caçar cada chamada de draw_text espalhada pelo
# código.
FONT_SCALE = 1


MOTIVATION = "Todo experimento pode falhar. Levante-se e tente novamente!"
