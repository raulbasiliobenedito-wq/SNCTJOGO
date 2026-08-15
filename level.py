import pygame
from enemy import Slime
from platform import Platform
from settings import ASSET_DIR, PLAYER_HEIGHT
from tiled_map import TiledMap


class _StaticZone:
    """Área fixa com um atributo .rect, para reaproveitar código (como o
    patrulhamento do Slime) que espera algo com essa interface, mesmo sem
    ser uma Platform de verdade — ex.: chão pintado direto no Tiled."""

    def __init__(self, rect):
        self.rect = rect


PHASES = [
    {
        "name": "Fase 1 — Escola", "subtitle": "A primeira pergunta pode mudar o mundo.",
        "world": 7420, "world_height": 1450, "world_top": -520, "step": 230, "widths": (160, 150, 170, 145),
        "heights": (650, 575, 505, 560, 470, 540, 600, 515),
        "checkpoints": (6, 11, 15),
        "research": ((4, "Curiosidade"), (7, "Observação"), (10, "Hipótese")),
        "dialogues": ((170, "Professora Ana", "Lia, toda grande descoberta começa com uma pergunta."),
                      (2500, "Lia", "Há um laboratório sob a escola. Talvez eu encontre novas pistas lá.")),
        "moving": (),
    },
    {
        "name": "Fase 2 — Universidade", "subtitle": "Conhecimento se constrói em movimento.",
        "world": 6880, "world_height": 900, "world_top": 0,
        # Layout desenhado à mão (x, y, largura) e verificado com um simulador físico
        # próprio (mesma gravidade/velocidade/pulo do jogo) para garantir que todo
        # salto é alcançável. Larguras múltiplas de 32 encaixam perfeitamente nos tiles.
        "layout": (
            (0, 650, 224), (280, 624, 160), (537, 573, 160), (752, 613, 128),
            (979, 506, 192), (1265, 486, 160), (1509, 591, 192), (1797, 617, 160),
            (2034, 592, 160), (2288, 615, 192), (2579, 585, 160), (2792, 605, 160),
            (3002, 634, 128), (3198, 652, 192), (3481, 567, 96), (3672, 604, 160),
            (3924, 479, 96), (4116, 568, 192), (4358, 618, 96), (4547, 586, 192),
            (4816, 637, 160), (5052, 643, 192), (5294, 548, 160), (5524, 495, 160),
            (5753, 568, 96), (5931, 483, 96), (6062, 490, 128), (6240, 591, 160),
            (6478, 477, 128), (6646, 560, 224),
        ),
        "checkpoints": (11, 24),
        "research": ((6, "Método"), (15, "Dados"), (20, "Análise")),
        "dialogues": ((170, "Mentora Beatriz", "Na universidade, errar também é aprender a investigar."),
                      (3650, "Lia", "Cada dado me aproxima de uma resposta responsável.")),
        "moving": ((4, 90, 110, "x"), (9, 70, 130, "y"), (13, 75, 100, "x"),
                    (18, 80, 140, "y"), (22, 70, 115, "x"), (26, 70, 125, "y")),
        # Decoração puramente visual (não sólida): itens sobre plataformas, bancos
        # e arbustos rentes ao chão do pátio, e flâmulas penduradas do alto.
        "decor_props": ((1, "plant_pot"), (5, "book_stack"), (10, "grad_cap"), (14, "plant_pot"),
                         (19, "book_stack"), (23, "grad_cap"), (27, "plant_pot")),
        "decor_ground": (620, 1950, 3260, 4600, 5950),
        "decor_banners": (900, 2600, 4200, 5900),
    },
    {
        "name": "Fase 3 — Centro de Pesquisa", "subtitle": "Pesquisa é colaboração, coragem e esperança.",
        "world": 8200, "world_height": 900, "world_top": 0, "step": 210, "widths": (130, 120, 145, 115, 135),
        "heights": (650, 570, 485, 550, 440, 525, 410, 500, 585, 475),
        "checkpoints": (17, 34),
        "research": ((9, "Testes"), (21, "Resultados"), (32, "Cura"), (37, "Pesquisa completa")),
        # Posições em x ao longo da descida (mundo agora tem 9600px de largura,
        # ver maps/fase3_pesquisa.tmx v4): a segunda fala dispara perto do
        # fim do percurso, já depois da câmara submersa.
        "dialogues": ((170, "Dra. Sofia", "Lia, ciência é feita por muitas mãos e muitas histórias."),
                      (8900, "Lia", "Chegou a hora de compartilhar a pesquisa com o congresso!")),
        "moving": ((8, 190, 90, "x"), (16, 140, 110, "y"), (25, 220, 90, "x"), (37, 150, 110, "y")),
    },
]

