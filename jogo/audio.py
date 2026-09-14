"""Música, efeitos sonoros e preferências de acessibilidade.

A fachada recebe um backend explícito de `pygame.mixer`, configurado pelos
dois pontos de entrada. Assim os módulos da partida não dependem dos globais
que o Pygame Zero injeta no script desktop.

Por que esse arquivo existe: as trilhas (Suno) e os efeitos vão ser
gerados aos poucos, um de cada vez — ver PLANO_AUDIO.md pra lista
completa, nome de arquivo esperado (convenção do próprio Raul: música
"<nome>_music", efeito "<nome>_sound", ex.: fase_1_music.mp3,
projectile_sound.wav — algumas exceções curtas tipo jump/punch) e
prompt sugerido de cada um. Sem esse encapsulamento, uma tentativa direta
de reprodução DERRUBARIA o jogo com um erro assim que o código tentasse
tocar algo que ainda não tem arquivo em music/ ou
sounds/. Aqui, toda chamada é protegida: falta o arquivo, não toca
nada, e o jogo segue normal — dá pra ir testando cada trilha/efeito
assim que o Raul solta o arquivo certo em music/<nome>.mp3|ogg ou
sounds/<nome>.wav|mp3|ogg, sem precisar mexer em mais nenhuma linha de
código."""

import json
from audio_backend import (
    PygameMixerAudioBackend,
    SilentAudioBackend,
)
from settings import DATA_DIR, ROOT_DIR

_current_track = None
_backend = SilentAudioBackend()
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

_SETTINGS_PATH = DATA_DIR / "audio_settings.json"


def set_backend(backend):
    """Troca a implementação da plataforma e reinicia a faixa conhecida."""
    global _backend, _current_track
    _backend = backend
    _current_track = None


def use_pygame_mixer():
    """Configura caminhos estáveis para o desktop e o WASM."""
    set_backend(
        PygameMixerAudioBackend(ROOT_DIR / "music", ROOT_DIR / "sounds")
    )


def reset_backend():
    """Remove referências da plataforma, útil ao encerrar e nos testes."""
    set_backend(SilentAudioBackend())


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
    também play_music, que reaplica isso toda vez que troca de faixa."""
    global music_volume
    music_volume = min(1.0, max(0.0, value))
    try:
        _backend.set_music_volume(music_volume)
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
        _backend.play_music(name, loop)
        _backend.set_music_volume(music_volume)
        _current_track = name
    except Exception:
        # O recurso ainda não existe — silencioso de propósito.
        pass





def play_sfx(name, volume=1.0):
    """Toca um efeito de uma vez só (sounds/<name>.wav|mp3|ogg — `name`
    pode ter ponto pra indicar subpasta). `volume`
    (0.0-1.0) é o volume relativo desse efeito específico, multiplicado
    pelo volume mestre de efeitos escolhido em Configurações
    (sfx_volume) — ex.: um efeito já pedido mais baixo (volume=0.6)
    continua proporcionalmente mais baixo em qualquer volume mestre.
    Silencioso se o arquivo ainda não existir — ver PLANO_AUDIO.md."""
    try:
        _backend.play_sfx(name, volume * sfx_volume)
    except Exception:
        pass


load_settings()
