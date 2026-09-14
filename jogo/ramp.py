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
    """Rampa cuja forma sólida vem dos pixels alpha do próprio tile.

    O triângulo SAT continua disponível como fallback para rampas criadas
    por código, mas as rampas dos mapas recebem uma máscara. A superfície
    dessa máscara é resolvida verticalmente: subir não aplica a componente
    horizontal da normal da diagonal e, portanto, não empurra a Lia para
    trás. Laterais e parte inferior usam separação pixel a pixel.
    """

    def __init__(
        self,
        x,
        y,
        width,
        height,
        rising_right=True,
        collision_mask=None,
    ):
        self.x, self.y, self.width, self.height = x, y, width, height
        self.rising_right = rising_right
        self.collision_mask = collision_mask
        self._top_profile = (
            self._build_top_profile(collision_mask)
            if collision_mask is not None
            else None
        )

    @property
    def rect(self):
        """Retângulo delimitador usado somente no broad phase."""
        return pygame.Rect(round(self.x), round(self.y), round(self.width), round(self.height))

    def vertices(self):
        left, top = self.x, self.y
        right, bottom = self.x + self.width, self.y + self.height
        if self.rising_right:
            # "/": baixo na ponta esquerda, alto na ponta direita.
            return [(left, bottom), (right, top), (right, bottom)]
        # "\\": alto na ponta esquerda, baixo na ponta direita.
        return [(left, top), (right, bottom), (left, bottom)]

    @staticmethod
    def _build_top_profile(collision_mask):
        """Primeiro pixel sólido de cada coluna, calculado só no load."""
        width, height = collision_mask.get_size()
        return tuple(
            next(
                (y for y in range(height) if collision_mask.get_at((x, y))),
                None,
            )
            for x in range(width)
        )

    def _surface_y(self, left, right):
        """Pixel mais alto da rampa sob a largura atual da hitbox."""
        if self._top_profile is None:
            return None
        ramp_left = round(self.x)
        start = max(left, ramp_left) - ramp_left
        stop = min(right, ramp_left + len(self._top_profile)) - ramp_left
        heights = [
            self._top_profile[x]
            for x in range(start, stop)
            if self._top_profile[x] is not None
        ]
        if not heights:
            return None
        return round(self.y) + min(heights)

    def _mask_overlaps(self, player_mask, offset):
        return self.collision_mask.overlap(player_mask, offset) is not None

    def _clearance(self, player_mask, offset, step, limit):
        """Primeiro deslocamento inteiro no eixo que elimina o overlap."""
        for distance in range(1, limit + 1):
            shifted = (
                offset[0] + step[0] * distance,
                offset[1] + step[1] * distance,
            )
            if not self._mask_overlaps(player_mask, shifted):
                return step[0] * distance, step[1] * distance
        return None

    def _resolve_mask_overlap(self, player_rect, vx, vy):
        player_mask = pygame.Mask(player_rect.size, fill=True)
        offset = (
            player_rect.left - round(self.x),
            player_rect.top - round(self.y),
        )
        if not self._mask_overlaps(player_mask, offset):
            return None

        limits = {
            "left": self.width + player_rect.width,
            "right": self.width + player_rect.width,
            "up": self.height + player_rect.height,
            "down": self.height + player_rect.height,
        }
        steps = {
            "left": (-1, 0),
            "right": (1, 0),
            "up": (0, -1),
            "down": (0, 1),
        }
        candidates = {
            name: self._clearance(
                player_mask,
                offset,
                step,
                round(limits[name]),
            )
            for name, step in steps.items()
        }
        if vy < 0:
            order = ["down", "right" if vx < 0 else "left", "up"]
        elif vx > 0:
            order = ["left", "up", "down", "right"]
        elif vx < 0:
            order = ["right", "up", "down", "left"]
        else:
            available = [value for value in candidates.values() if value]
            if not available:
                return None
            dx, dy = min(available, key=lambda value: abs(value[0]) + abs(value[1]))
            return dx, dy, dx == 0 and dy < 0 and vy >= 0

        for name in order:
            candidate = candidates.get(name)
            if candidate is not None:
                dx, dy = candidate
                return dx, dy, dx == 0 and dy < 0 and vy >= 0
        return None

    def surface_resolution(
        self,
        player_rect,
        vx=0,
        vy=0,
        was_grounded=False,
        allow_snap=True,
    ):
        """Ajuste vertical necessário para acompanhar o contorno superior."""
        if self.collision_mask is None:
            return None
        surface_y = self._surface_y(player_rect.left, player_rect.right)
        if surface_y is None or vy < 0:
            return None
        delta_y = surface_y - player_rect.bottom
        climb_limit = math.ceil(max(abs(vx), vy, 1)) + 2
        snap_limit = math.ceil(max(abs(vx), 1)) + 2
        if -climb_limit <= delta_y <= 0:
            return 0, delta_y, True
        if allow_snap and was_grounded and 0 < delta_y <= snap_limit:
            return 0, delta_y, True
        return None

    def resolve(self, player_rect, vx=0, vy=0, was_grounded=False, allow_snap=True):
        """Devolve ``(dx, dy, apoiado)`` usando os pixels da rampa.

        A tolerância de subida acompanha o deslocamento do quadro. Isso
        permite vencer cada degrau do contorno 2x2 sem transformar uma
        parede alta na ponta da rampa em subida automática. Ao descer, o
        snap só é permitido se a Lia já estava apoiada no quadro anterior.
        """
        if self.collision_mask is not None:
            surface = self.surface_resolution(
                player_rect,
                vx,
                vy,
                was_grounded,
                allow_snap,
            )
            if surface is not None:
                return surface
            return self._resolve_mask_overlap(player_rect, vx, vy)

        player_vertices = [
            (player_rect.left, player_rect.top),
            (player_rect.right, player_rect.top),
            (player_rect.right, player_rect.bottom),
            (player_rect.left, player_rect.bottom),
        ]
        mtv = sat_mtv(player_vertices, self.vertices())
        if mtv is None:
            return None
        dx, dy = mtv
        return dx, dy, dy < 0 and vy >= 0
