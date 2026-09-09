"""Orquestra o ciclo de jogo, as interações e a renderização."""

import json
import random

import pygame

import audio
from cutscene import IntroCutscene
from dialogue import DialogueBox
from elevator_cutscene import ElevatorCutscene
from hint import Hint
from hud import draw_ability_ui, draw_hud, draw_inventory, draw_text
from level import PHASES, VILLAGE, Level
from minigame import (
    MICROSCOPE_ORDER,
    WIRE_COLORS,
    EnergyBoxMinigame,
    MicroscopeMinigame,
    MinigameManager,
)
from player import Player
from projectile import Projectile
from sprites import load_optional
from vfx import VFXManager
from settings import (
    ASSET_DIR,
    ROOT_DIR,
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
SETTINGS = "settings"
INTRO = "intro"
PLAYING = "playing"
GAME_OVER = "game_over"
COMPLETE = "complete"
PAUSED = "paused"

# Vida em corações fracionários (mob = 0.5, chefe = 1.0 — ver
# MOB_CONTACT_DAMAGE/BOSS_CONTACT_DAMAGE). 5 corações dá ~10 toques de mob
# antes do game over: margem confortável pra uma primeira jogada sem tornar
# a luta de chefe irrelevante. ATENÇÃO: estes dois valores estiveram em 1000
# (valor de depuração) por várias sessões — com eles a Lia era matematicamente
# invencível e todo o fluxo de derrota (pose de morte, death_sound, tela de
# game over, MOTIVATION) era inalcançável. Ver o assert no fim deste bloco.
STARTING_LIVES = 5
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
    # Ferramenta da caixa de energia (Fase 2, laboratório — ver
    # PLANO_MINIGAMES.md §3). "tool": nem "consumable" nem "quest" — não
    # ganha tecla de uso (ITEM_USE_KEYS só pega "consumable", abaixo) nem
    # bloqueia avanço de fase (PHASE_REQUIRED_ITEMS não a lista). Fica na
    # barra de itens sozinha, sem código novo em hud.draw_inventory (mostra
    # qualquer item com contagem > 0). "row": 7 ainda não existe em
    # items/items.png — ver _load_item_icons, que já tolera isso sem ícone
    # até a arte chegar. SÓ o item está pronto por enquanto: a passagem
    # secreta, a própria caixa de energia e o minigame de parafuso/fios
    # (modo "esperar a arte pronta", ver PLANO_MINIGAMES.md §4/§6) ainda
    # não existem — este item não é coletável em lugar nenhum do jogo hoje.
    "chave_fenda": {"row": 7, "name": "Chave de Fenda", "kind": "tool"},
}
ITEM_ORDER = (
    "gororoba", "essencia_slime", "carcaca_robo", "livro_magico",
    "amostra_especime", "dark_crystal", "sangue_dragao", "chave_fenda",
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
# Dano base do golpe corpo a corpo. Calibrado contra enemy.HEALTH:
# Slime(2)=2 golpes, CrystalStag(3)=3, JanitorGuardian(4)=4, chefes(12)=12
# golpes normais ou 6 finalizadores de combo, Dragon(16)=16 tiros de longe.
# Esteve em 100 (valor de depuração): TODO chefe morria em um único golpe,
# e o combo/dash/parry — que dão 2 e 3 — eram PUNIÇÕES, não recompensas.
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
# Hit-stop curto em QUALQUER acerto de espada, não só no parry: dois
# quadros de congelamento é o que separa "a espada encostou" de "a espada
# acertou". Menor que o do parry de propósito — o parry continua sendo o
# impacto mais pesado do jogo.
HIT_STOP_FRAMES = 2
PARRY_SHAKE_DURATION = 14
PARRY_SHAKE_MAGNITUDE = 6

# Tremor do impacto do Terremoto do Dragão (ver enemy.Dragon._start_
# terremoto_slam/consume_shake_event e Game._check_boss_shake_events) —
# pedido do Raul: uns 5 segundos tremendo (300 quadros a 60fps) enquanto
# MUITOS pedaços da caverna caem (ver Dragon.TERREMOTO_ROCK_TOTAL). A
# magnitude decai sozinha ao longo da duração (ver _shake_offset), então
# começa forte e vai assentando — não fica 5s inteiros no talo.
# Acordar de chefe (pedido antigo do Raul, IDEIAS_FUTURAS.md): a mesma
# infra de shake do parry, mais uma chuva de poeira caindo do teto da
# arena. Curto e forte — é uma pontuação, não um terremoto.
BOSS_WAKE_SHAKE_DURATION = 20
BOSS_WAKE_SHAKE_MAGNITUDE = 9
BOSS_WAKE_DUST_COUNT = 14

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

# Travas de sanidade: os valores acima já foram parar em números de
# depuração (STARTING_LIVES=1000, STANDARD_ATTACK_POWER=100) e ficaram
# assim por sessões sem ninguém notar, porque nada no jogo reclama — ele
# só vira um sandbox silenciosamente. Falhar no import é barulhento o
# bastante pra isso não acontecer de novo.
assert STANDARD_ATTACK_POWER < DASH_ATTACK_POWER <= PARRY_DAMAGE, (
    "O golpe de dash e o parry precisam causar MAIS dano que o golpe padrão"
)
assert STANDARD_ATTACK_POWER < COMBO_FINISHER_POWER, (
    "O 4º hit do combo precisa causar MAIS dano que os anteriores"
)
assert MAX_LIVES <= 12, "Vidas acima disso estouram a barra de corações do HUD"
assert STARTING_LIVES <= MAX_LIVES, "Não dá pra começar com mais vida que o máximo"

# Duração (em quadros) da caixa de mensagem da HUD. Existem como constantes
# nomeadas porque oito pontos diferentes de Game setavam self.message junto
# com `message_timer = 0`, e hud.draw_hud só desenha com `if message_timer`
# — ou seja, a mensagem era escrita e NUNCA aparecia. Ver Game.show_message.
MESSAGE_DURATION = 150          # 2,5 s — avisos comuns (item, pesquisa, achado)
MESSAGE_DURATION_LONG = 240     # 4 s   — desbloqueios e bloqueios de progresso

CAMERA_X_FOCUS = 0.42
# Quanto a câmera se adianta na direção em que a Lia olha (px).
CAMERA_LOOK_AHEAD = 80
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
# Moradores da vila (ver PLANO_VILA.md). Cada um é uma FOLHA PRÓPRIA em
# images/npcs/, não uma linha de cientistas_idle.png — por isso o mapa é
# nome -> arquivo em vez de nome -> linha. Só o Seu Joaquim tem arte
# desenhada até agora (288x48 = 6 quadros de 48x48, que estava no disco
# há tempos sem nenhum código carregando); os outros três continuam
# interagíveis e invisíveis até a folha deles existir, mesmo padrão de
# asset opcional do resto do jogo.
VILLAGER_SPRITE_FILES = {
    "Seu Joaquim": "seu_joaquim_idle.png",
    "Dona Marta": "dona_marta_idle.png",
    "Bento": "bento_idle.png",
    "Sra. Amélia": "sra_amelia_idle.png",
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

# SCHOOL_SPRITE_RECTS (chalkboard, whiteboard, clock, bulletin, exit,
# plant, desk_row, locker, bookshelf, door, lab_table) foi removido: os 11
# recortes eram fatiados de escola_sheet.png no carregamento e NENHUM era
# usado em lugar nenhum — o único uso de school_sprites no projeto inteiro
# é school_sprites[floor_name], que vem de SCHOOL_PLATFORM_SPRITES abaixo.
# Eram sobras do draw_school_background procedural, removido faz tempo.
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
        # Cutscene curta do elevador secreto do laboratório (Fase 1, ver
        # elevator_cutscene.ElevatorCutscene e Level._make_secret_elevators)
        # — mesma ideia do Hint/minigame abaixo: pausa o jogo, mas sem
        # precisar de um estado (self.state) novo, já que ela só acontece
        # durante PLAYING (ver update()/draw()).
        self.elevator_cutscene = ElevatorCutscene(self.player.frames[0])
        # Dicas contextuais (vinheta + texto, ver hint.Hint) — pausam o jogo
        # igual à DialogueBox, mas não são conversas com NPC, são avisos de
        # mecânica (ex.: painel do elevador na Fase 1). hints_shown mora em
        # load_level (reseta por fase, igual seen_dialogues).
        self.hint = Hint()
        # Minigames de arraste com mouse (montar o microscópio, e no futuro
        # a caixa de energia — ver minigame.py e PLANO_MINIGAMES.md). Mesmo
        # padrão de pausa do Hint acima: Game.update dá prioridade a
        # minigame.active antes até do dialogue.active (ver update()).
        self.minigame = MinigameManager()
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
        # Pano de fundo estático do menu (ver draw/_render_world_snapshot).
        # Invalidado em load_level, pra o menu nunca mostrar o mundo de uma
        # fase anterior depois de um reinício.
        self._menu_snapshot = None
        self.game_over_fade = 0
        self.game_over_characters = 0
        # Menu de título/Configurações (ver handle_menu_click/_drag/
        # _release, _title_buttons, _settings_widgets): qual slider está
        # sendo arrastado agora (None = nenhum) e pra onde "Voltar" no
        # menu de Configurações deve retornar — sempre TITLE por enquanto
        # (não existe menu de pausa ainda; se um dia existir, é só apontar
        # isso pra PLAYING antes de abrir Configurações a partir dele).
        self._dragging_slider = None
        self._settings_return_state = TITLE
        self._reset_combat_state()
        self._reset_input_state()
        self.load_level(0)
        self.state = TITLE

    def _load_assets(self):
        self.tiles = self._load_platform_tiles()
        self._load_backgrounds()
        self.school_sprites = self._load_school_sprites()
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
        self.energy_box_sprites = self._load_energy_box_sprites()
        # Elevador secreto do laboratório escondido (ver
        # elevator_cutscene.ElevatorCutscene/fog.FogBarrier) — três
        # arquivos totalmente independentes entre si, cada um opcional na
        # veia do resto do jogo: falta um, cai pro desenho por código
        # correspondente, sem travar nada.
        self.secret_elevator_sprite = self._load_optional_object_sprite("elevador_lab.png")
        self.fog_sprite = self._load_optional_object_sprite("fog_cloud.png")
        # Animação de verdade da névoa (ver fog.py/build_pixel_anim.py do
        # Raul) — 24 quadros em loop, "quadros" com rostos e
        # "quadros_corpo" só a massa (pra ladrilhar sem repetir cara).
        # Cai pro fog_sprite/desenho por código se as pastas não existirem
        # ainda (mesmo padrão opcional de tudo isso).
        # Carregados sob demanda por _apply_fog_sprite, só quando uma fase
        # realmente tem barreira de neblina (hoje só a Fase 1) — ver lá.
        self.fog_frames = None
        self.fog_frames_corpo = None
        self._fog_frames_tried = False
        self.scientist_sprites = self._load_scientist_sprites()
        # Um dicionário só, por NOME, com os quadros de qualquer NPC —
        # cientista ou morador. Level._draw_npcs consultava um índice de
        # LINHA numa folha única, o que tornava impossível um NPC ter folha
        # própria (era por isso que os 4 da vila apareciam invisíveis).
        self.npc_frames = self._build_npc_frames()
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
        # lab_background/library_background passaram pra _load_backgrounds
        # (agora já saem de lá com a cor de cena composta). Os dois "_mirror"
        # que existiam aqui eram carregados e NUNCA usados por ninguém —
        # só a universidade alterna cópias espelhadas ao ladrilhar (ver
        # draw_university_background) — eram 10,6 MB de superfície morta.

    @staticmethod
    def _load_image(relative_path, alpha=True):
        image = pygame.image.load(ASSET_DIR / relative_path)
        return image.convert_alpha() if alpha else image.convert()

    def _load_scaled_image(self, relative_path, size):
        return pygame.transform.smoothscale(self._load_image(relative_path), size)

    @staticmethod
    def _load_optional_object_sprite(filename):
        """Um único arquivo opcional em images/objects. Delega pro helper
        único do projeto (sprites.load_optional), que além de devolver None
        registra o caminho em sprites.missing — antes cada lugar tinha seu
        próprio jeito de "não achou, tudo bem" e nada ficava anotado."""
        return load_optional(ASSET_DIR / "objects" / filename)

    @staticmethod
    def _load_fog_frame_sequence(subfolder, prefix, count=24):
        """Carrega images/fog/<subfolder>/<prefix>_00.png .. _23.png NO
        TAMANHO NATIVO (480x270).

        Antes cada quadro era ampliado pra 1920x1080 já aqui: 48 quadros
        (rostos + corpo) x 8,3 MB = 380 MB residentes — 63% dos 600 MB de
        RSS do processo, para um efeito que só existe na Fase 1. Nativos são
        23,7 MB. O redimensionamento passou pra hora de desenhar, onde
        FogBarrier._scaled_frame cacheia o quadro atual (a animação roda a
        12 fps, então o mesmo quadro é pedido ~5 vezes seguidas a 60 fps).

        Devolve None (não uma lista vazia) se a pasta ainda não existir —
        mesmo padrão opcional do resto do jogo, FogBarrier cai pro
        fog_sprite/desenho por código."""
        folder = ASSET_DIR / "fog" / subfolder
        frames = []
        for i in range(count):
            frame = load_optional(folder / f"{prefix}_{i:02d}.png")
            if frame is None:
                return None
            frames.append(frame)
        return frames

    def _load_platform_tiles(self):
        return [
            self._load_image(f"tiles/platform{index}.png")
            for index in range(1, 5)
        ]



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

    # Cores de cena. Antes cada uma virava um Surface SRCALPHA de tela cheia
    # blitado por cima do fundo TODO QUADRO — medido em ~4,7 ms/quadro, a
    # operação mais cara do jogo inteiro. Agora são só dados: a cor é
    # composta DENTRO da imagem de fundo, uma vez, ainda na resolução
    # pequena (256x224 / 512x320), antes do redimensionamento. Como o fundo
    # é opaco e cobre a tela toda, e nada era desenhado entre ele e o
    # overlay, o resultado é pixel a pixel idêntico ao de antes.
    BG_TINT = (38, 53, 76, 72)
    UNIVERSITY_TINT = (55, 65, 80, 85)
    UNDERGROUND_TINT = (8, 12, 27, 155)

    def _load_backgrounds(self):
        """Carrega cada fundo em DUAS variantes já tingidas: "normal" e
        "underground" (o filtro escuro que entra quando a Lia desce abaixo
        de UNDERGROUND_Y).

        Qual família de cor cada fundo leva depende de ONDE ele é usado, não
        de qual arquivo é: o overlay antigo era escolhido por
        `level.index == 1`, então o fundo da universidade e os das duas salas
        dela (que também têm index 1) levam o filtro "university", e o resto
        leva só o básico."""
        self.backgrounds = {}
        village_exists = (ASSET_DIR / "backgrounds" / "ceu.png").exists()
        specs = [
            ("university", "backgrounds/university_background.png", True),
            ("cave", "backgrounds/cave_background_v2.png", False),
            ("lab", "backgrounds/lab_background.png", True),
            ("library", "backgrounds/library_background.png", True),
        ]
        if village_exists:
            specs.append(("village", "backgrounds/ceu.png", False))
        else:
            # Fallback histórico da Fase 1. Só é carregado quando ceu.png não
            # existe, em vez de sempre: com o céu novo no lugar, eram ~15 MB
            # de imagem escalada que nunca chegava a ser desenhada.
            specs.append(("school", "backgrounds/background_school.png", False))
        for key, path, is_university in specs:
            if not (ASSET_DIR / path).exists():
                continue
            raw = self._load_image(path, alpha=False)
            self.backgrounds[key] = {
                variant: self._scale_to_screen(self._tinted(raw, color))
                for variant, color in self._scene_tints(is_university).items()
            }
        self.background_mirror = {
            variant: pygame.transform.flip(image, True, False)
            for variant, image in self.backgrounds.get("university", {}).items()
        }

    def _scene_tints(self, is_university):
        """As combinações de cor que cada fundo precisa. Reaproveita
        _combine_overlay_colors, que já compunha as camadas numa cor só —
        faltava só aplicar o resultado no fundo em vez de num overlay."""
        if is_university:
            return {
                "normal": self._combine_overlay_colors(self.BG_TINT, self.UNIVERSITY_TINT),
                "underground": self._combine_overlay_colors(
                    self.BG_TINT, self.UNIVERSITY_TINT, self.UNDERGROUND_TINT
                ),
            }
        return {
            "normal": self.BG_TINT,
            "underground": self._combine_overlay_colors(self.BG_TINT, self.UNDERGROUND_TINT),
        }

    @staticmethod
    def _tinted(raw, rgba):
        """Compõe uma cor RGBA sólida sobre uma cópia OPACA da imagem — o
        mesmo resultado de blitar um overlay SRCALPHA por cima, só que uma
        vez, na imagem pequena."""
        base = raw.convert()
        layer = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        layer.fill(rgba)
        base.blit(layer, (0, 0))
        return base

    def _scale_to_screen(self, image):
        scale = HEIGHT / image.get_height()
        return pygame.transform.scale(
            image, (round(image.get_width() * scale), HEIGHT)
        ).convert()

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
        return {
            name: pygame.transform.scale(self._sheet_crop(sheet, rectangle), size)
            for name, (rectangle, size) in SCHOOL_PLATFORM_SPRITES.items()
        }

    # _create_scene_filters foi removido. Ele criava SETE Surfaces SRCALPHA
    # de tela cheia (55 MB): quatro overlays combinados — agora compostos
    # direto nos fundos por _load_backgrounds — e três (background_filter,
    # university_filter, underground_filter) que o próprio comentário
    # marcava como "mantidos apenas como referência/compat" e que ninguém
    # nunca leu. As cores viraram BG_TINT/UNIVERSITY_TINT/UNDERGROUND_TINT.

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

    # Mesma ampliação das cientistas (ver NPC_SCALE) pros moradores.
    def _build_npc_frames(self):
        """name -> lista de quadros. As cientistas vêm das 5 linhas de
        cientistas_idle.png; cada morador vem da sua própria folha de uma
        linha só, se o arquivo existir."""
        frames = {
            name: self.scientist_sprites[row]
            for name, row in NPC_SPRITE_ROWS.items()
            if row < len(self.scientist_sprites)
        }
        npcs_dir = ASSET_DIR / "npcs"
        for name, filename in VILLAGER_SPRITE_FILES.items():
            path = npcs_dir / filename
            if not path.exists():
                continue
            sheet = pygame.image.load(path).convert_alpha()
            # Uma linha só; a contagem de quadros vem da largura real do
            # arquivo, então redesenhar a folha com mais/menos quadros não
            # exige tocar em código.
            count = max(1, sheet.get_width() // sheet.get_height())
            frames[name] = self._load_grid_sheet(
                path, sheet.get_height(), sheet.get_height(), [count], scale=self.NPC_SCALE
            )[0]
        return frames

    def _load_item_icons(self):
        """items.png: quadro 16x16, 4 col x N lin, 6fps — usa só o primeiro
        quadro de cada linha como ícone estático do inventário/HUD (ver
        hud.draw_inventory); a animação de 4 quadros fica pro chão, se algum
        dia o item ganhar uma versão "largada" animada.

        N vem da altura real do arquivo (não fixo em 7): a chave de fenda
        (ver ITEM_DEFS, PLANO_MINIGAMES.md §3.1) pede uma linha 7 nova que
        ainda não foi desenhada. Enquanto ela não existir, o item continua
        funcionando (inventário, sem tecla de uso) só que sem ícone — ver o
        `continue` abaixo e hud.draw_inventory (`icons.get(key)`, tolera
        ícone ausente)."""
        sheet_path = ASSET_DIR / "items" / "items.png"
        row_count = pygame.image.load(sheet_path).get_height() // 16
        rows = self._load_grid_sheet(sheet_path, 16, 16, [4] * row_count)
        icons = {}
        for key, definition in ITEM_DEFS.items():
            row = definition["row"]
            if row >= len(rows):
                continue
            frame = rows[row][0]
            icons[key] = pygame.transform.scale(frame, (28, 28))
        return icons

    def _load_energy_box_sprites(self):
        """Caixa de energia (Fase 2, laboratório — ver PLANO_MINIGAMES.md
        §3, minigame.EnergyBoxMinigame). Só carrega de verdade se TODOS os
        arquivos já existirem: enquanto faltar um só, devolve None e a
        mecânica inteira fica desligada — Level._draw_energy_box não
        desenha nada (self.energy_box_sprites nunca chega lá) e
        _use_energy_box não abre o minigame. Mesmo padrão já usado pro céu
        da vila (village_background) e pro parry_flash.png: o jogo não
        quebra enquanto a arte não chega, só a mecânica fica invisível."""
        objects_dir = ASSET_DIR / "objects"
        required = (
            "caixa_energia_fechada.png", "caixa_energia_aberta.png",
            "caixa_energia_ligada.png", "tampa_caixa.png", "parafuso.png",
            "fio_ponta.png", "terminal.png", "chave_fenda_grande.png",
        )
        if not all((objects_dir / name).exists() for name in required):
            return None

        def load(name):
            return pygame.image.load(objects_dir / name).convert_alpha()

        def split(name, count):
            # Divide a folha em `count` quadros iguais lado a lado — não
            # assume nenhum tamanho de pixel fixo (o Raul pode ter
            # exportado em qualquer resolução), só que os quadros têm
            # todos a mesma largura dentro do arquivo.
            sheet = load(name)
            frame_width = sheet.get_width() // count
            return [
                sheet.subsurface(pygame.Rect(index * frame_width, 0, frame_width, sheet.get_height())).copy()
                for index in range(count)
            ]

        parafuso_no_lugar, parafuso_caindo = split("parafuso.png", 2)
        terminal_vazio, terminal_conectado = split("terminal.png", 2)
        fio_frames = split("fio_ponta.png", len(WIRE_COLORS))
        sprites = {
            "fechada": load("caixa_energia_fechada.png"),
            "aberta": load("caixa_energia_aberta.png"),
            "ligada": load("caixa_energia_ligada.png"),
            "tampa": load("tampa_caixa.png"),
            "parafuso_no_lugar": parafuso_no_lugar,
            "parafuso_caindo": parafuso_caindo,
            "terminal_vazio": terminal_vazio,
            "terminal_conectado": terminal_conectado,
            "fio_por_cor": dict(zip(WIRE_COLORS, fio_frames)),
            "chave_grande": load("chave_fenda_grande.png"),
        }

        # Dois extras totalmente opcionais, cada um checado por conta
        # própria (não entram no `required` acima — o minigame já sabe
        # cair pro visual desenhado por código enquanto um dos dois não
        # existir, ver minigame.py EnergyBoxMinigame._draw_wire_band e
        # _draw_fios):
        # - fio_corpo.png: 4 quadros lado a lado (mesma ordem de
        #   WIRE_COLORS — vermelho/azul/verde/amarelo), cada um um trecho
        #   sólido de fio na cor certa. O código estica/encolhe e
        #   rotaciona esse quadro pra caber entre âncora e ponta — não
        #   precisa ser do tamanho exato, pygame.transform.scale ajusta
        #   pra qualquer comprimento. Sem ele, o fio continua sendo
        #   desenhado por círculos.
        fio_corpo_path = objects_dir / "fio_corpo.png"
        if fio_corpo_path.exists():
            sprites["fio_esticado_por_cor"] = dict(
                zip(WIRE_COLORS, split("fio_corpo.png", len(WIRE_COLORS)))
            )
        # - tomada.png: 2 quadros pra desenhar no lugar de
        #   terminal_vazio/terminal_conectado. Sem ele, usa os quadros de
        #   terminal.png que já carregam sempre (ver `required`). Já
        #   inverti essa ordem uma vez e saiu do jeito errado (conectado
        #   parecendo desligado e vice-versa) — voltando pra ordem
        #   original do arquivo: quadro 1 = vazia, quadro 2 = conectada.
        tomada_path = objects_dir / "tomada.png"
        if tomada_path.exists():
            tomada_vazia, tomada_conectada = split("tomada.png", 2)
            sprites["tomada_vazia"] = tomada_vazia
            sprites["tomada_conectada"] = tomada_conectada

        # - chave_desparafusando.png: laço de giro da chave "desapertando",
        #   6 quadros. Sem ele, minigame.py rotaciona chave_grande em
        #   tempo real (pygame.transform.rotate borra a pixel art fora de
        #   múltiplos de 90°, então isso é só o provisório até o
        #   quadro-a-quadro chegar — ver EnergyBoxMinigame._draw_screw_anim).
        chave_anim_path = objects_dir / "chave_desparafusando.png"
        if chave_anim_path.exists():
            sprites["chave_desparafusando"] = split("chave_desparafusando.png", 6)

        # - parafuso_caindo_anim.png: o parafuso saltando pra fora e
        #   tombando até o chão, 6 quadros. Sem ele, mesma lógica acima:
        #   rotaciona parafuso_caindo em tempo real como provisório.
        parafuso_anim_path = objects_dir / "parafuso_caindo_anim.png"
        if parafuso_anim_path.exists():
            sprites["parafuso_caindo_anim"] = split("parafuso_caindo_anim.png", 6)

        return sprites

    def load_level(self, index):
        """Inicia uma fase sem modificar a quantidade atual de vidas."""
        self.level = Level(index)
        self._apply_fog_sprite(self.level)
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
        # Progresso do minigame de montagem (ver minigame.MicroscopeMinigame
        # e _open_microscope_minigame) — dict identidade->bool, começa tudo
        # False. Passado por referência pro minigame, então fechar com ESC
        # no meio não perde peça já encaixada; reseta aqui junto com
        # microscope_collected porque os dois nascem de novo a cada troca
        # de fase (só existe de verdade na Fase 1).
        self.microscope_slots = dict.fromkeys(MICROSCOPE_ORDER, False)
        # Segunda bancada de microscópio, independente da acima — a do
        # laboratório ESCONDIDO (ver Level._make_lab_bench/
        # _make_lab_microscope_parts e a conversa sobre o elevador
        # secreto). Mesmo esquema de estado (set de índices coletados +
        # dict de encaixes), só que sem nenhuma ligação com is_underground/
        # sequence_progress/buttons do sistema antigo.
        self.lab_microscope_collected = set()
        self.lab_microscope_assembled = False
        self.lab_microscope_slots = dict.fromkeys(MICROSCOPE_ORDER, False)
        # Ferramentas largadas no mapa (hoje só a chave de fenda, na sala do
        # laboratório da Fase 2 — ver Level._make_tool_pickups,
        # PLANO_MINIGAMES.md §3.1) e progresso da caixa de energia (mesmo
        # esquema de referência mutável do microscope_slots acima: fechar
        # com ESC no meio do modo fios não perde progresso). Nenhum dos
        # dois faz nada visível enquanto self.level.energy_box/tool_pickups
        # estiverem vazios (sem o objeto no Tiled ainda) ou enquanto
        # self.energy_box_sprites for None (arte ainda não chegou).
        self.tools_collected = set()
        self.energy_box_state = {"screws_removed": False, "wired": False}
        self.energy_box_wires = dict.fromkeys(WIRE_COLORS, False)
        self.minigame.close()
        self.riding_platform = None
        self.pending_drops = []
        self._reset_combat_state()
        self._reset_input_state()
        self._reset_vfx_state()
        self._reset_status_state()
        self.camera_x = 0
        self.camera_y = 0
        self._menu_snapshot = None
        self.show_message(self.level.data["subtitle"], MESSAGE_DURATION_LONG)
        self.state = PLAYING

    def enter_room(self, room_key):
        """Troca para uma sala secundária (porta interativa no corredor),
        preservando a fase principal intacta (inimigos, pesquisa coletada)
        pra restaurar exatamente como estava ao sair — ver exit_room."""
        self._base_level = self.level
        self._base_state = (self.player.x, self.player.y, self.camera_x, self.camera_y)
        self.level = Level(self.level.index, room=room_key)
        self._apply_fog_sprite(self.level)
        self.player.reset(*self.level.spawn)
        self.riding_platform = None
        self.pending_drops = []
        self.camera_x = self.camera_y = 0
        # Suprime o [E] desta troca de tela: sem isso, segurar a tecla ao
        # atravessar a porta reaciona a interação do outro lado no mesmo
        # quadro (ex.: entrar e sair de novo instantaneamente).
        self.interact_was_down = True
        self.show_message(self.level.data["subtitle"], MESSAGE_DURATION_LONG)

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

    # Progresso salvo em disco. Mesmo padrão já provado por
    # audio_settings.json: JSON simples na raiz, gravado em pontos
    # discretos (checkpoint e fim de fase) e lido uma vez na abertura.
    # Nada de auto-save por quadro.
    SAVE_PATH = ROOT_DIR / "save.json"
    SAVE_VERSION = 1

    def save_progress(self):
        """Grava fase, checkpoint, inventário e habilidades. Silencioso em
        caso de erro de escrita — perder o save é chato, travar o jogo no
        meio de uma partida é pior."""
        if self.level.room:
            # Dentro de uma sala não há checkpoint; o ponto de retorno de
            # verdade é o do corredor, que já foi salvo ao entrar nele.
            return
        try:
            self.SAVE_PATH.write_text(json.dumps({
                "version": self.SAVE_VERSION,
                "level": self.level.index,
                "checkpoint": list(self.checkpoint),
                "lives": self.lives,
                "shield": self.shield,
                "inventory": self.inventory,
                "ranged_unlocked": self.ranged_unlocked,
                "collected": sorted(self.collected),
            }), encoding="utf-8")
        except Exception:
            pass

    def load_progress(self):
        """Retoma o save, se houver. Devolve True se conseguiu. Qualquer
        inconsistência (arquivo de uma versão antiga, fase que não existe
        mais, JSON corrompido) simplesmente começa um jogo novo — um save
        quebrado não pode impedir alguém de jogar."""
        try:
            data = json.loads(self.SAVE_PATH.read_text(encoding="utf-8"))
            if data.get("version") != self.SAVE_VERSION:
                return False
            index = data["level"]
            if index != VILLAGE and not (0 <= index < len(PHASES)):
                return False
            self.load_level(index)
            self.checkpoint = tuple(data["checkpoint"])
            self.player.reset(*self.checkpoint)
            self.lives = min(MAX_LIVES, float(data.get("lives", STARTING_LIVES)))
            self.shield = int(data.get("shield", 0))
            self.inventory = {k: int(v) for k, v in data.get("inventory", {}).items()
                              if k in ITEM_DEFS}
            self.ranged_unlocked = bool(data.get("ranged_unlocked", False))
            self.collected = {i for i in data.get("collected", [])
                              if 0 <= i < len(self.level.research)}
            return True
        except Exception:
            return False

    def has_save(self):
        return self.SAVE_PATH.exists()

    def show_message(self, text, duration=MESSAGE_DURATION):
        """Único ponto de entrada da caixa de mensagem da HUD.

        Existe porque oito lugares diferentes setavam self.message junto com
        `message_timer = 0`, e hud.draw_hud só desenha a caixa com
        `if message_timer:` — a mensagem era escrita e nunca aparecia. O caso
        mais grave era o de _advance_level_if_ready: o jogador chegava no fim
        da fase, era empurrado 60px pra trás e não recebia NENHUMA explicação
        na tela. Concentrar tudo aqui evita que o próximo `= 0` volte."""
        self.message = text
        self.message_timer = duration

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
        # Debounce do ESC no menu de Configurações (ver _update_settings) —
        # mesma ideia dos *_was_down acima, só que pra uma tecla que não
        # passa por _read_input.
        self._escape_was_down = False
        self._minigame_escape_was_down = False
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
            self.show_message("O escudo absorveu o dano!")
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
        self.show_message(MOTIVATION, MESSAGE_DURATION_LONG)

    def update(self, keyboard, dt=1 / FPS):
        self._update_music()
        dialogue_advance_pressed, attack_pressed, dash_pressed, ranged_pressed = self._read_input(keyboard)

        if self.state == TITLE:
            self._update_title(keyboard)
        elif self.state == SETTINGS:
            self._update_settings(keyboard)
        elif self.state == INTRO:
            self._update_intro(keyboard, dialogue_advance_pressed)
        elif self.state == PAUSED:
            self._update_paused(keyboard)
        elif self.state in (GAME_OVER, COMPLETE):
            self._update_end_state(keyboard)
        elif self.minigame.active:
            self._update_minigame(keyboard, dt)
        elif self.elevator_cutscene.active:
            self.elevator_cutscene.update()
        elif self.dialogue.active:
            self._update_dialogue(dialogue_advance_pressed)
        elif self.hint.active:
            self._update_hint(dialogue_advance_pressed)
        else:
            if self._escape_pressed(keyboard):
                # Pausa: o comentário de _settings_return_state já previa
                # isso ("se um dia existir um menu de pausa, é só apontar
                # isso pra PLAYING antes de abrir Configurações a partir
                # dele") — só faltava o estado existir.
                audio.play_sfx("select_sound")
                self.state = PAUSED
                self._menu_snapshot = None
                return
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
            self.show_message("Vidas já estão cheias.")
            return
        self.inventory[item_key] = count - 1
        if self.inventory[item_key] <= 0:
            del self.inventory[item_key]
        if heal:
            self.lives = min(MAX_LIVES, self.lives + heal)
        if shield:
            self.shield += shield
        self.show_message(f"{definition['name']} usado!")
        self.vfx.spawn("dust", self.player.rect.centerx, self.player.rect.centery)

    def _update_title(self, keyboard):
        # Atalho de teclado (histórico, de antes do menu com botões
        # existir) continua funcionando junto com clicar em "JOGAR" — ver
        # handle_menu_click.
        if keyboard.space or keyboard.RETURN:
            self._start_game()

    def _start_game(self):
        audio.play_sfx("select_sound")
        self.lives = STARTING_LIVES
        self.state = INTRO
        self.intro.start()

    def _escape_pressed(self, keyboard):
        """ESC com debounce, compartilhado por pausa e configurações (antes
        cada um tinha sua própria flag *_was_down espalhada)."""
        down = bool(getattr(keyboard, "escape", False))
        pressed = down and not self._escape_was_down
        self._escape_was_down = down
        return pressed

    def _update_paused(self, keyboard):
        """ESC volta pro jogo; os botões do menu de pausa são tratados por
        handle_menu_click, igual ao título."""
        if self._escape_pressed(keyboard):
            audio.play_sfx("select_sound")
            self.state = PLAYING

    def _pause_buttons(self):
        button_width, button_height = 360, 74
        center_x = WIDTH // 2
        return {
            "resume": pygame.Rect(0, 0, button_width, button_height).move(
                center_x - button_width // 2, HEIGHT // 2 - 30
            ),
            "settings": pygame.Rect(0, 0, button_width, button_height).move(
                center_x - button_width // 2, HEIGHT // 2 + 64
            ),
        }

    def _update_settings(self, keyboard):
        # Interação é toda por mouse (ver handle_menu_click/_drag/
        # _release) — ESC aqui é só um atalho extra pra voltar sem
        # precisar acertar o botão "Voltar" na tela.
        if self._escape_pressed(keyboard):
            audio.play_sfx("select_sound")
            self.state = self._settings_return_state

    def _title_buttons(self):
        """Retângulos dos botões do menu de título, em coordenadas de
        tela (mesmo espaço de WIDTH x HEIGHT usado por draw_text/pygame —
        ver Game.draw/_blit_zoomed_world: a janela real abre exatamente
        nesse tamanho, então a posição do mouse do Pygame Zero já chega
        nessas mesmas coordenadas, sem precisar converter nada)."""
        button_width, button_height = 360, 74
        center_x = WIDTH // 2
        top = HEIGHT // 2 - (94 if self.has_save() else 10)
        buttons = {}
        if self.has_save():
            # Só aparece se existir save.json — quem nunca jogou não vê um
            # botão morto.
            buttons["continue"] = pygame.Rect(0, 0, button_width, button_height).move(
                center_x - button_width // 2, top
            )
            top += 94
        buttons["play"] = pygame.Rect(0, 0, button_width, button_height).move(
            center_x - button_width // 2, top
        )
        buttons["settings"] = pygame.Rect(0, 0, button_width, button_height).move(
            center_x - button_width // 2, top + 94
        )
        return buttons

    SETTINGS_BAR_WIDTH = 480
    SETTINGS_BAR_HEIGHT = 16
    # Área clicável de cada slider é mais alta que a barra visual (ver
    # _draw_slider em vez desse comentário se quiser conferir o desenho)
    # só pra facilitar acertar com o mouse sem precisar caprichar no pixel.
    SETTINGS_BAR_HIT_HEIGHT = 44

    # Ordem dos sliders na tela: (chave, rótulo, getter, setter).
    SETTINGS_SLIDERS = (
        ("music_bar", "Volume da Música", lambda: audio.music_volume, audio.set_music_volume),
        ("sfx_bar", "Volume dos Efeitos", lambda: audio.sfx_volume, audio.set_sfx_volume),
        ("shake_bar", "Tremor de Tela", lambda: audio.shake_scale, audio.set_shake_scale),
        ("text_bar", "Velocidade do Texto", lambda: audio.text_speed / 2.0,
         lambda ratio: audio.set_text_speed(ratio * 2.0)),
    )
    SETTINGS_ROW_SPACING = 88

    def _settings_widgets(self):
        center_x = WIDTH // 2
        bar_x = center_x - self.SETTINGS_BAR_WIDTH // 2
        top = HEIGHT // 2 - 165
        widgets = {}
        for index, (key, _label, _get, _set) in enumerate(self.SETTINGS_SLIDERS):
            widgets[key] = pygame.Rect(
                bar_x,
                top + index * self.SETTINGS_ROW_SPACING - self.SETTINGS_BAR_HIT_HEIGHT // 2,
                self.SETTINGS_BAR_WIDTH,
                self.SETTINGS_BAR_HIT_HEIGHT,
            )
        widgets["back"] = pygame.Rect(0, 0, 260, 64).move(
            center_x - 130, top + len(self.SETTINGS_SLIDERS) * self.SETTINGS_ROW_SPACING + 10
        )
        return widgets

    @staticmethod
    def _slider_ratio_at(bar_rect, x):
        if bar_rect.width <= 0:
            return 0.0
        return min(1.0, max(0.0, (x - bar_rect.x) / bar_rect.width))

    def handle_menu_click(self, pos):
        """Chamado por main.py (on_mouse_down) só quando self.state é
        TITLE ou SETTINGS — cliques durante o jogo em si continuam indo
        pro ataque (ver request_mouse_attack), não passam por aqui."""
        if self.state == TITLE:
            buttons = self._title_buttons()
            if "continue" in buttons and buttons["continue"].collidepoint(pos):
                audio.play_sfx("select_sound")
                if not self.load_progress():
                    self._start_game()
            elif buttons["play"].collidepoint(pos):
                self._start_game()
            elif buttons["settings"].collidepoint(pos):
                audio.play_sfx("select_sound")
                self._settings_return_state = TITLE
                self.state = SETTINGS
        elif self.state == PAUSED:
            buttons = self._pause_buttons()
            if buttons["resume"].collidepoint(pos):
                audio.play_sfx("select_sound")
                self.state = PLAYING
            elif buttons["settings"].collidepoint(pos):
                audio.play_sfx("select_sound")
                self._settings_return_state = PAUSED
                self.state = SETTINGS
        elif self.state == SETTINGS:
            widgets = self._settings_widgets()
            if widgets["back"].collidepoint(pos):
                audio.play_sfx("select_sound")
                self.state = self._settings_return_state
            else:
                for key, _label, _get, setter in self.SETTINGS_SLIDERS:
                    if widgets[key].collidepoint(pos):
                        self._dragging_slider = key
                        setter(self._slider_ratio_at(widgets[key], pos[0]))
                        if key == "sfx_bar":
                            audio.play_sfx("select_sound")
                        break

    def handle_menu_drag(self, pos):
        """Chamado por main.py (on_mouse_move) todo quadro em que o mouse
        se move — só faz algo se um slider está sendo arrastado (ver
        handle_menu_click/_release)."""
        if self._dragging_slider is None:
            return
        widgets = self._settings_widgets()
        bar = widgets[self._dragging_slider]
        ratio = self._slider_ratio_at(bar, pos[0])
        for key, _label, _get, setter in self.SETTINGS_SLIDERS:
            if key == self._dragging_slider:
                setter(ratio)
                break

    def handle_menu_release(self):
        """Chamado por main.py (on_mouse_up) — grava em disco só ao
        soltar o slider (ver audio.save_settings), não a cada pixel
        arrastado."""
        if self._dragging_slider is not None:
            self._dragging_slider = None
            audio.save_settings()

    def _update_minigame(self, keyboard, dt):
        """Chamado por update() enquanto self.minigame.active — ver
        minigame.py. ESC fecha sem terminar (progresso já mora num
        atributo do próprio Game, passado por referência ao abrir, ver
        _open_microscope_minigame), com o mesmo debounce que Configurações
        usa (_escape_was_down) só que numa flag própria, pra não interferir
        com o ESC do menu."""
        escape_down = getattr(keyboard, "escape", False)
        if escape_down and not self._minigame_escape_was_down:
            self._minigame_escape_was_down = escape_down
            audio.play_sfx("select_sound")
            self.minigame.close()
            return
        self._minigame_escape_was_down = escape_down

        self.minigame.update(dt)
        for name in self.minigame.drain_sfx():
            audio.play_sfx(name)
        result = self.minigame.pop_result()
        if result is not None:
            self._finish_minigame(*result)

    def _finish_minigame(self, key, result):
        if key == "microscope" and result == "completed":
            self.microscope_assembled = True
            audio.play_sfx("microscope_sound")
            self.level.activate_return_route()
            self.dialogue.start(
                "Lia",
                "Microscópio montado! As plataformas de retorno foram liberadas; preciso voltar pelo caminho acima.",
            )
        elif key == "lab_microscope" and result == "completed":
            self.lab_microscope_assembled = True
            audio.play_sfx("microscope_sound")
            libera = (self.level.lab_bench or {}).get("libera")
            if libera:
                self._release_fog_barrier(libera)
            self.dialogue.start(
                "Lia",
                "Microscópio montado! Acho que isso acabou de abrir alguma coisa lá fora.",
            )
        elif key == "energy_box":
            if result == "wired":
                audio.play_sfx("correct_sequence_sound")
                self.dialogue.start(
                    "Lia",
                    "A caixa de energia está ligada! Bom saber que funciona — ainda preciso descobrir o que"
                    " isso destrava por aqui.",
                )
            elif result == "closed_mistakes":
                self.dialogue.start(
                    "Lia",
                    "Uma faísca! Melhor conferir o diagrama de novo antes de tentar outra vez.",
                )

    def handle_minigame_click(self, pos):
        """Chamado por main.py/main_web.py (mouse down) quando
        self.minigame.active é True — ver PLANO_MINIGAMES.md §0/§1."""
        self.minigame.on_click(pos)

    def handle_minigame_drag(self, pos):
        self.minigame.on_drag(pos)

    def handle_minigame_release(self, pos):
        self.minigame.on_release(pos)

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
        self.level.update(dt)
        self._check_fog_barriers()
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
                self._boss_wake_impact(enemy)

    def _boss_wake_impact(self, boss):
        """Tremor de tela + poeira caindo do teto no instante em que o chefe
        acorda (IDEIAS_FUTURAS.md). A poeira nasce espalhada ao longo do
        TOPO DA TELA acima da arena, não no chefe: a ideia é a masmorra
        reagindo, não um efeito de impacto nele."""
        self._trigger_shake(BOSS_WAKE_SHAKE_DURATION, BOSS_WAKE_SHAKE_MAGNITUDE)
        left = int(self.camera_x)
        top = int(self.camera_y)
        for _ in range(BOSS_WAKE_DUST_COUNT):
            self.vfx.spawn(
                "dust",
                random.randint(left, left + WIDTH),
                top + random.randint(0, HEIGHT // 4),
            )

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
        # audio.shake_scale é a preferência de acessibilidade (0 desliga).
        magnitude = (
            self.shake_magnitude
            * (self.shake_timer / self.shake_duration)
            * audio.shake_scale
        )
        if magnitude <= 0:
            return 0, 0
        return random.uniform(-magnitude, magnitude), random.uniform(-magnitude, magnitude)

    def _update_camera(self):
        arena_zone = self._active_boss_arena()
        if arena_zone:
            self._update_boss_camera(arena_zone)
            return
        # Câmera antecipatória: desloca o alvo na direção pra onde a Lia
        # olha, então o jogador enxerga o caminho ANTES de chegar nele em
        # vez de ficar sempre centralizado. Como o alvo passa pela mesma
        # suavização de sempre (CAMERA_X_SMOOTHING), virar de lado desliza
        # em vez de dar um salto.
        look_ahead = CAMERA_LOOK_AHEAD * (1 if self.player.facing_right else -1)
        target_x = self.player.x + look_ahead - WIDTH * CAMERA_X_FOCUS
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

        # Poeira levantada pelo dash: reaproveita a partícula que já existe
        # em vez de mais retângulos azuis (draw_dash_trail continua, é o
        # rastro; isto é o pó que fica pra trás). Só no chão — debaixo
        # d'água o dash nem acontece (ver _update_playing).
        if player.dashing and self.player_grounded and player.dash_timer % 3 == 0:
            self.vfx.spawn("dust", player.rect.centerx, player.rect.bottom)

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
        # Pouso: só no quadro em que ela ENCOSTA (não enquanto fica parada).
        if landed and not self.player_grounded and not player.swimming:
            player.start_squash("squash")
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
            player.start_squash("stretch")
            audio.play_sfx("jump")

    def _player_in_water(self, player):
        return any(player.rect.colliderect(zone) for zone in self.level.water_zones)

    def _check_fog_barriers(self):
        """Fala de "bloqueio" na primeira vez que a Lia esbarra numa
        neblina ainda sólida (ver fog.FogBarrier) — só a fala; a neblina
        continua bloqueando fisicamente do mesmo jeito (ver
        _all_solid_rectangles), quem libera de verdade é
        _release_fog_barrier. barrier.encountered marca isso pra sempre
        nesta passagem pela fase (mesmo objeto Level entre entrar/sair de
        uma sala — ver enter_room/exit_room —, então não repete a fala à
        toa), e também é o que outro sistema (ex.: o elevador do
        laboratório escondido) pode checar pra saber se já pode ser usado."""
        if self.dialogue.active:
            return
        for barrier in self.level.fog_barriers:
            if barrier.encountered or not barrier.solid():
                continue
            if self.player.rect.colliderect(barrier.rect.inflate(12, 12)):
                barrier.encountered = True
                self.dialogue.start(
                    "Lia",
                    barrier.mensagem
                    or "Tem um campo de contenção aqui, não dá pra passar assim... preciso achar outro caminho.",
                )
                break

    def _apply_fog_sprite(self, level):
        """FogBarrier nasce sem sprite (ver Level._make_fog_barriers —
        Level não tem acesso às sprites carregadas por Game); isso é
        chamado logo depois de criar/trocar de Level (load_level/
        enter_room) pra ligar a arte de verdade em cada barreira, se já
        tiver sido carregada (ver _load_assets). None é um valor válido
        pra tudo isso — sem os quadros animados nem o fog_cloud.png,
        FogBarrier.draw cai pro desenho por código igual antes."""
        if not level.fog_barriers:
            # Nenhuma barreira nesta fase: não há por que ter 48 quadros de
            # neblina residentes. Antes eles eram carregados no Game() e
            # ficavam na memória o jogo inteiro (ver
            # _load_fog_frame_sequence).
            return
        if not self._fog_frames_tried:
            self._fog_frames_tried = True
            self.fog_frames = self._load_fog_frame_sequence("quadros", "quadro")
            self.fog_frames_corpo = self._load_fog_frame_sequence("quadros_corpo", "corpo")
        for barrier in level.fog_barriers:
            barrier.sprite = self.fog_sprite
            barrier.frames = self.fog_frames
            barrier.frames_corpo = self.fog_frames_corpo

    def _release_fog_barrier(self, chave):
        """Chamado por quem completar o que libera uma neblina (ex.: o
        microscópio do laboratório escondido — ver
        minigame.MicroscopeMinigame/_finish_minigame) — inicia a
        animação de dissipar (fog.FogBarrier.release) em vez de sumir na
        hora. Sem efeito se nenhuma neblina desta fase tiver essa chave.
        A neblina vive no corredor principal, não na sala — se quem
        chamou isso estiver dentro de uma sala (self._base_level not
        None, ver enter_room), procura lá, não em self.level."""
        target_level = self._base_level if self._base_level is not None else self.level
        for barrier in target_level.fog_barriers:
            if barrier.chave == chave:
                barrier.release()

    def _all_solid_rectangles(self):
        # solids_near em vez de self.level.grounds inteiro: numa
        # fase grande (Fase 3, 315x100 tiles) essas listas passam de mil
        # retângulos, e checar todos 2x por quadro (colisão horizontal e
        # vertical) era o motivo real do lag reportado lá — ver
        # Level.solids_near/_build_solid_chunks.
        return (
            self.level.solids_near(self.player.rect)
            + [platform.rect for platform in self.level.platforms]
            + [barrier.rect for barrier in self.level.fog_barriers if barrier.solid()]
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
                self.show_message(f"Item obtido: {ITEM_DEFS[key]['name']}")
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
            # obrigatória nem avanço de fase — só o achado opcional, as
            # peças do microscópio do laboratório escondido (se for o
            # caso, ver Level.lab_microscope_parts) e a porta de saída
            # (tratada em handle_interactions).
            self._collect_artifacts(player)
            self._collect_tools(player)
            self._collect_lab_microscope_parts(player)
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
            self.show_message(f"Achado: {name}")
            audio.play_sfx("item_sound")
            lore = ROOM_LORE.get(name, DEFAULT_ROOM_LORE)
            self.dialogue.start("Lia", lore)
            return True
        return False

    def _collect_tools(self, player):
        """Ferramentas largadas no mapa (hoje só a chave de fenda — ver
        Level._make_tool_pickups, PLANO_MINIGAMES.md §3.1). Mesmo padrão de
        índice de _collect_artifacts/_collect_research, mas vai pro
        inventário em vez de um set separado, porque a chave se comporta
        como qualquer outro item (aparece na barra, ver ITEM_DEFS)."""
        for index, (item, item_key) in enumerate(self.level.tool_pickups):
            if index in self.tools_collected or not player.rect.colliderect(item):
                continue
            self.tools_collected.add(index)
            self.inventory[item_key] = self.inventory.get(item_key, 0) + 1
            self.show_message(f"Item obtido: {ITEM_DEFS[item_key]['name']}")
            audio.play_sfx("item_sound")

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
                    self.save_progress()
                self.checkpoint = new_checkpoint
                self.show_message("Checkpoint: Centro de pesquisa alcançado!")

    def _collect_research(self, player):
        for index, (item, name) in enumerate(self.level.research):
            if index in self.collected or not player.rect.colliderect(item):
                continue

            self.collected.add(index)
            self.show_message(f"Parte da pesquisa obtida: {name}")
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

    def _collect_lab_microscope_parts(self, player):
        """Peças do microscópio do laboratório ESCONDIDO (ver
        Level._make_lab_microscope_parts) — sem nenhuma condição prévia
        (ao contrário de _collect_microscope_parts, que exige a
        sequência antiga resolvida): a sala em si só é alcançável depois
        do elevador liberado, isso já é gate suficiente."""
        for index, (item, _name) in enumerate(self.level.lab_microscope_parts):
            if index not in self.lab_microscope_collected and player.rect.colliderect(item):
                self.lab_microscope_collected.add(index)
                audio.play_sfx("item_sound")

    def _use_lab_microscope_bench(self, player):
        """Bancada do laboratório escondido (ver Level._make_lab_bench) —
        mesmo formato de _use_microscope_bench, mas totalmente
        independente: progresso próprio (lab_microscope_*) e libera uma
        fog.FogBarrier (propriedade "libera" do objeto "bancada_
        microscopio") em vez de ativar rota de retorno nenhuma."""
        if self.level.lab_bench is None:
            return False
        if not player.rect.colliderect(self.level.lab_bench["rect"].inflate(70, 60)):
            return False
        if len(self.lab_microscope_collected) < len(self.level.lab_microscope_parts):
            self.dialogue.start("Lia", "Ainda faltam peças para montar o microscópio.")
            return True
        if not self.lab_microscope_assembled:
            self._open_lab_microscope_minigame()
        return True

    def _open_lab_microscope_minigame(self):
        self.minigame.open(
            MicroscopeMinigame(
                WIDTH,
                HEIGHT,
                self._microscope_sprites_by_identity(),
                self.puzzle_sprites["microscope_complete"],
                self.lab_microscope_slots,
                key="lab_microscope",
            )
        )

    def _lab_microscope_sprites(self):
        """Empacota as MESMAS sprites do microscópio (ver
        _microscope_sprites_by_identity) no formato que
        Level._draw_lab_microscope espera — lista simples por posição em
        vez de dict por identidade, igual ao antigo puzzle_sprites[
        "microscope_parts"] já usava."""
        return {
            "parts": self.puzzle_sprites["microscope_parts"],
            "complete": self.puzzle_sprites["microscope_complete"],
        }

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

        needs_microscope = (
            self.level.is_underground and not self.level.room and not self.microscope_assembled
        )
        missing_items = [
            key for key in PHASE_REQUIRED_ITEMS.get(self.level.index, ())
            if self.inventory.get(key, 0) <= 0
        ]
        if len(self.collected) < len(self.level.research) or needs_microscope:
            self.show_message(
                "Encontre todas as partes da pesquisa antes de avançar.",
                MESSAGE_DURATION_LONG,
            )
            player.x = self.level.world_width - 160
        elif missing_items:
            names = ", ".join(ITEM_DEFS[key]["name"] for key in missing_items)
            self.show_message(f"Ainda falta: {names}.", MESSAGE_DURATION_LONG)
            player.x = self.level.world_width - 160
        elif self.level.index == VILLAGE:
            self.save_progress()
            # Fim da rua da vila = caminho pra floresta → Fase 1 (ver
            # PLANO_VILA.md). Não é "fase+1" porque VILLAGE não é um índice
            # numérico — cai fora de PHASES de propósito.
            self.load_level(0)
        elif self.level.index == len(PHASES) - 1:
            self.state = COMPLETE
        else:
            finished_index = self.level.index
            self.load_level(finished_index + 1)
            self.save_progress()
            # load_level já sobrescreveu self.message com o subtítulo da fase
            # nova (message_timer=0, ver load_level) — o aviso de desbloqueio
            # entra DEPOIS de propósito, pra não ser apagado por ele.
            if finished_index == 0 and not self.ranged_unlocked:
                self.ranged_unlocked = True
                self.show_message(
                    "Novo poder: Ataque à Distância [R] desbloqueado!",
                    MESSAGE_DURATION_LONG,
                )

    def check_enemies(self):
        """Verifica ataque, ataque reforçado durante dash e contato com slimes.
        `melee_vulnerable` (Dragon/Librarian/Specimen em enemy.py — os
        inimigos comuns e o Rei Slime não definem isso, então getattr cai em
        True) deixa um chefe imune a corpo a corpo em certas fases (ex.:
        voando, escudo levantado, dentro do casulo); nesses momentos,
        acertar o corpo dele com a espada não causa dano — só o ataque à
        distância funciona — mas ainda dói tocar nele."""
        attack_box = self._attack_box()
        # O dano de contato era resolvido com um `return` no meio do laço:
        # ao encostar num inimigo, todos os que vinham DEPOIS dele na lista
        # não eram testados pro golpe de espada naquele quadro — com vários
        # mobs juntos, acertar quem estava atrás virava loteria. Agora o
        # laço vai até o fim e o contato é aplicado uma única vez no final
        # (o pior contato do quadro; ver `contact_damage`).
        contact_damage = 0
        for enemy in self.level.enemies:
            if not enemy.alive:
                continue
            is_boss = type(enemy).__name__ in BOSS_DROP_TABLE
            melee_hit = (
                attack_box
                and attack_box.colliderect(enemy.rect)
                and getattr(enemy, "melee_vulnerable", True)
            )
            if melee_hit:
                if enemy.take_hit(self.attack_power):
                    self.hitstop_timer = max(self.hitstop_timer, HIT_STOP_FRAMES)
                    self.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                    if not enemy.alive:
                        self._on_enemy_defeated(enemy)
                    else:
                        audio.play_sfx("boss_hit_sound" if is_boss else "enemy_hit_sound")
            elif self.player.rect.colliderect(enemy.rect):
                damage = BOSS_CONTACT_DAMAGE if is_boss else MOB_CONTACT_DAMAGE
                contact_damage = max(contact_damage, damage)
        if contact_damage and self.invuln_timer <= 0:
            self.take_damage(contact_damage)

    def _attack_box(self):
        if not self.attack_timer:
            return None
        # Comparar poderes (`attack_power > STANDARD_ATTACK_POWER`) acoplava
        # "alcance" a "dano": bastou STANDARD_ATTACK_POWER virar 100 pra o
        # golpe de dash perder o alcance estendido sem ninguém notar. Agora
        # o alcance vem do que está acontecendo de fato.
        reach = DASH_ATTACK_REACH if self.player.dashing else STANDARD_ATTACK_REACH
        offset = (
            PLAYER_HITBOX_WIDTH
            if self.player.facing_right
            else -(24 + reach)
        )
        return self.player.rect.move(offset, 4).inflate(reach, 10)

    def handle_interactions(self):
        """Processa portas (qualquer fase), a caixa de energia (sala do
        laboratório, Fase 2) e, na Fase 1 subterrânea, elevadores, painel,
        botões e bancada do laboratório."""
        if not self.interact_pressed:
            return
        if self._use_doors():
            return
        if self._use_secret_elevator():
            return
        if self._talk_to_npc():
            return
        if self.level.room == "laboratorio" and self._use_energy_box(self.player):
            return
        if self.level.room == "laboratorio_secreto" and self._use_lab_microscope_bench(self.player):
            return
        if not self.level.is_underground or self.level.room:
            # "or self.level.room": o laboratório escondido tem
            # index==0 (is_underground True) mas não usa NADA do sistema
            # antigo abaixo (alavancas/painel/botões/bancada do
            # corredor) — sem este corte, _use_microscope_bench quebraria
            # tentando usar self.level.bench, que fica None numa sala
            # (ver Level._reset_lab_state).
            return

        player = self.player
        if self._use_elevator_lever(player):
            return
        if self._use_panel_lever(player):
            return
        if self._use_sequence_button(player):
            return
        self._use_microscope_bench(player)

    def _use_energy_box(self, player):
        """Caixa de energia (Fase 2, laboratório — ver PLANO_MINIGAMES.md
        §3.2/§3.3). self.level.energy_box é None em qualquer mapa sem o
        objeto "caixa_energia" ainda (ver Level._make_energy_box), e
        self.energy_box_sprites é None enquanto faltar algum arquivo de
        arte (ver _load_energy_box_sprites) — os dois casos fazem esse
        método devolver False sem fazer nada, exatamente como se a caixa
        não existisse no jogo ainda."""
        if self.level.energy_box is None or self.energy_box_sprites is None:
            return False
        if not player.rect.colliderect(self.level.energy_box.inflate(70, 60)):
            return False
        if self.energy_box_state["wired"]:
            self.dialogue.start("Lia", "A caixa de energia está funcionando normalmente.")
            return True
        if not self.energy_box_state["screws_removed"] and self.inventory.get("chave_fenda", 0) <= 0:
            self.dialogue.start("Lia", "A tampa está parafusada. Preciso de uma chave de fenda.")
            return True
        self.minigame.open(
            EnergyBoxMinigame(
                WIDTH,
                HEIGHT,
                self.energy_box_sprites,
                self.energy_box_state,
                self.energy_box_wires,
            )
        )
        return True

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

    SECRET_ELEVATOR_RANGE = 40

    def _use_secret_elevator(self):
        """Elevador secreto (objeto "elevador_lab" — ver
        Level._make_secret_elevators e a conversa sobre o "elevador
        chat"). Mesmo raio/formato de _use_doors, mas a troca de sala só
        acontece depois de uma cutscene curta (ver
        elevator_cutscene.ElevatorCutscene): do lado de fora, o elevador
        só funciona depois da Lia esbarrar no bloqueio de neblina ligado
        a ele pela propriedade "chave" (ver _check_fog_barriers, que
        marca barrier.encountered) — do lado de dentro da sala (objeto
        sem "chave", destino "sair"), sempre funciona."""
        if self.elevator_cutscene.active:
            return False
        player = self.player
        for elevator in self.level.secret_elevators:
            if not player.rect.colliderect(
                elevator["rect"].inflate(self.SECRET_ELEVATOR_RANGE, self.SECRET_ELEVATOR_RANGE)
            ):
                continue
            if elevator["chave"] and not self._fog_barrier_encountered(elevator["chave"]):
                self.dialogue.start(
                    "Lia",
                    "Melhor eu não usar isso ainda — vou ver o que tem lá na frente primeiro.",
                )
                return True
            audio.play_sfx("door_sound")
            if elevator["destino"] == "sair":
                self.elevator_cutscene.start(reverse=True, on_finish=self.exit_room)
            else:
                target = elevator["destino"]
                self.elevator_cutscene.start(reverse=False, on_finish=lambda: self.enter_room(target))
            return True
        return False

    def _fog_barrier_encountered(self, chave):
        return any(
            barrier.chave == chave and barrier.encountered
            for barrier in self.level.fog_barriers
        )

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
            self._open_microscope_minigame()

    # Ordem fixa de carregamento em _load_puzzle_sprites (lens, base,
    # light, ocular) — não tem relação com a ordem de Level.microscope_parts
    # (que é sobre onde as peças nascem largadas no mapa, não sobre qual
    # sprite é qual peça), então esse mapeamento é sempre o mesmo,
    # independente de fase/room/Tiled.
    MICROSCOPE_SPRITE_IDENTITY_ORDER = ("objetiva", "base", "iluminador", "ocular")

    def _microscope_sprites_by_identity(self):
        sprites = self.puzzle_sprites["microscope_parts"]
        return dict(zip(self.MICROSCOPE_SPRITE_IDENTITY_ORDER, sprites))

    def _open_microscope_minigame(self):
        self.minigame.open(
            MicroscopeMinigame(
                WIDTH,
                HEIGHT,
                self._microscope_sprites_by_identity(),
                self.puzzle_sprites["microscope_complete"],
                self.microscope_slots,
            )
        )

    def draw(self, screen):
        real_surface = screen.surface
        # Os dois fill((6,14,29)) que ficavam aqui e logo abaixo saíram:
        # _draw_background sempre cobre a superfície inteira (ladrilha ou
        # preenche) e _blit_zoomed_world sempre cobre a tela inteira. Eram
        # ~1,6 ms por quadro pintando pixels sobrescritos no blit seguinte.
        # Se um dia entrar um estado novo que NÃO cubra a tela toda, ele
        # precisa preencher o fundo por conta própria.
        if self.state == INTRO:
            self.intro.draw(real_surface, draw_text)
            return
        if self.elevator_cutscene.active:
            self.elevator_cutscene.draw(real_surface, draw_text)
            return
        if self.state in (TITLE, SETTINGS, PAUSED):
            # O mundo inteiro era desenhado (~7 ms/quadro medidos) só pra
            # ficar embaixo de um _dim_background(alpha=210) quase opaco. Um
            # instantâneo tirado uma vez dá exatamente o mesmo visual de
            # graça — nada se move atrás do menu, já que update() nesses dois
            # estados só roda _update_title/_update_settings.
            if self._menu_snapshot is None:
                # Já sai ESCURECIDO: no título e nas configurações o alpha é
                # sempre o mesmo (MENU_DIM_ALPHA), então compor uma vez evita
                # também o blit translúcido de tela cheia por quadro.
                snapshot = self._render_world_snapshot()
                self._dim_background(snapshot, self.MENU_DIM_ALPHA)
                self._menu_snapshot = snapshot
            real_surface.blit(self._menu_snapshot, (0, 0))
            self._draw_state_overlay(real_surface)
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
        self.minigame.draw(real_surface, draw_text)

    def _render_world_snapshot(self):
        """Desenha o mundo uma única vez numa Surface própria, pro menu usar
        como pano de fundo estático (ver draw). Reaproveita exatamente o
        mesmo caminho de desenho do jogo, então o visual é idêntico ao que o
        menu mostrava antes — só que calculado uma vez em vez de 60x/s."""
        snapshot = pygame.Surface((WIDTH, HEIGHT)).convert()
        world = pygame.Surface((WIDTH, HEIGHT)).convert()
        self._draw_background(world)
        self._draw_world(world)
        self._draw_player_light(world)
        self.player.draw(world, self.camera_x, self.camera_y)
        self._draw_world_foreground(world)
        self._blit_zoomed_world(snapshot, world)
        self._draw_interface(snapshot)
        return snapshot

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

    # Y a partir do qual o cenário conta como "subterrâneo". Calibrado pro
    # mapa antigo da Fase 1 — reajustar quando o laboratório novo existir de
    # verdade no .tmx (ver PLANO_FASE1.md, item 1).
    UNDERGROUND_Y = 780

    # Fator de parallax por fundo (<1.0 anda mais devagar que a câmera).
    PARALLAX = {
        "school": 0.3, "village": 0.3, "cave": 0.35,
        "university": 1.0, "lab": 1.0, "library": 1.0,
    }

    def _draw_background(self, surface):
        """Um único blit opaco por ladrilho, sem nenhum overlay depois — a
        cor de cena já veio composta na imagem (ver _load_backgrounds)."""
        variant = "underground" if self.player.y > self.UNDERGROUND_Y else "normal"
        images = self.backgrounds.get(self._background_key())
        if images is None:
            # Nenhuma arte de fundo disponível pra este contexto (hoje só a
            # vila sem ceu.png) — céu liso, que também cobre a tela toda.
            surface.fill(self.VILLAGE_PLACEHOLDER_SKY)
            return
        image = images[variant]
        if self._background_key() == "university":
            self.draw_university_background(surface, image, variant)
        else:
            self._draw_repeating_background(
                surface, image, parallax=self.PARALLAX.get(self._background_key(), 1.0)
            )

    def _background_key(self):
        """Qual fundo este contexto usa. A ordem reproduz exatamente a
        cascata de ifs que existia em _draw_background."""
        if self.level.room == "laboratorio":
            return "lab"
        if self.level.room == "biblioteca":
            return "library"
        if self.level.index == 1:
            return "university"
        if self.level.index == 2:
            return "cave"
        # Fase 1 e vila compartilham o céu novo (pedido do Raul: "vai ficar
        # melhor"); sem ceu.png, a Fase 1 cai no fundo antigo da escola e a
        # vila no preenchimento liso.
        if "village" in self.backgrounds:
            return "village"
        return "school" if self.level.index == 0 else None

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
            self.npc_frames,
            tool_icon=self.item_icons.get("chave_fenda"),
            tools_collected=self.tools_collected,
            energy_box_sprites=self.energy_box_sprites,
            energy_box_state=self.energy_box_state,
            lab_microscope_sprites=self._lab_microscope_sprites(),
            lab_microscope_collected=self.lab_microscope_collected,
            lab_microscope_assembled=self.lab_microscope_assembled,
            secret_elevator_sprite=self.secret_elevator_sprite,
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
        if self.state in (TITLE, SETTINGS):
            # Configurações só é alcançável a partir do título por
            # enquanto (ver _settings_return_state) — mesma trilha dos
            # dois, senão a música trocaria pra da Fase 1 ao só abrir o
            # menu de volume.
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
            self._draw_title_menu(surface)
        elif self.state == SETTINGS:
            self._draw_settings_menu(surface)
        elif self.state == PAUSED:
            self._draw_pause_menu(surface)
        elif self.state == GAME_OVER:
            self.draw_game_over_overlay(surface)
        elif self.state == COMPLETE:
            self.overlay(
                surface,
                "Pesquisa apresentada no congresso!",
                "Lia corre pra contar tudo pra mãe: a pesquisa vai continuar,\n"
                "e agora ela sabe que não está sozinha nisso.\nPressione R para jogar novamente",
            )

    # Paleta compartilhada dos botões/sliders do menu (mesmo estilo dos
    # painéis do HUD em hud.py — retângulo escuro arredondado + borda
    # azul clara) — BUTTON_HOVER_* fica um pouco mais claro, pra dar
    # feedback de "isso é clicável" sem precisar de nenhuma imagem nova.
    BUTTON_FILL = (12, 25, 43)
    BUTTON_FILL_HOVER = (22, 42, 68)
    BUTTON_BORDER = (101, 184, 228)
    BUTTON_BORDER_HOVER = (150, 216, 255)

    # Camadas escuras já prontas, uma por valor de alpha usado. Antes
    # _dim_background criava um Surface SRCALPHA de tela cheia A CADA
    # QUADRO — no título e nas configurações isso rodava eternamente, e na
    # tela de game over o alpha varia de 0 a 210 durante o fade, então são
    # (o alpha varia de 0 a 210 durante o fade da tela de game over), então
    # a camada é criada uma vez e só o set_alpha muda entre quadros.
    _DIM_LAYER = None

    def _dim_background(self, surface, alpha=210):
        """Camada escura translúcida por cima do mundo (que continua
        sendo desenhado atrás — ver draw()), usada por todo overlay de
        estado (título, configurações, game over, vitória)."""
        if Game._DIM_LAYER is None:
            # OPACA (convert(), sem SRCALPHA) de propósito: com alpha por
            # pixel, set_alpha obriga o pygame a combinar os dois alphas e
            # cai num caminho de blit bem mais lento (medido: 10,6 ms contra
            # 1,1 ms por quadro). Como a camada é uma cor chapada, alpha
            # uniforme dá exatamente o mesmo resultado pela via rápida.
            layer = pygame.Surface((WIDTH, HEIGHT)).convert()
            layer.fill((5, 12, 28))
            Game._DIM_LAYER = layer
        layer = Game._DIM_LAYER
        layer.set_alpha(alpha)
        surface.blit(layer, (0, 0))

    def _draw_menu_button(self, surface, rect, label, sublabel=None):
        """Um botão clicável do menu — hover checado direto por
        pygame.mouse.get_pos() (disponível sempre via `import pygame`,
        sem depender de nenhum evento/global do Pygame Zero) porque é só
        pra pintar o botão mais claro embaixo do cursor; o clique de
        verdade continua vindo de handle_menu_click (main.py/
        on_mouse_down), não daqui."""
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        fill = self.BUTTON_FILL_HOVER if hovered else self.BUTTON_FILL
        border = self.BUTTON_BORDER_HOVER if hovered else self.BUTTON_BORDER
        pygame.draw.rect(surface, fill, rect, border_radius=14)
        pygame.draw.rect(surface, border, rect, 3, border_radius=14)
        label_y = rect.centery - (10 if sublabel else 0)
        draw_text(surface, label, (rect.centerx, label_y), 26, "#ffe477", True)
        if sublabel:
            draw_text(surface, sublabel, (rect.centerx, rect.centery + 18), 14, "#9fb4c9", True)

    def _draw_slider(self, surface, bar_rect, ratio, label):
        """Barra + alça arrastável de um volume (0.0-1.0). `bar_rect` é a
        área CLICÁVEL (mais alta que a barra visual, ver
        SETTINGS_BAR_HIT_HEIGHT/_settings_widgets) — a barra desenhada de
        verdade fica centralizada dentro dela, mais fina."""
        draw_text(
            surface,
            f"{label} — {round(ratio * 100)}%",
            (bar_rect.centerx, bar_rect.top - 22),
            20,
            "white",
            True,
        )
        track = pygame.Rect(
            bar_rect.x,
            bar_rect.centery - self.SETTINGS_BAR_HEIGHT // 2,
            bar_rect.width,
            self.SETTINGS_BAR_HEIGHT,
        )
        pygame.draw.rect(surface, (30, 45, 66), track, border_radius=8)
        filled = pygame.Rect(track.x, track.y, round(track.width * ratio), track.height)
        pygame.draw.rect(surface, (95, 201, 255), filled, border_radius=8)
        handle_x = track.x + round(track.width * ratio)
        pygame.draw.circle(surface, "white", (handle_x, track.centery), 14)
        pygame.draw.circle(surface, (95, 201, 255), (handle_x, track.centery), 14, 3)

    # Escurecimento fixo do título/configurações (ver draw: já vem composto
    # no instantâneo, por isso _draw_title_menu/_draw_settings_menu não
    # chamam mais _dim_background — se chamassem, escureceria duas vezes).
    MENU_DIM_ALPHA = 210

    def _draw_title_menu(self, surface):
        draw_text(surface, "Echoes of Life", (WIDTH // 2, HEIGHT // 2 - 140), 54, "#ffe477", True)
        buttons = self._title_buttons()
        if "continue" in buttons:
            self._draw_menu_button(surface, buttons["continue"], "CONTINUAR", "retoma o último checkpoint")
        self._draw_menu_button(surface, buttons["play"], "JOGO NOVO" if "continue" in buttons else "JOGAR",
                               "ou pressione ESPAÇO")
        self._draw_menu_button(surface, buttons["settings"], "CONFIGURAÇÕES")

    def _draw_pause_menu(self, surface):
        draw_text(surface, "Pausado", (WIDTH // 2, HEIGHT // 2 - 140), 48, "#ffe477", True)
        buttons = self._pause_buttons()
        self._draw_menu_button(surface, buttons["resume"], "CONTINUAR", "ou pressione ESC")
        self._draw_menu_button(surface, buttons["settings"], "CONFIGURAÇÕES")

    def _draw_settings_menu(self, surface):
        draw_text(surface, "Configurações", (WIDTH // 2, HEIGHT // 2 - 260), 44, "#ffe477", True)
        widgets = self._settings_widgets()
        for key, label, getter, _set in self.SETTINGS_SLIDERS:
            self._draw_slider(surface, widgets[key], getter(), label)
        self._draw_menu_button(surface, widgets["back"], "VOLTAR")

    def draw_university_background(self, surface, background, variant="normal"):
        """Repete o pátio alternando cópias normais e espelhadas. Recebe a
        imagem já tingida de fora (ver _draw_background) em vez de buscar em
        self.backgrounds[1] — o dicionário agora é por nome + variante."""
        mirror = self.background_mirror[variant]
        image_width = background.get_width()
        x = -int(self.camera_x) % image_width - image_width
        tile_number = (x + int(self.camera_x)) // image_width
        while x < WIDTH:
            image = mirror if tile_number % 2 else background
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
        self._dim_background(surface, alpha)
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
        self._dim_background(surface, alpha)

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
