"""Regressão e benchmark sem janela: python bench.py [--quick] [--profile 1]."""

import argparse
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

import pygame
from settings import FPS, HEIGHT, WIDTH
from test_support import isolated_game_data

KEYS = ("left", "right", "up", "down", "space", "a", "d", "w", "e", "f", "q", "r",
        "RETURN", "escape", "k_1", "k_2", "k_3")
SCRIPT = (
    (0, "right", True), (120, "space", True), (126, "space", False),
    (200, "f", True), (206, "f", False), (240, "q", True), (246, "q", False),
    (300, "e", True), (306, "e", False), (340, "k_1", True), (346, "k_1", False),
    (380, "right", False), (400, "left", True), (460, "left", False),
    (480, "right", True), (520, "r", True), (526, "r", False),
)


class Keyboard:
    def __init__(self):
        self.clear()

    def clear(self):
        for key in KEYS:
            setattr(self, key, False)


class Screen:
    def __init__(self):
        self.surface = pygame.Surface((WIDTH, HEIGHT)).convert()


def peak_rss_mb():
    """Pico de memória residente; disponível em Unix e Windows."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class MemoryCounters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "peak_working_set", "working_set", "peak_paged", "paged",
                    "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile",
                )
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        query = psapi.GetProcessMemoryInfo
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD]
        query.restype = wintypes.BOOL
        counters = MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not query(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.peak_working_set / 1024 ** 2
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 ** 2 if sys.platform == "darwin" else 1024)


def check_pgzero_hooks():
    """Valida nomes e assinaturas exigidos pelo Pygame Zero, sem iniciar o loop."""
    from pgzero import spellcheck
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8-sig"))
    namespace = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            node.body = [ast.Pass()]
            node.decorator_list = []
            module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
            exec(compile(module, "<hooks>", "exec"), namespace)
    spellcheck.spellcheck(namespace)


def exercise(game, screen, frames):
    keyboard = Keyboard()
    inputs = {}
    for frame, key, value in SCRIPT:
        inputs.setdefault(frame, []).append((key, value))
    states = Counter()
    for frame in range(frames):
        for key, value in inputs.get(frame % 600, ()):
            setattr(keyboard, key, value)
        game.update(keyboard, 1 / FPS)
        game.draw(screen)
        states[game.state] += 1
    return dict(states)


def run(args):
    from game import Game, PLAYING
    from level import VILLAGE

    check_pgzero_hooks()
    print("Hooks desktop: OK")
    random.seed(args.seed)
    start = time.perf_counter()
    game = Game()
    boot_seconds = time.perf_counter() - start
    screen = Screen()
    targets = [("vila", VILLAGE, None), ("fase1", 0, None),
               ("fase2", 1, None), ("fase3", 2, None)]
    if not args.quick:
        targets += [("laboratorio", 1, "laboratorio"), ("biblioteca", 1, "biblioteca"),
                    ("laboratorio_secreto", 0, "laboratorio_secreto")]
    if args.profile:
        wanted = {"vila": "vila", "1": "fase1", "2": "fase2", "3": "fase3"}[args.profile]
        targets = [t for t in targets if t[0] == wanted]
    results = []
    for name, index, room in targets:
        random.seed(args.seed)
        game.lives = 5
        game.shield = 0
        game.inventory = {}
        game.ranged_unlocked = isinstance(index, int) and index > 0
        game.dialogue.close()
        game.load_level(index)
        if room:
            game.enter_room(room)
        game.state = PLAYING
        game.draw(screen)
        initial_hash = hashlib.sha256(pygame.image.tostring(screen.surface, "RGB")).hexdigest()
        if args.capture_dir:
            args.capture_dir.mkdir(parents=True, exist_ok=True)
            pygame.image.save(screen.surface, args.capture_dir / f"{name}.png")
        if args.profile:
            import cProfile
            profiler = cProfile.Profile()
            profiler.enable()
        start = time.perf_counter()
        states = exercise(game, screen, args.frames)
        ms = (time.perf_counter() - start) * 1000 / args.frames
        if args.profile:
            profiler.disable()
            profiler.print_stats(sort="tottime")
        result = {"scene": name, "ms_per_frame": ms, "states": states,
                  "initial_image_sha256": initial_hash,
                  "player": [game.player.x, game.player.y], "lives": game.lives}
        results.append(result)
        print(f"{name:24} {ms:7.2f} ms/quadro | estados: {states}")
    report = {"frames": args.frames, "seed": args.seed, "boot_seconds": boot_seconds,
              "peak_rss_mb": peak_rss_mb(), "results": results}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.compare:
        reference = json.loads(args.compare.read_text(encoding="utf-8"))
        if any(reference[key] != report[key] for key in ("frames", "seed")):
            raise ValueError("A referência deve usar o mesmo número de quadros e a mesma semente")
        previous = {result["scene"]: result for result in reference["results"]}
        differences = []
        for result in results:
            old = previous.get(result["scene"], {})
            for key in ("initial_image_sha256", "player", "lives", "states"):
                if old.get(key) != result[key]:
                    differences.append(f"{result['scene']}: {key}")
        if differences:
            raise AssertionError("Diferenças em relação à referência: " + ", ".join(differences))
        print(f"Referência: pixels iniciais e estado final idênticos nos {len(results)} cenários.")
    print(f"Inicialização: {boot_seconds:.2f}s | pico RSS: {report['peak_rss_mb']:.1f} MiB")
    print(f"OK: {len(results)} cenários sem exceções. O roteiro não substitui uma partida completa.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="Não percorre as três salas")
    parser.add_argument("--profile", choices=("vila", "1", "2", "3"))
    parser.add_argument("--frames", type=int, default=600)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--capture-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--compare", type=Path, help="Compara pixels e simulação com um relatório anterior")
    args = parser.parse_args()
    if args.frames < 1:
        parser.error("--frames deve ser positivo")
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    try:
        with isolated_game_data():
            run(args)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
