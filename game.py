"""Orquestra o ciclo de jogo, as interações e a renderização."""

import random

import pygame

import audio
from cutscene import IntroCutscene
from dialogue import DialogueBox
from hint import Hint
from hud import draw_ability_ui, draw_hud, draw_inventory, draw_text
from level import PHASES, VILLAGE, Level
from player import Player
from projectile import Projectile
from vfx import VFXManager
from settings import (
    ASSET_DIR,
    CAMERA_ZOOM,
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
# Nome de exibição de cada chefe, usado só pela barra de vida (ver
# Game._draw_boss_health_bar) — mesmas 4 chaves de BOSS_DROP_TABLE.
BOSS_NAMES = {
    "SlimeKing": "Rei Slime",
    "Librarian": "Bibliotecário",
    "Specimen": "Espécime",
    "Dragon": "Dragão",
}
# Nome da faixa em music/ (ver PLANO_AUDIO.md) tocada enquanto cada chefe
# está acordado — mesmas 4 chaves de BOSS_DROP_TABLE/BOSS_NAMES.
BOSS_MUSIC = {
    "SlimeKing": "rei_slime_music",
    "Librarian": "bibliotecario_music",
    "Specimen": "especime_music",
    "Dragon": "dragao_music",
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

# Dano que a Lia sofre por contato (pedido do Raul, deixar o jogo mais
# frenético): mob comum tira só meio coração, chefe tira 1 coração
# inteiro — ver take_damage/_lose_life, que agora trabalham com
# self.lives fracionário. BOSS_DROP_TABLE (abaixo) já é o jeito que o
# resto do código distingue chefe de mob comum, reaproveitado aqui em vez
# de criar outra lista. Hazards ambientais (espinho/lava) e afogamento
# também usam MOB_CONTACT_DAMAGE — não são "chefe", então caem no mesmo
# balde dos mobs comuns.
MOB_CONTACT_DAMAGE = 0.5
BOSS_CONTACT_DAMAGE = 1

# Combo de 4 hits corpo a corpo (pedido do Raul, ver frames 8-11 de
# player_sheet.png): cada ataque dentro da janela de COMBO_RESET_WINDOW
# quadros depois do anterior avança o combo; parar de atacar por mais que
# isso volta pro hit 1 (ver _update_attack). Maior que ATTACK_COOLDOWN de
# propósito — se fosse igual, cliques no ritmo mais rápido permitido ainda
# perderiam a janela por pouco.
COMBO_HIT_COUNT = 4
COMBO_RESET_WINDOW = 40
COMBO_FINISHER_POWER = 2

# Parry: acertar o ataque corpo a corpo [F] num hazard "aparável" de chefe
# (ver <Boss>.parryable_hazards em enemy.py) destrói o hazard e devolve esse
# dano nele mesmo — mais que o ataque padrão e mais que o de dash, prêmio
# por acertar o timing curto em vez de só tocar a espada nele.
PARRY_DAMAGE = 3
# 1s de invencibilidade após um parry bem-sucedido (pedido do Raul): o
# Bibliotecário solta várias lâminas em sequência (ver BLADE_FIRE_INTERVAL
# em enemy.py) — sem isso, aparar uma ainda deixava a Lia tomar dano da
# próxima poucos quadros depois. Reaproveita o mesmo self.invuln_timer que
# já bloqueia hazard/contato normal (ver _check_hazards etc.), só que
# escrito de fora do fluxo de dano de verdade.
PARRY_INVULN_FRAMES = FPS
# Hit-stop + screen shake no parry (linguagem de Cuphead/Hollow Knight,
# pedido do Raul) — congela a simulação por alguns quadros e depois sacode
# a câmera, decaindo até 0 (ver Game._update_shake/_shake_offset). A mesma
# infra de shake fica pronta pra ser reaproveitada depois pela ideia
# guardada do tremor ao acordar o chefe (ver IDEIAS_FUTURAS.md).
PARRY_HITSTOP_FRAMES = 3
PARRY_SHAKE_DURATION = 14
PARRY_SHAKE_MAGNITUDE = 6

# Tremor do impacto do Terremoto do Dragão (ver enemy.Dragon._start_
# terremoto_slam/consume_shake_event e Game._check_boss_shake_events) —
# pedido do Raul: uns 5 segundos tremendo (300 quadros a 60fps) enquanto
# MUITOS pedaços da caverna caem (ver Dragon.TERREMOTO_ROCK_TOTAL). A
# magnitude decai sozinha ao longo da duração (ver _shake_offset), então
# começa forte e vai assentando — não fica 5s inteiros no talo.
EARTHQUAKE_SHAKE_DURATION = 300
EARTHQUAKE_SHAKE_MAGNITUDE = 14

# Ataque à distância: desbloqueado ao concluir a Fase 1 (ver
# _advance_level_if_ready). Cooldown baixo de propósito (quase semi-
# automático, não um "especial" raro) e alcance quase de tela inteira
# (WIDTH=1600) — pensado pras lutas de chefe estilo Cuphead que vêm a
# seguir (Fase 2 e Dragão): arena grande, chefe longe/no alto boa parte da
# luta, Lia precisa sustentar fogo de qualquer ponto do cenário.
RANGED_ATTACK_POWER = 1
RANGED_ATTACK_COOLDOWN = 70
RANGED_PROJECTILE_SPEED = 14.0
RANGED_PROJECTILE_RANGE = 500

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
    # NPCs da vila (prólogo antes da Fase 1, ver PLANO_VILA.md/maps/vila.tmx)
    # — mesmo dicionário, mesma tecla [E], sem sprite próprio ainda (ver
    # Level._draw_npcs: NPC sem entrada em NPC_SPRITE_ROWS só não desenha
    # corpo, mas continua interagível normalmente). Sra. Amélia usa uma
    # TUPLA (múltiplas falas em sequência, ver _talk_to_npc/_update_dialogue)
    # em vez de uma string só — as outras têm uma fala fixa, como sempre.
    "Seu Joaquim": (
        "Ei, Lia! Cedo pra andar por aí, hein? Vai com calma: as setas te "
        "movem, o espaço faz pular. Se precisar bater em alguma coisa — ou "
        "em alguém —, é só apertar o F. Segurou fôlego demais parada? "
        "Aperta Q e sai correndo no susto. E qualquer um por aqui que "
        "quiser conversar, é só chegar perto e apertar E."
    ),
    "Dona Marta": (
        "Bom dia, flor! Olha o tanto que você cresceu... Sua mãe tem muito "
        "orgulho de você, sabia? Ela fala isso toda vez que passo lá em "
        "casa."
    ),
    "Bento": (
        "Lia! Depois eu te chamo pra jogar bola, tá? ...Ou você tá com "
        "pressa hoje? Parece que tá indo em algum lugar importante."
    ),
    "Sra. Amélia": (
        "Lia, filha, vem cá um instantinho.",
        "É chato de perguntar, mas... me falaram que sua mãe não anda bem. "
        "É verdade, isso? Que ela tá com câncer?",
        "Eu sinto muito. Mas você tem uma cara decidida hoje — vai atrás "
        "de alguma coisa, não vai? Então vai. E volta pra contar pra "
        "gente.",
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
        # Fila de falas restantes de uma conversa de NPC com múltiplos
        # beats (ex.: Sra. Amélia na vila, ver NPC_DIALOGUES/_talk_to_npc/
        # _update_dialogue) — vazia pra NPCs de fala única (a maioria).
        self._npc_dialogue_queue = []
        self._npc_dialogue_speaker = None
        # Cutscene inicial (mãe de Lia no hospital) — reaproveita a mesma
        # DialogueBox acima pro texto e o quadro parado de Lia pro retrato,
        # ver cutscene.IntroCutscene. Só toca entre TITLE e PLAYING.
        self.intro = IntroCutscene(self.dialogue, self.player.frames[0])
        # Dicas contextuais (vinheta + texto, ver hint.Hint) — pausam o jogo
        # igual à DialogueBox, mas não são conversas com NPC, são avisos de
        # mecânica (ex.: painel do elevador na Fase 1). hints_shown mora em
        # load_level (reseta por fase, igual seen_dialogues).
        self.hint = Hint()
        # Ataque à distância (ver RANGED_* acima e _advance_level_if_ready):
        # desbloqueia ao concluir a Fase 1 e, como inventário/escudo, atravessa
        # trocas de fase normais — só reseta num Game() novo de verdade (não
        # em load_level, que roda a cada avanço de fase).
        self.ranged_unlocked = False
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
        # Surface intermediária pro zoom da câmera (ver _blit_zoomed_world) —
        # criada só uma vez (não a cada quadro) e reaproveitada.
        self._world_surface = None
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
                # parry_flash.png ainda não foi salvo pelo Raul nessa pasta —
                # VFXManager ignora sozinho uma folha extra que não existe
                # ainda (ver __init__/spawn em vfx.py), então isso não
                # derruba o jogo enquanto o arquivo não chega.
                "parry": ASSET_DIR / "vfx" / "parry_flash.png",
            },
        )
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
    # Mesma ideia pro fundo da escola (céu/montanhas ao longe, visto pelas
    # janelas dos corredores) — anda bem mais devagar que a câmera.
    SCHOOL_BACKGROUND_PARALLAX = 0.3
    # Fundo dedicado da vila (céu com nuvens) — mesma ideia de parallax.
    VILLAGE_BACKGROUND_PARALLAX = 0.3
    # Cor lisa usada enquanto não existe backgrounds/village_background.png
    # (ver _draw_background) — um azul de céu simples, só pra não reaproveitar
    # o fundo da escola nem deixar a vila preta.
    VILLAGE_PLACEHOLDER_SKY = (144, 197, 230)

    def _load_backgrounds(self):
        school_background = self._load_scaled_background("backgrounds/background_school.png")
        university_background = self._load_scaled_background("backgrounds/university_background.png")
        cave_background = self._load_scaled_background("backgrounds/cave_background_v2.png")
        self.backgrounds = [school_background, university_background, cave_background]
        self.background_mirror = pygame.transform.flip(university_background, True, False)
        # Opcional: só existe depois que a arte "backgrounds/ceu.png" (céu com
        # nuvens, pedida pro Raul) for colocada na pasta. Até lá,
        # _draw_background cai no preenchimento liso (VILLAGE_PLACEHOLDER_SKY).
        village_path = ASSET_DIR / "backgrounds" / "ceu.png"
        self.village_background = (
            self._load_scaled_background("backgrounds/ceu.png")
            if village_path.exists()
            else None
        )

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
        /ataque 1 jato(7)/ataque 2 investida(8)/dano(4)/morte(12).

        casulo_acido.png/esporo_e_poca.png (vfx/boss_attacks) são o ataque C
        novo (Casulo Ácido, ver enemy.Specimen) — sprites únicos e estáticos
        gerados por código (LEIA-ME_sprites_chapados.md), não spritesheets.
        esporo_e_poca.png guarda os dois desenhos na mesma imagem (esporo em
        x 4..19, poça em x 28..61); _sheet_crop separa cada um."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "lab_specimen.png", 56, 48, [8, 8, 7, 8, 4, 12], scale=self.SPECIMEN_SCALE
        )
        spore_and_puddle = self._load_image("vfx/boss_attacks/esporo_e_poca.png")
        return {
            "idle": rows[0], "walk": rows[1],
            "jet": rows[2], "lunge": rows[3],
            "hurt": rows[4], "dead": rows[5],
            "cocoon": self._load_image("vfx/boss_attacks/casulo_acido.png"),
            "spore": self._sheet_crop(spore_and_puddle, (4, 0, 15, 32)),
            "puddle": self._sheet_crop(spore_and_puddle, (28, 0, 33, 32)),
        }

    def _load_librarian_sprites(self):
        """librarian_boss.png: quadro 64x64, grade 14x6 — repouso(8)/
        deslize(8)/ataque A silêncio(9)/ataque B errata(10)/dano(4)/
        morte(14). Os tomos do ataque B reaproveitam o ícone de livro da
        pesquisa (self.book) — mesma silhueta, sem precisar de arte nova.

        livro_escudo.png/lamina_de_pagina.png (vfx/boss_attacks) são o
        ataque C novo (Escudo de Página, ver enemy.Librarian) — sprites
        únicos e estáticos, mesmo padrão do meteoro/indicador do Dragão."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "librarian_boss.png", 64, 64, [8, 8, 9, 10, 4, 14], scale=self.LIBRARIAN_SCALE
        )
        return {
            "idle": rows[0], "walk": rows[1],
            "attack_a": rows[2], "attack_b": rows[3],
            "hurt": rows[4], "dead": rows[5],
            "tome": self.book,
            "shield": self._load_image("vfx/boss_attacks/livro_escudo.png"),
            "blade": self._load_image("vfx/boss_attacks/lamina_de_pagina.png"),
        }

    def _load_small_slime_sprites(self):
        """slime_common.png: quadro 32x32, grade 8x4 — repouso(6, não usado)
        /pulo(8)/dano(3)/morte(6). Mesmo corpo do Rei Slime sem coroa nem
        núcleo, usado pelos filhotes da Cisão."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "slime_common.png", 32, 32, [6, 8, 3, 6]
        )
        return {"walk": rows[1], "hurt": rows[2], "dead": rows[3]}

    # slime_king.png/dragon.png já nascem grandes (64x64/324x265); esta
    # escala é só o empurrão extra pedido no LEIA-ME pra eles lerem como os
    # maiores do jogo, o topo da hierarquia de tamanho.
    SLIME_KING_SCALE = 1.3
    # Folha nova do Dragão (2026-08, 9 quadros de 324x265 desenhados pelo
    # Raul) já nasce bem maior em pixels crus que a antiga (112x96) — daí a
    # escala em si ser menor que antes (era 2.4), mas o resultado final
    # ainda é BEM maior (324*2.0=648 x 265*2.0=530, quase 1/3 da largura da
    # tela de 1920 — pedido explícito: "ele será BEM maior do que o atual
    # já é... enorme"). Ver Dragon.WIDTH/HEIGHT em enemy.py pro ajuste
    # equivalente da hitbox (menor que o visual, mesmo padrão já usado nos
    # outros inimigos).
    DRAGON_SCALE = 2.0
    # Pedido do Raul: pedaços de pedra do Terremoto maiores (dragon_rock.png
    # nasce só 24x24, pequeno demais perto do Dragão enorme). A hitbox
    # (Dragon.ROCK_SIZE, em enemy.py) foi atualizada pra bater com o
    # mesmo tamanho final (24 * 2.2 arredondado = 53) — pedido do Raul:
    # "aumente a hitbox dos meteoros para ficarem iguais ao tamanho deles".
    # Mudar este número aqui exige atualizar ROCK_SIZE lá também.
    ROCK_SPRITE_SCALE = 2.2

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
        """dragon.png: folha nova do Raul (2026-08), UMA fileira só de 9
        quadros de 324x265 — 1 idle, 2 sopro (jato de fogo), 3 voo
        (decolagem/pairando) e 3 terremoto (batendo no chão), ver
        enemy.Dragon._sprite_key pro mapeamento exato de cada estado pra
        cada fatia. As pedras da queda do Terremoto (reaproveitadas da
        antiga Brasas) usam dragon_rock.png (24x24, 8 quadros: queda/
        impacto/explosão), desenhadas à parte pelo próprio Dragon.draw.

        Sem mais meteor/danger_marker aqui — o antigo ataque Voo da Fúria
        (meteoros mirados no chão) saiu de cena, ver docstring de
        enemy.Dragon."""
        rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "dragon.png", 324, 265, [9], scale=self.DRAGON_SCALE
        )
        frames = rows[0]
        rock_rows = self._load_grid_sheet(
            ASSET_DIR / "enemies" / "dragon_rock.png", 24, 24, [8], scale=self.ROCK_SPRITE_SCALE
        )
        sopro_ember, sopro_flame = self._load_dragon_fire_sprites()
        return {
            "idle": frames[0:1],
            "sopro": frames[1:3],
            "voo": frames[3:6],
            "terremoto": frames[6:9],
            "rock": rock_rows[0],
            "sopro_flame": sopro_flame,
            "sopro_ember": sopro_ember,
        }

    def _load_dragon_fire_sprites(self):
        """dragon_fire.png (imagem do Raul): uma faísca pequena e uma chama
        grande lado a lado no mesmo arquivo, tamanhos bem diferentes, sem
        grade fixa — em vez de recortar por coordenada fixa (frágil, ia
        quebrar se o Raul reexportar com proporções um pouco diferentes),
        corta a folha ao meio por proporção (a faísca sempre nasceu bem
        menor e à esquerda) e deixa get_bounding_rect achar o conteúdo real
        de cada metade, mesma técnica que _load_enemy_sheet já usa pros
        slimes. Devolve (faísca, chama) crus, sem escala — Dragon.draw (ver
        enemy.py) redimensiona a chama pra caber no retângulo de verdade
        do jato (SOPRO_RANGE x SOPRO_HEIGHT) a cada quadro."""
        sheet = pygame.image.load(ASSET_DIR / "enemies" / "dragon_fire.png").convert_alpha()
        split_x = round(sheet.get_width() * 0.32)
        ember_half = sheet.subsurface(pygame.Rect(0, 0, split_x, sheet.get_height()))
        flame_half = sheet.subsurface(
            pygame.Rect(split_x, 0, sheet.get_width() - split_x, sheet.get_height())
        )
        ember_content = ember_half.get_bounding_rect()
        flame_content = flame_half.get_bounding_rect()
        ember = ember_half.subsurface(ember_content).copy() if ember_content.width else None
        flame = flame_half.subsurface(flame_content).copy() if flame_content.width else None
        return ember, flame

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
        self._npc_dialogue_queue = []
        self._npc_dialogue_speaker = None
        self.hints_shown = set()
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
        self.combo_count = 0
        self.combo_timer = 0
        self.mouse_attack_requested = False
        self.ranged_cooldown = 0
        self.projectiles = []

    def _reset_input_state(self):
        self.interact_was_down = False
        self.attack_was_down = False
        self.dash_was_down = False
        self.ranged_was_down = False
        self.dialogue_advance_was_down = False
        self._item_key_was_down = {}

    def _reset_vfx_state(self):
        self.vfx.active = []
        self.dust_timer = 0
        self.was_swimming = False
        self.player_grounded = False

    # Quadros de invencibilidade após renascer: sem isso, se o checkpoint (ou
    # o próprio spawn) ficar perto de um espinho/inimigo, o toque volta a
    # acontecer nos quadros seguintes e consome as 3 vidas quase instantaneamente
    # — parecendo "morte direta" mesmo cada toque só custando 1 vida.
    INVULN_FRAMES = 90

    # Quadros dos 2 frames de morte (Player.DEATH_FRAMES, pedido do Raul)
    # parada no lugar onde ela morreu, antes do reposicionamento de verdade
    # (ver _finish_respawn) — metade do tempo em cada quadro.
    DEATH_POSE_DURATION = 24

    def _reset_status_state(self):
        self.invuln_timer = 0
        self.hitstop_timer = 0
        self.shake_timer = 0
        self.shake_duration = 0
        self.shake_magnitude = 0
        self.death_pose_timer = 0

    def _lose_life(self, amount=1):
        """Núcleo comum de qualquer perda de vida (pedido do Raul: dano de
        contato deixou de reposicionar — ver take_damage/respawn abaixo).
        `amount` é em corações (1 = coração inteiro, 0.5 = meio coração —
        ver MOB_CONTACT_DAMAGE/BOSS_CONTACT_DAMAGE) — self.lives virou
        fracionário por causa disso, e o HUD (hud.draw_hud/_draw_hearts)
        já sabe desenhar meio coração. Escudo absorve primeiro (Carcaça de
        robô/Dark Crystal, ver ITEM_DEFS — vale pra qualquer fonte e
        qualquer tamanho de dano: espinho, chefe, queda, afogar). Devolve
        True só quando vida foi perdida DE VERDADE (não absorvida pelo
        escudo e ainda sobrou vida) — quem chamou decide o que fazer
        depois disso (respawn reposiciona, take_damage não)."""
        if self.shield > 0:
            self.shield -= 1
            self.invuln_timer = self.INVULN_FRAMES
            self.vfx.spawn("impact", self.player.rect.centerx, self.player.rect.centery)
            self.message = "O escudo absorveu o dano!"
            self.message_timer = 90
            audio.play_sfx("shield_sound")
            return False
        # Na universidade, o "toque que machuca" costuma ser vidro quebrado
        # ou a poça química — o estilhaço de vidro combina melhor com o
        # tema do que o impacto genérico usado nas outras fases.
        if self.level.room == "laboratorio":
            vfx_kind = "acid_burn"
        elif self.level.room == "biblioteca":
            vfx_kind = "ink_splash"
        elif self.level.index == 1:
            vfx_kind = "glass"
        else:
            vfx_kind = "impact"
        self.vfx.spawn(vfx_kind, self.player.rect.centerx, self.player.rect.centery)
        audio.play_sfx("damage_sound")
        # max(0, ...) em vez de só subtrair: sem isso um chefe (1 coração
        # inteiro) batendo com meio coração sobrando deixaria self.lives
        # negativo, o que o HUD não sabe desenhar.
        self.lives = max(0, self.lives - amount)
        self.invuln_timer = self.INVULN_FRAMES
        if self.lives <= 0:
            self.state = GAME_OVER
            self.game_over_fade = 0
            self.game_over_characters = 0
            audio.play_sfx("death_sound")
            return False
        return True

    def take_damage(self, amount=1):
        """Dano de contato (inimigo, espinho, lava, ataque à distância de
        chefe, afogamento) — pedido do Raul: NÃO reposiciona mais a Lia,
        só tira `amount` corações e dá 1s de invencibilidade
        (INVULN_FRAMES). Ela continua exatamente onde apanhou. Só cair no
        vazio ainda reposiciona de verdade — ver respawn()."""
        self._lose_life(amount)

    def respawn(self):
        """Reservado pra quando a Lia cai no vazio (ver check_events, a
        única chamada que sobrou) — continua reposicionando de verdade:
        perde 1 coração inteiro, congela na pose de morte, e só depois
        volta pro checkpoint/saída de sala (ver _finish_respawn)."""
        if self._lose_life():
            # Reposicionar (exit_room/checkpoint) fica pra depois — ver
            # _finish_respawn, chamado por _update_playing quando
            # death_pose_timer chega a 0. Isso dá tempo dos 2 frames de
            # morte (Player.DEATH_FRAMES) aparecerem parada no lugar onde
            # ela morreu, em vez dela sumir/reaparecer instantaneamente.
            self.death_pose_timer = self.DEATH_POSE_DURATION

    def _apply_death_frame(self):
        elapsed = self.DEATH_POSE_DURATION - self.death_pose_timer
        index = 1 if elapsed >= self.DEATH_POSE_DURATION / 2 else 0
        self.player.frame = self.player.DEATH_FRAMES[index]

    def _finish_respawn(self):
        """A parte de respawn() que reposiciona de verdade — adiada até o
        fim da pose de morte (ver respawn/_apply_death_frame)."""
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
        self._update_music()
        dialogue_advance_pressed, attack_pressed, dash_pressed, ranged_pressed = self._read_input(keyboard)

        if self.state == TITLE:
            self._update_title(keyboard)
        elif self.state == INTRO:
            self._update_intro(keyboard, dialogue_advance_pressed)
        elif self.state in (GAME_OVER, COMPLETE):
            self._update_end_state(keyboard)
        elif self.dialogue.active:
            self._update_dialogue(dialogue_advance_pressed)
        elif self.hint.active:
            self._update_hint(dialogue_advance_pressed)
        else:
            self._read_item_use(keyboard)
            self._update_playing(keyboard, dash_pressed, attack_pressed, ranged_pressed, dt)

    def _read_input(self, keyboard):
        interaction_down = keyboard.e or keyboard.RETURN
        dialogue_advance_down = interaction_down or keyboard.space
        attack_down = keyboard.f
        dash_down = keyboard.q
        ranged_down = keyboard.r

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

        ranged_pressed = ranged_down and not self.ranged_was_down
        self.ranged_was_down = ranged_down
        return dialogue_advance_pressed, attack_pressed, dash_pressed, ranged_pressed

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
            audio.play_sfx("select_sound")
            self.lives = STARTING_LIVES
            self.state = INTRO
            self.intro.start()

    def _update_intro(self, keyboard, dialogue_advance_pressed):
        """A mãe de Lia no hospital (ver cutscene.IntroCutscene) — ESC pula
        direto pra vila, senão a cena avança do mesmo jeito que qualquer
        outro diálogo do jogo (E/Enter/Espaço). Dali ela vai pra vila (ver
        PLANO_VILA.md/level.VILLAGE) antes da Fase 1 — não direto pra
        Fase 1 como antes."""
        if getattr(keyboard, "escape", False):
            self.intro.skip()
        else:
            self.intro.update(dialogue_advance_pressed)
        if not self.intro.active:
            self.load_level(VILLAGE)

    def _update_end_state(self, keyboard):
        if self.state == GAME_OVER:
            self.game_over_fade = min(60, self.game_over_fade + 1)
            if self.game_over_fade >= 18:
                self.game_over_characters += 0.75
        if keyboard.r:
            audio.play_sfx("select_sound")
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
            audio.play_sfx("dialogue_sound")
            if self.dialogue.finished:
                if self._npc_dialogue_queue:
                    # Conversa de vários beats (ex.: Sra. Amélia, ver
                    # _talk_to_npc) — próxima fala em vez de fechar.
                    next_text = self._npc_dialogue_queue.pop(0)
                    self.dialogue.start(self._npc_dialogue_speaker, next_text)
                else:
                    self.dialogue.close()
            else:
                self.dialogue.reveal_all()
        else:
            self.dialogue.update()

    def _update_playing(self, keyboard, dash_pressed, attack_pressed, ranged_pressed, dt):
        self._update_shake()
        if self.hitstop_timer > 0:
            # Congela a simulação (pedido do Raul: hit-stop no parry, ver
            # _check_parries) — o shake continua contando acima pra já estar
            # decaindo quando a simulação voltar, em vez de só começar depois.
            self.hitstop_timer -= 1
            return
        if self.death_pose_timer > 0:
            # Congela do mesmo jeito que o hit-stop, mas pra mostrar os 2
            # frames de morte (ver respawn/_apply_death_frame) parada onde
            # ela caiu antes de reaparecer no checkpoint/porta.
            self.death_pose_timer -= 1
            self._apply_death_frame()
            if self.death_pose_timer == 0:
                self._finish_respawn()
            return
        self.player.update_abilities()
        if dash_pressed and not self.player.swimming:
            if self.player.start_dash():
                audio.play_sfx("dash_sound")
        self.player.read_controls(keyboard)
        self._update_attack(attack_pressed)
        self._update_ranged_attack(ranged_pressed)
        self._maybe_wake_bosses()
        self._face_bosses_at_player()
        self.level.update()
        self._check_boss_shake_events()
        if self.level.tiled_map:
            # Avança a animação dos tiles do Tiled (ex.: água da Fase 3) em ms.
            self.level.tiled_map.update(dt * 1000)
        self._move_with_platform()
        self.move_player()
        self._apply_boss_arena_clamp()
        self.player.animate()
        self._apply_attack_frame()
        self._update_vfx()
        self._update_camera()
        self.message_timer = max(0, self.message_timer - 1)
        self.handle_interactions()
        self._maybe_trigger_hints()
        self.check_events()

    def _update_hint(self, dialogue_advance_pressed):
        # A alavanca continua animando durante a dica, igual acontece durante
        # um diálogo (ver _update_dialogue) — evita ela "congelar" no meio de
        # um movimento se a dica disparar bem na hora de puxar a alavanca.
        if self.level.is_underground:
            self.level.update_lever_animations()
        self.hint.update()
        if dialogue_advance_pressed:
            self.hint.close()

    def _maybe_trigger_hints(self):
        """Dicas contextuais de uma vez só por fase (hints_shown reseta em
        load_level, igual seen_dialogues). Por enquanto só a do painel do
        elevador na Fase 1: dispara ao pisar na plataforma que antecede o
        primeiro elevador — ANTES da Lia sequer chegar na alavanca —
        enquanto o painel ainda não foi ligado."""
        if self.hint.active or self.dialogue.active:
            return
        if (
            self.level.is_underground
            and not self.lever_on
            and "elevator_panel" not in self.hints_shown
            and self._touching_elevator_approach()
        ):
            self.hints_shown.add("elevator_panel")
            self.hint.show(
                "Painel do Elevador",
                (
                    "Os botões lá em cima só funcionam com o painel ligado.",
                    "Ative a alavanca do painel antes de subir pelo elevador.",
                ),
            )

    # Raio (px, medido centro-a-centro) em que um chefe dormente acorda ao
    # se aproximar a Lia (ver enemy.py: SlimeKing/Librarian/Specimen/Dragon
    # nascem em DORMANT e só saem desse estado via wake_up()). Generoso o
    # bastante pra acordar antes da Lia encostar nele, cedo o suficiente pra
    # não ficar sendo golpeado "de graça" enquanto ainda dorme, mas sem
    # acordar assim que a fase carrega — estilo Silksong, onde o chefe fica
    # parado até o jogador chegar perto da arena.
    BOSS_WAKE_RADIUS = 420

    def _maybe_wake_bosses(self):
        """Confere todo inimigo vivo da fase (não só os de boss_arenas —
        Librarian/Specimen não têm arena gerada por código, só a sala fixa
        do Tiled, então checar self.level.enemies direto cobre os 4 chefes
        com o mesmo código). Uma vez acordado (wake_up), o chefe nunca volta
        a dormir, mesmo que a Lia se afaste — combina com o resto do jogo,
        onde nenhum chefe "reseta" sozinho."""
        player_center = self.player.rect.center
        for enemy in self.level.enemies:
            wake_up = getattr(enemy, "wake_up", None)
            if wake_up is None or enemy.state != getattr(enemy, "DORMANT", None):
                continue
            dx = enemy.rect.centerx - player_center[0]
            dy = enemy.rect.centery - player_center[1]
            if dx * dx + dy * dy <= self.BOSS_WAKE_RADIUS * self.BOSS_WAKE_RADIUS:
                wake_up()
                audio.play_sfx("boss_wake_sound")

    def _face_bosses_at_player(self):
        """Chefes sempre virados pra Lia (pedido do Raul: eles às vezes
        ficavam olhando pro lado errado e os ataques saíam desalinhados) —
        cada classe decide sozinha quando é seguro virar (ver
        enemy.<Boss>.face_player/FACING_STATES: nunca no meio da própria
        patrulha nem de um ataque já em execução, só parado ou ainda na
        antecipação — assim a direção já está certa bem antes do golpe
        de verdade sair)."""
        player_x = self.player.rect.centerx
        for enemy in self.level.enemies:
            face_player = getattr(enemy, "face_player", None)
            if face_player:
                face_player(player_x)

    def _check_boss_shake_events(self):
        """Genérico de propósito (getattr, só o Dragão define isso hoje —
        ver enemy.Dragon.consume_shake_event/_slam_impact): dá o "peso" do
        tranco do Terremoto sacudindo a câmera + tocando earthquake_dragon_
        sound, igual ao hit-stop/shake que o parry já usa (ver
        _trigger_shake)."""
        for enemy in self.level.enemies:
            consume = getattr(enemy, "consume_shake_event", None)
            if consume and consume():
                self._trigger_shake(EARTHQUAKE_SHAKE_DURATION, EARTHQUAKE_SHAKE_MAGNITUDE)
                audio.play_sfx("earthquake_dragon_sound")

    # Distância (px) antes do elevador em que o corredor de aproximação
    # começa — folga generosa de propósito, pra não depender de acertar uma
    # faixa estreita de pixels.
    ELEVATOR_APPROACH_RANGE = 750

    def _touching_elevator_approach(self):
        """Corredor antes do PRIMEIRO elevador que a Lia encontra andando da
        esquerda pra direita a partir do spawn. Conferindo fase1_escola.tmx:
        elevador_superior nasce em x=1750 e elevador_principal em x=2670 —
        ou seja, apesar do nome, é o "superior" (Level.upper_elevator, o que
        leva lá em cima pros botões do painel) que vem PRIMEIRO no percurso,
        não o "principal" (Level.elevator, que só aparece depois, e desce
        pra um andar de baixo onde fica a alavanca do painel). A dica é
        sobre os botões precisarem do painel ligado, então faz sentido
        mesmo ser este: é o elevador que leva direto pra área dos botões.
        Dispara em qualquer lugar dentro de ELEVATOR_APPROACH_RANGE px à
        esquerda dele, sem exigir uma faixa vertical exata. Ancorado no x
        (fixo; só a altura muda ao subir/descer, ver call_upper_elevator),
        então funciona tanto no laboratório manual (fallback) quanto no
        mapa do Tiled."""
        elevator = self.level.upper_elevator
        if not elevator:
            return False
        return elevator.rect.x - self.ELEVATOR_APPROACH_RANGE <= self.player.rect.centerx <= elevator.rect.x

    def _update_attack(self, attack_pressed):
        self.attack_cooldown = max(0, self.attack_cooldown - 1)
        self.combo_timer = max(0, self.combo_timer - 1)
        if attack_pressed and self.attack_cooldown == 0:
            self.attack_timer = ATTACK_DURATION
            self.attack_cooldown = ATTACK_COOLDOWN
            # Combo (pedido do Raul): ainda dentro da janela do golpe
            # anterior avança pro próximo hit (ciclando 1-4); passou da
            # janela, volta pro 1 — ver COMBO_RESET_WINDOW.
            if self.combo_timer > 0:
                self.combo_count += 1
                if self.combo_count > COMBO_HIT_COUNT:
                    self.combo_count = 1
            else:
                self.combo_count = 1
            self.combo_timer = COMBO_RESET_WINDOW
            # 4 variações gravadas (sounds/punch/punch_1..4, ver
            # PLANO_AUDIO.md) — uma pra cada hit do combo, em vez de tocar
            # sempre o mesmo som de soco.
            audio.play_sfx(f"punch.punch_{self.combo_count}")
            if self.player.dashing:
                self.attack_power = DASH_ATTACK_POWER
            elif self.combo_count == COMBO_HIT_COUNT:
                self.attack_power = COMBO_FINISHER_POWER
            else:
                self.attack_power = STANDARD_ATTACK_POWER
        if self.attack_timer:
            self.attack_timer -= 1
            if self.attack_timer == 0:
                self.attack_power = STANDARD_ATTACK_POWER

    def _apply_attack_frame(self):
        """Sobrepõe o frame calculado por Player.animate() enquanto o golpe
        tá ativo — combo_count já reflete o hit certo desse swing (definido
        em _update_attack, sempre antes disso rodar, ver _update_playing).
        Fora daí Player.animate() decide sozinho (parado/andando/pulando)."""
        if not self.attack_timer:
            return
        self.player.frame = self.player.ATTACK_FRAMES[self.combo_count - 1]

    def _update_ranged_attack(self, ranged_pressed):
        self.ranged_cooldown = max(0, self.ranged_cooldown - 1)
        if not (ranged_pressed and self.ranged_unlocked and self.ranged_cooldown == 0):
            return
        self.ranged_cooldown = RANGED_ATTACK_COOLDOWN
        audio.play_sfx("projectile_sound")
        direction = 1 if self.player.facing_right else -1
        # Nasce um pouco à frente da hitbox, na altura do peito — assim o
        # projétil não colide "dentro" da própria Lia no quadro em que nasce.
        origin_x = self.player.rect.centerx + direction * (PLAYER_HITBOX_WIDTH // 2 + 8)
        origin_y = self.player.rect.centery - 4
        self.projectiles.append(
            Projectile(
                origin_x, origin_y, direction,
                RANGED_PROJECTILE_SPEED, RANGED_ATTACK_POWER, RANGED_PROJECTILE_RANGE,
            )
        )

    def _update_projectiles(self):
        """Move cada projétil e confere colisão contra os mesmos inimigos que
        check_enemies já usa pro ataque corpo a corpo (mesma interface
        take_hit/alive, incluindo chefes) — um acerto consome o projétil."""
        for projectile in self.projectiles:
            if not projectile.alive:
                continue
            projectile.update()
            if not projectile.alive:
                continue
            for enemy in self.level.enemies:
                if not enemy.alive:
                    continue
                if not projectile.rect.colliderect(enemy.rect):
                    continue
                if enemy.take_hit(projectile.power):
                    self.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                    if not enemy.alive:
                        self._on_enemy_defeated(enemy)
                projectile.alive = False
                break
        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]

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

    def _update_shake(self):
        self.shake_timer = max(0, self.shake_timer - 1)

    def _trigger_shake(self, duration, magnitude):
        """Genérico de propósito (não só do parry) — guarda a duração junto
        pra _shake_offset saber a proporção certa de decaimento, já que
        shake_timer sozinho não diz se começou em 14 quadros ou em 40."""
        self.shake_timer = duration
        self.shake_duration = duration
        self.shake_magnitude = magnitude

    def _shake_offset(self):
        if self.shake_timer <= 0 or self.shake_duration <= 0:
            return 0, 0
        magnitude = self.shake_magnitude * (self.shake_timer / self.shake_duration)
        return random.uniform(-magnitude, magnitude), random.uniform(-magnitude, magnitude)

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

    def move_player(self):
        """Resolve colisões horizontais, verticais e o pulo sobre inimigos."""
        player = self.player
        solids = self._all_solid_rectangles()
        player.swimming = self._player_in_water(player)
        if player.swimming:
            player.cancel_dash()

        previous_x = player.x
        player.x += player.vx
        self._resolve_horizontal_collisions(player, solids, previous_x)

        if player.swimming:
            player.apply_swim_gravity()
        else:
            player.apply_gravity()

        previous_y = player.y
        previous_bottom = previous_y + PLAYER_HEIGHT
        player.y += player.vy

        if not player.swimming and self._stomp_enemy_if_possible(player, previous_bottom):
            return

        landed = self._resolve_vertical_collisions(player, previous_y, previous_bottom)
        self.player_grounded = landed
        # Espelha no próprio Player (pedido do Raul: pulo de 3 fases —
        # subindo/no ar/caindo — ver Player.animate) porque animate() roda
        # dentro da classe Player, sem acesso direto a self.player_grounded
        # daqui.
        player.grounded = landed
        if player.swimming:
            # Sem chão firme pra reaproveitar debaixo d'água.
            player.coyote_time = 0
        else:
            player.coyote_time = 7 if landed else max(0, player.coyote_time - 1)
        if player.try_jump():
            audio.play_sfx("jump")

    def _player_in_water(self, player):
        return any(player.rect.colliderect(zone) for zone in self.level.water_zones)

    def _all_solid_rectangles(self):
        # solids_near em vez de self.level.grounds inteiro: numa
        # fase grande (Fase 3, 315x100 tiles) essas listas passam de mil
        # retângulos, e checar todos 2x por quadro (colisão horizontal e
        # vertical) era o motivo real do lag reportado lá — ver
        # Level.solids_near/_build_solid_chunks.
        return (
            self.level.solids_near(self.player.rect)
            + [platform.rect for platform in self.level.platforms]
        )

    @staticmethod
    def _resolve_horizontal_collisions(player, solids, previous_x):
        """Pedido do Raul (melhorar colisões — às vezes dava pra entrar
        dentro de bloco): o teste antigo exigia `previous_right <=
        solid.left` (zero de tolerância) pra empurrar a Lia de volta pra
        fora. Isso só funciona se o quadro anterior tiver a hitbox
        COMPLETAMENTE fora do bloco — em qualquer situação que já comece
        um pouco embromada pra dentro (dash a 14px/quadro, ou o empurrão
        extra de uma plataforma móvel somado ao próprio vx no mesmo
        quadro, ver Game._move_with_platform, que roda ANTES daqui e já
        desloca previous_x), o teste falhava silenciosamente e ela ficava
        atravessando o bloco quadro após quadro sem nunca ser reposicionada.
        Comparar contra a borda OPOSTA do bloco (`solid.right`/`solid.left`)
        em vez da borda de entrada resolve isso: só deixa de empurrar pra
        fora quando ela já tiver saído por completo do outro lado (um
        "atravessou de ponta a ponta num quadro só" de verdade, que exigiria
        mais de ~32px de deslocamento horizontal num único quadro — bem
        acima de qualquer velocidade que a Lia atinge hoje)."""
        for solid in solids:
            if not player.rect.colliderect(solid):
                continue

            previous_right = previous_x + PLAYER_HITBOX_OFFSET_X + PLAYER_HITBOX_WIDTH
            previous_left = previous_x + PLAYER_HITBOX_OFFSET_X
            if player.vx > 0 and previous_right <= solid.right:
                player.x = solid.left - PLAYER_HITBOX_WIDTH - PLAYER_HITBOX_OFFSET_X
                player.cancel_dash()
            elif player.vx < 0 and previous_left >= solid.left:
                player.x = solid.right - PLAYER_HITBOX_OFFSET_X
                player.cancel_dash()

    def _stomp_enemy_if_possible(self, player, previous_bottom):
        for enemy in self.level.enemies:
            # Chefes (BOSS_DROP_TABLE = SlimeKing/Librarian/Specimen/Dragon)
            # ficam de fora do pulo-que-mata: pousar na cabeça deles não pode
            # ser um jeito de matar em um golpe só uma luta pensada pra durar
            # vários acertos — pisar neles agora não faz nada de especial,
            # cai no contato normal (dano) tratado por check_enemies.
            if type(enemy).__name__ in BOSS_DROP_TABLE:
                continue
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
            audio.play_sfx("boss_death_sound")
            self._spawn_drop(quest_item, enemy.rect.centerx, enemy.rect.centery)
            return
        audio.play_sfx("enemy_death_sound")
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
                audio.play_sfx("item_sound")
                self.vfx.spawn("dust", drop["x"], drop["y"])
            else:
                remaining.append(drop)
        self.pending_drops = remaining

    def _resolve_vertical_collisions(self, player, previous_y, previous_bottom):
        """Mesma correção de _resolve_horizontal_collisions (pedido do
        Raul — atravessar plataforma às vezes): a tolerância antiga de
        "+10"/"-10" era um número mágico fixo, sem relação com a espessura
        de verdade da plataforma/bloco — uma plataforma móvel fina ou uma
        queda rápida o bastante podia passar direto sem os 10px darem
        conta. Comparar contra a borda OPOSTA do sólido (`solid.bottom`/
        `solid.top`, igual ao equivalente horizontal) usa a espessura real
        dele como tolerância em vez de um valor fixo — só deixa de
        resolver quando ela já tiver atravessado o bloco INTEIRO num
        quadro só.

        Pedido do Raul (Fase 1 lagando muito depois de pintar chão de
        verdade): esta função ainda montava ground_solids a partir de
        self.level.grounds INTEIRO — TODO tile sólido do mapa, sem
        nenhum filtro — e testava colisão contra a lista toda a cada
        quadro. Isso passou despercebido no ajuste de lag da Fase 3
        porque na época só o lado horizontal (_all_solid_rectangles,
        chamado por move_player) tinha sido trocado pra usar
        Level.solids_near (chunks perto da Lia); o vertical continuou
        com a lista cheia, só que ninguém tinha chão pintado o
        suficiente pra sentir o custo — a Fase 1 só expôs o bug de
        verdade quando ganhou terreno real na camada Colisão. Mesmo
        remédio aqui: solids_near em vez da lista inteira."""
        landed = False
        self.riding_platform = None
        platform_solids = [
            (platform.rect, platform) for platform in self.level.platforms
        ]
        ground_solids = [
            (ground, None) for ground in self.level.solids_near(player.rect)
        ]

        for solid, moving_platform in platform_solids + ground_solids:
            if (
                player.rect.colliderect(solid)
                and player.vy >= 0
                and previous_bottom <= solid.bottom
            ):
                player.y = solid.top - PLAYER_HEIGHT
                player.vy = 0
                landed = True
                if moving_platform:
                    self.riding_platform = moving_platform
            elif (
                player.rect.colliderect(solid)
                and player.vy < 0
                and previous_y >= solid.top
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
        self._check_parries(player)
        if self._check_enemy_attack_hazards(player):
            return

        self.check_enemies()
        self._update_projectiles()
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
            audio.play_sfx("item_sound")
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
        # Sem esse guard, ela tomaria dano TODO quadro parada embaixo
        # d'água sem ar (não reposiciona mais pra fora da água — ver
        # take_damage) — o mesmo guard que _check_hazards/
        # _check_enemy_attack_hazards já usavam, só que esse aqui não
        # existia porque antes respawn() sempre tirava ela dali na hora.
        if self.invuln_timer > 0:
            return False
        player.oxygen = max(0, player.oxygen - player.OXYGEN_DRAIN_PER_FRAME)
        if player.oxygen <= 0:
            # Afogar não é "chefe" nem "mob" — cai no mesmo balde dos
            # hazards ambientais (MOB_CONTACT_DAMAGE), não no dano cheio de
            # chefe.
            self.take_damage(MOB_CONTACT_DAMAGE)
            return True
        return False

    def _check_hazards(self, player):
        if self.invuln_timer > 0:
            return False
        # Espinho/lava são hazard ambiental, não "chefe" — mesmo dano de
        # mob comum (ver MOB_CONTACT_DAMAGE).
        for hazard in self.level.hazards:
            if player.rect.colliderect(hazard):
                self.take_damage(MOB_CONTACT_DAMAGE)
                return True
        for lake in self.level.lava_lakes:
            if player.rect.colliderect(lake):
                self.take_damage(MOB_CONTACT_DAMAGE)
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
                    # active_hazards só existe nos chefes (jato do Espécime,
                    # onda do Rei Slime, tomos/lâminas do Bibliotecário) —
                    # sempre dano de chefe, não precisa checar BOSS_DROP_TABLE.
                    self.take_damage(BOSS_CONTACT_DAMAGE)
                    return True
        return False

    def _check_parries(self, player):
        """Parry (pedido do Raul): só hazards que "voam" — pedras/meteoros
        do Dragão ainda caindo, tomos mergulhando e lâminas do Bibliotecário,
        jato do Espécime (ver <Boss>.parryable_hazards em enemy.py) — nunca
        ondas no chão nem investidas corpo a corpo, essas classes nem
        definem o método, então getattr cai em None e passa reto. Sem botão
        novo: é o mesmo attack_box do ataque corpo a corpo normal
        (_attack_box), só que testado ANTES de _check_enemy_attack_hazards
        pra um parry bem-sucedido não também respawnar a Lia no mesmo
        quadro. Acerto certo: cancel() destrói o hazard específico e o dano
        volta pro chefe que o lançou via take_hit — mesma interface que o
        ataque à distância já usa pra furar melee_vulnerable."""
        attack_box = self._attack_box()
        if not attack_box:
            return False
        for enemy in self.level.enemies:
            if not enemy.alive:
                continue
            get_pairs = getattr(enemy, "parryable_hazards", None)
            if not get_pairs:
                continue
            for rect, cancel in get_pairs():
                if not attack_box.colliderect(rect):
                    continue
                cancel()
                self.vfx.spawn("parry_flash", rect.centerx, rect.centery)
                # 1s de invencibilidade (pedido do Raul) pra sobreviver ao
                # resto de um ataque com vários hits (ex.: as 5 lâminas do
                # Bibliotecário) depois de aparar só o primeiro — max() pra
                # nunca ENCURTAR um invuln maior já rolando (ex.: acabou de
                # respawnar). Hit-stop + shake dão o "peso" do acerto.
                self.invuln_timer = max(self.invuln_timer, PARRY_INVULN_FRAMES)
                self.hitstop_timer = PARRY_HITSTOP_FRAMES
                self._trigger_shake(PARRY_SHAKE_DURATION, PARRY_SHAKE_MAGNITUDE)
                audio.play_sfx("parry_sound")
                if enemy.take_hit(PARRY_DAMAGE) and not enemy.alive:
                    self._on_enemy_defeated(enemy)
                return True
        return False

    def _check_checkpoints(self, player):
        for checkpoint in self.level.checkpoints:
            if player.rect.colliderect(checkpoint):
                new_checkpoint = (checkpoint.x, checkpoint.bottom - PLAYER_HEIGHT)
                if new_checkpoint != self.checkpoint:
                    audio.play_sfx("checkpoint_sound")
                self.checkpoint = new_checkpoint
                self.message = "Checkpoint: Centro de pesquisa alcançado!"
                self.message_timer = 130

    def _collect_research(self, player):
        for index, (item, name) in enumerate(self.level.research):
            if index in self.collected or not player.rect.colliderect(item):
                continue

            self.collected.add(index)
            self.message = f"Parte da pesquisa obtida: {name}"
            self.message_timer = 0
            audio.play_sfx("item_sound")
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
                audio.play_sfx("item_sound")

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
        elif self.level.index == VILLAGE:
            # Fim da rua da vila = caminho pra floresta → Fase 1 (ver
            # PLANO_VILA.md). Não é "fase+1" porque VILLAGE não é um índice
            # numérico — cai fora de PHASES de propósito.
            self.load_level(0)
        elif self.level.index == len(PHASES) - 1:
            self.state = COMPLETE
        else:
            finished_index = self.level.index
            self.load_level(finished_index + 1)
            # load_level já sobrescreveu self.message com o subtítulo da fase
            # nova (message_timer=0, ver load_level) — o aviso de desbloqueio
            # entra DEPOIS de propósito, pra não ser apagado por ele.
            if finished_index == 0 and not self.ranged_unlocked:
                self.ranged_unlocked = True
                self.message = "Novo poder: Ataque à Distância [R] desbloqueado!"
                self.message_timer = 240

    def check_enemies(self):
        """Verifica ataque, ataque reforçado durante dash e contato com slimes.
        `melee_vulnerable` (Dragon/Librarian/Specimen em enemy.py — os
        inimigos comuns e o Rei Slime não definem isso, então getattr cai em
        True) deixa um chefe imune a corpo a corpo em certas fases (ex.:
        voando, escudo levantado, dentro do casulo); nesses momentos,
        acertar o corpo dele com a espada não causa dano — só o ataque à
        distância funciona — mas ainda dói tocar nele."""
        attack_box = self._attack_box()
        for enemy in self.level.enemies:
            if not enemy.alive:
                continue
            melee_hit = (
                attack_box
                and attack_box.colliderect(enemy.rect)
                and getattr(enemy, "melee_vulnerable", True)
            )
            if melee_hit:
                if enemy.take_hit(self.attack_power):
                    self.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                    if not enemy.alive:
                        self._on_enemy_defeated(enemy)
                    else:
                        is_boss = type(enemy).__name__ in BOSS_DROP_TABLE
                        audio.play_sfx("boss_hit_sound" if is_boss else "enemy_hit_sound")
            elif self.invuln_timer <= 0 and self.player.rect.colliderect(enemy.rect):
                is_boss = type(enemy).__name__ in BOSS_DROP_TABLE
                self.take_damage(BOSS_CONTACT_DAMAGE if is_boss else MOB_CONTACT_DAMAGE)
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
            audio.play_sfx("door_sound")
            if door["target"] == "sair":
                self.exit_room()
            else:
                self.enter_room(door["target"])
            return True
        return False

    NPC_INTERACT_RANGE = 40

    def _talk_to_npc(self):
        """Os NPCs nunca são consumidos — dá pra falar com eles quantas
        vezes quiser (ver NPC_DIALOGUES). Mesmo raio/padrão de detecção das
        portas, só que contra Level.npcs. NPC_DIALOGUES[nome] pode ser uma
        string (fala única, a maioria) ou uma tupla (várias falas em
        sequência, ex.: Sra. Amélia na vila) — nesse caso só a primeira
        entra aqui; o resto é consumido por _update_dialogue a cada [E]
        seguinte, via self._npc_dialogue_queue."""
        player = self.player
        for npc in self.level.npcs:
            if not player.rect.colliderect(npc["rect"].inflate(self.NPC_INTERACT_RANGE, self.NPC_INTERACT_RANGE)):
                continue
            text = NPC_DIALOGUES.get(npc["name"])
            if isinstance(text, tuple):
                if text:
                    self._npc_dialogue_speaker = npc["name"]
                    self._npc_dialogue_queue = list(text[1:])
                    self.dialogue.start(npc["name"], text[0])
            elif text:
                self._npc_dialogue_queue = []
                self.dialogue.start(npc["name"], text)
            return True
        return False

    def _use_elevator_lever(self, player):
        if self.level.top_lever and player.rect.colliderect(self.level.top_lever.inflate(55, 55)):
            audio.play_sfx("lever_sound")
            self.level.call_elevator("down")
            return True
        if self.level.bottom_lever and player.rect.colliderect(self.level.bottom_lever.inflate(55, 55)):
            audio.play_sfx("lever_sound")
            self.level.call_elevator("up")
            return True
        if (
            self.level.upper_bottom_lever
            and player.rect.colliderect(self.level.upper_bottom_lever.inflate(55, 55))
        ):
            audio.play_sfx("lever_sound")
            self.level.call_upper_elevator("up")
            return True
        if (
            self.level.upper_top_lever
            and player.rect.colliderect(self.level.upper_top_lever.inflate(55, 55))
        ):
            audio.play_sfx("lever_sound")
            self.level.call_upper_elevator("down")
            return True
        return False

    def _use_panel_lever(self, player):
        if not player.rect.colliderect(self.level.panel_lever.inflate(55, 55)):
            return False

        audio.play_sfx("lever_sound")
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
                audio.play_sfx("button_sound")
                self.sequence_progress += 1
                if self.sequence_progress == len(self.level.buttons):
                    self.sequence_solved = True
                    audio.play_sfx("correct_sequence_sound")
                    self.dialogue.start(
                        "Painel",
                        "Sequência correta! As peças do microscópio foram liberadas.",
                    )
            else:
                audio.play_sfx("wrong_sequence_sound")
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
            audio.play_sfx("microscope_sound")
            self.level.activate_return_route()
            self.dialogue.start(
                "Lia",
                "Microscópio montado! As plataformas de retorno foram liberadas; preciso voltar pelo caminho acima.",
            )

    def draw(self, screen):
        real_surface = screen.surface
        real_surface.fill((6, 14, 29))
        if self.state == INTRO:
            self.intro.draw(real_surface, draw_text)
            return
        # Mundo inteiro continua desenhado do jeito de sempre, só que numa
        # surface separada do mesmo tamanho (WIDTH x HEIGHT) em vez de ir
        # direto pra tela — _blit_zoomed_world recorta uma janela menor
        # centrada na Lia e amplia pro tamanho da tela (ver CAMERA_ZOOM em
        # settings.py). Isso dá o efeito de zoom sem precisar mexer em
        # nenhuma conta de câmera/parallax/HUD já existente.
        if self._world_surface is None:
            self._world_surface = pygame.Surface((WIDTH, HEIGHT)).convert()
        surface = self._world_surface
        surface.fill((6, 14, 29))
        # Shake (ver _trigger_shake/_update_shake) só desloca o mundo — a
        # câmera some pro valor de verdade logo antes do HUD, senão a barra
        # de vida do chefe e o resto da interface também tremeriam junto,
        # o que fica ilegível em vez de impactante.
        shake_x, shake_y = self._shake_offset()
        self.camera_x += shake_x
        self.camera_y += shake_y
        self._draw_background(surface)
        self._draw_world(surface)
        self._draw_door_prompts(surface)
        self._draw_npc_prompts(surface)
        self._draw_player_light(surface)
        self.draw_dash_trail(surface)
        self.player.draw(surface, self.camera_x, self.camera_y)
        self._draw_world_foreground(surface)
        self.vfx.draw(surface, self.camera_x, self.camera_y)
        for projectile in self.projectiles:
            projectile.draw(surface, self.camera_x, self.camera_y)
        self.camera_x -= shake_x
        self.camera_y -= shake_y
        self._blit_zoomed_world(real_surface, surface)
        self._draw_interface(real_surface)
        self._draw_state_overlay(real_surface)
        self.hint.draw(real_surface, draw_text)

    def _blit_zoomed_world(self, real_surface, world_surface):
        """Recorta uma janela CAMERA_ZOOM vezes menor que a tela, centrada
        na Lia, e amplia de volta pro tamanho cheio — o mesmo truque de
        "recorta e amplia" que usamos pro tamanho do sprite dela, só que
        aplicado no frame inteiro. Roda uma vez por quadro (pygame.transform
        .scale é C puro, não pesa)."""
        if CAMERA_ZOOM == 1:
            real_surface.blit(world_surface, (0, 0))
            return
        crop_width = max(1, round(WIDTH / CAMERA_ZOOM))
        crop_height = max(1, round(HEIGHT / CAMERA_ZOOM))
        player_screen_x = self.player.rect.centerx - self.camera_x
        player_screen_y = self.player.rect.centery - self.camera_y
        crop_x = round(player_screen_x - crop_width / 2)
        crop_y = round(player_screen_y - crop_height / 2)
        crop_x = max(0, min(crop_x, WIDTH - crop_width))
        crop_y = max(0, min(crop_y, HEIGHT - crop_height))
        cropped = world_surface.subsurface(
            pygame.Rect(crop_x, crop_y, crop_width, crop_height)
        )
        scaled = pygame.transform.scale(cropped, (WIDTH, HEIGHT))
        real_surface.blit(scaled, (0, 0))

    def _draw_background(self, surface):
        if self.level.room == "laboratorio":
            self._draw_repeating_background(surface, self.lab_background)
        elif self.level.room == "biblioteca":
            self._draw_repeating_background(surface, self.library_background)
        elif self.level.index == 0:
            # Fase 1 (pedido do Raul: "vai ficar melhor") também usa o céu
            # com nuvens novo assim que backgrounds/village_background.png
            # existir — mesma arte da vila, mesma vibe "dia claro, ao ar
            # livre". Até lá, cai de volta no fundo antigo da escola pra não
            # quebrar nada.
            if self.village_background is not None:
                self._draw_repeating_background(
                    surface, self.village_background, parallax=self.SCHOOL_BACKGROUND_PARALLAX
                )
            else:
                self._draw_repeating_background(
                    surface, self.backgrounds[0], parallax=self.SCHOOL_BACKGROUND_PARALLAX
                )
        elif self.level.index == 1:
            self.draw_university_background(surface)
        elif self.level.index == 2:
            self._draw_repeating_background(
                surface, self.backgrounds[2], parallax=self.CAVE_BACKGROUND_PARALLAX
            )
        elif self.level.index == VILLAGE:
            # Fundo dedicado (ver acima) — mesmo esquema de fallback.
            if self.village_background is not None:
                self._draw_repeating_background(
                    surface, self.village_background, parallax=self.VILLAGE_BACKGROUND_PARALLAX
                )
            else:
                surface.fill(self.VILLAGE_PLACEHOLDER_SKY)
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

    def _draw_world_foreground(self, surface):
        """Camada "Frente" do Tiled (pedido do Raul, Fase 1 — ver
        TiledMap.draw_foreground/_is_foreground_layer): chamado DEPOIS de
        self.player.draw() em draw(), então esse cenário fica na frente da
        Lia. Sem isso, ela ficaria sempre por cima de qualquer tile,
        mesmo os pensados como primeiro plano. Guard de tiled_map porque
        fases sem mapa do Tiled (percurso gerado por código) não têm essa
        camada."""
        if self.level.tiled_map:
            self.level.tiled_map.draw_foreground(surface, self.camera_x, self.camera_y)
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

    def _active_boss(self):
        """Chefe em luta agora — vivo e já acordado (ver enemy.py DORMANT/
        wake_up e Game._maybe_wake_bosses) — None enquanto ele ainda dorme,
        depois que morre, ou se não há nenhum chefe na fase. Usado só pra
        decidir se a barra de vida aparece."""
        for enemy in self.level.enemies:
            if type(enemy).__name__ not in BOSS_DROP_TABLE:
                continue
            if not enemy.alive:
                continue
            if enemy.state == getattr(enemy, "DORMANT", None):
                continue
            return enemy
        return None

    def _update_music(self):
        """Roda uma vez por quadro (ver update()); audio.play_music já
        ignora a chamada se o nome pedido é o mesmo que já está tocando,
        então isso é barato mesmo rodando todo quadro — muito mais simples
        que espalhar play_music em cada ponto de transição de estado
        (trocar de fase, entrar/sair de sala, chefe acordar/morrer, ganhar/
        perder), que são muitos e fáceis de esquecer um. Mesma ideia de
        _draw_background: decide o resultado a partir do estado atual, sem
        guardar histórico de transições."""
        audio.play_music(self._desired_music_track())

    def _desired_music_track(self):
        """Nome da faixa (ver PLANO_AUDIO.md pro arquivo esperado em
        music/) que deveria estar tocando agora, dado o estado atual."""
        if self.state == GAME_OVER:
            return "derrota_music"
        if self.state == COMPLETE:
            return "vitoria_music"
        if self.state == TITLE:
            return "menu_music"
        if self.state == INTRO:
            return "intro_music"
        boss = self._active_boss()
        if boss is not None:
            return BOSS_MUSIC.get(type(boss).__name__)
        if self.level.room == "laboratorio":
            return "laboratorio_music"
        if self.level.room == "biblioteca":
            return "biblioteca_music"
        if self.level.index == VILLAGE:
            return "vila_music"
        return f"fase_{self.level.index + 1}_music"

    BOSS_HEALTH_BAR_WIDTH = 520
    BOSS_HEALTH_BAR_HEIGHT = 20

    def _draw_boss_health_bar(self, surface):
        """Barra de vida no topo da tela (estilo Cuphead) enquanto um chefe
        está acordado — some de novo assim que ele morre ou some da fase
        (ver _active_boss). BOSS_NAMES só existe pro rótulo; a vida de
        verdade continua vindo de boss.health/HEALTH, igual sempre foi.
        y=80 fica abaixo da caixa de mensagem central (_draw_message, y
        18-66) de propósito, pra não sobrepor se as duas aparecerem juntas
        (ex.: mensagem de item pego durante a luta)."""
        boss = self._active_boss()
        if boss is None:
            return
        name = BOSS_NAMES.get(type(boss).__name__, "Chefe")
        ratio = max(0, boss.health) / boss.HEALTH if boss.HEALTH else 0
        width, height = self.BOSS_HEALTH_BAR_WIDTH, self.BOSS_HEALTH_BAR_HEIGHT
        x = WIDTH // 2 - width // 2
        y = 80
        draw_text(surface, name, (WIDTH // 2, y), 17, "#ffd9d9", True)
        bar = pygame.Rect(x, y + 16, width, height)
        pygame.draw.rect(surface, (12, 8, 10), bar.inflate(6, 6), border_radius=8)
        pygame.draw.rect(surface, (46, 16, 20), bar, border_radius=6)
        pygame.draw.rect(
            surface, (214, 58, 58), (bar.x, bar.y, int(bar.width * ratio), bar.height), border_radius=6
        )
        pygame.draw.rect(surface, (250, 214, 214), bar, 2, border_radius=6)

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
        self._draw_boss_health_bar(surface)
        draw_inventory(surface, self.inventory, self.item_icons, ITEM_ORDER)
        draw_ability_ui(
            surface,
            self.player.dash_cooldown,
            self.player.DASH_COOLDOWN,
            self.attack_cooldown,
            ATTACK_COOLDOWN,
            self.ranged_unlocked,
            self.ranged_cooldown,
            RANGED_ATTACK_COOLDOWN,
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
