from pathlib import Path

# Resolução interna fixa. Todo o jogo é desenhado nesse canvas 16:9 e depois
# ampliado para a tela, mantendo sprites, HUD, física e câmera proporcionais.
WIDTH, HEIGHT = 1600, 900
TITLE = "Echoes of Life"
FPS = 60

GRAVITY = 0.72
MAX_FALL_SPEED = 17
MOVE_SPEED = 5.4
JUMP_SPEED = -15.5
PLAYER_WIDTH, PLAYER_HEIGHT = 32, 48
# A arte da Lia tem margem transparente nas laterais; a colisão acompanha o corpo.
PLAYER_HITBOX_OFFSET_X = 4
PLAYER_HITBOX_WIDTH = 24

ROOT_DIR = Path(__file__).resolve().parent
ASSET_DIR = ROOT_DIR / "images"
FONT_PATH = ROOT_DIR / "fonts" / "minha_fonte.ttf"
MOTIVATION = "Todo experimento pode falhar. Levante-se e tente novamente!"
