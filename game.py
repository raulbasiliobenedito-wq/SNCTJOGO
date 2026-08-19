"""Orquestra o ciclo de jogo, as interações e a renderização."""

import random

import pygame

from cutscene import IntroCutscene
from dialogue import DialogueBox
from hud import draw_ability_ui, draw_hud, draw_inventory, draw_text
from level import PHASES, Level
from player import Player
from vfx import VFXManager
from settings import (
    ASSET_DIR,
    FPS,
    HEIGHT,
    MOTIVATION,
    PLAYER_HEIGHT,
    PLAYER_HITBOX_OFFSET_X,
    PLAYER_HITBOX_WIDTH,
    WIDTH,
)


TITLE = "title"
INTRO = "intro"
PLAYING = "playing"
GAME_OVER = "game_over"
COMPLETE = "complete"

STARTING_LIVES = 3
MAX_LIVES = 5

# Itens (LEIA-ME_bosses_e_itens.md, items.png 16x16, 4 quadros/6fps, 7
# linhas). "consumable" tem efeito imediato ao usar (tecla própria);
# "quest" é drop garantido de chefe e só destrava o avanço da fase em que
# nasceu — nunca é "usado" pelo jogador.
ITEM_DEFS = {
    "gororoba": {"row": 0, "name": "Gororoba", "kind": "consumable", "heal": 1, "shield": 0, "key": "k_1"},
    "essencia_slime": {"row": 1, "name": "Essência de Slime", "kind": "quest", "phase": 0},
    "carcaca_robo": {"row": 2, "name": "Carcaça de Robô", "kind": "consumable", "heal": 0, "shield": 1, "key": "k_2"},
    "livro_magico": {"row": 3, "name": "Livro Mágico", "kind": "quest", "phase": 1},
    "amostra_especime": {"row": 4, "name": "Amostra de Espécime", "kind": "quest", "phase": 1},
    "dark_crystal": {"row": 5, "name": "Dark Crystal", "kind": "consumable", "heal": 1, "shield": 1, "key": "k_3"},
    "sangue_dragao": {"row": 6, "name": "Sangue do Dragão", "kind": "quest", "phase": 2},
}
ITEM_ORDER = (
    "gororoba", "essencia_slime", "carcaca_robo", "livro_magico",
    "amostra_especime", "dark_crystal", "sangue_dragao",
)
# Itens de pesquisa exigidos por fase pra liberar o avanço (ver
# _advance_level_if_ready) — Fase 2 depende dos dois chefes de sala
# (biblioteca e laboratório), então os dois deixam de ser opcionais.
PHASE_REQUIRED_ITEMS = {
    0: ("essencia_slime",),
    1: ("livro_magico", "amostra_especime"),
    2: ("sangue_dragao",),
}
# Tecla pgzero -> item consumível (derivado de ITEM_DEFS, só pros 3 que têm
# uso ativo; os 4 de pesquisa nunca são "usados").
ITEM_USE_KEYS = {
    definition["key"]: key for key, definition in ITEM_DEFS.items() if definition["kind"] == "consumable"
}

# Drop garantido (100%) de cada chefe — LEIA-ME_bosses_e_itens.md §4: os 4
# itens de pesquisa nunca são sorteados, sempre caem.
BOSS_DROP_TABLE = {
    "SlimeKing": "essencia_slime",
    "Librarian": "livro_magico",
    "Specimen": "amostra_especime",
    "Dragon": "sangue_dragao",
}
# Drop por chance dos inimigos comuns de cada fase (item, probabilidade).
ENEMY_DROP_TABLE = {
    "Slime": ("gororoba", 0.40),
    "PossessedStudent": ("carcaca_robo", 0.40),
    "JanitorGuardian": ("carcaca_robo", 0.40),
    "CrystalStag": ("dark_crystal", 0.30),
    "DarkWraith": ("dark_crystal", 0.30),
}
DROP_PICKUP_RADIUS = 22
ATTACK_DURATION = 11
ATTACK_COOLDOWN = 20
STANDARD_ATTACK_POWER = 1
DASH_ATTACK_POWER = 2
STANDARD_ATTACK_REACH = 22
DASH_ATTACK_REACH = 36

CAMERA_X_FOCUS = 0.42
CAMERA_X_SMOOTHING = 0.12
CAMERA_Y_FOCUS = 0.55
CAMERA_Y_SMOOTHING = 0.10

SCIENCE_FACTS = {
    "Curiosidade": "Marie Curie foi a primeira pessoa a receber dois Prêmios Nobel, em áreas científicas diferentes.",
    "Observação": "Bertha Lutz foi uma cientista brasileira e uma das grandes vozes pela participação das mulheres na sociedade.",
    "Hipótese": "Enedina Alves Marques foi a primeira mulher negra a se formar engenheira no Brasil.",
    "Experimento": "Jaqueline Goes de Jesus participou do sequenciamento do genoma do coronavírus no Brasil, em 2020.",
    "Registro": "Nise da Silveira transformou a psiquiatria brasileira com cuidado, arte e respeito às pessoas.",
    "Método": "Ada Lovelace é reconhecida por escrever um dos primeiros algoritmos para uma máquina.",
    "Dados": "Katherine Johnson calculou trajetórias essenciais para missões espaciais da NASA.",
    "Análise": "Sônia Guimarães foi a primeira mulher negra brasileira doutora em Física.",
    "Testes": "Rosalind Franklin produziu imagens de raios X que foram fundamentais para compreender a estrutura do DNA.",
    "Resultados": "Mayana Zatz é referência brasileira em genética humana e no estudo de doenças neuromusculares.",
    "Cura": "Johanna Döbereiner contribuiu para o estudo da fixação de nitrogênio, importante para a agricultura brasileira.",
    "Pesquisa completa": "A ciência avança quando muitas pessoas fazem perguntas, compartilham dados e persistem juntas.",
}
DEFAULT_SCIENCE_FACT = "Toda descoberta começa com uma pergunta e cresce com persistência."

# Lore dos achados opcionais nas salas secundárias (portas) — ao contrário
# de SCIENCE_FACTS, não é sobre cientistas reais: é a história da própria
# universidade amaldiçoada, contada em pedaços pra quem explora fora do
# caminho principal.
ROOM_LORE = {
    "Amostra do Espécime 07": (
        "Um frasco rachado, ainda quente. A etiqueta diz \"ESPÉCIME 07 — NÃO "
        "REMOVER DO TANQUE\", mas alguém removeu mesmo assim."
    ),
    "Página Arrancada": (
        "Uma página solta, arrancada na pressa. A letra muda no meio da "
        "frase — como se quem escrevia tivesse parado de ser humano."
    ),
}
DEFAULT_ROOM_LORE = "Um resquício de algo que este lugar preferia esquecer."

# As 5 cientistas-NPC (LEIA-ME_cientistas.md) — uma por local (ver
# Level.NPC_PLACEMENT). NPC_SPRITE_ROWS bate com a ordem de linhas de
# cientistas_idle.png; NPC_DIALOGUES é o texto fixo mostrado ao apertar [E]
# perto delas, substituindo os antigos diálogos automáticos dos professores.
NPC_SPRITE_ROWS = {
    "Marie Curie": 0,
    "Ada Lovelace": 1,
    "Katherine Johnson": 2,
    "Jaqueline Goes de Jesus": 3,
    "Rosalind Franklin": 4,
}
NPC_DIALOGUES = {
    "Rosalind Franklin": (
        "Minha Foto 51 revelou a estrutura do DNA. Olhe com atenção para o "
        "que os outros ignoram, Lia."
    ),
    "Katherine Johnson": (
        "Calculei à mão as trajetórias que levaram naves ao espaço. Confie "
        "na sua própria conta."
    ),
    "Marie Curie": (
        "Passei anos isolando o rádio, grama por grama. A ciência exige "
        "coragem tanto quanto método."
    ),
    "Ada Lovelace": (
        "Escrevi o primeiro algoritmo antes mesmo de existir a máquina "
        "para executá-lo. Os livros aqui guardam mais do que respostas."
    ),
    "Jaqueline Goes de Jesus": (
        "Sequenciei o genoma do coronavírus com uma equipe inteira ao meu "
        "lado. Compartilhe o que aprendeu, Lia."
    ),
}

SCHOOL_SPRITE_RECTS = {
    "chalkboard": (72, 54, 205, 124),
    "whiteboard": (281, 54, 190, 124),
    "clock": (600, 52, 112, 116),
    "bulletin": (494, 176, 184, 80),
    "exit": (415, 208, 74, 54),
    "plant": (694, 158, 93, 125),
    "desk_row": (912, 152, 310, 94),
    "locker": (1268, 246, 150, 188),
    "bookshelf": (478, 456, 196, 102),
    "door": (250, 554, 136, 190),
    "lab_table": (732, 610, 258, 126),
}
SCHOOL_PLATFORM_SPRITES = {
    "grass_tile": ((448, 756, 32, 64), (32, 32)),
    "wood_tile": ((768, 850, 32, 60), (32, 32)),
    "brick_tile": ((80, 286, 32, 64), (32, 32)),
    "cream_tile": ((80, 456, 32, 64), (32, 32)),
}


