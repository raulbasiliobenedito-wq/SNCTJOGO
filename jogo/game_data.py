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
# Nome de exibição e registro canônico dos chefes. BOSS_DROP_TABLE é um
# subconjunto: o Golem libera a estrada, mas não precisa criar outro item.
BOSS_NAMES = {
    "SlimeKing": "Rei Slime",
    "Librarian": "Bibliotecário",
    "Specimen": "Espécime",
    "AncientGolem": "Golem Ancião",
}
# Nome da faixa em music/ (ver PLANO_AUDIO.md) tocada enquanto cada chefe
# está acordado. Se a faixa do Golem ainda não existir, a fachada de áudio
# mantém o jogo funcional e volta a tentar quando o arquivo for adicionado.
BOSS_MUSIC = {
    "SlimeKing": "rei_slime_music",
    "Librarian": "bibliotecario_music",
    "Specimen": "especime_music",
    "AncientGolem": "golem_anciao_music",
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
# Um clique reproduz os 16 quadros do combo inteiro. Cada quadro da arte
# permanece por 4 updates (aprox. 16 fps), totalizando pouco mais de 1s.
# Depois da animação há mais 0,5s em que só um novo ataque fica bloqueado.
ATTACK_FRAME_TICKS = 4
ATTACK_DURATION = 16 * ATTACK_FRAME_TICKS
ATTACK_COOLDOWN = 30
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

# Combo de 4 hits corpo a corpo dentro da animação 53-68 da Lia. Os três
# primeiros socos dão dano normal; o quarto mantém o finalizador mais forte.
COMBO_HIT_COUNT = 4
COMBO_FINISHER_POWER = 2

# Parry: acertar o ataque corpo a corpo [F] num hazard "aparável" de chefe
# (ver <Boss>.parryable_hazards no módulo de cada chefe) destrói o hazard e
# devolve esse dano nele mesmo — mais que o ataque padrão e mais que o de dash, prêmio
# por acertar o timing curto em vez de só tocar a espada nele.
PARRY_DAMAGE = 3
# 1s de invencibilidade após um parry bem-sucedido (pedido do Raul): o
# Bibliotecário solta várias lâminas em sequência (ver BLADE_FIRE_INTERVAL
# nos módulos de chefes) — sem isso, aparar uma ainda deixava a Lia tomar
# dano da próxima poucos quadros depois. Reaproveita o mesmo
# self.invuln_timer que
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
SCIENCE_REACTIONS = {
    "Curiosidade": "Dois. A mesma pessoa. Ela devia ter feito muita pergunta.",
    "Observação": "Ela lutava por ciência e por gente ao mesmo tempo.",
    "Hipótese": "Primeira. Alguém sempre tem que ser a primeira.",
    "Experimento": "Eu era pequena. E já ajudou tanta gente.",
    "Registro": "Cuidar também é método, então.",
    "Método": "Ela programou uma máquina que nem existia ainda.",
    "Dados": "Conta feita à mão. E funcionou.",
    "Análise": "Primeira de novo. Quantas vezes alguém teve que ser a primeira?",
    "Testes": "Foi ela que tirou a foto. Eu li sobre isso na escola.",
    "Resultados": "Genética. Talvez seja por aí.",
    "Cura": "Nitrogênio não cura ninguém. Mas alimentou muita gente.",
    "Pesquisa completa": "Juntas. Sempre juntas. Acho que é isso que a minha mãe quis dizer.",
}

# Lore dos achados opcionais nas salas secundárias (portas) — ao contrário
# de SCIENCE_FACTS, não é sobre cientistas reais: é a história da própria
# universidade amaldiçoada, contada em pedaços pra quem explora fora do
# caminho principal.
ROOM_LORE = {
    "Amostra do Espécime 07": (
        (
            "Lia",
            "Um frasco rachado, ainda quente. A etiqueta diz \"ESPÉCIME 07 — "
            "NÃO REMOVER DO TANQUE\".",
        ),
        (
            "Lia",
            "Alguém removeu mesmo assim. E depois foi embora sem fechar a porta.",
        ),
    ),
    "Página Arrancada": (
        (
            "Lia",
            "Uma página solta, arrancada na pressa. A letra muda no meio da frase.",
        ),
        (
            "Lia",
            "Como se quem escrevia tivesse parado de ser humano no meio da palavra.",
        ),
    ),
}
DEFAULT_ROOM_LORE = "Um resquício de algo que este lugar preferia esquecer."

# As 5 cientistas-NPC (LEIA-ME_cientistas.md) — uma por local (ver
# Level.NPC_PLACEMENT). NPC_SPRITE_ROWS bate com a ordem de linhas de
# cientistas_idle.png; NPC_DIALOGUES guarda sequências (falante, texto)
# mostradas ao apertar [E] perto delas.
NPC_SPRITE_ROWS = {
    "Marie Curie": 0,
    "Ada Lovelace": 1,
    "Katherine Johnson": 2,
    "Jaqueline Goes de Jesus": 3,
    "Rosalind Franklin": 4,
}
# Moradores da vila (ver PLANO_VILA.md). Cada um é uma FOLHA PRÓPRIA em
# images/npcs/, não uma linha de cientistas_idle.png — por isso o mapa é
# nome -> arquivo em vez de nome -> linha. Sprites ausentes continuam sendo
# opcionais: o NPC permanece interagível mesmo sem corpo desenhado.
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
        ("Rosalind Franklin", "Você é a primeira pessoa a entrar aqui em semanas. E foi direto pro canto mais escuro da sala."),
        ("Lia", "É que tem uma coisa brilhando ali. Ninguém mais viu?"),
        ("Rosalind Franklin", "Viram. Só não olharam. É diferente."),
        ("Lia", "Qual é a diferença?"),
        ("Rosalind Franklin", "Eu passei dias fotografando uma coisa que ninguém conseguia enxergar. Raio X, fibra de DNA, uma exposição de cada vez."),
        ("Lia", "Dias numa foto só?"),
        ("Rosalind Franklin", "Uma delas levou mais de sessenta horas de exposição. A de número 51 foi a que finalmente mostrou a forma."),
        ("Lia", "Sessenta horas esperando uma foto."),
        ("Rosalind Franklin", "Olhar com atenção é trabalho, Lia, não é talento. Vai fundo no que os outros acharam que não valia a pena."),
    ),
    "Katherine Johnson": (
        ("Katherine Johnson", "Você parou. Por quê?"),
        ("Lia", "Porque eu acho que errei o caminho. Devia ter voltado lá atrás."),
        ("Katherine Johnson", "Você fez a conta ou você chutou?"),
        ("Lia", "...Fiz a conta."),
        ("Katherine Johnson", "Então confia nela. Eu calculei à mão a trajetória de uma cápsula que levava um homem pro espaço e trazia ele de volta."),
        ("Lia", "À mão? Não tinha computador?"),
        ("Katherine Johnson", "Tinha. E antes de subir, o astronauta pediu que eu conferisse os números da máquina. Ele não confiava mais em mim que na máquina — ele confiava na conta."),
        ("Lia", "..."),
        ("Katherine Johnson", "Refaz a sua e segue em frente."),
    ),
    "Marie Curie": (
        ("Marie Curie", "Cuidado com o que está naquele tanque. Não porque é monstro. Porque ninguém entende ainda."),
        ("Lia", "A senhora trabalha com coisa perigosa?"),
        ("Marie Curie", "Trabalhei. Tratei toneladas de minério pra tirar um décimo de grama de rádio. Anos mexendo com uma coisa que brilhava sozinha."),
        ("Lia", "E era perigoso?"),
        ("Marie Curie", "Era. Eu não sabia ainda o quanto."),
        ("Lia", "Se a senhora soubesse, teria parado?"),
        ("Marie Curie", "Não sei. Mas teria anotado tudo do mesmo jeito, pra que a próxima pessoa soubesse."),
        ("Lia", "É por isso que a senhora escrevia tanto?"),
        ("Marie Curie", "É por isso que qualquer um escreve. O que eu descubro só serve se atravessar até você."),
    ),
    "Ada Lovelace": (
        ("Ada Lovelace", "Esses livros todos, e você entrou procurando um só. Qual?"),
        ("Lia", "Um que explique uma coisa que ainda não tem explicação."),
        ("Ada Lovelace", "Ah. Esse é o tipo mais difícil. Costuma não estar escrito ainda."),
        ("Lia", "E aí, o que se faz?"),
        ("Ada Lovelace", "Escreve. Eu descrevi como uma máquina poderia calcular uma sequência de números antes de existir máquina capaz de rodar aquilo."),
        ("Lia", "A senhora escreveu instrução pra uma coisa que não existia?"),
        ("Ada Lovelace", "Alguém tem que imaginar primeiro. Se a resposta que você procura ainda não existe, pode ser que ela esteja esperando alguém escrever."),
    ),
    "Jaqueline Goes de Jesus": (
        ("Jaqueline Goes de Jesus", "Você vem descendo desde a superfície, não vem? Dá pra ver no rosto."),
        ("Lia", "Venho. Faz tempo."),
        ("Jaqueline Goes de Jesus", "Procurando o quê?"),
        ("Lia", "Alguma coisa que ajude a minha mãe. Ela está com câncer."),
        ("Jaqueline Goes de Jesus", "...Entendi."),
        ("Lia", "A senhora ia dizer que não funciona assim, né?"),
        ("Jaqueline Goes de Jesus", "Ia dizer que não funciona sozinho. Quando o vírus chegou no Brasil, a gente sequenciou o genoma dele em dois dias."),
        ("Lia", "Dois dias?"),
        ("Jaqueline Goes de Jesus", "Dois dias em cima de anos de gente que veio antes e publicou o que sabia. E foi equipe, não fui eu. É sempre assim que anda."),
        ("Lia", "E se ninguém achar a resposta a tempo?"),
        ("Jaqueline Goes de Jesus", "Aí alguém acha depois, por causa do que a gente tentou. Continua perguntando, Lia. E conta pra alguém o que você achar."),
    ),
    "Seu Joaquim": (
        ("Seu Joaquim", "Lia! Cedo pra tá de pé, hein. Vai pra onde com essa cara de missão?"),
        ("Lia", "Até o Bosque do Conhecimento. Preciso encontrar uma coisa por lá."),
        ("Seu Joaquim", "Vai ao bosque hoje? Tá certo. Então leva um conselho de graça: a estrada daqui pra lá não tá mais tão mansa quanto era."),
        ("Lia", "Como assim?"),
        ("Seu Joaquim", "Apareceu bicho. Nada do outro mundo, mas é bom saber se mexer. Seta pra andar, espaço pra pular."),
        ("Lia", "E se alguém quiser conversar?"),
        ("Seu Joaquim", "Chega perto e aperta E. Ninguém aqui morde. Vai com Deus, menina."),
    ),
    "Dona Marta": (
        ("Dona Marta", "Bom dia, flor! Olha o tamanho que você tá."),
        ("Lia", "Bom dia, dona Marta."),
        ("Dona Marta", "Sua mãe fala de você toda vez que eu passo lá. Todinha vez."),
        ("Lia", "Fala o quê?"),
        ("Dona Marta", "\"A Lia perguntou isso. A Lia quis saber aquilo.\" Com um orgulho que dá gosto de ouvir."),
        ("Lia", "..."),
        ("Dona Marta", "Se você for pra algum canto hoje, vai sabendo disso, viu?"),
    ),
    "Bento": (
        ("Bento", "Lia! Achei que você não ia sair hoje."),
        ("Lia", "Ia sim. Só demorei."),
        ("Bento", "Joga bola depois? Tá todo mundo lá no campinho."),
        ("Lia", "Hoje não dá."),
        ("Bento", "...Tá. Você tá indo pra algum lugar importante, né? Dá pra ver na sua cara."),
        ("Lia", "Dá tanto assim?"),
        ("Bento", "Dá. Vai lá. Eu seguro a sua vaga no time."),
    ),
    "Cadu": (
        ("Cadu", "Psiu! Lia! Tem um bichinho de geleia ali na frente."),
        ("Lia", "Ele morde?"),
        ("Cadu", "Não muito, mas fica no meio do caminho da gente."),
        ("Lia", "E como eu tiro ele da frente?"),
        ("Cadu", "Aperta F ou usa o clique esquerdo do mouse quando ele chegar perto. Se continuar vindo, acerta de novo."),
        ("Lia", "F ou clique esquerdo. Beleza."),
        ("Cadu", "Se aparecer mais, faz igual. Dizem que tem uns bem maiores lá pra frente."),
    ),
    "Zeca": (
        ("Zeca", "Ô Lia, para aí. Tá vendo esse buraco?"),
        ("Lia", "Tô. É largo."),
        ("Zeca", "Largo demais pra pular normal. Eu já tentei e já caí. Duas vezes."),
        ("Lia", "E como você passou?"),
        ("Zeca", "Olha pro lado que quer ir e aperta Q. Você dispara naquela direção e passa por cima antes de perceber."),
        ("Lia", "E se eu apertar na hora errada?"),
        ("Zeca", "Aí você cai igual eu caí. Mas cair também ensina, né? Vai lá."),
    ),
    "Sra. Amélia": (
        ("Sra. Amélia", "Lia. Vem cá um instantinho, minha filha."),
        ("Lia", "Oi, dona Amélia."),
        ("Sra. Amélia", "Eu não sei se é da minha conta. Mas me falaram uma coisa da sua mãe e eu não consegui dormir direito ontem."),
        ("Lia", "..."),
        ("Sra. Amélia", "É verdade mesmo, filha?"),
        ("Lia", "É. Câncer. Os médicos falaram essa semana."),
        ("Sra. Amélia", "Sinto muito. Sinto muito mesmo, meu bem."),
        ("Lia", "Todo mundo fala isso."),
        ("Sra. Amélia", "Porque não tem outra coisa pra falar. A gente fica sem palavra."),
        ("Lia", "Eu não quero palavra. Eu quero saber se dá pra fazer alguma coisa."),
        ("Sra. Amélia", "E dá?"),
        ("Lia", "Eu não sei ainda. É isso que eu vou descobrir."),
        ("Sra. Amélia", "Então vai. Mas passa aqui na volta, ouviu? Nem que seja pra dizer que não achou nada."),
    ),
}

NPC_REPEAT = {
    "Seu Joaquim": "Seta pra andar, espaço pra pular. E volta pra contar, menina.",
    "Bento": "Tua vaga tá guardada, viu?",
    "Dona Marta": "Toda vez, Lia. Ela fala de você toda vez.",
    "Cadu": "F ou clique esquerdo quando ele chegar perto. Se continuar vindo, bate de novo.",
    "Zeca": "Olha pro lado que quer ir e aperta Q. Você dispara naquela direção.",
    "Sra. Amélia": "Passa aqui na volta, minha filha. Nem que seja pra dizer que não achou.",
    "Rosalind Franklin": "Olhe de novo. Tem sempre uma coisa que a primeira olhada perdeu.",
    "Katherine Johnson": "Refaz a conta. E confia nela.",
    "Marie Curie": "Anote o que você vir. Serve pra próxima pessoa.",
    "Ada Lovelace": "Se não está escrito, escreva.",
    "Jaqueline Goes de Jesus": "Continua perguntando. E conta pra alguém.",
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
