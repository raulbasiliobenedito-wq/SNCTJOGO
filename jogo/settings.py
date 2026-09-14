"""Constantes compartilhadas e caminhos do projeto."""

import os
from pathlib import Path


# Canvas lógico fixo: a janela apenas amplia esta área de jogo em 16:9.
WIDTH = 1920
HEIGHT = 1080
TITLE = "Echoes of Life"
FPS = 60

# Movimento da personagem. Estes valores definem a jogabilidade e não devem
# ser alterados durante ajustes exclusivamente visuais.
GRAVITY = 0.6
MAX_FALL_SPEED = 9
MOVE_SPEED = 5
JUMP_SPEED = -13
# A nova sheet da Lia usa quadros visuais de 48x48. Estes valores continuam
# descrevendo o corpo lógico usado pela física: Player.draw centraliza o
# quadro de 48px sobre esta largura de 32px sem alterar a colisão existente.
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 48

# A arte da Lia tem margem transparente nas laterais; a colisão acompanha o corpo.
PLAYER_HITBOX_OFFSET_X = 4
PLAYER_HITBOX_WIDTH = 24

# Zoom da câmera (pedido do Raul, dica do professor: tava difícil de ver).
# O mundo continua desenhado normalmente em WIDTH x HEIGHT — só recortamos
# uma janela CAMERA_ZOOM vezes menor centrada na Lia e ampliamos de volta
# pro tamanho da tela (ver Game._blit_zoomed_world em game.py), então isso
# NÃO muda a resolução final nem exige tocar em nenhuma lógica de câmera/
# mundo/HUD existente. 1.5 = tudo aparece 50% maior. Usar 1.0 desliga o zoom.
CAMERA_ZOOM = 1

ROOT_DIR = Path(__file__).resolve().parent
# Testes podem isolar os dados. Sem a variável, mantém os caminhos existentes.
DATA_DIR = Path(os.environ.get("ECHOES_DATA_DIR", ROOT_DIR))
ASSET_DIR = ROOT_DIR / "images"
FONT_PATH = ROOT_DIR / "fonts" / "minha_fonte.ttf"
# Multiplicador aplicado a TODO tamanho de fonte pedido no jogo (ver
# hud.get_font) — meche aqui pra redimensionar HUD, diálogos e menus de
# uma vez só, sem precisar caçar cada chamada de draw_text espalhada pelo
# código.
FONT_SCALE = 1


MOTIVATION = "Todo experimento pode falhar. Levante-se e tente novamente!"
