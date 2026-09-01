"""Música e efeitos sonoros.

Fino encapsulamento em cima de `music`/`sounds` (globais injetados pelo
Pygame Zero em tempo de execução — mesmo padrão de `keyboard`/`screen`
usados direto em game.py, sem import nenhum: ver docstring de main.py).

Por que esse arquivo existe: as trilhas (Suno) e os efeitos vão ser
gerados aos poucos, um de cada vez — ver PLANO_AUDIO.md pra lista
completa, nome de arquivo esperado (convenção do próprio Raul: música
"<nome>_music", efeito "<nome>_sound", ex.: fase_1_music.mp3,
projectile_sound.wav — algumas exceções curtas tipo jump/punch) e
prompt sugerido de cada um. Sem esse encapsulamento, `music.play(...)`
ou `sounds.algo.play()` DERRUBARIAM o jogo com um erro assim que o
código tentasse tocar algo que ainda não tem arquivo em music/ ou
sounds/. Aqui, toda chamada é protegida: falta o arquivo, não toca
nada, e o jogo segue normal — dá pra ir testando cada trilha/efeito
assim que o Raul solta o arquivo certo em music/<nome>.mp3 ou
sounds/<nome>.wav|mp3, sem precisar mexer em mais nenhuma linha de
código."""

_current_track = None
music_enabled = True
sfx_enabled = True


def play_music(name, loop=True):
    """Troca a música de fundo pra `name` (sem extensão — ver
    PLANO_AUDIO.md pros nomes esperados em music/). Não faz nada se `name`
    já é a música tocando agora (evita reiniciar a mesma faixa do zero
    todo quadro, já que quem chama isso roda uma vez por quadro) nem se o
    arquivo ainda não existe."""
    global _current_track
    if not music_enabled or name == _current_track:
        return
    try:
        if loop:
            music.play(name)
        else:
            music.play_once(name)
        _current_track = name
    except Exception:
        # music/<name>.ogg ainda não existe (Suno) — silencioso de propósito.
        pass


def stop_music():
    global _current_track
    _current_track = None
    try:
        music.stop()
    except Exception:
        pass


def _resolve_sound(name):
    """`name` aceita ponto pra pastas dentro de sounds/ (ex.: o Raul
    organizou as variações de soco em sounds/punch/punch_1.mp3..._4.mp3 —
    o Pygame Zero enxerga isso como sounds.punch.punch_1, não um nome
    plano só; ver PLANO_AUDIO.md)."""
    target = sounds
    for part in name.split("."):
        target = getattr(target, part)
    return target


def play_sfx(name, volume=1.0):
    """Toca um efeito de uma vez só (sounds/<name>.wav|mp3|ogg — `name`
    pode ter ponto pra indicar subpasta, ver _resolve_sound). Silencioso
    se o arquivo ainda não existir — ver PLANO_AUDIO.md."""
    if not sfx_enabled:
        return
    try:
        sound = _resolve_sound(name)
        sound.set_volume(volume)
        sound.play()
    except Exception:
        pass
