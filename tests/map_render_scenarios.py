"""Capturas determinísticas do desenho TMX em vários pontos de câmera."""

import hashlib
from pathlib import Path

import pygame

from tiled_map import TiledMap


SURFACE_SIZE = (768, 432)
BACKGROUND = (23, 37, 53, 255)
MAP_DIR = Path(__file__).parents[1] / "jogo" / "maps"

# Inclui bordas de chunks, tiles maiores que o grid, camada de primeiro
# plano e mapas com animação. As coordenadas fracionárias reproduzem a
# suavização usada pela câmera real.
CASES = {
    "vila/left_house_boundary": ("vila.tmx", 224.5, 0.25, 0),
    "vila/tall_house_boundary": ("vila.tmx", 1856.5, 96.25, 0),
    "vila/props_and_animation": ("vila.tmx", 1280.5, 208.25, 350),
    "vila/right_house_boundary": ("vila.tmx", 2240.5, 96.25, 0),
    "school/early_large_tiles": ("fase1_escola.tmx", 480.5, 352.25, 0),
    "school/foreground_boundary": ("fase1_escola.tmx", 896.5, 352.25, 0),
    "school/right_large_tiles": ("fase1_escola.tmx", 6144.5, 352.25, 0),
    "secret_lab/animated_tiles": ("fase1_laboratorio_secreto.tmx", 768.5, 320.25, 375),
    "university/animated_tiles": ("fase2_universidade.tmx", 2048.5, 576.25, 525),
    "library/animated_tiles": ("fase2_biblioteca_sala.tmx", 512.5, 576.25, 725),
    "laboratory/animated_tiles": ("fase2_laboratorio_sala.tmx", 480.5, 576.25, 925),
    "cave/upper_tiles": ("fase3_pesquisa.tmx", 0.5, 0.25, 275),
    "cave/deep_animated_tiles": ("fase3_pesquisa.tmx", 4096.5, 1408.25, 875),
}


def _sha256(surface):
    return hashlib.sha256(pygame.image.tostring(surface, "RGBA")).hexdigest()


def record_map_renderings():
    loaded = {}
    result = {}
    for case_name, (filename, camera_x, camera_y, elapsed_ms) in CASES.items():
        tiled = loaded.setdefault(filename, TiledMap(MAP_DIR / filename))
        tiled.elapsed_ms = elapsed_ms
        tiled._recompute_animation_frames()

        surface = pygame.Surface(SURFACE_SIZE, pygame.SRCALPHA)
        surface.fill(BACKGROUND)
        tiled.draw(surface, camera_x, camera_y)
        base_sha256 = _sha256(surface)

        # Uma faixa opaca representa algo desenhado entre o mapa normal e a
        # camada Frente, como a Lia. Assim a segunda hash também protege a
        # ordem de sobreposição de draw_foreground().
        pygame.draw.rect(surface, (221, 53, 137, 255), (0, 144, SURFACE_SIZE[0], 112))
        tiled.draw_foreground(surface, camera_x, camera_y)
        result[case_name] = {
            "map": filename,
            "camera": [camera_x, camera_y],
            "elapsed_ms": elapsed_ms,
            "base_sha256": base_sha256,
            "foreground_sha256": _sha256(surface),
        }
    return result