class Game:
    """Mantém o estado de uma sessão de jogo e coordena seus componentes."""

    def __init__(self):
        self._load_assets()
        self.player = Player()
        self.dialogue = DialogueBox()
        # Cutscene inicial (mãe de Lia no hospital) — reaproveita a mesma
        # DialogueBox acima pro texto e o quadro parado de Lia pro retrato,
        # ver cutscene.IntroCutscene. Só toca entre TITLE e PLAYING.
        self.intro = IntroCutscene(self.dialogue, self.player.frames[0])
        self.lives = STARTING_LIVES
        # Inventário e escudo atravessam trocas de fase normais (Lia não
        # perde os itens ao avançar) — só zeram ao reiniciar o jogo do zero
        # (ver _update_end_state). self.pending_drops é o oposto: reseta a
        # cada load_level/enter_room/exit_room, porque um item largado no
        # chão de uma sala não faz sentido reaparecer em outro mapa.
        self.inventory = {}
        self.shield = 0
        self.pending_drops = []
        self.camera_x = 0
        self.camera_y = 0
        self.game_over_fade = 0
        self.game_over_characters = 0
        self._reset_combat_state()
        self._reset_input_state()
        self.load_level(0)
        self.state = TITLE

    def _load_assets(self):
        self.tiles = self._load_platform_tiles()
        self.university_tiles = self._load_university_tiles()
        self.university_props = self._load_university_props()
        self._load_backgrounds()
        self.school_sprites = self._load_school_sprites()
        self._create_scene_filters()
        self.player_light = self._create_player_light()
        self.book = self._load_scaled_image("items/book.png", (30, 38))
        self.checkpoint_flag = self._load_image("objects/checkpoint_flag.png")
        self.puzzle_sprites = self._load_puzzle_sprites()
        self.slime_sprites = self._load_slime_sprites()
        self.stag_sprites = self._load_stag_sprites()
        self.wraith_sprites = self._load_wraith_sprites()
        self.student_sprites = self._load_student_sprites()
        self.janitor_sprites = self._load_janitor_sprites()
        self.specimen_sprites = self._load_specimen_sprites()
        self.librarian_sprites = self._load_librarian_sprites()
        self.small_slime_sprites = self._load_small_slime_sprites()
        self.slime_king_sprites = self._load_slime_king_sprites()
        self.dragon_sprites = self._load_dragon_sprites()
        self.item_icons = self._load_item_icons()
        self.scientist_sprites = self._load_scientist_sprites()
        self.artifact_image = self._load_scaled_image("items/artifact_lab.png", (28, 28))
        self.artifact_library_image = self._load_scaled_image("items/artifact_library.png", (28, 28))
        self.vfx = VFXManager(
            ASSET_DIR / "vfx" / "vfx.png",
            {
                "fase2": ASSET_DIR / "vfx" / "vfx_university.png",
                "lab": ASSET_DIR / "vfx" / "vfx_lab.png",
                "library": ASSET_DIR / "vfx" / "vfx_library.png",
            },
        )
        self.lava_lake_frames = self._load_lava_lake_frames()
        self.lab_background = self._load_scaled_background("backgrounds/lab_background.png")
        self.lab_background_mirror = pygame.transform.flip(self.lab_background, True, False)
        self.library_background = self._load_scaled_background("backgrounds/library_background.png")
        self.library_background_mirror = pygame.transform.flip(self.library_background, True, False)

    @staticmethod
    def _load_image(relative_path, alpha=True):
        image = pygame.image.load(ASSET_DIR / relative_path)
        return image.convert_alpha() if alpha else image.convert()

    def _load_scaled_image(self, relative_path, size):
        return pygame.transform.smoothscale(self._load_image(relative_path), size)

    def _load_platform_tiles(self):
        return [
            self._load_image(f"tiles/platform{index}.png")
            for index in range(1, 5)
        ]

    def _load_university_tiles(self):
        sheet = self._load_image("tiles/university_sheet.png")
        return [
            [self._sheet_crop(sheet, (column * 32, row * 32, 32, 32)) for column in range(4)]
            for row in range(4)
        ]

    @staticmethod
    def _load_university_props():
        return {
            name: pygame.image.load(ASSET_DIR / "props" / f"{name}.png").convert_alpha()
            for name in ("plant_pot", "book_stack", "grad_cap", "banner", "bench", "bush")
        }

    # Fator de velocidade do fundo da caverna em relação à câmera: <1.0 faz o
    # fundo se mover mais devagar que o primeiro plano (efeito parallax).
    CAVE_BACKGROUND_PARALLAX = 0.35

    def _load_backgrounds(self):
        school_background = self._load_image("backgrounds/background_school.png", alpha=False)
        university_background = self._load_scaled_background("backgrounds/university_background.png")
        cave_background = self._load_scaled_background("backgrounds/cave_background_v2.png")
        self.backgrounds = [school_background, university_background, cave_background]
        self.background_mirror = pygame.transform.flip(university_background, True, False)

    def _load_scaled_background(self, relative_path):
        """Várias artes de fundo (universidade, caverna) vêm em baixa
        resolução (pensadas pra ladrilhar); aqui elas são ampliadas até
        cobrir a altura do canvas, preservando a proporção, pra servir de
        camada de fundo com parallax."""
        raw = self._load_image(relative_path, alpha=False)
        scale = HEIGHT / raw.get_height()
        size = (round(raw.get_width() * scale), HEIGHT)
        return pygame.transform.scale(raw, size)

    def _load_school_sprites(self):
        sheet = self._load_image("fase_escola_tileset/escola_sheet.png", alpha=False)
        sprites = {
            name: self._sheet_crop(sheet, rectangle)
            for name, rectangle in SCHOOL_SPRITE_RECTS.items()
        }
        sprites.update(
            {
                name: pygame.transform.scale(self._sheet_crop(sheet, rectangle), size)
                for name, (rectangle, size) in SCHOOL_PLATFORM_SPRITES.items()
            }
        )
        return sprites

    def _create_scene_filters(self):
        # Cores base dos filtros (mantidas apenas como referência/compat).
        bg_color = (38, 53, 76, 72)
        university_color = (55, 65, 80, 85)
        underground_color = (8, 12, 27, 155)
        self.background_filter = self._solid_overlay(bg_color)
        self.university_filter = self._solid_overlay(university_color)
        self.underground_filter = self._solid_overlay(underground_color)

        # Cada nível pode empilhar até 3 filtros translúcidos por cima do
        # fundo (background + university + underground) todo quadro, e
        # blitar múltiplas surfaces SRCALPHA de tela cheia é a operação de
        # desenho mais cara do jogo. Como cada filtro é uma cor sólida
        # constante (não depende do conteúdo por baixo além da própria
        # fórmula de mistura "over"), dá pra pré-combinar as camadas numa
        # única cor equivalente, uma vez, no carregamento — o resultado
        # pixel a pixel é idêntico a aplicar as camadas em sequência, mas
        # custa 1 blit em vez de até 3.
        self._overlay_plain = self.background_filter
        self._overlay_underground = self._solid_overlay(
            self._combine_overlay_colors(bg_color, underground_color)
        )
        self._overlay_university = self._solid_overlay(
            self._combine_overlay_colors(bg_color, university_color)
        )
        self._overlay_university_underground = self._solid_overlay(
            self._combine_overlay_colors(bg_color, university_color, underground_color)
        )

    @staticmethod
    def _combine_overlay_colors(*colors):
        """Compõe cores RGBA sólidas (alpha compositing 'over', em sequência)
        numa única cor equivalente. Aplicar essa cor combinada uma vez
        produz o mesmo resultado, pixel a pixel, que aplicar cada cor em
        sequência."""
        accum_r = accum_g = accum_b = 0.0
        alpha_acc = 0.0
        for cr, cg, cb, ca in colors:
            a = ca / 255
            accum_r = cr * a + accum_r * (1 - a)
            accum_g = cg * a + accum_g * (1 - a)
            accum_b = cb * a + accum_b * (1 - a)
            alpha_acc = 1 - (1 - alpha_acc) * (1 - a)
        if alpha_acc <= 0:
            return (0, 0, 0, 0)
        return (
            round(accum_r / alpha_acc),
            round(accum_g / alpha_acc),
            round(accum_b / alpha_acc),
            round(alpha_acc * 255),
        )

    @staticmethod
    def _solid_overlay(color):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill(color)
        return overlay

    @staticmethod
    def _create_player_light():
        light_size = 280
        light = pygame.Surface((light_size, light_size), pygame.SRCALPHA)
        center = light_size // 2
        for radius in range(center, 0, -4):
            intensity = 1 - radius / center
            alpha = int(3 + 52 * intensity * intensity)
            pygame.draw.circle(light, (255, 239, 192, alpha), (center, center), radius)
        return light

    def _load_puzzle_sprites(self):
        objects_dir = ASSET_DIR / "objects"
        return {
            "lever_animation": [
                pygame.transform.scale(
                    pygame.image.load(objects_dir / f"alavanca_animation{frame}.png").convert_alpha(),
                    (86, 64),
                )
                for frame in range(1, 6)
            ],
            "microscope_parts": [
                pygame.image.load(objects_dir / f"microscope_{name}.png").convert_alpha()
                for name in ("lens", "base", "light", "ocular")
            ],
            "microscope_complete": pygame.image.load(
                objects_dir / "microscope_complete.png"
            ).convert_alpha(),
            "buttons": [
                pygame.transform.scale(
                    pygame.image.load(objects_dir / f"button_{color}.png").convert_alpha(),
                    (36, 20),
                )
                for color in ("blue", "green", "yellow", "red")
            ],
        }

    def _load_slime_sprites(self):
        enemies_dir = ASSET_DIR / "enemies"
        return {
            state: self._load_enemy_sheet(enemies_dir / f"slime_{state}.png")
            for state in ("walk", "jump", "dead", "hurt")
        }

    @staticmethod
    def _load_enemy_sheet(path):
        """Extrai e amplia os quadros retangulares das folhas de slime."""
        sheet = pygame.image.load(path).convert_alpha()
        frame_width = sheet.get_height() * 2
        frames = []
        for x in range(0, sheet.get_width(), frame_width):
            frame = sheet.subsurface(pygame.Rect(x, 0, frame_width, sheet.get_height()))
            content = frame.get_bounding_rect()
            if content.width and content.height:
                frame = frame.subsurface(content)
            frames.append(pygame.transform.scale(frame, (64, 32)))
        return frames

    @staticmethod
    def _sheet_crop(sheet, rectangle):
        """Copia um elemento do sprite sheet."""
        return sheet.subsurface(pygame.Rect(rectangle)).copy()

    @staticmethod
    def _load_grid_sheet(path, frame_width, frame_height, rows_frame_counts, scale=1.0):
        """Recorta uma spritesheet em grade (várias linhas de animação, uma
        contagem de quadros por linha) numa lista de listas de superfícies,
        uma lista por linha. Usado pelo cervo de cristal e pela sombra.
        `scale` amplia cada quadro depois de recortado (os quadros originais
        de crystal_stag/dark_wraith são pequenos perto do sprite da Lia)."""
        sheet = pygame.image.load(path).convert_alpha()
        size = (round(frame_width * scale), round(frame_height * scale))
        rows = []
        for row, count in enumerate(rows_frame_counts):
            frames = []
            for column in range(count):
                frame = sheet.subsurface(
                    pygame.Rect(column * frame_width, row * frame_height, frame_width, frame_height)
                ).copy()
                if scale != 1.0:
                    frame = pygame.transform.scale(frame, size)
                frames.append(frame)
            rows.append(frames)
        return rows

    # Fatores de ampliação dos inimigos novos — os quadros crus (40x34 e
    # 48x48) ficam pequenos demais perto do sprite da Lia e do slime.
    STAG_SCALE = 1.8
    WRAITH_SCALE = 1.6

    def _load_stag_sprites(self):
        """crystal_stag.png: quadro 40x34, grade 14x4 — repouso(8)/marcha(8)
        /dano(4)/mineralização(14)."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "crystal_stag.png", 40, 34, [8, 8, 4, 14], scale=self.STAG_SCALE
        )
        return {"idle": rows[0], "walk": rows[1], "hurt": rows[2], "dead": rows[3]}

    def _load_wraith_sprites(self):
        """dark_wraith.png: quadro 48x48, grade 14x4 — repouso(8)/investida(7)
        /dano(4)/dissolução(14)."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "dark_wraith.png", 48, 48, [8, 7, 4, 14], scale=self.WRAITH_SCALE
        )
        return {"idle": rows[0], "lunge": rows[1], "hurt": rows[2], "dead": rows[3]}

    def _load_student_sprites(self):
        """possessed_student.png: quadro 48x48, grade 12x5 — repouso(8)/
        marcha(8)/ataque(6, não usado)/dano(4)/morte(12). Já nasce no mesmo
        tamanho da Lia (48px), sem precisar ampliar."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "possessed_student.png", 48, 48, [8, 8, 6, 4, 12]
        )
        return {"idle": rows[0], "walk": rows[1], "hurt": rows[3], "dead": rows[4]}

    def _load_janitor_sprites(self):
        """janitor_guardian.png: quadro 64x64, grade 12x6 — repouso(8)/
        marcha(8)/varrida(8, não usada)/pancada(8, não usada)/dano(4)/
        morte(12). 64px já lê como "maior" que a Lia/o estudante sem precisar
        ampliar (ver LEIA-ME_fase2.md — a escala é o que dá peso de chefe)."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "janitor_guardian.png", 64, 64, [8, 8, 8, 8, 4, 12]
        )
        return {"idle": rows[0], "walk": rows[1], "hurt": rows[4], "dead": rows[5]}

    # Os dois chefes de sala também cresceram nesta leva (LEIA-ME_bosses_e_
    # itens.md pede "aumentar o tamanho dos bosses" — não só os dois novos):
    # mesma técnica de ampliação pós-recorte usada em STAG_SCALE/WRAITH_SCALE.
    SPECIMEN_SCALE = 1.3
    LIBRARIAN_SCALE = 1.25

    def _load_specimen_sprites(self):
        """lab_specimen.png: quadro 56x48, grade 12x6 — repouso(8)/rastejo(8)
        /ataque 1 jato(7)/ataque 2 investida(8)/dano(4)/morte(12)."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "lab_specimen.png", 56, 48, [8, 8, 7, 8, 4, 12], scale=self.SPECIMEN_SCALE
        )
        return {
            "idle": rows[0], "walk": rows[1],
            "jet": rows[2], "lunge": rows[3],
            "hurt": rows[4], "dead": rows[5],
        }

    def _load_librarian_sprites(self):
        """librarian_boss.png: quadro 64x64, grade 14x6 — repouso(8)/
        deslize(8)/ataque A silêncio(9)/ataque B errata(10)/dano(4)/
        morte(14). Os tomos do ataque B reaproveitam o ícone de livro da
        pesquisa (self.book) — mesma silhueta, sem precisar de arte nova."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "librarian_boss.png", 64, 64, [8, 8, 9, 10, 4, 14], scale=self.LIBRARIAN_SCALE
        )
        return {
            "idle": rows[0], "walk": rows[1],
            "attack_a": rows[2], "attack_b": rows[3],
            "hurt": rows[4], "dead": rows[5],
            "tome": self.book,
        }

    def _load_small_slime_sprites(self):
        """slime_common.png: quadro 32x32, grade 8x4 — repouso(6, não usado)
        /pulo(8)/dano(3)/morte(6). Mesmo corpo do Rei Slime sem coroa nem
        núcleo, usado pelos filhotes da Cisão."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "slime_common.png", 32, 32, [6, 8, 3, 6]
        )
        return {"walk": rows[1], "hurt": rows[2], "dead": rows[3]}

    # slime_king.png/dragon.png já nascem grandes (64x64/112x96); esta escala
    # é só o empurrão extra pedido no LEIA-ME pra eles lerem como os maiores
    # do jogo, o topo da hierarquia de tamanho.
    SLIME_KING_SCALE = 1.3
    DRAGON_SCALE = 1.25

    def _load_slime_king_sprites(self):
        """slime_king.png: quadro 64x64, grade 12x6 — repouso(8)/pulo(8)/
        ataque A esmagar(9)/ataque B cisão(10)/dano(4)/morte(12)."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "slime_king.png", 64, 64, [8, 8, 9, 10, 4, 12], scale=self.SLIME_KING_SCALE
        )
        return {
            "idle": rows[0], "walk": rows[1],
            "attack_a": rows[2], "attack_b": rows[3],
            "hurt": rows[4], "dead": rows[5],
        }

    def _load_dragon_sprites(self):
        """dragon.png: quadro 112x96, grade 14x6 — repouso(8)/marcha(8)/
        ataque A sopro(10)/ataque B brasas(10)/dano(4)/morte(14). As pedras
        das Brasas usam dragon_rock.png (24x24, 8 quadros: queda/impacto/
        explosão), desenhadas à parte pelo próprio Dragon.draw."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "dragon.png", 112, 96, [8, 8, 10, 10, 4, 14], scale=self.DRAGON_SCALE
        )
        rock_rows = self._load_grid_sheet(ASSET_DIR / "enemies" / "dragon_rock.png", 24, 24, [8])
        return {
            "idle": rows[0], "walk": rows[1],
            "attack_a": rows[2], "attack_b": rows[3],
            "hurt": rows[4], "dead": rows[5],
            "rock": rock_rows[0],
        }

    # Um pouco maiores que o quadro cru (48x48, igual à Lia) pra se
    # destacarem melhor perto dela sem deixar de ler como "gente", mesma
    # técnica de ampliação pós-recorte usada nos inimigos/chefes.
    NPC_SCALE = 1.65

    def _load_scientist_sprites(self):
        """cientistas_idle.png: quadro 48x48, grade 8x5 — uma linha por
        cientista (ver NPC_SPRITE_ROWS), 8 quadros a 8fps, sem espelhamento
        (elas são desenhadas sempre de frente, LEIA-ME_cientistas.md)."""
        return self._load_grid_sheet(
            ASSET_DIR / "npcs" / "cientistas_idle.png", 48, 48, [8, 8, 8, 8, 8], scale=self.NPC_SCALE
        )

    def _load_item_icons(self):
        """items.png: quadro 16x16, 4 col x 7 lin, 6fps — usa só o primeiro
        quadro de cada linha como ícone estático do inventário/HUD (ver
        hud.draw_inventory); a animação de 4 quadros fica pro chão, se algum
        dia o item ganhar uma versão "largada" animada."""
        rows = self._load_grid_sheet(ASSET_DIR / "items" / "items.png", 16, 16, [4] * 7)
        icons = {}
        for key, definition in ITEM_DEFS.items():
            frame = rows[definition["row"]][0]
            icons[key] = pygame.transform.scale(frame, (28, 28))
        return icons

    # Tamanho de cada lago de lava esculpido pelo gerador de mapa (ver
    # LAKE_WIDTH/LAKE_DEPTH em build_fase3_map_v6.py) — os 8 quadros de
    # lava_lake.png (160x96 cada) são pré-ampliados pra esse tamanho uma
    # única vez no load, em vez de re-escalar a cada quadro desenhado.
    LAVA_LAKE_SIZE = (7 * 32, 6 * 32)
    LAVA_LAKE_FPS = 10

    def _load_lava_lake_frames(self):
        sheet = self._load_image("lava_lake.png")
        frame_width = 160
        frame_height = sheet.get_height()
        count = sheet.get_width() // frame_width
        frames = [
            self._sheet_crop(sheet, (i * frame_width, 0, frame_width, frame_height))
            for i in range(count)
        ]
        return [pygame.transform.scale(frame, self.LAVA_LAKE_SIZE) for frame in frames]

    def load_level(self, index):
        """Inicia uma fase sem modificar a quantidade atual de vidas."""
        self.level = Level(index)
        self.checkpoint = self.level.spawn
        self.player.reset(*self.checkpoint)
        self.collected = set()
        self.artifacts_collected = set()
        # Enquanto self._base_level não for None, self.level aponta pra uma
        # sala (biblioteca/laboratório) e self._base_level guarda a fase
        # principal, intacta, pra restaurar ao sair — ver enter_room/exit_room.
        self._base_level = None
        self._base_state = None
        self.seen_dialogues = set()
        self.lever_on = False
        self.sequence_solved = False
        self.microscope_assembled = False
        self.sequence_progress = 0
        self.microscope_collected = set()
        self.riding_platform = None
        self.pending_drops = []
        self._reset_combat_state()
        self._reset_input_state()
        self._reset_vfx_state()
        self._reset_status_state()
        self.camera_x = 0
        self.camera_y = 0
        self.message = self.level.data["subtitle"]
        self.message_timer = 0
        self.state = PLAYING

    def enter_room(self, room_key):
        """Troca para uma sala secundária (porta interativa no corredor),
        preservando a fase principal intacta (inimigos, pesquisa coletada)
        pra restaurar exatamente como estava ao sair — ver exit_room."""
        self._base_level = self.level
        self._base_state = (self.player.x, self.player.y, self.camera_x, self.camera_y)
        self.level = Level(self.level.index, room=room_key)
        self.player.reset(*self.level.spawn)
        self.riding_platform = None
        self.pending_drops = []
        self.camera_x = self.camera_y = 0
        # Suprime o [E] desta troca de tela: sem isso, segurar a tecla ao
        # atravessar a porta reaciona a interação do outro lado no mesmo
        # quadro (ex.: entrar e sair de novo instantaneamente).
        self.interact_was_down = True
        self.message = self.level.data["subtitle"]
        self.message_timer = 0

    def exit_room(self):
        """Volta da sala pra fase principal, no ponto exato de onde Lia
        entrou pela porta."""
        if self._base_level is None:
            return
        self.level = self._base_level
        self._base_level = None
        player_x, player_y, camera_x, camera_y = self._base_state
        self._base_state = None
        self.player.reset(player_x, player_y)
        self.riding_platform = None
        self.pending_drops = []
        self.camera_x, self.camera_y = camera_x, camera_y
        self.interact_was_down = True

    def _reset_combat_state(self):
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_power = STANDARD_ATTACK_POWER
        self.mouse_attack_requested = False

    def _reset_input_state(self):
        self.interact_was_down = False
        self.attack_was_down = False
        self.dash_was_down = False
        self.dialogue_advance_was_down = False
        self._item_key_was_down = {}

    def _reset_vfx_state(self):
        self.vfx.active = []
        self.dust_timer = 0
        self.was_swimming = False
        self.player_grounded = False
        self.lava_lake_anim = 0

    # Quadros de invencibilidade após renascer: sem isso, se o checkpoint (ou
    # o próprio spawn) ficar perto de um espinho/inimigo, o toque volta a
    # acontecer nos quadros seguintes e consome as 3 vidas quase instantaneamente
    # — parecendo "morte direta" mesmo cada toque só custando 1 vida.
    INVULN_FRAMES = 90

    def _reset_status_state(self):
        self.invuln_timer = 0

    def respawn(self):
        # Carcaça de robô/Dark Crystal (ver ITEM_DEFS): 1 ponto de escudo
        # absorve o PRÓXIMO dano por completo, sem tirar vida nem reiniciar
        # a posição — vale pra qualquer fonte (espinho, chefe, queda, afogar).
        if self.shield > 0:
            self.shield -= 1
            self.invuln_timer = self.INVULN_FRAMES
            self.vfx.spawn("impact", self.player.rect.centerx, self.player.rect.centery)
            self.message = "O escudo absorveu o dano!"
            self.message_timer = 90
            return
        # Na universidade, o "toque que mata" costuma ser vidro quebrado ou
        # a poça química — o estilhaço de vidro combina melhor com o tema do
        # que o impacto genérico usado nas outras fases.
        if self.level.room == "laboratorio":
            vfx_kind = "acid_burn"
        elif self.level.room == "biblioteca":
            vfx_kind = "ink_splash"
        elif self.level.index == 1:
            vfx_kind = "glass"
        else:
            vfx_kind = "impact"
        self.vfx.spawn(vfx_kind, self.player.rect.centerx, self.player.rect.centery)
        self.lives -= 1
        self.invuln_timer = self.INVULN_FRAMES
        if self.lives <= 0:
            self.state = GAME_OVER
            self.game_over_fade = 0
            self.game_over_characters = 0
            return

        if self._base_level is not None:
            # Machucar-se numa sala te tira dela: mais simples e mais
            # temático (Lia cambaleia de volta pro corredor) do que tentar
            # achar um checkpoint dentro de um espaço tão pequeno. exit_room
            # já restaura a câmera exata de antes da porta, então não zera
            # camera_y como no respawn normal por checkpoint.
            self.exit_room()
        else:
            self.player.reset(*self.checkpoint)
            self.camera_y = 0
        self.riding_platform = None
        self.message = MOTIVATION
        self.message_timer = 0

    def update(self, keyboard, dt=1 / FPS):
        dialogue_advance_pressed, attack_pressed, dash_pressed = self._read_input(keyboard)

        if self.state == TITLE:
            self._update_title(keyboard)
        elif self.state == INTRO:
            self._update_intro(keyboard, dialogue_advance_pressed)
        elif self.state in (GAME_OVER, COMPLETE):
            self._update_end_state(keyboard)
        elif self.dialogue.active:
            self._update_dialogue(dialogue_advance_pressed)
        else:
            self._read_item_use(keyboard)
            self._update_playing(keyboard, dash_pressed, attack_pressed, dt)

    def _read_input(self, keyboard):
        interaction_down = keyboard.e or keyboard.RETURN
        dialogue_advance_down = interaction_down or keyboard.space
        attack_down = keyboard.f
        dash_down = keyboard.q

        self.interact_pressed = interaction_down and not self.interact_was_down
        self.interact_was_down = interaction_down

        dialogue_advance_pressed = (
            dialogue_advance_down and not self.dialogue_advance_was_down
        )
        self.dialogue_advance_was_down = dialogue_advance_down

        attack_pressed = (
            attack_down and not self.attack_was_down
        ) or self.mouse_attack_requested
        self.attack_was_down = attack_down
        self.mouse_attack_requested = False

        dash_pressed = dash_down and not self.dash_was_down
        self.dash_was_down = dash_down
        return dialogue_advance_pressed, attack_pressed, dash_pressed

    def _read_item_use(self, keyboard):
        """Teclas 1/2/3 (ver ITEM_USE_KEYS) consomem um consumível do
        inventário — os 4 itens de pesquisa nunca aparecem aqui, eles só
        destravam o avanço de fase ao serem coletados (ver
        _advance_level_if_ready)."""
        for key_name, item_key in ITEM_USE_KEYS.items():
            down = bool(getattr(keyboard, key_name, False))
            was_down = self._item_key_was_down.get(key_name, False)
            if down and not was_down:
                self._use_item(item_key)
            self._item_key_was_down[key_name] = down

    def _use_item(self, item_key):
        count = self.inventory.get(item_key, 0)
        if count <= 0:
            return
        definition = ITEM_DEFS[item_key]
        if definition["kind"] != "consumable":
            return
        heal = definition["heal"]
        shield = definition["shield"]
        if heal and not shield and self.lives >= MAX_LIVES:
            self.message = "Vidas já estão cheias."
            self.message_timer = 90
            return
        self.inventory[item_key] = count - 1
        if self.inventory[item_key] <= 0:
            del self.inventory[item_key]
        if heal:
            self.lives = min(MAX_LIVES, self.lives + heal)
        if shield:
            self.shield += shield
        self.message = f"{definition['name']} usado!"
        self.message_timer = 90
        self.vfx.spawn("dust", self.player.rect.centerx, self.player.rect.centery)

    def _update_title(self, keyboard):
        if keyboard.space or keyboard.RETURN:
            self.lives = STARTING_LIVES
            self.state = INTRO
            self.intro.start()

    def _update_intro(self, keyboard, dialogue_advance_pressed):
        """A mãe de Lia no hospital (ver cutscene.IntroCutscene) — ESC pula
        direto pra Fase 1, senão a cena avança do mesmo jeito que qualquer
        outro diálogo do jogo (E/Enter/Espaço)."""
        if getattr(keyboard, "escape", False):
            self.intro.skip()
        else:
            self.intro.update(dialogue_advance_pressed)
        if not self.intro.active:
            self.state = PLAYING

    def _update_end_state(self, keyboard):
        if self.state == GAME_OVER:
            self.game_over_fade = min(60, self.game_over_fade + 1)
            if self.game_over_fade >= 18:
                self.game_over_characters += 0.75
        if keyboard.r:
            self.lives = STARTING_LIVES
            self.shield = 0
            if self.state == COMPLETE:
                self.inventory = {}
            level_index = 0 if self.state == COMPLETE else self.level.index
            self.load_level(level_index)

    def _update_dialogue(self, dialogue_advance_pressed):
        # A animação da alavanca continua enquanto a mensagem é exibida.
        if self.level.is_underground:
            self.level.update_lever_animations()
        if dialogue_advance_pressed:
            if self.dialogue.finished:
                self.dialogue.close()
            else:
                self.dialogue.reveal_all()
        else:
            self.dialogue.update()

    def _update_playing(self, keyboard, dash_pressed, attack_pressed, dt):
        self.player.update_abilities()
        if dash_pressed and not self.player.swimming:
            self.player.start_dash()
        self.player.read_controls(keyboard)
        self._update_attack(attack_pressed)
        self.level.update()
        if self.level.tiled_map:
            # Avança a animação dos tiles do Tiled (ex.: água da Fase 3) em ms.
            self.level.tiled_map.update(dt * 1000)
        self._move_with_platform()
        self.move_player()
        self._apply_boss_arena_clamp()
        self.player.animate()
        self._update_vfx()
        self._update_camera()
        self.message_timer = max(0, self.message_timer - 1)
        self.handle_interactions()
        self.check_events()

    def _update_attack(self, attack_pressed):
        self.attack_cooldown = max(0, self.attack_cooldown - 1)
        if attack_pressed and self.attack_cooldown == 0:
            self.attack_timer = ATTACK_DURATION
            self.attack_cooldown = ATTACK_COOLDOWN
            self.attack_power = (
                DASH_ATTACK_POWER if self.player.dashing else STANDARD_ATTACK_POWER
            )
        if self.attack_timer:
            self.attack_timer -= 1
            if self.attack_timer == 0:
                self.attack_power = STANDARD_ATTACK_POWER

    def _move_with_platform(self):
        if self.riding_platform:
            self.player.x += self.riding_platform.dx
            self.player.y += self.riding_platform.dy

    def _active_boss_arena(self):
        """Zona do chefe que Lia está atravessando agora, com o chefe ainda
        vivo (ver Level._make_boss_arenas: Rei Slime na Fase 1, Dragão na
        Fase 3) — None fora dela, ou depois do chefe morrer, o que libera a
        câmera/o limite horizontal de volta ao normal automaticamente."""
        for arena in getattr(self.level, "boss_arenas", ()):
            if arena["enemy"].alive and self.player.rect.colliderect(arena["zone"]):
                return arena["zone"]
        return None

    def _apply_boss_arena_clamp(self):
        """Enquanto dentro da arena de um chefe vivo, Lia não sai pelos
        lados (LEIA-ME_bosses_e_itens.md: "que Lia não consiga sair daquele
        campo de visão") — mesma ideia de trava de câmera de outros jogos,
        aqui aplicada também ao próprio jogador, não só à câmera."""
        zone = self._active_boss_arena()
        if not zone:
            return
        min_x = zone.left - PLAYER_HITBOX_OFFSET_X
        max_x = zone.right - PLAYER_HITBOX_OFFSET_X - PLAYER_HITBOX_WIDTH
        if max_x < min_x:
            max_x = min_x
        self.player.x = max(min_x, min(self.player.x, max_x))

    def _update_camera(self):
        arena_zone = self._active_boss_arena()
        if arena_zone:
            self._update_boss_camera(arena_zone)
            return
        target_x = self.player.x - WIDTH * CAMERA_X_FOCUS
        self.camera_x += (target_x - self.camera_x) * CAMERA_X_SMOOTHING
        self.camera_x = max(0, min(self.camera_x, self.level.world_width - WIDTH))

        target_y = self.player.y - HEIGHT * CAMERA_Y_FOCUS
        self.camera_y += (target_y - self.camera_y) * CAMERA_Y_SMOOTHING
        self.camera_y = max(
            self.level.world_top,
            min(self.camera_y, self.level.world_height - HEIGHT),
        )

    def _update_boss_camera(self, zone):
        """Foca a arena inteira na tela (as duas são bem mais estreitas que
        WIDTH) em vez de seguir Lia — é isso que lê como "a câmera focou no
        chefe" em vez do scroll normal continuar."""
        if zone.width <= WIDTH:
            target_x = zone.centerx - WIDTH / 2
        else:
            target_x = self.player.x - WIDTH * CAMERA_X_FOCUS
        target_x = max(0, min(target_x, self.level.world_width - WIDTH))
        self.camera_x += (target_x - self.camera_x) * CAMERA_X_SMOOTHING

        target_y = self.player.y - HEIGHT * CAMERA_Y_FOCUS
        self.camera_y += (target_y - self.camera_y) * CAMERA_Y_SMOOTHING
        self.camera_y = max(
            self.level.world_top,
            min(self.camera_y, self.level.world_height - HEIGHT),
        )

    # Distância mínima entre poeiras consecutivas enquanto anda (em quadros).
    DUST_INTERVAL = 10

    def _update_vfx(self):
        """Avança as partículas ativas e dispara poeira ao andar / respingo
        ao entrar na água. O impacto (dano) é disparado nos próprios pontos
        onde o dano acontece — ver respawn() e check_enemies()."""
        self.vfx.update()
        self.lava_lake_anim += 1
        player = self.player

        walking = (
            not player.swimming
            and self.player_grounded
            and abs(player.vx) > 0.2
        )
        if walking:
            self.dust_timer -= 1
            if self.dust_timer <= 0:
                self.vfx.spawn("dust", player.rect.centerx, player.rect.bottom)
                self.dust_timer = self.DUST_INTERVAL
        else:
            self.dust_timer = 0

        if player.swimming and not self.was_swimming:
            self.vfx.spawn("splash", player.rect.centerx, player.rect.centery)
        self.was_swimming = player.swimming

    def request_mouse_attack(self):
        """Registra o clique; o ataque será iniciado no próximo update."""
        self.mouse_attack_requested = True

    # Quadros de tolerância após soltar o encosto na parede em que o wall
    # jump ainda é aceito (mesma ideia do coyote_time do chão). Sem isso, o
    # jogador solta a direção pra preparar o pulo, o encosto conta como
    # perdido no mesmo quadro e o wall jump falha de forma inconsistente.
    WALL_COYOTE_FRAMES = 8

    def move_player(self):
        """Resolve colisões horizontais, verticais e o pulo sobre inimigos."""
        player = self.player
        solids = self._all_solid_rectangles()
        player.wall_side = 0
        player.swimming = self._player_in_water(player)
        if player.swimming:
            player.cancel_dash()

        previous_x = player.x
        player.x += player.vx
        self._resolve_horizontal_collisions(player, solids, previous_x)

        if player.wall_side and not player.swimming:
            player.last_wall_side = player.wall_side
            player.wall_coyote_time = self.WALL_COYOTE_FRAMES
        else:
            player.wall_coyote_time = max(0, player.wall_coyote_time - 1)

        if player.swimming:
            player.apply_swim_gravity()
        else:
            player.apply_gravity()
            if player.wall_side and player.vy > player.WALL_SLIDE_SPEED:
                player.vy = player.WALL_SLIDE_SPEED

        previous_y = player.y
        previous_bottom = previous_y + PLAYER_HEIGHT
        player.y += player.vy

        if not player.swimming and self._stomp_enemy_if_possible(player, previous_bottom):
            return

        landed = self._resolve_vertical_collisions(player, previous_y, previous_bottom)
        self.player_grounded = landed
        if player.swimming:
            # Sem chão firme nem parede pra reaproveitar debaixo d'água.
            player.coyote_time = 0
            player.wall_jump_used = True
        else:
            player.coyote_time = 7 if landed else max(0, player.coyote_time - 1)
            if landed:
                player.wall_jump_used = False
        player.try_jump()

    def _player_in_water(self, player):
        return any(player.rect.colliderect(zone) for zone in self.level.water_zones)

    def _all_solid_rectangles(self):
        return (
            self.level.grounds
            + self.level.wall_blocks
            + [platform.rect for platform in self.level.platforms]
        )

    @staticmethod
    def _resolve_horizontal_collisions(player, solids, previous_x):
        for solid in solids:
            if not player.rect.colliderect(solid):
                continue

            previous_right = previous_x + PLAYER_HITBOX_OFFSET_X + PLAYER_HITBOX_WIDTH
            previous_left = previous_x + PLAYER_HITBOX_OFFSET_X
            if player.vx > 0 and previous_right <= solid.left:
                player.x = solid.left - PLAYER_HITBOX_WIDTH - PLAYER_HITBOX_OFFSET_X
                player.wall_side = 1
                player.cancel_dash()
            elif player.vx < 0 and previous_left >= solid.right:
                player.x = solid.right - PLAYER_HITBOX_OFFSET_X
                player.wall_side = -1
                player.cancel_dash()

    def _stomp_enemy_if_possible(self, player, previous_bottom):
        for enemy in self.level.enemies:
            if (
                enemy.alive
                and player.vy > 0
                and player.rect.colliderect(enemy.rect)
                and previous_bottom <= enemy.rect.top + 12
            ):
                enemy.stomp()
                self.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                self._on_enemy_defeated(enemy)
                player.y = enemy.rect.top - PLAYER_HEIGHT
                player.vy = -10.5
                return True
        return False

    def _on_enemy_defeated(self, enemy):
        """Chamado uma única vez, no quadro exato em que um inimigo morre
        (stomp() sempre mata; take_hit() só às vezes — ver check_enemies).
        Chefe larga o item de pesquisa garantido (BOSS_DROP_TABLE); inimigo
        comum sorteia contra ENEMY_DROP_TABLE. Slimes pequenos da Cisão e
        os dois chefes de sala antigos sem entrada em nenhuma tabela não
        largam nada."""
        name = type(enemy).__name__
        quest_item = BOSS_DROP_TABLE.get(name)
        if quest_item:
            self._spawn_drop(quest_item, enemy.rect.centerx, enemy.rect.centery)
            return
        entry = ENEMY_DROP_TABLE.get(name)
        if entry and random.random() < entry[1]:
            self._spawn_drop(entry[0], enemy.rect.centerx, enemy.rect.centery)

    def _spawn_drop(self, item_key, x, y):
        self.pending_drops.append({"item": item_key, "x": x, "y": y})

    def _collect_drops(self, player):
        """Itens largados no chão (ver _spawn_drop) somem da lista assim que
        Lia encosta neles e entram no inventário — igual à pesquisa/achados,
        mas numa lista à parte (pending_drops), porque um item largado numa
        sala não deve reaparecer depois de sair dela (ver enter_room/
        exit_room/load_level, que zeram essa lista)."""
        if not self.pending_drops:
            return
        remaining = []
        for drop in self.pending_drops:
            pickup = pygame.Rect(0, 0, DROP_PICKUP_RADIUS * 2, DROP_PICKUP_RADIUS * 2)
            pickup.center = (drop["x"], drop["y"])
            if player.rect.colliderect(pickup):
                key = drop["item"]
                self.inventory[key] = self.inventory.get(key, 0) + 1
                self.message = f"Item obtido: {ITEM_DEFS[key]['name']}"
                self.message_timer = 0
                self.vfx.spawn("dust", drop["x"], drop["y"])
            else:
                remaining.append(drop)
        self.pending_drops = remaining

    def _resolve_vertical_collisions(self, player, previous_y, previous_bottom):
        landed = False
        self.riding_platform = None
        platform_solids = [
            (platform.rect, platform) for platform in self.level.platforms
        ]
        ground_solids = [(ground, None) for ground in self.level.grounds]
        wall_solids = [(wall, None) for wall in self.level.wall_blocks]

        for solid, moving_platform in platform_solids + ground_solids + wall_solids:
            if (
                player.rect.colliderect(solid)
                and player.vy >= 0
                and previous_bottom <= solid.top + 10
            ):
                player.y = solid.top - PLAYER_HEIGHT
                player.vy = 0
                landed = True
                if moving_platform:
                    self.riding_platform = moving_platform
            elif (
                player.rect.colliderect(solid)
                and player.vy < 0
                and previous_y >= solid.bottom - 10
            ):
                player.y = solid.bottom
                player.vy = 0
        return landed

    def check_events(self):
        player = self.player
        if player.y > self.level.world_height + 180:
            self.respawn()
            return

        self.invuln_timer = max(0, self.invuln_timer - 1)
        if self._update_oxygen(player):
            return
        if self._check_hazards(player):
            return
        if self._check_enemy_attack_hazards(player):
            return

        self.check_enemies()
        if self.state != PLAYING:
            return
        self._collect_drops(self.player)
        if self.level.room:
            # Dentro de uma sala secundária não há checkpoint, pesquisa
            # obrigatória nem avanço de fase — só o achado opcional e a
            # porta de saída (tratada em handle_interactions).
            self._collect_artifacts(player)
            return
        self._check_checkpoints(player)
        if self._collect_research(player):
            return
        self._collect_microscope_parts(player)
        if self._start_pending_dialogue(player):
            return
        self._advance_level_if_ready(player)

    def _collect_artifacts(self, player):
        for index, (item, name) in enumerate(self.level.artifacts):
            if index in self.artifacts_collected or not player.rect.colliderect(item):
                continue
            self.artifacts_collected.add(index)
            self.message = f"Achado: {name}"
            self.message_timer = 0
            lore = ROOM_LORE.get(name, DEFAULT_ROOM_LORE)
            self.dialogue.start("Lia", lore)
            return True
        return False

    def _update_oxygen(self, player):
        """Consome o fôlego enquanto a cabeça está submersa em alguma zona de
        água (Level.water_zones); recarrega assim que ela sai. Como o rect da
        cabeça só limpa a zona onde o teto tem uma folga acima da superfície
        (bolsão de ar), isso já implementa naturalmente os bolsões de ar da
        caverna submersa sem precisar de geometria especial por bolsão."""
        head = player.head_rect
        breathing = not any(head.colliderect(zone) for zone in self.level.water_zones)
        if breathing:
            player.oxygen = min(player.OXYGEN_MAX_FRAMES, player.oxygen + player.OXYGEN_REFILL_PER_FRAME)
            return False
        player.oxygen = max(0, player.oxygen - player.OXYGEN_DRAIN_PER_FRAME)
        if player.oxygen <= 0:
            self.respawn()
            return True
        return False

    def _check_hazards(self, player):
        if self.invuln_timer > 0:
            return False
        for hazard in self.level.hazards:
            if player.rect.colliderect(hazard):
                self.respawn()
                return True
        for lake in self.level.lava_lakes:
            if player.rect.colliderect(lake):
                self.respawn()
                return True
        return False

    def _check_enemy_attack_hazards(self, player):
        """Feixe do jato do espécime, onda do Silêncio e tomos do Errata: os
        três alcançam além da hitbox do próprio inimigo (ver
        Enemy.active_hazards em enemy.py), então não bastam o teste de
        colisão corpo-a-corpo normal de check_enemies."""
        if self.invuln_timer > 0:
            return False
        for enemy in self.level.enemies:
            if not enemy.alive:
                continue
            get_hazards = getattr(enemy, "active_hazards", None)
            if not get_hazards:
                continue
            for hazard in get_hazards():
                if player.rect.colliderect(hazard):
                    self.respawn()
                    return True
        return False

    def _check_checkpoints(self, player):
        for checkpoint in self.level.checkpoints:
            if player.rect.colliderect(checkpoint):
                self.checkpoint = (checkpoint.x, checkpoint.bottom - PLAYER_HEIGHT)
                self.message = "Checkpoint: Centro de pesquisa alcançado!"
                self.message_timer = 130

    def _collect_research(self, player):
        for index, (item, name) in enumerate(self.level.research):
            if index in self.collected or not player.rect.colliderect(item):
                continue

            self.collected.add(index)
            self.message = f"Parte da pesquisa obtida: {name}"
            self.message_timer = 0
            fact = SCIENCE_FACTS.get(name, DEFAULT_SCIENCE_FACT)
            self.dialogue.start("Ciência Delas", fact)
            return True
        return False

    def _collect_microscope_parts(self, player):
        if not (self.level.is_underground and self.sequence_solved):
            return
        for index, (item, _) in enumerate(self.level.microscope_parts):
            if index not in self.microscope_collected and player.rect.colliderect(item):
                self.microscope_collected.add(index)

    def _start_pending_dialogue(self, player):
        for index, (position, speaker, text) in enumerate(self.level.data["dialogues"]):
            if index not in self.seen_dialogues and player.x >= position:
                self.seen_dialogues.add(index)
                self.dialogue.start(speaker, text)
                return True
        return False

    def _advance_level_if_ready(self, player):
        if player.x < self.level.world_width - 100:
            return

        needs_microscope = self.level.is_underground and not self.microscope_assembled
        missing_items = [
            key for key in PHASE_REQUIRED_ITEMS.get(self.level.index, ())
            if self.inventory.get(key, 0) <= 0
        ]
        if len(self.collected) < len(self.level.research) or needs_microscope:
            self.message = "Encontre todas as partes da pesquisa antes de avançar."
            self.message_timer = 0
            player.x = self.level.world_width - 160
        elif missing_items:
            names = ", ".join(ITEM_DEFS[key]["name"] for key in missing_items)
            self.message = f"Ainda falta: {names}."
            self.message_timer = 0
            player.x = self.level.world_width - 160
        elif self.level.index == len(PHASES) - 1:
            self.state = COMPLETE
        else:
            self.load_level(self.level.index + 1)

    def check_enemies(self):
        """Verifica ataque, ataque reforçado durante dash e contato com slimes."""
        attack_box = self._attack_box()
        for enemy in self.level.enemies:
            if not enemy.alive:
                continue
            if attack_box and attack_box.colliderect(enemy.rect):
                if enemy.take_hit(self.attack_power):
                    self.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                    if not enemy.alive:
                        self._on_enemy_defeated(enemy)
            elif self.invuln_timer <= 0 and self.player.rect.colliderect(enemy.rect):
                self.respawn()
                return

    def _attack_box(self):
        if not self.attack_timer:
            return None
        reach = DASH_ATTACK_REACH if self.attack_power > STANDARD_ATTACK_POWER else STANDARD_ATTACK_REACH
        offset = (
            PLAYER_HITBOX_WIDTH
            if self.player.facing_right
            else -(24 + reach)
        )
        return self.player.rect.move(offset, 4).inflate(reach, 10)

    def handle_interactions(self):
        """Processa portas (qualquer fase) e, na Fase 1 subterrânea,
        elevadores, painel, botões e bancada do laboratório."""
        if not self.interact_pressed:
            return
        if self._use_doors():
            return
        if self._talk_to_npc():
            return
        if not self.level.is_underground:
            return

        player = self.player
        if self._use_elevator_lever(player):
            return
        if self._use_panel_lever(player):
            return
        if self._use_sequence_button(player):
            return
        self._use_microscope_bench(player)

    DOOR_INTERACT_RANGE = 40

    def _use_doors(self):
        player = self.player
        for door in self.level.doors:
            if not player.rect.colliderect(door["rect"].inflate(self.DOOR_INTERACT_RANGE, self.DOOR_INTERACT_RANGE)):
                continue
            if door["target"] == "sair":
                self.exit_room()
            else:
                self.enter_room(door["target"])
            return True
        return False

    NPC_INTERACT_RANGE = 40

    def _talk_to_npc(self):
        """As cientistas nunca são consumidas — dá pra falar com elas quantas
        vezes quiser, sempre a mesma fala fixa (ver NPC_DIALOGUES). Mesmo
        raio/padrão de detecção das portas, só que contra Level.npcs."""
        player = self.player
        for npc in self.level.npcs:
            if not player.rect.colliderect(npc["rect"].inflate(self.NPC_INTERACT_RANGE, self.NPC_INTERACT_RANGE)):
                continue
            text = NPC_DIALOGUES.get(npc["name"])
            if text:
                self.dialogue.start(npc["name"], text)
            return True
        return False

    def _use_elevator_lever(self, player):
        if self.level.top_lever and player.rect.colliderect(self.level.top_lever.inflate(55, 55)):
            self.level.call_elevator("down")
            return True
        if self.level.bottom_lever and player.rect.colliderect(self.level.bottom_lever.inflate(55, 55)):
            self.level.call_elevator("up")
            return True
        if (
            self.level.upper_bottom_lever
            and player.rect.colliderect(self.level.upper_bottom_lever.inflate(55, 55))
        ):
            self.level.call_upper_elevator("up")
            return True
        if (
            self.level.upper_top_lever
            and player.rect.colliderect(self.level.upper_top_lever.inflate(55, 55))
        ):
            self.level.call_upper_elevator("down")
            return True
        return False

    def _use_panel_lever(self, player):
        if not player.rect.colliderect(self.level.panel_lever.inflate(55, 55)):
            return False

        self.lever_on = not self.lever_on
        self.level.set_lever_active("panel", self.lever_on)
        if self.lever_on:
            self.dialogue.start(
                "Lia",
                "A alavanca ligou o painel. A ordem é: azul, verde, amarelo e vermelho.",
            )
        else:
            self.sequence_progress = 0
            self.dialogue.start("Lia", "A alavanca desligou o painel.")
        return True

    def _use_sequence_button(self, player):
        for index, button in enumerate(self.level.buttons):
            if not player.rect.colliderect(button.inflate(55, 55)):
                continue
            if not self.lever_on:
                self.dialogue.start(
                    "Painel",
                    "O painel está sem energia. Encontre e puxe a alavanca.",
                )
            elif self.sequence_solved:
                self.dialogue.start(
                    "Painel",
                    "Sequência concluída. As peças do microscópio foram liberadas.",
                )
            elif index == self.sequence_progress:
                self.sequence_progress += 1
                if self.sequence_progress == len(self.level.buttons):
                    self.sequence_solved = True
                    self.dialogue.start(
                        "Painel",
                        "Sequência correta! As peças do microscópio foram liberadas.",
                    )
            else:
                self.sequence_progress = 0
                self.dialogue.start("Painel", "Sequência incorreta. O painel foi reiniciado.")
            return True
        return False

    def _use_microscope_bench(self, player):
        if not player.rect.colliderect(self.level.bench.inflate(70, 60)):
            return
        if len(self.microscope_collected) < len(self.level.microscope_parts):
            self.dialogue.start("Lia", "Ainda faltam peças para montar o microscópio.")
        elif not self.microscope_assembled:
            self.microscope_assembled = True
            self.level.activate_return_route()
            self.dialogue.start(
                "Lia",
                "Microscópio montado! As plataformas de retorno foram liberadas; preciso voltar pelo caminho acima.",
            )

    def draw(self, screen):
        surface = screen.surface
        surface.fill((6, 14, 29))
        if self.state == INTRO:
            self.intro.draw(surface, draw_text)
            return
        self._draw_background(surface)
        self._draw_world(surface)
        self._draw_door_prompts(surface)
        self._draw_npc_prompts(surface)
        self._draw_player_light(surface)
        self.draw_dash_trail(surface)
        self.player.draw(surface, self.camera_x, self.camera_y)
        self.vfx.draw(surface, self.camera_x, self.camera_y)
        self.draw_attack(surface)
        self._draw_interface(surface)
        self._draw_state_overlay(surface)

    def _draw_background(self, surface):
        if self.level.room == "laboratorio":
            self._draw_repeating_background(surface, self.lab_background)
        elif self.level.room == "biblioteca":
            self._draw_repeating_background(surface, self.library_background)
        elif self.level.index == 0:
            self.draw_school_background(surface)
        elif self.level.index == 1:
            self.draw_university_background(surface)
        elif self.level.index == 2:
            self._draw_repeating_background(
                surface, self.backgrounds[2], parallax=self.CAVE_BACKGROUND_PARALLAX
            )
        else:
            self._draw_repeating_background(surface, self.backgrounds[self.level.index])

        underground = self.player.y > 780
        if self.level.index == 1:
            overlay = self._overlay_university_underground if underground else self._overlay_university
        else:
            overlay = self._overlay_underground if underground else self._overlay_plain
        surface.blit(overlay, (0, 0))

    def _draw_repeating_background(self, surface, background, parallax=1.0):
        """Ladrilha o fundo horizontalmente. Com parallax<1.0 o fundo anda
        mais devagar que a câmera, dando sensação de profundidade."""
        image_width = background.get_width()
        offset = int(self.camera_x * parallax)
        start_x = -offset % image_width - image_width
        for x in range(start_x, WIDTH, image_width):
            surface.blit(background, (x, 0))

    def _draw_world(self, surface):
        self.level.draw(
            surface,
            self.camera_x,
            self.camera_y,
            self.tiles,
            self.book,
            self.checkpoint_flag,
            self.checkpoint,
            self.collected,
            self.lever_on,
            self.sequence_progress,
            self.sequence_solved,
            self.microscope_collected,
            self.microscope_assembled,
            self.puzzle_sprites,
            self.slime_sprites,
            self.school_sprites,
            draw_text,
            self.university_tiles,
            self.university_props,
            self.stag_sprites,
            self.wraith_sprites,
            self.student_sprites,
            self.janitor_sprites,
            self.specimen_sprites,
            self._current_artifact_image(),
            self.artifacts_collected,
            self.librarian_sprites,
            self.small_slime_sprites,
            self.slime_king_sprites,
            self.dragon_sprites,
            self.scientist_sprites,
            NPC_SPRITE_ROWS,
        )
        self._draw_lava_lakes(surface)
        self._draw_drops(surface)

    def _draw_drops(self, surface):
        """Itens largados no chão (ver _spawn_drop/_collect_drops) — ícone
        de items.png com um pulso leve, pra ficar claramente "pegável" e não
        parecer decoração ou parte do cenário."""
        if not self.pending_drops:
            return
        pulse = 3 * abs((pygame.time.get_ticks() % 900) / 450 - 1)
        for drop in self.pending_drops:
            icon = self.item_icons.get(drop["item"])
            if not icon:
                continue
            x = drop["x"] - icon.get_width() / 2 - self.camera_x
            y = drop["y"] - icon.get_height() / 2 - self.camera_y - pulse
            surface.blit(icon, (x, y))

    def _current_artifact_image(self):
        if self.level.room == "biblioteca":
            return self.artifact_library_image
        return self.artifact_image

    def _draw_lava_lakes(self, surface):
        lakes = getattr(self.level, "lava_lakes", None)
        if not lakes or not self.lava_lake_frames:
            return
        frame_index = (self.lava_lake_anim * self.LAVA_LAKE_FPS // FPS) % len(self.lava_lake_frames)
        frame = self.lava_lake_frames[frame_index]
        for lake in lakes:
            image = frame
            if (lake.width, lake.height) != self.LAVA_LAKE_SIZE:
                image = pygame.transform.scale(frame, (lake.width, lake.height))
            surface.blit(image, (lake.x - self.camera_x, lake.y - self.camera_y))

    DOOR_PROMPT_RANGE = 60

    def _draw_door_prompts(self, surface):
        """Mostra "[E] ENTRAR"/"[E] SAIR" só quando Lia está perto o
        bastante da porta pra interagir — mesmo raio usado em _use_doors."""
        player_rect = self.player.rect
        for door in self.level.doors:
            if not player_rect.colliderect(door["rect"].inflate(self.DOOR_PROMPT_RANGE, self.DOOR_PROMPT_RANGE)):
                continue
            label = "[E] SAIR" if door["target"] == "sair" else "[E] ENTRAR"
            rect = door["rect"]
            draw_text(
                surface,
                label,
                (rect.centerx - self.camera_x, rect.top - 22 - self.camera_y),
                14,
                "#f4e4a5",
                True,
            )

    NPC_PROMPT_RANGE = 60

    def _draw_npc_prompts(self, surface):
        """"APERTE E PARA FALAR" acima da cientista, só quando Lia está perto
        o bastante pra falar com ela — mesmo raio/padrão de _draw_door_
        prompts, contra Level.npcs em vez de Level.doors."""
        player_rect = self.player.rect
        for npc in self.level.npcs:
            rect = npc["rect"]
            if not player_rect.colliderect(rect.inflate(self.NPC_PROMPT_RANGE, self.NPC_PROMPT_RANGE)):
                continue
            draw_text(
                surface,
                "APERTE E PARA FALAR",
                (rect.centerx - self.camera_x, rect.top - 22 - self.camera_y),
                14,
                "#f4e4a5",
                True,
            )

    def _draw_player_light(self, surface):
        light_x = int(
            self.player.x
            - self.camera_x
            + PLAYER_HITBOX_WIDTH // 2
            - self.player_light.get_width() // 2
        )
        light_y = int(
            self.player.y
            - self.camera_y
            + PLAYER_HEIGHT // 2
            - self.player_light.get_height() // 2
        )
        surface.blit(self.player_light, (light_x, light_y))

    def _draw_interface(self, surface):
        show_oxygen = bool(self.level.water_zones) and (
            self.player.swimming or self.player.oxygen < self.player.OXYGEN_MAX_FRAMES
        )
        oxygen_ratio = (
            self.player.oxygen / self.player.OXYGEN_MAX_FRAMES if show_oxygen else None
        )
        draw_hud(
            surface,
            self.level.data["name"],
            self.lives,
            len(self.collected),
            len(self.level.research),
            self.message,
            self.message_timer,
            len(self.microscope_collected),
            len(self.level.microscope_parts),
            self.microscope_assembled,
            oxygen_ratio,
            self.shield,
        )
        draw_inventory(surface, self.inventory, self.item_icons, ITEM_ORDER)
        draw_ability_ui(
            surface,
            self.player.dash_cooldown,
            self.player.DASH_COOLDOWN,
            self.attack_cooldown,
            ATTACK_COOLDOWN,
            not self.player.wall_jump_used,
        )
        self.dialogue.draw(surface, draw_text)

    def _draw_state_overlay(self, surface):
        if self.state == TITLE:
            self.overlay(surface, "Echoes of Life", "Pressione ESPAÇO para começar")
        elif self.state == GAME_OVER:
            self.draw_game_over_overlay(surface)
        elif self.state == COMPLETE:
            self.overlay(
                surface,
                "Pesquisa apresentada no congresso!",
                "Lia corre pra contar tudo pra mãe: a pesquisa vai continuar,\n"
                "e agora ela sabe que não está sozinha nisso.\nPressione R para jogar novamente",
            )

    def draw_university_background(self, surface):
        """Repete o pátio alternando cópias normais e espelhadas."""
        background = self.backgrounds[1]
        image_width = background.get_width()
        x = -int(self.camera_x) % image_width - image_width
        tile_number = (x + int(self.camera_x)) // image_width
        while x < WIDTH:
            image = self.background_mirror if tile_number % 2 else background
            surface.blit(image, (x, 0))
            x += image_width
            tile_number += 1

    def draw_school_background(self, surface):
        """Desenha salas e corredores com os recortes do sprite sheet da escola."""
        surface.fill((28, 42, 61))
        pygame.draw.rect(surface, (42, 63, 84), (0, 140, WIDTH, HEIGHT - 140))
        self._draw_school_tile_bands(surface)
        self._draw_school_rooms(surface)

    def _draw_school_tile_bands(self, surface):
        sprites = self.school_sprites
        tile_start = -int(self.camera_x * 0.16) % 32 - 32
        for x in range(tile_start, WIDTH + 32, 32):
            surface.blit(sprites["brick_tile"], (x, int(142 - self.camera_y * 0.15)))
            surface.blit(sprites["cream_tile"], (x, int(594 - self.camera_y * 0.42)))

    def _draw_school_rooms(self, surface):
        room_width = 1120
        first_room = int(self.camera_x // room_width) - 1
        last_room = int((self.camera_x + WIDTH) // room_width) + 1
        for room in range(first_room, last_room + 1):
            self._draw_school_room(surface, room, room * room_width - self.camera_x)

    def _draw_school_room(self, surface, room, origin_x):
        sprites = self.school_sprites

        def put(name, x, y):
            surface.blit(sprites[name], (int(x), int(y)))

        put("chalkboard", origin_x + 68, 190 - self.camera_y * 0.30)
        put("whiteboard", origin_x + 304, 190 - self.camera_y * 0.30)
        put("clock", origin_x + 548, 78 - self.camera_y * 0.16)
        put("bulletin", origin_x + 676, 190 - self.camera_y * 0.30)
        put("exit", origin_x + 898, 216 - self.camera_y * 0.30)

        room_variant = room % 3
        if room_variant == 0:
            put("bookshelf", origin_x + 60, 420 - self.camera_y * 0.48)
            put("plant", origin_x + 640, 393 - self.camera_y * 0.48)
            put("desk_row", origin_x + 755, 392 - self.camera_y * 0.48)
        elif room_variant == 1:
            put("door", origin_x + 94, 388 - self.camera_y * 0.48)
            put("locker", origin_x + 335, 375 - self.camera_y * 0.48)
            put("lab_table", origin_x + 620, 420 - self.camera_y * 0.48)
        else:
            put("desk_row", origin_x + 80, 385 - self.camera_y * 0.48)
            put("bookshelf", origin_x + 500, 420 - self.camera_y * 0.48)
            put("plant", origin_x + 926, 392 - self.camera_y * 0.48)

    def draw_attack(self, surface):
        """Desenha o efeito visual temporário do ataque."""
        if not self.attack_timer or self.state != PLAYING:
            return
        boosted = self.attack_power > STANDARD_ATTACK_POWER
        center_x = self.player.x - self.camera_x + (52 if self.player.facing_right else -20)
        center_y = self.player.y - self.camera_y + PLAYER_HEIGHT // 2
        color = (255, 158, 74) if boosted else (255, 236, 137)
        radius = 33 if boosted else 23
        pygame.draw.circle(
            surface,
            color,
            (int(center_x), int(center_y)),
            radius,
            4 if boosted else 3,
        )

    def draw_dash_trail(self, surface):
        """Desenha o rastro que torna o dash legível."""
        if not self.player.dashing:
            return
        direction = 1 if self.player.dash_direction > 0 else -1
        start_x = (
            self.player.x
            - self.camera_x
            + PLAYER_HITBOX_WIDTH // 2
            - direction * 12
        )
        center_y = self.player.y - self.camera_y + PLAYER_HEIGHT // 2
        for offset, alpha in ((0, 150), (12, 95), (24, 45)):
            layer = pygame.Surface((42, 8), pygame.SRCALPHA)
            layer.fill((91, 220, 255, alpha))
            x = start_x - direction * (offset + (42 if direction < 0 else 0))
            surface.blit(layer, (int(x), int(center_y - 4)))

    def overlay(self, surface, title, body, alpha=210):
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        layer.fill((5, 12, 28, alpha))
        surface.blit(layer, (0, 0))
        draw_text(surface, title, (WIDTH // 2, HEIGHT // 2 - 65), 42, "#ffe477", True)
        for line_number, line in enumerate(body.split("\n")):
            draw_text(
                surface,
                line,
                (WIDTH // 2, HEIGHT // 2 + 5 + line_number * 34),
                24,
                "white",
                True,
            )

    def draw_game_over_overlay(self, surface):
        """Desenha o fade escuro e os textos revelados em sequência."""
        alpha = int(210 * self.game_over_fade / 60)
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        layer.fill((5, 12, 28, alpha))
        surface.blit(layer, (0, 0))

        title = "Você consegue, Lia!"
        message = MOTIVATION
        restart = "Pressione R para tentar de novo"
        visible_title, visible_message, visible_restart = self._game_over_text(
            title,
            message,
            restart,
        )

        draw_text(surface, visible_title, (WIDTH // 2, HEIGHT // 2 - 65), 42, "#ffe477", True)
        draw_text(surface, visible_message, (WIDTH // 2, HEIGHT // 2 + 5), 24, "white", True)
        draw_text(surface, visible_restart, (WIDTH // 2, HEIGHT // 2 + 39), 24, "white", True)

    def _game_over_text(self, title, message, restart):
        remaining = int(self.game_over_characters)
        visible_title = title[:max(0, min(len(title), remaining))]
        remaining -= len(title)
        visible_message = message[:max(0, min(len(message), remaining))]
        remaining -= len(message)
        visible_restart = restart[:max(0, min(len(restart), remaining))]
        return visible_title, visible_message, visible_restart
