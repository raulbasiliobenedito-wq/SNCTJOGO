"""Utilidades de Surface compartilhadas entre player, inimigos e cenário.

Existe pra não obrigar player.py a importar de enemy.py (ou vice-versa) só
por causa de um helper de desenho — os dois precisam da mesma coisa e
nenhum dos dois é "dono" dela.
"""

from pathlib import Path

import pygame


#: Caminhos que load_optional procurou e não achou — útil pra listar de uma
#: vez o que ainda falta de arte (ver load_optional).
missing = set()


# Cada inimigo vivo chamava pygame.transform.flip no seu draw(), TODO
# QUADRO — ~10 Surfaces novas por quadro de jogo (mais a Lia) só pra virar
# sprites que nunca mudam. As folhas são carregadas uma vez no Game() e
# vivem a sessão inteira, então o cache é limitado pelo número de quadros
# distintos (algumas centenas, ~10 MB) e nunca precisa invalidar.
#
# A entrada guarda o próprio quadro junto com o espelho de propósito: isso
# mantém o original vivo enquanto o cache existir e impede que o id() seja
# reciclado por outro objeto — o que devolveria silenciosamente o espelho
# errado.
_FLIP_CACHE = {}


def flipped(frame):
    """Versão espelhada horizontalmente de `frame`, cacheada."""
    entry = _FLIP_CACHE.get(id(frame))
    if entry is None or entry[0] is not frame:
        entry = (frame, pygame.transform.flip(frame, True, False))
        _FLIP_CACHE[id(frame)] = entry
    return entry[1]


def load_optional(path, alpha=True):
    """Carrega uma imagem que pode ainda não existir no disco.

    Devolve None em vez de estourar. Existe porque o projeto tinha QUATRO
    jeitos diferentes de fazer a mesma coisa — `path.exists()` antes de
    carregar (Game._load_optional_object_sprite, _load_energy_box_sprites,
    IntroCutscene, ElevatorCutscene), pular a entrada no laço
    (VFXManager.__init__) e `try/except Exception` genérico (audio.play_sfx)
    — e o quarto estilo escondeu por muito tempo uma referência quebrada de
    verdade (elevador_lab_moldura.png com o nome errado no disco): o arquivo
    simplesmente não aparecia, sem nenhum sinal.

    Aqui a ausência é silenciosa (é o comportamento desejado: a arte chega
    aos poucos), mas fica REGISTRADA em `missing`, pra dar pra perguntar ao
    jogo o que ele não achou em vez de descobrir olhando a tela.
    """
    path = Path(path)
    if not path.exists():
        missing.add(str(path))
        return None
    image = pygame.image.load(path)
    return image.convert_alpha() if alpha else image.convert()


def load_optional_sheet(path, frame_width, frame_height, rows_frame_counts, scale=1.0):
    """Versão em grade de load_optional: devolve None se o arquivo não
    existir, senão uma lista de listas de quadros (uma por linha)."""
    sheet = load_optional(path)
    if sheet is None:
        return None
    size = (round(frame_width * scale), round(frame_height * scale))
    rows = []
    for row, count in enumerate(rows_frame_counts):
        frames = []
        for column in range(count):
            frame = sheet.subsurface(
                pygame.Rect(column * frame_width, row * frame_height, frame_width, frame_height)
            ).copy()
            if scale != 1.0:
                frame = pygame.transform.scale(frame, size)
            frames.append(frame)
        rows.append(frames)
    return rows
