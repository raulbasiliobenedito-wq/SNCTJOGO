import math

import pygame


def _normalize(vector):
    x, y = vector
    length = math.hypot(x, y)
    if length == 0:
        return (0.0, 0.0)
    return (x / length, y / length)


def _edge_normals(vertices):
    """Um eixo perpendicular a cada aresta do polígono (SAT testa a
    projeção nesses eixos, não nos vértices em si). Polígono precisa estar
    em ordem (sentido horário ou anti-horário, tanto faz) — cada aresta é
    o vértice atual até o próximo, dando a volta no fim da lista."""
    normals = []
    count = len(vertices)
    for i in range(count):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % count]
        normal = _normalize((-(y2 - y1), x2 - x1))
        if normal != (0.0, 0.0):
            normals.append(normal)
    return normals


def _project(vertices, axis):
    dots = [vx * axis[0] + vy * axis[1] for vx, vy in vertices]
    return min(dots), max(dots)


def _polygon_center(vertices):
    count = len(vertices)
    return (
        sum(v[0] for v in vertices) / count,
        sum(v[1] for v in vertices) / count,
    )


def sat_mtv(vertices_a, vertices_b):
    """Separating Axis Theorem de verdade entre dois polígonos convexos —
    aqui, a hitbox retangular da Lia (4 vértices) contra o triângulo de
    uma rampa (3 vértices, ver Ramp.vertices). Testa um eixo perpendicular
    a CADA aresta dos dois polígonos: se existir um eixo onde as
    projeções não se sobrepõem, os dois não se tocam de verdade (early
    exit, devolve None) — é isso que evita tratar o canto vazio do
    retângulo delimitador da rampa (ver docstring de Ramp) como sólido.

    Sem esse eixo separador, devolve o MTV (menor vetor de translação)
    que tira A de dentro de B: o eixo com a MENOR sobreposição entre
    todos os testados, com o sinal escolhido pela posição relativa dos
    centros dos dois polígonos (empurra A pra longe do centro de B)."""
    axes = _edge_normals(vertices_a) + _edge_normals(vertices_b)
    min_overlap = None
    mtv_axis = None
    for axis in axes:
        a_min, a_max = _project(vertices_a, axis)
        b_min, b_max = _project(vertices_b, axis)
        overlap = min(a_max, b_max) - max(a_min, b_min)
        if overlap <= 0:
            return None
        if min_overlap is None or overlap < min_overlap:
            min_overlap = overlap
            mtv_axis = axis
    if mtv_axis is None:
        return None
    center_a = _polygon_center(vertices_a)
    center_b = _polygon_center(vertices_b)
    direction = (center_a[0] - center_b[0], center_a[1] - center_b[1])
    if direction[0] * mtv_axis[0] + direction[1] * mtv_axis[1] < 0:
        mtv_axis = (-mtv_axis[0], -mtv_axis[1])
    return (mtv_axis[0] * min_overlap, mtv_axis[1] * min_overlap)


class Ramp:
    """Rampa triangular com colisão SAT de verdade (pedido do Raul —
    "coloque colisão SAT para as rampas"), não uma aproximação por
    distância ou por "altura do chão nesse x". Uma instância cobre UM
    tile: identificada pela propriedade "rampa" no tileset do Tiled (ver
    TiledMap._load_tile_ramps/Level._make_ramps), não por um objeto
    posicionado à mão — qualquer tile marcado assim, pintado na camada de
    Colisão, vira um triângulo do tamanho da célula automaticamente
    ("direita", padrão — sobe da esquerda pra direita, tipo "/";
    "esquerda" — sobe da direita pra esquerda, tipo "\\"). Uma fileira de
    tiles-rampa encostados forma uma rampa contínua sozinha.

    A colisão de verdade é o TRIÂNGULO dentro do quadrado do tile, não o
    quadrado inteiro: toda rampa tem um canto vazio (acima da ponta
    baixa) que não deve bloquear nada — só a rampa em si. Por isso ela
    fica de fora de Level.grounds/solids_near (a lista de sólidos
    genérica, toda em AABB) e ganha sua própria checagem em
    Game._resolve_ramp_collisions."""

    def __init__(self, x, y, width, height, rising_right=True):
        self.x, self.y, self.width, self.height = x, y, width, height
        # True = sobe da esquerda pra direita ("/"), False = sobe da
        # direita pra esquerda ("\\") — ver vertices().
        self.rising_right = rising_right

    @property
    def rect(self):
        """Retângulo delimitador — só pra filtro rápido (broad phase,
        `colliderect`) antes de rodar o SAT de verdade, mesmo padrão já
        usado pelos outros sólidos do jogo (ver Level.solids_near)."""
        return pygame.Rect(round(self.x), round(self.y), round(self.width), round(self.height))

    def vertices(self):
        left, top = self.x, self.y
        right, bottom = self.x + self.width, self.y + self.height
        if self.rising_right:
            # "/": baixo na ponta esquerda, alto na ponta direita.
            return [(left, bottom), (right, top), (right, bottom)]
        # "\\": alto na ponta esquerda, baixo na ponta direita.
        return [(left, top), (right, bottom), (left, bottom)]

    def resolve(self, player_rect):
        """Devolve (dx, dy) — o vetor que tira a Lia de dentro do
        triângulo — ou None se elas não se tocam de verdade (o retângulo
        delimitador pode bater sem o triângulo bater, ver docstring da
        classe)."""
        player_vertices = [
            (player_rect.left, player_rect.top),
            (player_rect.right, player_rect.top),
            (player_rect.right, player_rect.bottom),
            (player_rect.left, player_rect.bottom),
        ]
        return sat_mtv(player_vertices, self.vertices())
