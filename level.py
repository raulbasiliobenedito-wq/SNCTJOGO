import pygame
from enemy import Slime
from platform import Platform
from settings import ASSET_DIR, PLAYER_HEIGHT
from tiled_map import TiledMap


PHASES = [
    {
        "name": "Fase 1 — Escola", "subtitle": "A primeira pergunta pode mudar o mundo.",
        "world": 7420, "world_height": 1450, "world_top": -520, "step": 230, "widths": (160, 150, 170, 145),
        "heights": (650, 575, 505, 560, 470, 540, 600, 515),
        "checkpoints": (6, 11, 15),
        "research": ((6, "Curiosidade"), (13, "Observação"), (21, "Hipótese")),
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
        "dialogues": ((170, "Dra. Sofia", "Lia, ciência é feita por muitas mãos e muitas histórias."),
                      (4550, "Lia", "Chegou a hora de compartilhar a pesquisa com o congresso!")),
        "moving": ((8, 190, 90, "x"), (16, 140, 110, "y"), (25, 220, 90, "x"), (37, 150, 110, "y")),
    },
]

# A Fase 1 usa plataformas manuais mais espaçadas. Mantemos os nomes já traduzidos
# no dicionário original, mudando somente onde os livros aparecem.
PHASES[0]["research"] = (
    (4, "Curiosidade"),
    # Os dois livros seguintes ficam nas plataformas altas das torres de parede.
    (7, PHASES[0]["research"][1][1]),
    (10, PHASES[0]["research"][2][1]),
)


