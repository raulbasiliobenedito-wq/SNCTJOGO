"""Harness de regressão + benchmark do Echoes of Life.

Roda as 4 fases + 3 salas, exercita entradas (andar, pular, atacar, dash,
interagir, usar item), captura qualquer exceção, mede ms/quadro e RSS.
Uso:  python3 /home/claude/bench.py [--quick] [--profile FASE]
"""
import os, sys, time, traceback, resource, argparse

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, '/home/claude/snct')
os.chdir('/home/claude/snct')

import pygame
pygame.init()
pygame.display.set_mode((1920, 1080))

KEYS = ("left","right","up","down","space","a","d","w","e","f","q","r",
        "RETURN","escape","k_1","k_2","k_3")

class KB:
    def __init__(self):
        for n in KEYS: setattr(self, n, False)
    def clear(self):
        for n in KEYS: setattr(self, n, False)

class Scr:
    def __init__(self): self.surface = pygame.Surface((1920,1080)).convert()

def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

import game, level

SCRIPT = [   # (quadro, tecla, valor)
    (0,'right',True), (120,'space',True), (126,'space',False),
    (200,'f',True), (206,'f',False), (240,'q',True), (246,'q',False),
    (300,'e',True), (306,'e',False), (340,'k_1',True), (346,'k_1',False),
    (380,'right',False), (400,'left',True), (460,'left',False),
    (480,'right',True), (520,'r',True), (526,'r',False),
]

def exercise(g, scr, kb, frames, collect_errors):
    kb.clear()
    script = dict()
    for f,k,v in SCRIPT: script.setdefault(f, []).append((k,v))
    for i in range(frames):
        for k,v in script.get(i % 600, ()): setattr(kb, k, v)
        try:
            g.update(kb, 1/60)
            g.draw(scr)
        except Exception as e:
            collect_errors.append((i, traceback.format_exc()))
            if len(collect_errors) > 3: return

def check_pgzero_hooks():
    """Roda a MESMA validação que o pgzero faz ao abrir o jogo.

    Existe porque este harness importa game.py direto e NUNCA passa por
    pgzrun.go() — então um hook com nome de parâmetro errado (o pgzero
    valida os NOMES, ver pgzero/spellcheck.py) passava em todos os testes
    aqui e só quebrava na mão de quem ia jogar. Foi exatamente o que
    aconteceu com `on_mouse_move(pos, _rel)`: o `_rel` calava o pyflakes e
    derrubava o jogo no arranque com InvalidParameter.

    Não importa main.py de verdade (isso dispararia pgzrun.go()): lê o
    arquivo, recria cada função de topo com a mesma assinatura e corpo
    vazio, e submete esse namespace ao spellcheck.
    """
    import ast
    from pgzero import spellcheck
    problems = []
    for entry in ("main.py", "main_web.py"):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), entry)
        if not os.path.exists(path):
            continue
        tree = ast.parse(open(path, encoding="utf-8").read())
        namespace = {}
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            stub = ast.FunctionDef(
                name=node.name, args=node.args, body=[ast.Pass()],
                decorator_list=[], returns=None, type_params=[],
            )
            module = ast.fix_missing_locations(ast.Module(body=[stub], type_ignores=[]))
            scope = {}
            exec(compile(module, "<check>", "exec"), scope)
            namespace[node.name] = scope[node.name]
        try:
            spellcheck.spellcheck(namespace)
        except Exception as exc:
            problems.append(f"{entry}: {type(exc).__name__}: {exc}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--profile', default=None)
    ap.add_argument('--frames', type=int, default=250)
    args = ap.parse_args()

    scr, kb = Scr(), KB()
    errors = []

    hook_problems = check_pgzero_hooks()
    if hook_problems:
        print("!!! HOOKS DO PYGAME ZERO INVÁLIDOS — o jogo NÃO abre com pgzrun !!!")
        for problem in hook_problems:
            print("   ", problem)
        sys.exit(1)
    print("Hooks do Pygame Zero .. OK (main.py e main_web.py abrem com pgzrun)")
    print("                        (para o teste completo do ponto de entrada, "
          "rode tambem: python smoke_main.py)")

    t0 = time.perf_counter()
    g = game.Game()
    boot = time.perf_counter() - t0
    rss_boot = rss_mb()
    print(f"Game() ................ {boot:5.2f} s de carregamento | RSS {rss_boot:6.1f} MB")

    targets = [(level.VILLAGE,'Vila'), (0,'Fase 1'), (1,'Fase 2'), (2,'Fase 3')]
    rooms   = [('laboratorio',1), ('biblioteca',1), ('laboratorio_secreto',0)]

    if args.profile:
        import cProfile, pstats, io
        idx = {'vila':level.VILLAGE,'1':0,'2':1,'3':2}[args.profile]
        g.load_level(idx); g.state = game.PLAYING
        exercise(g, scr, kb, 40, errors)
        pr = cProfile.Profile(); pr.enable()
        exercise(g, scr, kb, 300, errors)
        pr.disable()
        s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats('tottime').print_stats(18)
        print(s.getvalue())
        return

    results = []
    for idx, name in targets:
        try:
            g.load_level(idx)
        except Exception:
            errors.append((name, traceback.format_exc())); continue
        g.state = game.PLAYING
        exercise(g, scr, kb, 30, errors)
        t = time.perf_counter(); exercise(g, scr, kb, args.frames, errors)
        ms = (time.perf_counter()-t)/args.frames*1000
        results.append((name, ms))
    if not args.quick:
        for room, base in rooms:
            try:
                g.load_level(base); g.enter_room(room)
            except Exception:
                errors.append((room, traceback.format_exc())); continue
            g.state = game.PLAYING
            exercise(g, scr, kb, 30, errors)
            t = time.perf_counter(); exercise(g, scr, kb, args.frames, errors)
            ms = (time.perf_counter()-t)/args.frames*1000
            results.append(('sala:'+room, ms))

    print()
    for name, ms in results:
        print(f"  {name:<26} {ms:6.2f} ms/quadro   ({1000/ms:5.1f} fps teóricos)")
    print()
    print(f"RSS final ............. {rss_mb():6.1f} MB")
    if errors:
        print(f"\n!!! {len(errors)} ERRO(S) DURANTE A EXECUÇÃO !!!")
        for where, tb in errors[:4]:
            print(f"--- em {where} ---"); print(tb)
        sys.exit(1)
    print("\nOK: nenhuma exceção nas 4 fases + 3 salas.")

main()