class Level:
    """Fases de plataformas; a primeira também possui um laboratório subterrâneo."""

    BUTTON_NAMES = ("AZUL", "VERDE", "AMARELO", "VERMELHO")
    LEVER_FRAME_DELAY = 6
    LEVER_ACTIVATION_TIME = 300
    ELEVATOR_RETURN_DELAY = 10 * 60
    ELEVATOR_SPEED = 3
    DEFAULT_SPAWN = (100, 650 - PLAYER_HEIGHT)
    DEFAULT_SURFACE_RETURN = (4460, 412)
    ENEMY_PLATFORM_SPAWNS = (
        (3, 8, 12, 15),
        (2, 8, 17, 25),
        (6, 14, 22, 30, 36),
    )

    # Mapa do Tiled por fase (índice em PHASES). Fases sem entrada aqui, ou cujo
    # arquivo ainda não existe em maps/, caem no percurso gerado por código.
    TILED_MAP_FILES = {0: "fase1_escola.tmx", 2: "fase3_pesquisa.tmx"}

    def __init__(self, index):
        self.index = index
        self.data = PHASES[index]
        self.tiled_map = self._load_tiled_map()
        self._configure_world_dimensions()
        self.is_underground = index == 0
        # Tiles pintados numa camada colisao=true (ou chamada "Colisão"/"Collision")
        # viram blocos sólidos automaticamente, sem precisar desenhar objetos.
        self.grounds = list(self.tiled_map.tile_collisions) if self.tiled_map else []
        self.dynamic_platforms = []
        self.platforms = self._build_course()
        self.wall_blocks = self._build_wall_jump_walls() if self.is_underground else []
        # Espinhos (morte instantânea ao toque) e zonas de água (o jogador
        # nada livremente dentro delas — ver Game.move_player). Ambos vêm de
        # objetos tipados na camada "Entidades" do Tiled, sem precisar de
        # nenhum código novo de parsing (mesmo padrão de spawn/checkpoint/livro).
        self.hazards = self._make_hazards()
        self.water_zones = self._make_water_zones()
        self.spawn = self._map_spawn() if self.tiled_map else self.DEFAULT_SPAWN
        self.surface_return = self.DEFAULT_SURFACE_RETURN
        self.enemies = self._make_enemies()
        self.checkpoints = self._make_checkpoints()
        self.research = self._make_research()
        self._reset_lab_state()
        self.university_decor = self._make_university_decor() if self.index == 1 else None
        if self.is_underground:
            self._build_underground_lab()

    def _configure_world_dimensions(self):
        self.world_width = self.data["world"]
        self.world_height = self.data["world_height"]
        self.world_top = self.data["world_top"]
        if self.tiled_map:
            self.world_width = self.tiled_map.pixel_width
            self.world_height = self.tiled_map.pixel_height

    def _reset_lab_state(self):
        self.top_lever = self.bottom_lever = self.panel_lever = None
        self.elevator = None
        self.elevator_target = None
        self.elevator_return_timer = 0
        self.elevator_return_target = None
        self.elevator_lever_timers = {"top": 0, "bottom": 0}
        self.upper_elevator = None
        self.upper_elevator_target = None
        self.upper_elevator_return_timer = 0
        self.upper_elevator_return_target = None
        self.upper_lever_timers = {"bottom": 0, "top": 0}
        # Cada alavanca guarda o quadro atual, o quadro-alvo e o tempo até o
        # próximo movimento. Os quadros 0..4 correspondem às imagens 1..5.
        self.lever_animations = {
            name: {"frame": 0, "target": 0, "delay": 0}
            for name in ("top", "bottom", "upper_bottom", "upper_top", "panel")
        }
        self.upper_bottom_lever = self.upper_top_lever = None
        self.buttons = []
        self.microscope_parts = []
        self.bench = None
        self.return_route_platforms = []
        self.return_route_active = False

    def _load_tiled_map(self):
        filename = self.TILED_MAP_FILES.get(self.index)
        if not filename:
            return None
        path = ASSET_DIR.parent / "maps" / filename
        # Mantém o jogo abrindo caso o arquivo seja removido por acidente. O pacote
        # entregue já inclui os TMX, e o fallback preserva o percurso gerado por código.
        return TiledMap(path) if path.exists() else None

    @staticmethod
    def _rect_from_object(item):
        return pygame.Rect(item["x"], item["y"], item["width"], item["height"])

    @classmethod
    def _platform_from_object(cls, item):
        """Cria uma Platform a partir de um objeto do Tiled. Se o objeto tiver as
        propriedades opcionais "percurso" (pixels) e "periodo" (quadros), a
        plataforma se move sozinha ao longo do eixo "eixo" (x ou y, padrão x) —
        útil para plataformas flutuantes na caverna da Fase 3."""
        properties = item["properties"]
        travel = int(properties.get("percurso", 0) or 0)
        period = int(properties.get("periodo", 0) or 0)
        axis = properties.get("eixo", "x")
        return Platform(
            item["x"],
            item["y"],
            item["width"],
            cls._object_style(item),
            travel,
            period,
            axis,
        )

    @staticmethod
    def _object_style(item):
        value = item["properties"].get("estilo", item["properties"].get("style", "0"))
        styles = {"grama": 0, "madeira": 1, "tijolo": 2, "brick": 2}
        text = str(value)
        numeric_style = int(text) if text.lstrip("-").isdigit() else 0
        return styles.get(text.casefold(), numeric_style)

    def _make_hazards(self):
        if not self.tiled_map:
            return []
        return [
            self._rect_from_object(item)
            for item in self.tiled_map.entities("espinho")
            if item["width"] > 0 and item["height"] > 0
        ]

    def _make_water_zones(self):
        if not self.tiled_map:
            return []
        return [
            self._rect_from_object(item)
            for item in self.tiled_map.entities("agua")
            if item["width"] > 0 and item["height"] > 0
        ]

    def _map_spawn(self):
        item = self.tiled_map.entity("spawn")
        if not item:
            return self.DEFAULT_SPAWN
        return item["x"], item["y"] - PLAYER_HEIGHT

    def _build_course(self):
        if self.index == 0:
            tiled_platforms = self._build_tiled_object_platforms() if self.tiled_map else []
            if tiled_platforms:
                return tiled_platforms
            return self._build_school_course()
        if self.index == 1:
            return self._build_university_course()
        if self.index == 2 and self.tiled_map:
            # A caverna da Fase 3 apoia o chão na camada de colisão pintada no
            # Tiled (self.grounds); esta lista cobre só as plataformas extras
            # (flutuantes/móveis) desenhadas como objetos.
            return self._build_tiled_object_platforms()
        return self._build_generated_course()

    def _build_generated_course(self):
        """Monta a Fase 3 a partir de suas sequências de altura e largura."""
        phase = self.data
        platforms = [Platform(0, 650, 210)]
        moving = {number: values for number, *values in phase["moving"]}
        x, number = 210, 1
        while x < phase["world"] - 320:
            width = phase["widths"][number % len(phase["widths"])]
            height = phase["heights"][number % len(phase["heights"])]
            platforms.append(
                self._platform_with_motion(
                    x,
                    height,
                    width,
                    number % 4,
                    moving.get(number),
                )
            )
            x += phase["step"]
            number += 1
        platforms.append(Platform(phase["world"] - 220, 560, 220, 3))
        return platforms

    @staticmethod
    def _platform_with_motion(x, y, width, image_index, movement=None):
        if movement:
            travel, period, axis = movement
            return Platform(x, y, width, image_index, travel, period, axis)
        return Platform(x, y, width, image_index)

    def _build_tiled_object_platforms(self):
        """Cria plataformas a partir de objetos retangulares do Tiled (grupos
        Plataformas/Plataformas Móveis/Colisões/Collision). Usado pela Fase 1
        (escola) e pela Fase 3 (caverna) quando um mapa do Tiled está carregado."""
        return [
            self._platform_from_object(item)
            for item in self.tiled_map.objects(
                "Plataformas", "Plataformas Móveis", "Colisoes", "Collision"
            )
            if item["width"] > 0 and item["height"] > 0
        ]

    def _draw_automatic_school_platforms(self):
        """Permite desligar a arte provisória quando o cenário for todo pintado no Tiled."""
        if not self.tiled_map:
            return True
        value = self.tiled_map.properties.get("plataformas_automaticas", "true")
        return str(value).casefold() not in ("0", "false", "nao", "não")

    def _build_university_course(self):
        """Percurso com layout desenhado à mão (ver PHASES[1]['layout']), com estilo
        visual variando por trecho do campus: pátio de pedra -> biblioteca -> laboratório.
        Plataformas móveis usam sempre a pele "tech" (índice 3), para o jogador
        identificar de longe quais plataformas se movem."""
        phase = self.data
        layout = phase["layout"]
        moving = {number: values for number, *values in phase["moving"]}
        third = phase["world"] / 3
        platforms = []
        for index, (x, y, width) in enumerate(layout):
            if index in moving:
                platforms.append(self._platform_with_motion(x, y, width, 3, moving[index]))
                continue
            skin = self._university_platform_skin(index, x, third)
            platforms.append(Platform(x, y, width, skin))
        return platforms

    @staticmethod
    def _university_platform_skin(index, x, third):
        if index == 0 or x < third:
            return 0
        if x < 2 * third:
            return 1
        return 2

    def _make_university_decor(self):
        """Pré-calcula posições de decoração (não sólida) da Fase 2: itens sobre
        plataformas específicas, bancos/arbustos rentes ao chão e flâmulas no alto."""
        on_platform = []
        for platform_number, prop_name in self.data["decor_props"]:
            platform = self.platforms[platform_number]
            on_platform.append((platform.rect.right - 40, platform.rect.top, prop_name))
        ground = [(x, "bench") for x in self.data["decor_ground"]]
        ground += [(x + 70, "bush") for x in self.data["decor_ground"]]
        banners = [(x, "banner") for x in self.data["decor_banners"]]
        return {"on_platform": on_platform, "ground": ground, "banners": banners}

    @staticmethod
    def _build_school_course():
        """Percurso longo da escola: vãos de dash e duas torres de pulo na parede."""
        layout = [
            # O espaço vazio em x=1750 e x=2670 é ocupado somente pelos elevadores.
            (0, 650, 256), (360, 600, 160), (640, 515, 160), (950, 590, 160),
            (1270, 475, 192), (2020, 450, 160), (2330, 525, 160),
            # As plataformas altas ficam afastadas da parede: Lia ganha espaço para quicar e pousar.
            # Lia reaparece após o laboratório no começo desta rota final.
            (4420, 460, 160), (4770, 560, 192), (5250, 650, 192),
            # A segunda torre consolida a mecânica antes do trecho final com dash.
            (5280, 405, 160), (5780, 465, 160), (6110, 545, 160), (6450, 620, 192),
            (6480, 380, 160), (6840, 500, 160), (7200, 520, 224),
        ]
        return [Platform(x, y, width, index % 3) for index, (x, y, width) in enumerate(layout)]

    def _build_wall_jump_walls(self):
        if self.tiled_map:
            walls = [
                self._rect_from_object(item)
                for item in self.tiled_map.objects("Paredes", "Wall Jump")
                if item["width"] > 0 and item["height"] > 0
            ]
            if walls:
                return walls
        return [
            pygame.Rect(wall_x, wall_y, 32, 32)
            for wall_x, wall_top in ((5540, 450), (6740, 420))
            for wall_y in range(wall_top, 650, 32)
        ]

    def _build_underground_lab(self):
        if self.tiled_map:
            self._build_tiled_underground_lab()
        else:
            self._build_default_underground_lab()

    def _build_default_underground_lab(self):
        """Mantém o laboratório manual como fallback para a Fase 1."""
        # O elevador substitui a plataforma inútil que ficava logo abaixo da superfície.
        self.elevator_top, self.elevator_bottom = 650, 1090
        self.elevator = Platform(2670, self.elevator_top, 160, 2)
        self.elevator_target = self.elevator_top
        self.platforms.append(self.elevator)

        # Segundo elevador: leva à área suspensa onde ficam os botões do painel.
        self.upper_elevator_bottom, self.upper_elevator_top = 575, 100
        self.upper_elevator = Platform(1750, self.upper_elevator_bottom, 160, 1)
        self.upper_elevator_target = self.upper_elevator_bottom
        self.platforms.append(self.upper_elevator)

        upper_platforms = [
            (1995, 100, 160), (2210, 0, 160), (2410, 90, 145),
            (2610, 0, 160), (2810, 100, 150),
        ]
        self._append_platform_layout(upper_platforms, style_offset=1)

        underground = [
            (2940, 1090, 160), (3140, 1000, 145), (3340, 1090, 160), (3560, 1000, 145),
            (3760, 1090, 160), (3980, 1010, 145), (4180, 1110, 165), (4390, 1040, 145),
            (4580, 1120, 170), (4790, 1040, 145), (4980, 950, 160),
        ]
        self._append_platform_layout(underground)

        # Caminho de volta ao percurso principal. Ele aparece somente depois da
        # montagem, para Lia precisar concluir o laboratório antes de seguir.
        return_route = [
            (5100, 820, 140), (4890, 700, 140),
            (4690, 580, 150), (4470, 460, 180),
        ]
        self.return_route_platforms = [
            Platform(x, y, width, (i + 2) % 4)
            for i, (x, y, width) in enumerate(return_route)
        ]

        self._configure_elevator_levers()
        self.panel_lever = pygame.Rect(3180, 948, 34, 52)

        button_platforms = ((2210, 0, 160), (2410, 90, 145), (2610, 0, 160), (2810, 100, 150))
        self.buttons = [
            pygame.Rect(x + width // 2 - 18, y - 20, 36, 20)
            for x, y, width in button_platforms
        ]

        self.microscope_parts = [
            # As imagens das peças ocupam 64x64; a base continua apoiada na plataforma.
            (pygame.Rect(4423, 976, 64, 64), "Lente"),
            (pygame.Rect(4633, 1056, 64, 64), "Base"),
            (pygame.Rect(4823, 976, 64, 64), "Luz"),
            (pygame.Rect(5023, 886, 64, 64), "Ocular"),
        ]
        self.research.extend([
            # Livros distribuídos pelo laboratório, em vez de agrupados no mesmo trecho.
            (pygame.Rect(3380, 1052, 28, 34), "Experimento"),
            (pygame.Rect(4220, 1072, 28, 34), "Registro"),
        ])
        self.bench = pygame.Rect(4940, 870, 110, 80)

    def _append_platform_layout(self, layout, style_offset=0):
        self.platforms.extend(
            Platform(x, y, width, (index + style_offset) % 4)
            for index, (x, y, width) in enumerate(layout)
        )

    def _configure_elevator_levers(self):
        self.top_lever = self._lever_above(self.elevator)
        self.bottom_lever = None
        self.upper_bottom_lever = self._lever_above(self.upper_elevator)
        self.upper_top_lever = None

    @staticmethod
    def _lever_above(platform):
        return pygame.Rect(
            platform.rect.centerx - 17,
            platform.rect.top - 52,
            34,
            52,
        )

    def _build_tiled_underground_lab(self):
        """Lê os objetos especiais da camada Entidades do mapa do Tiled."""
        lower = self.tiled_map.entity("elevador_principal")
        upper = self.tiled_map.entity("elevador_superior")
        if not lower or not upper:
            raise ValueError(
                "O mapa fase1_escola.tmx precisa dos objetos elevador_principal e elevador_superior."
            )

        self.elevator_top = int(lower["properties"].get("top", lower["y"]))
        self.elevator_bottom = int(lower["properties"].get("bottom", lower["y"]))
        self.elevator = self._platform_from_object(lower)
        self.elevator_target = self.elevator.y
        self._add_dynamic_platform(self.elevator)

        self.upper_elevator_top = int(upper["properties"].get("top", upper["y"]))
        self.upper_elevator_bottom = int(upper["properties"].get("bottom", upper["y"]))
        self.upper_elevator = self._platform_from_object(upper)
        self.upper_elevator_target = self.upper_elevator.y
        self._add_dynamic_platform(self.upper_elevator)

        self.return_route_platforms = [
            self._platform_from_object(item)
            for item in self.tiled_map.objects("Rota Retorno")
            if item["width"] > 0 and item["height"] > 0
        ]

        self._configure_elevator_levers()
        panel = self.tiled_map.entity("painel")
        self.panel_lever = self._rect_from_object(panel) if panel else pygame.Rect(3180, 948, 34, 52)

        buttons = self.tiled_map.entities("botao")
        self.buttons = [
            self._rect_from_object(item)
            for item in sorted(buttons, key=lambda item: int(item["properties"].get("ordem", 0)))
        ]
        parts = self.tiled_map.entities("parte_microscopio")
        self.microscope_parts = [
            (self._rect_from_object(item), item["properties"].get("nome", "Peça"))
            for item in sorted(parts, key=lambda item: int(item["properties"].get("ordem", 0)))
        ]
        bench = self.tiled_map.entity("bancada")
        self.bench = self._rect_from_object(bench) if bench else pygame.Rect(4940, 870, 110, 80)
        return_point = self.tiled_map.entity("retorno_superficie")
        if return_point:
            self.surface_return = (return_point["x"], return_point["y"] - PLAYER_HEIGHT)

    def _add_dynamic_platform(self, platform):
        self.platforms.append(platform)
        self.dynamic_platforms.append(platform)

    def activate_return_route(self):
        """Libera as plataformas que conectam o laboratório ao caminho superior."""
        if not self.return_route_active:
            self.return_route_active = True
            self.platforms.extend(self.return_route_platforms)
            self.dynamic_platforms.extend(self.return_route_platforms)

    def call_elevator(self, direction):
        """Move o elevador e agenda o retorno automático após dez segundos."""
        lever_name = "top" if direction == "down" else "bottom"
        if self.elevator_lever_timers[lever_name] != 0:
            return
        self.elevator_target = self._alternate_target(
            self.elevator_target,
            self.elevator_top,
            self.elevator_bottom,
        )
        self.elevator_return_target = self._alternate_target(
            self.elevator_target,
            self.elevator_top,
            self.elevator_bottom,
        )
        self.elevator_return_timer = self.ELEVATOR_RETURN_DELAY
        self.elevator_lever_timers[lever_name] = self.LEVER_ACTIVATION_TIME
        self.set_lever_active(lever_name, True)

    def elevator_lever_active(self, lever_name):
        return self.elevator_lever_timers[lever_name] > 0

    def call_upper_elevator(self, direction):
        lever_name = "bottom" if direction == "up" else "top"
        if self.upper_lever_timers[lever_name] != 0:
            return
        self.upper_elevator_target = self._alternate_target(
            self.upper_elevator_target,
            self.upper_elevator_top,
            self.upper_elevator_bottom,
        )
        self.upper_elevator_return_target = self._alternate_target(
            self.upper_elevator_target,
            self.upper_elevator_top,
            self.upper_elevator_bottom,
        )
        self.upper_elevator_return_timer = self.ELEVATOR_RETURN_DELAY
        self.upper_lever_timers[lever_name] = self.LEVER_ACTIVATION_TIME
        self.set_lever_active(f"upper_{lever_name}", True)

    def upper_lever_active(self, lever_name):
        return self.upper_lever_timers[lever_name] > 0

    @staticmethod
    def _alternate_target(current, top, bottom):
        return bottom if current == top else top

    def set_lever_active(self, lever_name, active):
        """Inicia a animação para o estado acionado ou de repouso."""
        animation = self.lever_animations[lever_name]
        animation["target"] = 4 if active else 0
        animation["delay"] = 0

    def update_lever_animations(self):
        for animation in self.lever_animations.values():
            if animation["frame"] == animation["target"]:
                continue
            animation["delay"] += 1
            if animation["delay"] >= self.LEVER_FRAME_DELAY:
                animation["frame"] += 1 if animation["target"] > animation["frame"] else -1
                animation["delay"] = 0

    def lever_image(self, lever_name, puzzle_sprites):
        return puzzle_sprites["lever_animation"][self.lever_animations[lever_name]["frame"]]

    @staticmethod
    def _move_elevator(elevator, target):
        old_y = elevator.y
        if elevator.y < target:
            elevator.y = min(target, elevator.y + Level.ELEVATOR_SPEED)
        elif elevator.y > target:
            elevator.y = max(target, elevator.y - Level.ELEVATOR_SPEED)
        elevator.dy = elevator.y - old_y

    def _make_checkpoints(self):
        if self.tiled_map:
            return [
                self._rect_from_object(item)
                for item in self.tiled_map.entities("checkpoint")
            ]
        return [
            pygame.Rect(
                self.platforms[number].rect.x + 20,
                self.platforms[number].rect.top - 90,
                35,
                90,
            )
            for number in self.data["checkpoints"]
        ]

    def _make_research(self):
        if self.tiled_map:
            return [
                (
                    self._rect_from_object(item),
                    item["properties"].get("nome", "Pesquisa"),
                )
                for item in self.tiled_map.entities("livro")
            ]
        return [
            (
                pygame.Rect(
                    self.platforms[number].rect.centerx - 14,
                    self.platforms[number].rect.top - 38,
                    28,
                    34,
                ),
                name,
            )
            for number, name in self.data["research"]
        ]

    def _make_enemies(self):
        if self.tiled_map:
            return self._make_tiled_enemies()
        spawn_numbers = self.ENEMY_PLATFORM_SPAWNS[self.index]
        return [
            Slime(self.platforms[number])
            for number in spawn_numbers
            if number < len(self.platforms)
        ]

    def _make_tiled_enemies(self):
        enemies = []
        for item in self.tiled_map.entities("slime"):
            platform = self._enemy_platform_from_map_object(item)
            if platform:
                enemies.append(Slime(platform))
        return enemies

    def _enemy_platform_from_map_object(self, item):
        center_x = item["x"] + item["width"] // 2
        candidates = [
            platform
            for platform in self.platforms
            if platform.rect.left - 10 <= center_x <= platform.rect.right + 10
        ]
        best = min(
            candidates,
            key=lambda platform: abs(platform.rect.top - item["y"]),
            default=None,
        )
        # Na caverna da Fase 3 o chão normalmente vem da camada de colisão
        # pintada no Tiled (self.grounds), não de objetos Platform — nesse
        # caso, funde os tiles de chão contíguos sob o slime numa área de
        # patrulha.
        return best or self._ground_zone_at(item)

    def _ground_zone_at(self, item):
        """Funde os tiles de solo contíguos (mesma linha) mais próximos do
        objeto num único retângulo, para o slime patrulhar sobre chão
        pintado direto no Tiled (sem objeto Platform)."""
        center_x = item["x"] + item["width"] // 2
        column_rects = [rect for rect in self.grounds if rect.left <= center_x < rect.right]
        if not column_rects:
            return None
        surface = min(column_rects, key=lambda rect: rect.top)
        row_rects = sorted(
            (rect for rect in self.grounds if rect.top == surface.top),
            key=lambda rect: rect.left,
        )
        index = row_rects.index(surface)
        left = index
        while left > 0 and row_rects[left - 1].right == row_rects[left].left:
            left -= 1
        right = index
        while right < len(row_rects) - 1 and row_rects[right + 1].left == row_rects[right].right:
            right += 1
        span = pygame.Rect(
            row_rects[left].left,
            surface.top,
            row_rects[right].right - row_rects[left].left,
            surface.height,
        )
        return _StaticZone(span)

    def update(self):
        for platform in self.platforms:
            platform.update()
        for enemy in self.enemies:
            enemy.update()
        if self.is_underground:
            self._update_lever_timers(self.elevator_lever_timers)
            self._update_lever_timers(self.upper_lever_timers, "upper_")
            self._update_elevator_return_timers()
            self.update_lever_animations()
            self._move_elevator(self.elevator, self.elevator_target)
            self._move_elevator(self.upper_elevator, self.upper_elevator_target)
            self._update_elevator_lever_positions()

    def _update_lever_timers(self, timers, name_prefix=""):
        for name, timer in timers.items():
            was_active = timer > 0
            timers[name] = max(0, timer - 1)
            if was_active and timers[name] == 0:
                self.set_lever_active(f"{name_prefix}{name}", False)

    def _update_elevator_return_timers(self):
        self.elevator_return_timer = self._update_return_timer(
            self.elevator_return_timer,
            self.elevator_return_target,
            "elevator_target",
        )
        self.upper_elevator_return_timer = self._update_return_timer(
            self.upper_elevator_return_timer,
            self.upper_elevator_return_target,
            "upper_elevator_target",
        )

    def _update_return_timer(self, timer, return_target, target_name):
        if not timer:
            return 0
        timer -= 1
        if timer == 0:
            setattr(self, target_name, return_target)
        return timer

    def _update_elevator_lever_positions(self):
        self.top_lever.midbottom = (self.elevator.rect.centerx, self.elevator.rect.top)
        self.upper_bottom_lever.midbottom = (
            self.upper_elevator.rect.centerx,
            self.upper_elevator.rect.top,
        )

    def draw(self, surface, camera_x, camera_y, tiles, book_image, checkpoint_image, _checkpoint,
             collected, lever_on, sequence_progress, sequence_solved, microscope_collected,
             microscope_assembled, puzzle_sprites, slime_sprites, school_sprites, text_fn,
             university_tiles=None, university_props=None):
        if self.tiled_map:
            self.tiled_map.draw(surface, camera_x, camera_y)
        if self.index == 1 and self.university_decor:
            self._draw_university_backdrop(surface, camera_x, camera_y, university_props)

        self._draw_platforms(
            surface,
            camera_x,
            camera_y,
            tiles,
            school_sprites,
            university_tiles,
        )
        self._draw_school_walls(surface, camera_x, camera_y, school_sprites)
        self._draw_university_platform_props(
            surface,
            camera_x,
            camera_y,
            university_props,
        )
        self._draw_collectibles(
            surface,
            camera_x,
            camera_y,
            book_image,
            checkpoint_image,
            collected,
        )
        if self.is_underground:
            self._draw_lab(
                surface,
                camera_x,
                camera_y,
                lever_on,
                sequence_progress,
                sequence_solved,
                microscope_collected,
                microscope_assembled,
                puzzle_sprites,
                text_fn,
            )
        for enemy in self.enemies:
            enemy.draw(surface, camera_x, camera_y, slime_sprites)

    def _draw_platforms(
        self,
        surface,
        camera_x,
        camera_y,
        tiles,
        school_sprites,
        university_tiles,
    ):
        for platform in self.platforms:
            if self.index == 0:
                if self._should_skip_tiled_platform(platform):
                    continue
                floor_name = ("grass_tile", "wood_tile", "brick_tile")[platform.image_index % 3]
                platform_sprite = school_sprites[floor_name]
                self._draw_school_platform(surface, platform, camera_x, camera_y, platform_sprite)
            elif self.index == 1:
                self._draw_shadow(surface, platform, camera_x, camera_y)
                skin = university_tiles[platform.image_index % len(university_tiles)]
                platform.draw(surface, camera_x, camera_y, skin)
            else:
                platform.draw(surface, camera_x, camera_y, tiles)

    def _should_skip_tiled_platform(self, platform):
        return (
            self.tiled_map
            and platform not in self.dynamic_platforms
            and not self._draw_automatic_school_platforms()
        )

    def _draw_school_walls(self, surface, camera_x, camera_y, school_sprites):
        if self.index == 0 and self._draw_automatic_school_platforms():
            for wall in self.wall_blocks:
                for x in range(wall.left, wall.right, 32):
                    for y in range(wall.top, wall.bottom, 32):
                        surface.blit(
                            school_sprites["brick_tile"],
                            (x - camera_x, y - camera_y),
                        )

    def _draw_university_platform_props(self, surface, camera_x, camera_y, university_props):
        if self.index == 1 and self.university_decor and university_props:
            for world_x, top_y, prop_name in self.university_decor["on_platform"]:
                image = university_props[prop_name]
                surface.blit(image, (world_x - camera_x, top_y - image.get_height() - camera_y))

    def _draw_collectibles(
        self,
        surface,
        camera_x,
        camera_y,
        book_image,
        checkpoint_image,
        collected,
    ):
        for cp in self.checkpoints:
            flag_x = cp.centerx - checkpoint_image.get_width() // 2 - camera_x
            flag_y = cp.bottom - checkpoint_image.get_height() - camera_y
            surface.blit(checkpoint_image, (flag_x, flag_y))
        for index, (item, _) in enumerate(self.research):
            if index not in collected:
                surface.blit(book_image, (item.x - camera_x, item.y - camera_y))

    def _draw_school_platform(self, surface, platform, camera_x, camera_y, platform_sprite):
        """Repete apenas um tile de piso para cada plataforma, sem misturar estilos."""
        for offset in range(0, platform.width, 32):
            surface.blit(platform_sprite, (platform.x + offset - camera_x, platform.y - camera_y))

    @staticmethod
    def _draw_shadow(surface, platform, camera_x, camera_y):
        """Sombra suave sob a plataforma, pra ela parecer apoiada no cenário em vez
        de flutuando desconectada do fundo."""
        shadow = pygame.Surface((platform.width, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (10, 14, 18, 70), (0, 0, platform.width, 10))
        surface.blit(shadow, (platform.x - camera_x, platform.y + 30 - camera_y))

    def _draw_university_backdrop(self, surface, camera_x, camera_y, university_props):
        """Bancos, arbustos e flâmulas do campus — decoração sem colisão, desenhada
        atrás das plataformas para dar profundidade à Fase 2."""
        if not university_props:
            return
        for world_x, prop_name in self.university_decor["banners"]:
            image = university_props[prop_name]
            surface.blit(image, (world_x - camera_x, 0 - camera_y))
        for world_x, prop_name in self.university_decor["ground"]:
            image = university_props[prop_name]
            surface.blit(image, (world_x - camera_x, 784 - image.get_height() - camera_y))

    def _draw_lab(self, surface, camera_x, camera_y, lever_on, sequence_progress,
                  sequence_solved, microscope_collected, microscope_assembled, puzzle_sprites, text_fn):
        top_image = self.lever_image("top", puzzle_sprites)
        panel_image = self.lever_image("panel", puzzle_sprites)
        upper_bottom_image = self.lever_image("upper_bottom", puzzle_sprites)
        # Centraliza cada sprite maior e mantém sua base na posição original.
        for image, lever in ((top_image, self.top_lever), (panel_image, self.panel_lever),
                             (upper_bottom_image, self.upper_bottom_lever)):
            surface.blit(image, (lever.centerx - image.get_width() // 2 - camera_x,
                                 lever.bottom - image.get_height() - camera_y))
        text_fn(surface, "ELEVADOR [E]", (self.top_lever.x-42-camera_x, self.top_lever.y-24-camera_y), 14, "#f4e4a5")
        text_fn(surface, "PAINEL [E]", (self.panel_lever.x-30-camera_x, self.panel_lever.y-24-camera_y), 14, "#f4e4a5")
        text_fn(surface, "ELEVADOR [E]", (self.upper_bottom_lever.x-42-camera_x, self.upper_bottom_lever.y-24-camera_y), 14, "#f4e4a5")

        for index, button in enumerate(self.buttons):
            surface.blit(puzzle_sprites["buttons"][index], (button.x-camera_x, button.y-camera_y))
            if sequence_solved or index < sequence_progress:
                pygame.draw.rect(surface, (225, 255, 218),
                                 (button.x-camera_x, button.y-camera_y, button.width, button.height), 2, border_radius=5)
            text_fn(surface, self.BUTTON_NAMES[index], (button.centerx-camera_x, button.y-20-camera_y), 13, "#ffffff", True)

        for index, (item, _) in enumerate(self.microscope_parts):
            if index in microscope_collected:
                continue
            image = puzzle_sprites["microscope_parts"][index]
            # Peças ficam apagadas até a sequência do painel ser concluída.
            if not sequence_solved:
                image = image.copy()
                image.fill((105, 105, 105, 145), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(image, (item.x-camera_x, item.y-camera_y))

        bench_color = (102, 220, 160) if microscope_assembled else (168, 112, 67)
        pygame.draw.rect(surface, bench_color, (self.bench.x-camera_x, self.bench.y-camera_y, self.bench.width, self.bench.height), border_radius=8)
        pygame.draw.rect(surface, (57, 42, 32), (self.bench.x-camera_x, self.bench.y-camera_y, self.bench.width, self.bench.height), 3, border_radius=8)
        if microscope_assembled:
            image = puzzle_sprites["microscope_complete"]
            surface.blit(image, (self.bench.centerx - image.get_width() // 2 - camera_x,
                                 self.bench.bottom - image.get_height() - camera_y))
        label = "MICROSCÓPIO MONTADO" if microscope_assembled else "BANCADA [E]"
        label_y = self.bench.y - 20 if microscope_assembled else self.bench.y + 27
        text_fn(surface, label, (self.bench.centerx-camera_x, label_y-camera_y), 14, "#ffffff", True)