class Level:
    """Fases de plataformas; a primeira também possui um laboratório subterrâneo."""
    BUTTON_COLORS = ((55, 142, 230), (74, 184, 101), (238, 198, 54), (215, 70, 68))
    BUTTON_NAMES = ("AZUL", "VERDE", "AMARELO", "VERMELHO")
    LEVER_FRAME_DELAY = 6

    def __init__(self, index):
        self.index, self.data = index, PHASES[index]
        # A primeira fase é lida diretamente do arquivo criado no Tiled.
        # As outras duas continuam usando seus layouts atuais enquanto seus mapas
        # ainda não forem desenhados no editor.
        self.tiled_map = self._load_school_map() if index == 0 else None
        self.world_width = self.data["world"]
        self.world_height = self.data["world_height"]
        self.world_top = self.data["world_top"]
        if self.tiled_map:
            self.world_width = self.tiled_map.pixel_width
            self.world_height = self.tiled_map.pixel_height
        self.is_underground = index == 0
        self.grounds = []
        self.dynamic_platforms = []
        self.platforms = self._build_course()
        self.wall_blocks = self._build_wall_jump_walls() if self.is_underground else []
        self.spawn = self._map_spawn() if self.tiled_map else (100, 650 - PLAYER_HEIGHT)
        self.surface_return = (4460, 412)
        self.enemies = self._make_enemies()
        self.checkpoints = self._make_checkpoints()
        self.research = self._make_research()
        self.top_lever = self.bottom_lever = self.panel_lever = None
        self.elevator = None
        self.elevator_target = None
        self.elevator_lever_timers = {"top": 0, "bottom": 0}
        self.upper_elevator = None
        self.upper_elevator_target = None
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
        self.university_decor = self._make_university_decor() if self.index == 1 else None
        if self.is_underground:
            self._build_underground_lab()

    @staticmethod
    def _map_path():
        return ASSET_DIR.parent / "maps" / "fase1_escola.tmx"

    def _load_school_map(self):
        path = self._map_path()
        # Mantém o jogo abrindo caso o arquivo seja removido por acidente. O pacote
        # entregue já inclui o TMX, e o fallback preserva a fase anterior.
        return TiledMap(path) if path.exists() else None

    @staticmethod
    def _rect_from_object(item):
        return pygame.Rect(item["x"], item["y"], item["width"], item["height"])

    @staticmethod
    def _object_style(item):
        value = item["properties"].get("estilo", item["properties"].get("style", "0"))
        styles = {"grama": 0, "madeira": 1, "tijolo": 2, "brick": 2}
        return styles.get(str(value).casefold(), int(value) if str(value).lstrip("-").isdigit() else 0)

    def _map_spawn(self):
        item = self.tiled_map.entity("spawn")
        if not item:
            return 100, 650 - PLAYER_HEIGHT
        return item["x"], item["y"] - PLAYER_HEIGHT

    def _build_course(self):
        if self.index == 0:
            if self.tiled_map:
                platforms = self._build_school_tiled_course()
                if platforms:
                    return platforms
            return self._build_school_course()
        if self.index == 1:
            return self._build_university_course()
        phase = self.data
        platforms = [Platform(0, 650, 210)]
        x, number = 210, 1
        moving = {entry[0]: entry[1:] for entry in phase["moving"]}
        while x < phase["world"] - 320:
            width = phase["widths"][number % len(phase["widths"])]
            height = phase["heights"][number % len(phase["heights"])]
            if number in moving:
                travel, period, axis = moving[number]
                platforms.append(Platform(x, height, width, number % 4, travel, period, axis))
            else:
                platforms.append(Platform(x, height, width, number % 4))
            x += phase["step"]
            number += 1
        platforms.append(Platform(phase["world"] - 220, 560, 220, 3))
        return platforms

    def _build_school_tiled_course(self):
        """Cria as colisões das plataformas a partir da camada ``Plataformas``."""
        return [
            Platform(item["x"], item["y"], item["width"], self._object_style(item))
            for item in self.tiled_map.objects("Plataformas", "Colisoes", "Collision")
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
        moving = {entry[0]: entry[1:] for entry in phase["moving"]}
        third = phase["world"] / 3
        platforms = []
        for index, (x, y, width) in enumerate(layout):
            if index in moving:
                travel, period, axis = moving[index]
                platforms.append(Platform(x, y, width, 3, travel, period, axis))
                continue
            if index == 0 or x < third:
                skin = 0
            elif x < 2 * third:
                skin = 1
            else:
                skin = 2
            platforms.append(Platform(x, y, width, skin))
        return platforms

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
        walls = []
        for wall_x, wall_top in ((5540, 450), (6740, 420)):
            for wall_y in range(wall_top, 650, 32):
                walls.append(pygame.Rect(wall_x, wall_y, 32, 32))
        return walls

    def _build_underground_lab(self):
        if self.tiled_map:
            self._build_tiled_underground_lab()
            return
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
        self.platforms.extend(Platform(x, y, width, (i + 1) % 4) for i, (x, y, width) in enumerate(upper_platforms))
        underground = [
            (2940, 1090, 160), (3140, 1000, 145), (3340, 1090, 160), (3560, 1000, 145),
            (3760, 1090, 160), (3980, 1010, 145), (4180, 1110, 165), (4390, 1040, 145),
            (4580, 1120, 170), (4790, 1040, 145), (4980, 950, 160),
        ]
        self.platforms.extend(Platform(x, y, width, i % 4) for i, (x, y, width) in enumerate(underground))

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

        # Alavancas de superfÃ­cie acompanham o novo percurso da escola.
        self.top_lever = pygame.Rect(self.elevator.rect.centerx - 17, self.elevator.rect.top - 52, 34, 52)
        self.bottom_lever = None
        self.panel_lever = pygame.Rect(3180, 948, 34, 52)
        self.upper_bottom_lever = pygame.Rect(
            self.upper_elevator.rect.centerx - 17, self.upper_elevator.rect.top - 52, 34, 52
        )
        self.upper_top_lever = None
        button_platforms = ((2210, 0, 160), (2410, 90, 145), (2610, 0, 160), (2810, 100, 150))
        for x, y, width in button_platforms:
            self.buttons.append(pygame.Rect(x + width // 2 - 18, y - 20, 36, 20))

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

    def _build_tiled_underground_lab(self):
        """Lê os objetos especiais da camada ``Entidades`` do mapa do Tiled."""
        lower = self.tiled_map.entity("elevador_principal")
        upper = self.tiled_map.entity("elevador_superior")
        if not lower or not upper:
            raise ValueError(
                "O mapa fase1_escola.tmx precisa dos objetos elevador_principal e elevador_superior."
            )

        self.elevator_top = int(lower["properties"].get("top", lower["y"]))
        self.elevator_bottom = int(lower["properties"].get("bottom", lower["y"]))
        self.elevator = Platform(lower["x"], lower["y"], lower["width"], self._object_style(lower))
        self.elevator_target = self.elevator.y
        self.platforms.append(self.elevator)
        self.dynamic_platforms.append(self.elevator)

        self.upper_elevator_top = int(upper["properties"].get("top", upper["y"]))
        self.upper_elevator_bottom = int(upper["properties"].get("bottom", upper["y"]))
        self.upper_elevator = Platform(upper["x"], upper["y"], upper["width"], self._object_style(upper))
        self.upper_elevator_target = self.upper_elevator.y
        self.platforms.append(self.upper_elevator)
        self.dynamic_platforms.append(self.upper_elevator)

        self.return_route_platforms = [
            Platform(item["x"], item["y"], item["width"], self._object_style(item))
            for item in self.tiled_map.objects("Rota Retorno")
            if item["width"] > 0 and item["height"] > 0
        ]

        # Alavancas elevatórias acompanham sempre a plataforma móvel.
        self.top_lever = pygame.Rect(self.elevator.rect.centerx - 17, self.elevator.rect.top - 52, 34, 52)
        self.bottom_lever = None
        panel = self.tiled_map.entity("painel")
        self.panel_lever = self._rect_from_object(panel) if panel else pygame.Rect(3180, 948, 34, 52)
        self.upper_bottom_lever = pygame.Rect(
            self.upper_elevator.rect.centerx - 17, self.upper_elevator.rect.top - 52, 34, 52
        )
        self.upper_top_lever = None

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

    def activate_return_route(self):
        """Libera as plataformas que conectam o laboratório ao caminho superior."""
        if not self.return_route_active:
            self.return_route_active = True
            self.platforms.extend(self.return_route_platforms)
            self.dynamic_platforms.extend(self.return_route_platforms)

    def call_elevator(self, direction):
        """Move o elevador; a alavanca volta ao repouso após cinco segundos."""
        lever_name = "top" if direction == "down" else "bottom"
        if self.elevator_lever_timers[lever_name] == 0:
            # Alterna o destino: no alto desce; embaixo sobe.
            self.elevator_target = (
                self.elevator_bottom if self.elevator_target == self.elevator_top
                else self.elevator_top
            )
            self.elevator_lever_timers[lever_name] = 300
            self.set_lever_active(lever_name, True)

    def elevator_lever_active(self, lever_name):
        return self.elevator_lever_timers[lever_name] > 0

    def call_upper_elevator(self, direction):
        lever_name = "bottom" if direction == "up" else "top"
        if self.upper_lever_timers[lever_name] == 0:
            # Mesmo comportamento de alternância para o elevador da área superior.
            self.upper_elevator_target = (
                self.upper_elevator_bottom if self.upper_elevator_target == self.upper_elevator_top
                else self.upper_elevator_top
            )
            self.upper_lever_timers[lever_name] = 300
            self.set_lever_active(f"upper_{lever_name}", True)

    def upper_lever_active(self, lever_name):
        return self.upper_lever_timers[lever_name] > 0

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
            elevator.y = min(target, elevator.y + 3)
        elif elevator.y > target:
            elevator.y = max(target, elevator.y - 3)
        elevator.dy = elevator.y - old_y

    def _make_checkpoints(self):
        if self.tiled_map:
            return [self._rect_from_object(item) for item in self.tiled_map.entities("checkpoint")]
        flags = []
        for platform_number in self.data["checkpoints"]:
            platform = self.platforms[platform_number]
            flags.append(pygame.Rect(platform.rect.x + 20, platform.rect.top - 90, 35, 90))
        return flags

    def _make_research(self):
        if self.tiled_map:
            return [
                (self._rect_from_object(item), item["properties"].get("nome", "Pesquisa"))
                for item in self.tiled_map.entities("livro")
            ]
        items = []
        for platform_number, name in self.data["research"]:
            platform = self.platforms[platform_number]
            items.append((pygame.Rect(platform.rect.centerx - 14, platform.rect.top - 38, 28, 34), name))
        return items

    def _make_enemies(self):
        if self.tiled_map:
            enemies = []
            for item in self.tiled_map.entities("slime"):
                center_x = item["x"] + item["width"] // 2
                candidates = [
                    platform for platform in self.platforms
                    if platform.rect.left - 10 <= center_x <= platform.rect.right + 10
                ]
                if candidates:
                    platform = min(candidates, key=lambda current: abs(current.rect.top - item["y"]))
                    enemies.append(Slime(platform))
            return enemies
        # Em cada fase, os slimes patrulham plataformas espaçadas para não bloquear os saltos iniciais.
        spawn_numbers = ((3, 8, 12, 15), (2, 8, 17, 25), (6, 14, 22, 30, 36))[self.index]
        return [Slime(self.platforms[number]) for number in spawn_numbers
                if number < len(self.platforms)]

    def update(self):
        for platform in self.platforms:
            platform.update()
        for enemy in self.enemies:
            enemy.update()
        if self.is_underground:
            for name in self.elevator_lever_timers:
                was_active = self.elevator_lever_timers[name] > 0
                self.elevator_lever_timers[name] = max(0, self.elevator_lever_timers[name] - 1)
                if was_active and self.elevator_lever_timers[name] == 0:
                    self.set_lever_active(name, False)
            for name in self.upper_lever_timers:
                was_active = self.upper_lever_timers[name] > 0
                self.upper_lever_timers[name] = max(0, self.upper_lever_timers[name] - 1)
                if was_active and self.upper_lever_timers[name] == 0:
                    self.set_lever_active(f"upper_{name}", False)
            self.update_lever_animations()
            self._move_elevator(self.elevator, self.elevator_target)
            self._move_elevator(self.upper_elevator, self.upper_elevator_target)
            self.top_lever.midbottom = (self.elevator.rect.centerx, self.elevator.rect.top)
            self.upper_bottom_lever.midbottom = (
                self.upper_elevator.rect.centerx, self.upper_elevator.rect.top
            )

    def draw(self, surface, camera_x, camera_y, tiles, book_image, checkpoint_image, checkpoint,
             collected, lever_on, sequence_progress, sequence_solved, microscope_collected,
             microscope_assembled, puzzle_sprites, slime_sprites, school_sprites, text_fn,
             university_tiles=None, university_props=None):
        if self.tiled_map:
            self.tiled_map.draw(surface, camera_x, camera_y)
        if self.index == 1 and self.university_decor:
            self._draw_university_backdrop(surface, camera_x, camera_y, university_props)
        for platform in self.platforms:
            if self.index == 0:
                if (self.tiled_map and platform not in self.dynamic_platforms
                        and not self._draw_automatic_school_platforms()):
                    continue
                # Cada plataforma mantém um piso único do início ao fim.
                floor_name = ("grass_tile", "wood_tile", "brick_tile")[platform.image_index % 3]
                platform_sprite = school_sprites[floor_name]
                self._draw_school_platform(surface, platform, camera_x, camera_y, platform_sprite)
            elif self.index == 1:
                self._draw_shadow(surface, platform, camera_x, camera_y)
                skin = university_tiles[platform.image_index % len(university_tiles)]
                platform.draw(surface, camera_x, camera_y, skin)
            else:
                platform.draw(surface, camera_x, camera_y, tiles)
        if self.index == 0 and self._draw_automatic_school_platforms():
            for wall in self.wall_blocks:
                for x in range(wall.left, wall.right, 32):
                    for y in range(wall.top, wall.bottom, 32):
                        surface.blit(school_sprites["brick_tile"], (x-camera_x, y-camera_y))
        if self.index == 1 and self.university_decor and university_props:
            for world_x, top_y, prop_name in self.university_decor["on_platform"]:
                image = university_props[prop_name]
                surface.blit(image, (world_x - camera_x, top_y - image.get_height() - camera_y))
        for cp in self.checkpoints:
            flag_x = cp.centerx - checkpoint_image.get_width() // 2 - camera_x
            flag_y = cp.bottom - checkpoint_image.get_height() - camera_y
            surface.blit(checkpoint_image, (flag_x, flag_y))
        for index, (item, _) in enumerate(self.research):
            if index not in collected:
                surface.blit(book_image, (item.x-camera_x, item.y-camera_y))
        if self.is_underground:
            self._draw_lab(surface, camera_x, camera_y, lever_on, sequence_progress,
                           sequence_solved, microscope_collected, microscope_assembled,
                           puzzle_sprites, text_fn)
        for enemy in self.enemies:
            enemy.draw(surface, camera_x, camera_y, slime_sprites)

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
