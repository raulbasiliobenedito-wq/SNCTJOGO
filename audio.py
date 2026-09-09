"""Música e efeitos sonoros.

Fino encapsulamento em cima de `music`/`sounds` (globais que o Pygame Zero
injeta, mas só no módulo que ele roda de verdade — `main.py`, o "__main__"
em tempo de execução; ver `_main()` abaixo pro porquê disso importa).

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

import json
import sys

from settings import ROOT_DIR

_current_track = None
# Volume mestre (0.0-1.0) do menu de Configurações — ver
# set_music_volume/set_sfx_volume (chamados pelos sliders em game.py) e
# _SETTINGS_PATH (persistência entre execuções, ver load_settings/
# save_settings). music_volume=0/sfx_volume=0 já funciona como "mudo",
# sem precisar de um botão de mute separado.
music_volume = 1.0
sfx_volume = 1.0
# --- Acessibilidade (persistidas no mesmo arquivo que os volumes) ---
#: Multiplicador do tremor de câmera, 0.0-1.0. O Terremoto do Dragão sacode
#: por 5 segundos seguidos (EARTHQUAKE_SHAKE_DURATION=300); pra parte do
#: público isso é desconfortável de verdade, não é preferência estética.
shake_scale = 1.0
#: Velocidade da revelação de texto do diálogo, em caracteres por quadro
#: (ver dialogue.DialogueBox.CHARACTERS_PER_FRAME). 0 = instantâneo.
text_speed = 0.65

_SETTINGS_PATH = ROOT_DIR / "audio_settings.json"


# Vira True depois do primeiro aviso, pra não repetir a cada som tocado.
_warned_no_audio = False


def _main():
    """`music`/`sounds` só existem de verdade dentro do módulo que o
    Pygame Zero executa como script principal (main.py) — não são
    builtins globais disponíveis em qualquer arquivo, ao contrário do
    que este arquivo assumia antes (por isso NENHUM som tocava: toda
    chamada dava NameError, só que o except Exception: pass escondia
    isso). game.py contorna o mesmo problema recebendo `keyboard` como
    parâmetro vindo do main.py (ver game.update(keyboard, dt) em
    main.py); aqui, como play_music/play_sfx são chamados de vários
    lugares diferentes em game.py, é mais simples buscar o módulo
    __main__ (que É o main.py rodando) toda vez, em vez de propagar
    music/sounds por parâmetro em cada função que toca som."""
    module = sys.modules["__main__"]
    if not hasattr(module, "music"):
        # main_web.py (pygbag) NÃO recebe os globais que o Pygame Zero
        # injeta em main.py, então todas as chamadas abaixo caíam no
        # `except Exception: pass` — a versão web do jogo rodava 100% muda,
        # em silêncio, sem nenhum sinal de que algo estava errado. Isto não
        # conserta o áudio no web (pra isso seria preciso um backend em
        # pygame.mixer direto), mas tira o problema do escuro.
        global _warned_no_audio
        if not _warned_no_audio:
            _warned_no_audio = True
            print(
                "[audio] música e efeitos indisponíveis neste ponto de entrada "
                f"({getattr(module, '__file__', module)}): os globais `music`/"
                "`sounds` do Pygame Zero não existem aqui. O jogo roda mudo."
            )
    return module


def load_settings():
    """Lê audio_settings.json (se existir) uma vez, no import deste
    módulo (ver final do arquivo) — assim o volume escolhido no menu de
    Configurações continua o mesmo na próxima vez que o jogo abrir.
    Silencioso se o arquivo não existir ainda (primeira execução) ou
    estiver corrompido: fica no volume padrão (1.0/1.0) nesse caso."""
    global music_volume, sfx_volume, shake_scale, text_speed
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        music_volume = min(1.0, max(0.0, float(data.get("music_volume", 1.0))))
        sfx_volume = min(1.0, max(0.0, float(data.get("sfx_volume", 1.0))))
        shake_scale = min(1.0, max(0.0, float(data.get("shake_scale", 1.0))))
        text_speed = min(3.0, max(0.0, float(data.get("text_speed", 0.65))))
    except Exception:
        pass


def save_settings():
    """Chamado pelo menu de Configurações ao soltar o mouse do slider
    (não a cada quadro de arraste, pra não ficar escrevendo no disco o
    tempo todo) — ver Game.handle_menu_release em game.py."""
    try:
        _SETTINGS_PATH.write_text(
            json.dumps({
                "music_volume": music_volume, "sfx_volume": sfx_volume,
                "shake_scale": shake_scale, "text_speed": text_speed,
            }),
            encoding="utf-8",
        )
    except Exception:
        pass


def set_music_volume(value):
    """0.0-1.0. Aplica na hora (mesmo com uma faixa já tocando) — ver
    também play_music, que reaplica isso de novo toda vez que troca de
    faixa (music.play reseta o volume da faixa nova pro padrão)."""
    global music_volume
    music_volume = min(1.0, max(0.0, value))
    try:
        _main().music.set_volume(music_volume)
    except Exception:
        pass


def set_sfx_volume(value):
    """0.0-1.0 — multiplicado no volume de cada efeito em play_sfx."""
    global sfx_volume
    sfx_volume = min(1.0, max(0.0, value))


def set_shake_scale(value):
    """0.0-1.0 — multiplica a magnitude de TODO tremor de câmera (ver
    Game._shake_offset). 0 desliga completamente."""
    global shake_scale
    shake_scale = min(1.0, max(0.0, value))


def set_text_speed(value):
    """Caracteres por quadro na revelação de texto do diálogo. 0 mostra a
    fala inteira de uma vez (ver DialogueBox.update)."""
    global text_speed
    text_speed = min(3.0, max(0.0, value))


def play_music(name, loop=True):
    """Troca a música de fundo pra `name` (sem extensão — ver
    PLANO_AUDIO.md pros nomes esperados em music/). Não faz nada se `name`
    já é a música tocando agora (evita reiniciar a mesma faixa do zero
    todo quadro, já que quem chama isso roda uma vez por quadro) nem se o
    arquivo ainda não existe."""
    global _current_track
    if name == _current_track:
        return
    try:
        music = _main().music
        if loop:
            music.play(name)
        else:
            music.play_once(name)
        music.set_volume(music_volume)
        _current_track = name
    except Exception:
        # music/<name>.ogg ainda não existe (Suno) — silencioso de propósito.
        pass





def _resolve_sound(name):
    """`name` aceita ponto pra pastas dentro de sounds/ (ex.: o Raul
    organizou as variações de soco em sounds/punch/punch_1.mp3..._4.mp3 —
    o Pygame Zero enxerga isso como sounds.punch.punch_1, não um nome
    plano só; ver PLANO_AUDIO.md)."""
    target = _main().sounds
    for part in name.split("."):
        target = getattr(target, part)
    return target


def play_sfx(name, volume=1.0):
    """Toca um efeito de uma vez só (sounds/<name>.wav|mp3|ogg — `name`
    pode ter ponto pra indicar subpasta, ver _resolve_sound). `volume`
    (0.0-1.0) é o volume relativo desse efeito específico, multiplicado
    pelo volume mestre de efeitos escolhido em Configurações
    (sfx_volume) — ex.: um efeito já pedido mais baixo (volume=0.6)
    continua proporcionalmente mais baixo em qualquer volume mestre.
    Silencioso se o arquivo ainda não existir — ver PLANO_AUDIO.md."""
    try:
        sound = _resolve_sound(name)
        sound.set_volume(volume * sfx_volume)
        sound.play()
    except Exception:
        pass


load_settings()
