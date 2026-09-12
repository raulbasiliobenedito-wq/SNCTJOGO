"""Regras, estados, diálogos e tabelas estáticas do jogo."""

from settings import FPS


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
    "amostra_especime", "dark_crystal", "chave_fenda",
)
# Itens de pesquisa exigidos por fase pra liberar o avanço (ver
# _advance_level_if_ready) — Fase 2 depende dos dois chefes de sala
# (biblioteca e laboratório), então os dois deixam de ser opcionais.
# Fase 3 (índice 2) ficou sem exigência por enquanto: o Dragão saiu do
# jogo (vai virar a Caveira, refeita do zero — pedido do Raul) e não tem
# chefe nenhum ainda pra soltar um item de pesquisa novo. Sem isso a fase
# ficaria travada pra sempre esperando um drop que não existe mais.
PHASE_REQUIRED_ITEMS = {
    0: ("essencia_slime",),
    1: ("livro_magico", "amostra_especime"),
    2: (),
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
}
# Nome de exibição de cada chefe, usado só pela barra de vida (ver
# Game._draw_boss_health_bar) — mesmas chaves de BOSS_DROP_TABLE.
BOSS_NAMES = {
    "SlimeKing": "Rei Slime",
    "Librarian": "Bibliotecário",
    "Specimen": "Espécime",
}
# Nome da faixa em music/ (ver PLANO_AUDIO.md) tocada enquanto cada chefe
# está acordado — mesmas chaves de BOSS_DROP_TABLE/BOSS_NAMES.
BOSS_MUSIC = {
    "SlimeKing": "rei_slime_music",
    "Librarian": "bibliotecario_music",
    "Specimen": "especime_music",
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
# golpes normais ou 6 finalizadores de combo.
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

# Acordar de chefe (pedido antigo do Raul, IDEIAS_FUTURAS.md): a mesma
# infra de shake do parry, mais uma chuva de poeira caindo do teto da
# arena. Curto e forte — é uma pontuação, não um terremoto.
BOSS_WAKE_SHAKE_DURATION = 20
BOSS_WAKE_SHAKE_MAGNITUDE = 9
BOSS_WAKE_DUST_COUNT = 14

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
    "Cadu": "cadu_idle.png",
    "Zeca": "zeca_idle.png",
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
    # Os dois abaixo são novos (vila maior, com tutorial espalhado pelo
    # caminho em vez de tudo de uma vez com o Seu Joaquim) — reforçam uma
    # mecânica cada, bem no ponto onde ela passa a ser necessária.
    "Cadu": (
        "Psiu, Lia! Um bichinho de geleia fugiu do quintal do meu avô — não "
        "morde forte, mas fica no meio do caminho. Se ele chegar perto, "
        "aperta o F que ele se afasta rapidinho."
    ),
    "Zeca": (
        "Esse buraco aqui é largo demais pra pular normal, já tentei. Mas "
        "se você apertar Q bem na hora de correr, sai disparada e passa "
        "reto por cima. Confia."
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
