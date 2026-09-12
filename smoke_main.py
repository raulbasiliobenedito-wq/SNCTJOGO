"""Executa main.py como o pgzrun executaria — sem abrir janela.

Substitui pgzrun.go() por um stub que (1) injeta os globais que o Pygame
Zero injeta no módulo principal (screen, keyboard, mouse, keys, music,
sounds, Actor, clock), (2) roda o spellcheck de hooks de verdade e (3)
chama update()/draw()/os handlers de mouse e teclado por alguns quadros.

Motivo: bench.py importa game.py direto e nunca passa pelo caminho do
pgzrun, então tudo que só existe no ponto de entrada (nome de parâmetro de
hook, globais injetados, ordem de inicialização) ficava sem teste. Foi
assim que `on_mouse_move(pos, _rel)` chegou na mão do jogador.
"""
import os, sys, types, traceback
from test_support import isolated_game_data

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import pygame
pygame.init()
real_surface = pygame.display.set_mode((1920, 1080))

import pgzero.game, pgzero.screen, pgzero.keyboard, pgzero.constants, pgzero.spellcheck
import pgzero.loaders

frames_run = {'n': 0}

class _FakeMouse:
    LEFT, MIDDLE, RIGHT = 1, 2, 3

def fake_go():
    mod = sys.modules['__main__']
    ns = vars(mod)
    # 1) spellcheck de verdade — é o que derruba o jogo no arranque
    pgzero.spellcheck.spellcheck(ns)
    # 2) globais que o pgzero injeta
    screen = pgzero.screen.Screen(real_surface)
    ns.update({
        'screen': screen,
        'keyboard': pgzero.keyboard.keyboard,
        'keys': pgzero.constants.keys,
        'mouse': _FakeMouse,
        'music': types.SimpleNamespace(
            play=lambda *a, **k: None, play_once=lambda *a, **k: None,
            stop=lambda *a, **k: None, set_volume=lambda *a, **k: None),
        'sounds': types.SimpleNamespace(),
    })
    # 3) roda o laço de verdade: update + draw + handlers
    update, draw = ns['update'], ns['draw']
    for i in range(120):
        update(1 / 60)
        draw()
        frames_run['n'] += 1
        if i == 20:
            ns['on_key_down'](pgzero.constants.keys.ESCAPE)
        if i == 30:
            ns['on_mouse_down']((960, 560), _FakeMouse.LEFT)
        if i == 32:
            ns['on_mouse_move']((970, 560), (10, 0))
        if i == 34:
            ns['on_mouse_up']((970, 560), _FakeMouse.LEFT)
        if i == 60:
            ns['on_key_down'](pgzero.constants.keys.ESCAPE)

import pgzrun
original_go = pgzrun.go
original_main = sys.modules["__main__"]
pgzrun.go = fake_go

try:
    with open(os.path.join(ROOT, 'main.py'), encoding='utf-8') as fh:
        source = fh.read()
    module = types.ModuleType('__main__')
    module.__file__ = os.path.join(ROOT, 'main.py')
    sys.modules['__main__'] = module
    with isolated_game_data():
        exec(compile(source, 'main.py', 'exec'), vars(module))
except Exception:
    print("FALHOU ao executar main.py:")
    traceback.print_exc()
    sys.exit(1)
finally:
    sys.modules["__main__"] = original_main
    pgzrun.go = original_go
    pygame.quit()

print(f"main.py executou de ponta a ponta: {frames_run['n']} quadros, "
      "spellcheck + update + draw + on_key_down + on_mouse_down/move/up OK")
