import pygame
from enemy import (
    CrystalStag, DarkWraith, JanitorGuardian, Librarian, PossessedStudent,
    Slime, SlimeKing, SmallSlime, Specimen,
)
from fog import FogBarrier
from plataform import Platform
from ramp import Ramp
from settings import ASSET_DIR, HEIGHT, PLAYER_HEIGHT
from tiled_map import TiledMap


class _StaticZone:
    """Área fixa com um atributo .rect, para reaproveitar código (como o
    patrulhamento do Slime) que espera algo com essa interface, mesmo sem
    ser uma Platform de verdade — ex.: chão pintado direto no Tiled."""

    def __init__(self, rect):
        self.rect = rect


# Dados descritivos de cada fase. As chaves de layout ("layout", "step",
# "widths", "heights", "moving", "decor_props", "decor_ground",
# "decor_banners") saíram junto com os percursos gerados por código: o
# terreno inteiro das três fases vem dos .tmx desde que a Fase 1 ganhou
# chão pintado, e esses números descreviam plataformas que não existem
# mais em lugar nenhum. "world"/"world_height"/"world_top" ficam porque
# _configure_world_dimensions ainda os lê antes de sobrescrever com o
# tamanho real do mapa; "checkpoints"/"research" ficam como documentação
# da intenção de cada fase (as posições de verdade vêm do Tiled).
PHASES = [
    {
        "name": "Fase 1 — Escola", "subtitle": "A primeira pergunta pode mudar o mundo.",
        "world": 7420, "world_height": 1450, "world_top": -520,
        # Os diálogos automáticos por posição (professores/Lia) saíram —
        # substituídos pela cientista-NPC de cada local (objeto "cientista"
        # no .tmx, ver Level._make_npcs/game.NPC_DIALOGUES), que só fala
        # quando Lia chega perto e aperta [E].
        "dialogues": (),
    },
    {
        "name": "Fase 2 — Universidade", "subtitle": "Conhecimento se constrói em movimento.",
        "world": 6880, "world_height": 900, "world_top": 0,
        "dialogues": (),
    },
    {
        "name": "Fase 3 — Centro de Pesquisa", "subtitle": "Pesquisa é colaboração, coragem e esperança.",
        "world": 8200, "world_height": 900, "world_top": 0,
        "dialogues": (),
    },
]

# A vila (prólogo, ver PLANO_VILA.md) não é uma fase de verdade — não entra em
# PHASES pra não bagunçar todo código que assume índice 0/1/2 (fase_N_music,
# COMPLETE em len(PHASES)-1, chefe do índice 2 etc.). VILLAGE é a "chave" que
# Level/Game usam no lugar de um índice inteiro; como nenhum desses lugares
# indexa PHASES/listas com ela diretamente (só compara com == ou usa .get),
# ela passa por eles sem quebrar nada — só cai nos poucos pontos com um
# branch dedicado (ver level.TILED_MAP_FILES/_build_course/_make_npcs e
# game._draw_background/_advance_level_if_ready/_desired_music_track).
VILLAGE = "vila"
VILLAGE_DATA = {
    "name": "Vila", "subtitle": "Antes da estrada — a vila onde Lia cresceu.",
    # world/world_height só valem se maps/vila.tmx sumir (fallback sem
    # Tiled) — com o mapa presente, _configure_world_dimensions troca os
    # dois pelo tamanho real do .tmx (220x20 tiles de 32px = 7040x640).
    # world_top NÃO é trocado pelo tamanho do .tmx (_configure_world_dimensions
    # só mexe em world/world_height) — com a tela em 1080px de altura e o
    # mapa tendo só 640px, world_top=0 prendia a câmera sempre no topo do
    # mundo (a conta de camera_y em Game._update_camera resulta numa
    # constante quando world_height < HEIGHT), sobrando ~440px de "nada"
    # (só o céu, sem chão) na parte de baixo da tela — parecia um bug visual
    # de mundo cortado/duplicado. -440 = -(1080 - 640) alinha o fundo do
    # mapa com o fundo da tela, cobrindo esse vão.
    "world": 7040, "world_height": 640, "world_top": -440,
    "dialogues": (),
}

class Level:
    """Fases de plataformas; a primeira também possui um laboratório subterrâneo."""

    BUTTON_NAMES = ("AZUL", "VERDE", "AMARELO", "VERMELHO")
    LEVER_FRAME_DELAY = 6
    DEFAULT_SPAWN = (100, 650 - PLAYER_HEIGHT)
    DEFAULT_SURFACE_RETURN = (4460, 412)

    # Mapa do Tiled por fase (índice em PHASES). Fases sem entrada aqui, ou cujo
    # arquivo ainda não existe em maps/, caem no percurso gerado por código.
    TILED_MAP_FILES = {
        0: "fase1_escola.tmx", 1: "fase2_universidade.tmx", 2: "fase3_pesquisa.tmx",
        VILLAGE: "vila.tmx",
    }

    # Salas secundárias, acessadas por uma porta interativa no corredor
    # principal (ver Game.enter_room/_use_doors) — não fazem parte da
    # progressão principal de nenhuma fase (self.index não muda ao entrar
    # numa sala; só self.room passa a apontar pra ela).
    ROOM_MAP_FILES = {
        "laboratorio": "fase2_laboratorio_sala.tmx",
        "biblioteca": "fase2_biblioteca_sala.tmx",
        # Laboratório escondido da Fase 1 (ver a conversa sobre o
        # elevador secreto/fog.FogBarrier) — mapa novo, ainda por criar
        # (ver LEIA-ME/instruções passadas ao Raul).
        "laboratorio_secreto": "fase1_laboratorio_secreto.tmx",
    }

    def __init__(self, index, room=None):
        self.index = index
        self.room = room
        # A vila (index == VILLAGE, uma string, ver VILLAGE_DATA acima) não
        # existe em PHASES — só fases de verdade (int 0/1/2) indexam a lista.
        self.data = PHASES[index] if isinstance(index, int) else VILLAGE_DATA
        self.tiled_map = self._load_tiled_map()
        self._configure_world_dimensions()
        self.is_underground = index == 0
        # Tiles pintados numa camada colisao=true (ou chamada "Colisão"/"Collision")
        # viram blocos sólidos automaticamente, sem precisar desenhar objetos.
        self.grounds = list(self.tiled_map.tile_collisions) if self.tiled_map else []
        # Pra cada coluna (x de tile), guarda só o retângulo sólido mais alto
        # dessa coluna — a superfície de fato pisável. Sem isso, montar uma
        # zona de patrulha (ver _ground_zone_at) confundia uma célula de
        # preenchimento enterrada (o "miolo" de rocha de um segmento vizinho
        # mais alto, que por acaso cai na mesma linha absoluta) com a
        # superfície real, e o inimigo acabava patrulhando por baixo do chão
        # visível nos trechos em "escada" da descida.
        self.column_tops = self._build_column_tops()
        self.dynamic_platforms = []
        self.platforms = self._build_course()
        # Índice espacial de chão em chunks (mesma ideia de
        # TiledMap._build_chunks, usada lá pro desenho) — Game.move_player
        # chamava _resolve_horizontal/vertical_collisions contra
        # self.grounds INTEIRO a cada quadro. Numa sala pequena isso é
        # irrelevante, mas na Fase 3 (315x100 tiles, um túnel comprido)
        # esses tiles de colisão passam de mil, e checar todos 2x por
        # quadro (horizontal e vertical) é o motivo real do lag/
        # travamento reportado lá — ver Level.solids_near, chamado por
        # Game._all_solid_rectangles no lugar da lista completa.
        self._ground_chunks = self._build_solid_chunks(self.grounds)
        # Espinhos (morte instantânea ao toque) e zonas de água (o jogador
        # nada livremente dentro delas — ver Game.move_player). Ambos vêm de
        # objetos tipados na camada "Entidades" do Tiled, sem precisar de
        # nenhum código novo de parsing (mesmo padrão de spawn/checkpoint/livro).
        self.hazards = self._make_hazards()
        self.water_zones = self._make_water_zones()
        # Rampas: identificadas pelo PRÓPRIO TILE, não por objeto (ver
        # TiledMap.tile_ramps/_load_tile_ramps) — um tile marcado com a
        # propriedade "rampa" no tileset vira um triângulo (ramp.Ramp) do
        # tamanho de uma célula sempre que for pintado na camada de
        # Colisão, sem precisar posicionar nada na camada Entidades. Ficam
        # de fora de self.grounds de propósito — colisão SAT de verdade
        # contra o triângulo, não um AABB genérico (ver
        # Game._resolve_ramp_collisions).
        self.ramps = self._make_ramps()
        # Portas (ver LEIA-ME das salas) e achados opcionais: ambos vêm de
        # objetos tipados na camada Entidades, mesmo padrão de sempre. Achados
        # (self.artifacts) são deliberadamente separados de self.research —
        # eles recompensam quem explora a sala, mas nunca bloqueiam o avanço
        # de fase (ver Game._advance_level_if_ready, que só olha research).
        self.doors = self._make_doors()
        self.artifacts = self._make_artifacts()
        self.tool_pickups = self._make_tool_pickups()
        self.energy_box = self._make_energy_box()
        # Bloqueios de neblina (objeto tipo "neblina" — ver fog.FogBarrier
        # e a conversa sobre o elevador do laboratório secreto). Genérico
        # por padrão: qualquer passagem do jogo que precise de "bloqueada
        # até X" usa o mesmo objeto, distinguido pela propriedade "chave".
        # self.fog_barriers é montado LÁ EMBAIXO, depois de _make_boss_arenas
        # — ver o comentário lá.
        # Elevador secreto (objeto "elevador_lab" — ver
        # Game._use_secret_elevator/elevator_cutscene.ElevatorCutscene) e
        # bancada/peças do microscópio do laboratório escondido, do outro
        # lado dele. Ambos genéricos e vazios até Raul posicionar os
        # objetos correspondentes no Tiled (ver LEIA-ME combinado com a
        # conversa sobre o elevador chat).
        self.secret_elevators = self._make_secret_elevators()
        self.lab_microscope_parts = self._make_lab_microscope_parts()
        self.lab_bench = self._make_lab_bench()
        # Objeto "lago_lava" (Entidades): só a área de perigo (ver
        # Game._check_hazards, que respawna a Lia no contato) — sem desenho
        # nenhum vinculado a ele. O visual da lava é 100% as tiles pintadas
        # no Tiled (Fundo/Perigos/Decoração), igual a água: mover/redimensionar
        # este objeto muda só a jogabilidade, nunca o que aparece na tela.
        self.lava_lakes = self._make_lava_lakes()
        self.spawn = self._map_spawn()
        self.surface_return = self.DEFAULT_SURFACE_RETURN
        self.enemies = self._make_enemies()
        # Chefes de arena (Rei Slime na Fase 1): não vêm de objeto do Tiled
        # como os outros inimigos — são posicionados em código, no fim do
        # percurso de cada fase, cada um com uma zona de câmera travada
        # (ver Game._active_boss_arena). self.boss_arenas fica vazio nas
        # salas e na Fase 2 (sem chefe de arena própria; os chefes dela —
        # Espécime/Bibliotecário — já travam a tela pequena o bastante da
        # sala secundária sem precisar de trava de câmera). Fase 3 também
        # fica sem arena própria por enquanto (Dragão removido, substituto
        # ainda não implementado).
        self.boss_arenas = self._make_boss_arenas()
        # ORDEM IMPORTA: _make_boss_arenas acabou de possivelmente ESTICAR
        # self.world_width (a arena do Rei Slime soma
        # SLIME_KING_ARENA_MARGIN à direita), e _make_fog_barriers monta o
        # retângulo da neblina até world_width. Enquanto a neblina era
        # criada antes, ela parava 28px antes da nova borda do mundo na
        # Fase 1 — sobrava uma fresta por onde dava pra ver o outro lado.
        self.fog_barriers = self._make_fog_barriers()
        # As cientistas-NPC (objeto "cientista" no .tmx de cada local, ver
        # _make_npcs/game.NPC_DIALOGUES) — uma por local (Fase 1, corredor/
        # laboratório/biblioteca da Fase 2, Fase 3). Não são Enemy nem
        # bloqueiam passagem: só existem pra Game desenhar e checar
        # proximidade/[E].
        self.npcs = self._make_npcs()
        self.npc_animation = 0
        self.checkpoints = self._make_checkpoints()
        self.research = self._make_research()
        self._reset_lab_state()
        if self.is_underground and not self.room:
            # "and not self.room": o laboratório ESCONDIDO (room=
            # "laboratorio_secreto", ver a conversa sobre o elevador
            # secreto/fog.FogBarrier) também tem index==0 (mesma fase),
            # mas não deve herdar nada do corredor antigo — o laboratório
            # escondido usa seu próprio sistema genérico
            # (self.lab_bench/self.lab_microscope_parts/
            # self.secret_elevators), independente deste.
            self._build_underground_lab()

    def _configure_world_dimensions(self):
        self.world_width = self.data["world"]
        self.world_height = self.data["world_height"]
        self.world_top = self.data["world_top"]
        if self.tiled_map:
            self.world_width = self.tiled_map.pixel_width
            self.world_height = self.tiled_map.pixel_height

    def _reset_lab_state(self):
        self.panel_lever = None
        # A alavanca guarda o quadro atual, o quadro-alvo e o tempo até o
        # próximo movimento. Os quadros 0..4 correspondem às imagens 1..5.
        self.lever_animations = {
            name: {"frame": 0, "target": 0, "delay": 0}
            for name in ("panel",)
        }
        self.buttons = []
        self.microscope_parts = []
        self.bench = None
        self.return_route_platforms = []
        self.return_route_active = False
        # Ver _draw_lab: cache das peças do microscópio esmaecidas.
        self._dimmed_microscope_parts = None

    def _load_tiled_map(self):
        if self.room:
            filename = self.ROOM_MAP_FILES.get(self.room)
        else:
            filename = self.TILED_MAP_FILES.get(self.index)
        if not filename:
            return None
        path = ASSET_DIR.parent / "maps" / filename
        if not path.exists():
            # Antes isto devolvia None e o jogo caía num percurso gerado por
            # código que não correspondia ao mapa nenhum — um mapa faltando
            # virava uma fase estranha em vez de um erro. Agora falha alto.
            raise FileNotFoundError(
                f"Mapa do Tiled ausente: maps/{filename}. Toda fase e sala do "
                "jogo depende do .tmx correspondente."
            )
        return TiledMap(path)

    def _make_doors(self):
        """Portas interativas (objeto tipo "porta", propriedade "destino"):
        no corredor "destino" é a chave de ROOM_MAP_FILES (ex.: "laboratorio");
        dentro da sala, "destino" é "sair" para voltar ao corredor. Ver
        Game._use_doors."""
        if not self.tiled_map:
            return []
        doors = []
        for item in self.tiled_map.entities("porta"):
            target = item["properties"].get("destino", "sair")
            doors.append({"rect": self._rect_from_object(item), "target": target})
        return doors

    def _make_artifacts(self):
        """Achado opcional (objeto tipo "artefato"): mesmo formato de
        self.research (rect, nome), mas coletado à parte (Game.artifacts_
        collected) para nunca travar o avanço de fase."""
        if not self.tiled_map:
            return []
        return [
            (self._rect_from_object(item), item["properties"].get("nome", "Achado"))
            for item in self.tiled_map.entities("artefato")
        ]

    def _make_tool_pickups(self):
        """Ferramentas largadas no mapa (hoje só a chave de fenda, na
        passagem secreta do laboratório da Fase 2 — ver PLANO_MINIGAMES.md
        §3.1). Mesmo padrão de objeto tipado + _rect_from_object de sempre;
        genérico o bastante pra outra ferramenta um dia reaproveitar sem
        mudar este método. Fica vazio até o Raul desenhar a passagem e
        posicionar o objeto "chave_fenda" no Tiled — não é preciso nenhuma
        flag extra pra "desligar" isso enquanto não existir."""
        if not self.tiled_map:
            return []
        return [
            (self._rect_from_object(item), "chave_fenda")
            for item in self.tiled_map.entities("chave_fenda")
        ]

    def _make_secret_elevators(self):
        """Elevador(es) secreto(s) (objeto tipo "elevador_lab",
        propriedades "destino" — mesma convenção de "porta": chave de
        ROOM_MAP_FILES pra entrar, "sair" pra voltar — e opcionalmente
        "chave", que liga esse elevador a uma fog.FogBarrier específica:
        só pode ser chamado depois da Lia esbarrar nela, ver
        Game._use_secret_elevator/_fog_barrier_encountered). Sem "chave"
        — o mesmo tipo de objeto usado do OUTRO lado, dentro da sala
        escondida, pra voltar — fica sempre liberado."""
        if not self.tiled_map:
            return []
        elevators = []
        for item in self.tiled_map.entities("elevador_lab"):
            properties = item["properties"]
            elevators.append(
                {
                    "rect": self._rect_from_object(item),
                    "destino": properties.get("destino", "sair"),
                    "chave": properties.get("chave") or None,
                }
            )
        return elevators

    def _make_lab_microscope_parts(self):
        """Peças do microscópio do laboratório ESCONDIDO (objeto tipo
        "peca_microscopio", propriedade "nome" — mesmo formato de
        self.research/self.artifacts). Nome de objeto deliberadamente
        diferente do antigo "parte_microscopio" (área subterrânea da Fase
        1 que está saindo de uso — ver a conversa sobre o elevador
        secreto), pra nunca haver ambiguidade entre os dois sistemas
        mesmo que os dois objetos um dia coexistam no mesmo .tmx."""
        if not self.tiled_map:
            return []
        return [
            (self._rect_from_object(item), item["properties"].get("nome", "Peça"))
            for item in self.tiled_map.entities("peca_microscopio")
        ]

    def _make_lab_bench(self):
        """Bancada de montagem do laboratório escondido (objeto tipo
        "bancada_microscopio", propriedade opcional "libera" — a "chave"
        de qual fog.FogBarrier essa bancada libera ao terminar, ver
        Game._use_lab_microscope_bench/_release_fog_barrier). None até
        Raul posicionar o objeto, mesmo padrão de self.energy_box."""
        if not self.tiled_map:
            return None
        item = self.tiled_map.entity("bancada_microscopio")
        if not item:
            return None
        return {
            "rect": self._rect_from_object(item),
            "libera": item["properties"].get("libera") or None,
        }

    def _make_fog_barriers(self):
        """Bloqueios de neblina (objeto tipo "neblina", propriedades "chave"
        e opcionalmente "mensagem") — ver fog.FogBarrier. Genérico: qualquer
        passagem do jogo que precise de "bloqueada até X" usa este mesmo
        objeto, distinguido só pela "chave" (ex.: "campo_contencao_lab"),
        que é o que liga essa neblina específica a quem for liberá-la (ver
        Game._release_fog_barrier).

        Pedido do Raul: em vez do Raul ter que acertar a altura/largura
        exata do objeto no Tiled (arriscado de errar sem ver o jogo
        rodando — já aconteceu), só o X do objeto importa. A partir dali
        a neblina cobre TUDO: do topo até o fundo do mapa, e do X
        colocado até a borda direita — a "parede" inteira que bloqueia
        a passagem, altura e largura do objeto em si são ignoradas (o
        Raul pode deixar qualquer tamanho no Tiled, só pra enxergar o
        objeto lá).  Sem objeto "neblina" no mapa, fica vazio — sem
        custo pra fases que não usam o sistema.

        O topo do rect começa BEM acima de y=0 (não exatamente em y=0) —
        Raul reportou um vão de céu/nuvem aparecendo por cima da parede
        (a câmera às vezes mostra um pouco além do topo real do mapa, que
        é só cenário de fundo ali, sem tile nenhum). Esticando pra cima
        uma margem generosa (algumas telas de altura) garante que não
        sobra brecha nenhuma ali em cima, mesmo com zoom da câmera."""
        if not self.tiled_map:
            return []
        SKY_MARGIN = HEIGHT * 3
        barriers = []
        for item in self.tiled_map.entities("neblina"):
            properties = item["properties"]
            chave = properties.get("chave", "")
            mensagem = properties.get("mensagem") or None
            x = item["x"]
            rect = pygame.Rect(
                x, -SKY_MARGIN, max(1, self.world_width - x), self.world_height + SKY_MARGIN
            )
            barriers.append(FogBarrier(rect, chave, mensagem))
        return barriers

    def _make_energy_box(self):
        """Caixa de energia (Fase 2, laboratório — ver PLANO_MINIGAMES.md
        §3.2/§3.3, minigame.py EnergyBoxMinigame). None em qualquer mapa
        que ainda não tenha o objeto "caixa_energia" na camada Entidades —
        é assim que a mecânica fica "desligada" até o Raul posicionar a
        caixa no Tiled, sem precisar de nenhuma flag extra (ver
        Game._use_energy_box, que já lida com self.level.energy_box is
        None)."""
        if not self.tiled_map:
            return None
        item = self.tiled_map.entity("caixa_energia")
        return self._rect_from_object(item) if item else None

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

    def _make_lava_lakes(self):
        if not self.tiled_map:
            return []
        return [
            self._rect_from_object(item)
            for item in self.tiled_map.entities("lago_lava")
            if item["width"] > 0 and item["height"] > 0
        ]

    def _make_ramps(self):
        """Rampas vêm do PRÓPRIO TILE (ver TiledMap.tile_ramps/
        _load_tile_ramps), não de um objeto na camada Entidades: qualquer
        tile pintado na camada de Colisão que tenha a propriedade "rampa"
        no tileset (valor "direita" — sobe da esquerda pra direita, tipo
        "/"; "esquerda" — sobe da direita pra esquerda, tipo "\\") vira um
        triângulo do tamanho de uma célula, automaticamente, sem precisar
        posicionar nada à parte.

        _merge_ramp_tiles junta tiles-rampa vizinhos (mesma direção, uma
        diagonal certinha) numa Ramp SÓ antes de virar objeto — pedido do
        Raul (ela travava um pouco em cada emenda entre um tile-rampa e o
        seguinte): sem isso, cada tile é um triângulo com suas PRÓPRIAS
        arestas verticais/horizontais internas, que deviam ficar
        escondidas dentro da rampa contínua; testar o SAT contra vários
        triângulos pequenos em sequência fazia a Lia bater nessas arestas
        bem na costura. Ver ramp.Ramp pra colisão SAT de verdade contra o
        triângulo (não o quadrado inteiro)."""
        if not self.tiled_map:
            return []
        return [
            Ramp(x, y, width, height, str(direction).strip().casefold() not in ("esquerda", "left"))
            for x, y, width, height, direction in self._merge_ramp_tiles(self.tiled_map.tile_ramps)
        ]

    @staticmethod
    def _merge_ramp_tiles(tile_ramps):
        """Encosta tiles-rampa vizinhos (mesma direção, andando exatamente
        um tile na diagonal certa — ver _make_ramps) numa única faixa
        (x, y, width, height, direção), do início ao fim da corrente, sem
        nenhuma emenda no meio."""
        by_position = {(x, y): (x, y, w, h, d) for x, y, w, h, d in tile_ramps}
        used = set()
        merged = []
        for key in by_position:
            if key in used:
                continue
            x, y, w, h, direction = by_position[key]
            rising_right = str(direction).strip().casefold() not in ("esquerda", "left")
            # "direita" sobe indo pra direita (y diminui a cada tile);
            # "esquerda" desce indo pra direita (y aumenta a cada tile).
            step_y = -h if rising_right else h
            # Volta até o INÍCIO da corrente — sem isso, um merge que
            # começasse no meio perderia os tiles anteriores dela.
            start_x, start_y = x, y
            while (start_x - w, start_y - step_y) in by_position:
                previous = by_position[(start_x - w, start_y - step_y)]
                if previous[4] != direction:
                    break
                start_x -= w
                start_y -= step_y
            chain = []
            cx, cy = start_x, start_y
            while (
                (cx, cy) in by_position
                and by_position[(cx, cy)][4] == direction
                and (cx, cy) not in used
            ):
                chain.append((cx, cy))
                used.add((cx, cy))
                cx += w
                cy += step_y
            left = min(px for px, _ in chain)
            top = min(py for _, py in chain)
            right = max(px for px, _ in chain) + w
            bottom = max(py for _, py in chain) + h
            merged.append((left, top, right - left, bottom - top, direction))
        return merged

    def _map_spawn(self):
        item = self.tiled_map.entity("spawn")
        if not item:
            return self.DEFAULT_SPAWN
        return item["x"], item["y"] - PLAYER_HEIGHT

    def _build_course(self):
        """Plataformas-objeto do Tiled. O ramo "sem Tiled" (percursos
        gerados por código: _build_generated_course/_build_school_course/
        _build_university_course + as chaves layout/step/widths/heights/
        moving/decor_* de PHASES) foi removido — os 7 .tmx cobrem todas as
        fases e salas, então ele era inalcançável há tempos e só existia
        pra ser mantido junto. Se um mapa sumir, _load_tiled_map agora
        falha com uma mensagem clara em vez de cair num percurso
        fantasma que não corresponde a nada."""
        return self._build_tiled_object_platforms()

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


    def _build_underground_lab(self):
        self._build_tiled_underground_lab()


    def _build_tiled_underground_lab(self):
        """Lê os objetos especiais da camada Entidades do mapa do Tiled
        (Fase 1 subterránea). Os elevadores móviles (elevador_principal/
        elevador_superior) e as alavancas ligadas a eles saíram — resta o
        quebra-cabeza do painel (painel, botões, peças, bancada) e a Rota
        Retorno."""
        self.return_route_platforms = [
            self._platform_from_object(item)
            for item in self.tiled_map.objects("Rota Retorno")
            if item["width"] > 0 and item["height"] > 0
        ]

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

    def activate_return_route(self):
        """Libera as plataformas que conectam o laboratório ao caminho superior."""
        if not self.return_route_active:
            self.return_route_active = True
            self.platforms.extend(self.return_route_platforms)
            self.dynamic_platforms.extend(self.return_route_platforms)


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

    def _make_checkpoints(self):
        return [
                self._rect_from_object(item)
                for item in self.tiled_map.entities("checkpoint")
        ]

    def _make_research(self):
        return [
                (
                    self._rect_from_object(item),
                    item["properties"].get("nome", "Pesquisa"),
                )
                for item in self.tiled_map.entities("livro")
        ]

    def _make_enemies(self):
        return self._make_tiled_enemies()

    def _make_tiled_enemies(self):
        enemies = []
        for item in self.tiled_map.entities("slime"):
            platform = self._enemy_platform_from_map_object(item)
            if platform:
                enemies.append(Slime(platform))
        for item in self.tiled_map.entities("cervo"):
            platform = self._enemy_platform_from_map_object(item)
            if platform:
                enemies.append(CrystalStag(platform))
        for item in self.tiled_map.entities("sombra"):
            enemies.append(DarkWraith(_StaticZone(self._rect_from_object(item))))
        # Estudante/zelador usam uma zona de patrulha explícita (largura
        # própria do objeto do Tiled), não a fusão automática de colunas do
        # chão (_ground_zone_at). Na Fase 2 o piso é uma única camada de
        # colisão contínua e plana do corredor inteiro — sem essa zona
        # explícita, TODOS os inimigos de chão se fundiriam numa única zona
        # gigante (o mapa inteiro) e nasceriam empilhados no centro dela.
        for item in self.tiled_map.entities("estudante"):
            enemies.append(PossessedStudent(_StaticZone(self._rect_from_object(item))))
        for item in self.tiled_map.entities("zelador"):
            enemies.append(JanitorGuardian(_StaticZone(self._rect_from_object(item))))
        # Espécime só existe na sala do laboratório velho, mesma lógica de
        # zona explícita (piso contínuo, sem fusão automática de colunas).
        for item in self.tiled_map.entities("especime"):
            enemies.append(Specimen(_StaticZone(self._rect_from_object(item))))
        # Bibliotecário só existe na sala da biblioteca.
        for item in self.tiled_map.entities("bibliotecario"):
            enemies.append(Librarian(_StaticZone(self._rect_from_object(item))))
        return enemies

    # Margem de segurança somada a world_width além da borda direita da
    # arena do Rei Slime (ver _make_boss_arenas), pra câmera nunca bater no
    # fim do mundo colada na arena.
    SLIME_KING_ARENA_MARGIN = 300

    def _make_boss_arenas(self):
        arenas = []
        # Pedido do Raul: o Rei Slime nascia sempre em código, colado no
        # fim do percurso gerado — quebrou quando "Plataformas" esvaziou
        # (self.platforms virou [], então a arena nascia em x=0, logo no
        # início da fase). Agora é objeto tipo "rei_slime" na camada
        # Entidades, igual a bibliotecario/especime: o retângulo do
        # objeto vira a área de patrulha dele (_StaticZone só empresta um
        # .rect pra reaproveitar Slime/SlimeKing sem precisar de uma
        # Platform de verdade, ver classe acima). Posição 100% livre no
        # Tiled — só precisa ter chão de verdade (Colisão) pintado por
        # baixo.
        if self.index == 0 and not self.room and self.tiled_map:
            item = self.tiled_map.entity("rei_slime")
            if item:
                zone_rect = self._rect_from_object(item)
                boss = SlimeKing(_StaticZone(zone_rect))
                self.enemies.append(boss)
                zone = pygame.Rect(
                    zone_rect.left - 60, 0, zone_rect.width + 120, self.world_height,
                )
                arenas.append({"zone": zone, "enemy": boss})
                self.world_width = max(
                    self.world_width, zone_rect.right + self.SLIME_KING_ARENA_MARGIN
                )
        # Fase 3 (index == 2) fica sem chefe de arena por enquanto — o
        # Dragão foi removido (será substituído por uma Caveira, ainda não
        # implementada). O objeto "dragao" pode continuar existindo no
        # .tmx sem problema: só fica sem leitor, igual a qualquer objeto
        # órfão do Tiled.
        return arenas

    NPC_WIDTH = 48
    NPC_HEIGHT = 48
    NPC_GROUND_LIFT = 3

    # Uma cientista por local (chave = (índice da fase, sala)); o nome bate
    # com NPC_DIALOGUES/NPC_SPRITE_ROWS em game.py — level.py só guarda
    # posição e nome, igual ao padrão já usado por research/artifacts (o
    # texto de verdade mora do lado de Game, não aqui). O deslocamento em x é
    # só o suficiente pra cair sobre o mesmo chão sólido do spawn (checado
    # manualmente contra cada mapa), nunca sobre uma borda/vão.
    def _make_npcs(self):
        """Objeto tipo "cientista" (propriedade "nome") na camada Entidades
        de cada mapa — mesmo padrão de livro/artefato/porta. Editável no
        Tiled: dá pra arrastar a cientista pra qualquer lugar do mapa sem
        mexer em código, só reabrir o .tmx correspondente (fase1_escola,
        fase2_universidade, fase2_laboratorio_sala, fase2_biblioteca_sala ou
        fase3_pesquisa) e mover o objeto."""
        if not self.tiled_map:
            return []
        npcs = []
        # "cientista" é o tipo usado nas fases (Rosalind Franklin etc.);
        # "npc" é o tipo genérico da vila (ver PLANO_VILA.md/maps/vila.tmx) —
        # os dois caem na mesma self.npcs, o nome é que decide a fala
        # (NPC_DIALOGUES em game.py).
        for entity_type in ("cientista", "npc"):
            for item in self.tiled_map.entities(entity_type):
                name = item["properties"].get("nome", "")
                rect = pygame.Rect(item["x"], item["y"], self.NPC_WIDTH, self.NPC_HEIGHT)
                npcs.append({"rect": rect, "name": name})
        return npcs

    def _enemy_platform_from_map_object(self, item):
        center_x = item["x"] + item["width"] // 2
        candidates = [
            platform
            for platform in self.platforms
            if platform.rect.left - 10 <= center_x <= platform.rect.right + 10
            # Só aceita uma Platform de verdade se a altura bater (+-80px);
            # caso contrário cai pro chão pintado no Tiled, que é o caso comum
            # na Fase 3. Sem esse limite, qualquer plataforma cujo x cruzasse
            # o do inimigo era aceita mesmo estando muito acima/abaixo dele.
            and abs(platform.rect.top - item["y"]) <= 80
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

    # Tamanho do chunk em tiles pro índice espacial de colisão (ver
    # __init__/_build_solid_chunks/solids_near) — mesmo valor de
    # TiledMap.CHUNK_TILES, sem precisar ser idêntico, só um bom equilíbrio
    # entre "poucos chunks pra olhar" e "poucos tiles sobrando por chunk".
    SOLID_CHUNK_TILES = 8

    def _chunk_size(self):
        tile_size = self.tiled_map.tile_width if self.tiled_map else 32
        return self.SOLID_CHUNK_TILES * tile_size

    def _build_solid_chunks(self, rects):
        """Agrupa retângulos sólidos (chão/parede) por chunk, indexados pelo
        canto superior esquerdo — mesma ideia de TiledMap._build_chunks."""
        chunk_size = self._chunk_size()
        chunks = {}
        for rect in rects:
            key = (rect.left // chunk_size, rect.top // chunk_size)
            chunks.setdefault(key, []).append(rect)
        return chunks

    def solids_near(self, rect, margin=128):
        """Só os retângulos de chão/parede dos chunks que cruzam `rect`
        (expandido por `margin`, folga pra cobrir o quanto a Lia se move num
        quadro) — evita percorrer TODO chão/parede do mapa a cada quadro de
        física (ver comentário em __init__ sobre o lag da Fase 3)."""
        chunk_size = self._chunk_size()
        expanded = rect.inflate(margin * 2, margin * 2)
        first_col = expanded.left // chunk_size
        last_col = expanded.right // chunk_size
        first_row = expanded.top // chunk_size
        last_row = expanded.bottom // chunk_size
        result = []
        for row in range(first_row, last_row + 1):
            for col in range(first_col, last_col + 1):
                key = (col, row)
                result.extend(self._ground_chunks.get(key, ()))
        return result

    def _build_column_tops(self):
        """Pra cada coluna (agrupando por rect.left), guarda só o tile sólido
        mais alto — a superfície de fato pisável dessa coluna."""
        tops = {}
        for rect in self.grounds:
            current = tops.get(rect.left)
            if current is None or rect.top < current.top:
                tops[rect.left] = rect
        return tops

    def _ground_zone_at(self, item):
        """Funde as colunas vizinhas que têm sua PRÓPRIA superfície na mesma
        linha, pra montar a área de patrulha de um inimigo sobre chão pintado
        direto no Tiled (sem objeto Platform).

        Importante: a fusão original comparava tiles de qualquer coluna que
        caíssem na mesma linha absoluta (rect.top), sem checar se aquele
        tile era realmente a superfície da sua coluna — numa descida em
        "escada", o preenchimento profundo (bedrock) de um degrau mais alto
        cai, por coincidência, na mesma linha da superfície do degrau vizinho
        mais baixo, e os dois eram fundidos numa zona só. O inimigo então
        herdava a altura errada em parte do percurso e patrulhava por baixo
        do chão visível. Usar self.column_tops (só a superfície real de cada
        coluna) evita essa fusão incorreta."""
        center_x = item["x"] + item["width"] // 2
        tile_width = self.tiled_map.tile_width if self.tiled_map else 32
        col_left = (center_x // tile_width) * tile_width
        surface = self.column_tops.get(col_left)
        if surface is None:
            return None

        left = surface.left
        while True:
            neighbor = self.column_tops.get(left - tile_width)
            if neighbor is None or neighbor.top != surface.top:
                break
            left -= tile_width

        right = surface.right
        while True:
            neighbor = self.column_tops.get(right)
            if neighbor is None or neighbor.top != surface.top:
                break
            right += tile_width

        span = pygame.Rect(left, surface.top, right - left, surface.height)
        return _StaticZone(span)

    def update(self, dt=1 / 60):
        self.npc_animation += 1
        for platform in self.platforms:
            platform.update()
        # Coleta os spawns e só insere DEPOIS do laço: _drain_pending_spawns
        # fazia self.enemies.append() enquanto a lista estava sendo
        # percorrida, então os filhotes da Cisão recebiam update() no mesmo
        # quadro em que nasciam. Hoje era inofensivo (SmallSlime não gera
        # spawns), mas vira laço infinito no dia em que qualquer inimigo
        # novo expuser pending_spawns.
        spawned = []
        for enemy in self.enemies:
            enemy.update()
            self._collect_pending_spawns(enemy, spawned)
        self.enemies.extend(spawned)
        for barrier in self.fog_barriers:
            barrier.update(dt)
        if self.is_underground and not self.room:
            # Ver comentário equivalente em __init__: o laboratório
            # escondido não usa este sistema antigo de alavancas/elevador.
            self.update_lever_animations()

    # Zona (largura) em que os filhotes da Cisão se espalham ao redor do
    # ponto onde nasceram — não a arena inteira, só um pedaço em volta do
    # Rei Slime, senão eles patrulhariam a plataforma toda.
    CISAO_SPAWN_ZONE_WIDTH = 150

    def _collect_pending_spawns(self, enemy, destination):
        """SlimeKing.pending_spawns guarda posições (x, y) registradas pelo
        ataque Cisão — um Enemy não tem referência à Level pra se
        auto-inserir em self.enemies, então isso é feito aqui, todo quadro,
        pra qualquer inimigo que exponha essa fila (só o Rei Slime, por
        enquanto). Escreve em `destination` em vez de em self.enemies: quem
        chamou insere na lista depois de terminar de percorrê-la (ver
        update)."""
        spawns = getattr(enemy, "pending_spawns", None)
        if not spawns:
            return
        half = self.CISAO_SPAWN_ZONE_WIDTH // 2
        for x, y in spawns:
            zone = pygame.Rect(x - half, y, self.CISAO_SPAWN_ZONE_WIDTH, 32)
            destination.append(SmallSlime(_StaticZone(zone)))
        spawns.clear()

    def draw(self, surface, camera_x, camera_y, tiles, book_image, checkpoint_image, _checkpoint,
             collected, lever_on, sequence_progress, sequence_solved, microscope_collected,
             microscope_assembled, puzzle_sprites, slime_sprites, school_sprites, text_fn,
             stag_sprites=None, wraith_sprites=None,
             student_sprites=None, janitor_sprites=None, specimen_sprites=None,
             artifact_image=None, artifacts_collected=None, librarian_sprites=None,
             small_slime_sprites=None, slime_king_sprites=None,
             npc_frames=None,
             tool_icon=None, tools_collected=None,
             energy_box_sprites=None, energy_box_state=None,
             lab_microscope_sprites=None, lab_microscope_collected=None,
             lab_microscope_assembled=False, secret_elevator_sprite=None):
        if self.tiled_map:
            self.tiled_map.draw(surface, camera_x, camera_y)
        self._draw_platforms(surface, camera_x, camera_y, tiles, school_sprites)
        self._draw_collectibles(
            surface,
            camera_x,
            camera_y,
            book_image,
            checkpoint_image,
            collected,
        )
        if artifact_image is not None:
            self._draw_artifacts(surface, camera_x, camera_y, artifact_image, artifacts_collected or set())
        if tool_icon is not None:
            self._draw_tool_pickups(surface, camera_x, camera_y, tool_icon, tools_collected or set())
        if energy_box_sprites is not None:
            self._draw_energy_box(surface, camera_x, camera_y, energy_box_sprites, energy_box_state or {})
        self._draw_secret_elevators(surface, camera_x, camera_y, secret_elevator_sprite)
        if lab_microscope_sprites is not None:
            self._draw_lab_microscope(
                surface,
                camera_x,
                camera_y,
                lab_microscope_sprites,
                lab_microscope_collected or set(),
                lab_microscope_assembled,
            )
        if npc_frames:
            self._draw_npcs(surface, camera_x, camera_y, npc_frames)
        if self.is_underground and not self.room:
            # Idem: o laboratório escondido desenha sua própria bancada/
            # peças (ver Game._draw_lab_bench/_draw_lab_microscope_parts),
            # não a antiga bancada/microscópio do corredor.
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
            if isinstance(enemy, CrystalStag):
                enemy.draw(surface, camera_x, camera_y, stag_sprites)
            elif isinstance(enemy, DarkWraith):
                enemy.draw(surface, camera_x, camera_y, wraith_sprites)
            elif isinstance(enemy, PossessedStudent):
                enemy.draw(surface, camera_x, camera_y, student_sprites)
            elif isinstance(enemy, JanitorGuardian):
                enemy.draw(surface, camera_x, camera_y, janitor_sprites)
            elif isinstance(enemy, Specimen):
                enemy.draw(surface, camera_x, camera_y, specimen_sprites)
            elif isinstance(enemy, Librarian):
                enemy.draw(surface, camera_x, camera_y, librarian_sprites)
            elif isinstance(enemy, SlimeKing):
                enemy.draw(surface, camera_x, camera_y, slime_king_sprites)
            elif isinstance(enemy, SmallSlime):
                enemy.draw(surface, camera_x, camera_y, small_slime_sprites)
            else:
                enemy.draw(surface, camera_x, camera_y, slime_sprites)
        self._draw_enemy_attack_hazards(surface, camera_x, camera_y)
        for barrier in self.fog_barriers:
            barrier.draw(surface, camera_x, camera_y)

    def _draw_enemy_attack_hazards(self, surface, camera_x, camera_y):
        """Pinta um aviso translúcido sobre cada hazard de ataque ativo (o
        feixe do jato, a onda do Silêncio, os tomos do Errata) — sem isso
        o jogador só veria a hitbox por levar dano, não por enxergar a
        ameaça, o oposto do que os LEIA-ME pedem ("comunicar a mecânica
        sem tutorial"). overlay_hazards (opcional) deixa um chefe excluir
        daqui hazards que já têm aviso visual próprio, sem afetar o dano
        de verdade — quem decide dano é sempre active_hazards, nunca isso
        aqui."""
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            get_hazards = getattr(enemy, "overlay_hazards", None) or getattr(enemy, "active_hazards", None)
            color = getattr(enemy, "HAZARD_COLOR", None)
            if not get_hazards or not color:
                continue
            for rect in get_hazards():
                surface.blit(
                    self._hazard_overlay(rect.size, color),
                    (rect.x - camera_x, rect.y - camera_y),
                )

    # Cache de classe: as cores são constantes por chefe e os tamanhos de
    # hazard se repetem (o Bibliotecário chega a 11 simultâneos entre tomos e
    # lâminas, todos do mesmo tamanho). Antes era um pygame.Surface SRCALPHA
    # novo por hazard, POR QUADRO.
    _HAZARD_OVERLAYS = {}

    @classmethod
    def _hazard_overlay(cls, size, color):
        key = (size, color)
        overlay = cls._HAZARD_OVERLAYS.get(key)
        if overlay is None:
            overlay = pygame.Surface(size, pygame.SRCALPHA)
            overlay.fill(color)
            cls._HAZARD_OVERLAYS[key] = overlay
        return overlay

    def _draw_platforms(self, surface, camera_x, camera_y, tiles, school_sprites):
        """Só sobram plataformas-objeto do Tiled: os 2 elevadores da Fase 1
        (pele de piso da escola) e, em qualquer outra fase, a pele genérica.
        Os ramos "sem Tiled" (sombra procedural, peles da universidade)
        saíram junto com os percursos gerados por código."""
        for platform in self.platforms:
            if self.index == 0:
                floor_name = ("grass_tile", "wood_tile", "brick_tile")[platform.image_index % 3]
                self._draw_school_platform(
                    surface, platform, camera_x, camera_y, school_sprites[floor_name]
                )
            else:
                platform.draw(surface, camera_x, camera_y, tiles)

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

    def _draw_artifacts(self, surface, camera_x, camera_y, artifact_image, artifacts_collected):
        for index, (item, _) in enumerate(self.artifacts):
            if index not in artifacts_collected:
                surface.blit(artifact_image, (item.x - camera_x, item.y - camera_y))

    def _draw_tool_pickups(self, surface, camera_x, camera_y, tool_icon, tools_collected):
        """Ferramentas largadas no mapa (ver _make_tool_pickups) ainda não
        pegas — mesmo padrão de _draw_artifacts, centralizado no rect do
        objeto do Tiled em vez de ancorado no canto (o ícone de items.png
        é pequeno, 16x16 ampliado; centralizar evita flutuar estranho
        sobre objetos maiores)."""
        for index, (item, _key) in enumerate(self.tool_pickups):
            if index in tools_collected:
                continue
            surface.blit(
                tool_icon,
                (
                    item.centerx - tool_icon.get_width() // 2 - camera_x,
                    item.centery - tool_icon.get_height() // 2 - camera_y,
                ),
            )

    def _draw_energy_box(self, surface, camera_x, camera_y, energy_box_sprites, energy_box_state):
        """A caixa de energia embutida na parede (ver _make_energy_box,
        PLANO_MINIGAMES.md §3.2) — troca de sprite conforme o progresso
        (fechada/aberta/ligada), mesmos 3 estados que Game.energy_box_state
        já guarda para o minigame. self.energy_box é None em qualquer mapa
        sem o objeto ainda, então isso nunca desenha nada até o Raul
        posicioná-lo no Tiled."""
        if self.energy_box is None:
            return
        if energy_box_state.get("wired"):
            image = energy_box_sprites["ligada"]
        elif energy_box_state.get("screws_removed"):
            image = energy_box_sprites["aberta"]
        else:
            image = energy_box_sprites["fechada"]
        surface.blit(
            image,
            (
                self.energy_box.centerx - image.get_width() // 2 - camera_x,
                self.energy_box.bottom - image.get_height() - camera_y,
            ),
        )

    def _draw_secret_elevators(self, surface, camera_x, camera_y, sprite):
        """Porta do elevador secreto (ver _make_secret_elevators e a
        conversa sobre o elevador chat). `sprite` opcional (ver
        Game._load_optional_object_sprite("elevador_lab.png")) é
        esticado pro tamanho exato do objeto do Tiled — sem ele, cai num
        retângulo simples, só pra Lia ter uma pista visual de onde
        interagir enquanto a arte não chega."""
        for elevator in self.secret_elevators:
            rect = elevator["rect"]
            if sprite is not None:
                # Escalado UMA vez por elevador e guardado no próprio dict —
                # antes era um pygame.transform.scale por quadro, por
                # elevador, sempre pro mesmo tamanho (o rect do objeto do
                # Tiled não muda).
                image = elevator.get("_scaled")
                if image is None or image.get_size() != rect.size:
                    image = pygame.transform.scale(sprite, rect.size)
                    elevator["_scaled"] = image
                surface.blit(image, (rect.x - camera_x, rect.y - camera_y))
            else:
                draw_rect = (rect.x - camera_x, rect.y - camera_y, rect.width, rect.height)
                pygame.draw.rect(surface, (46, 68, 82), draw_rect, border_radius=6)
                pygame.draw.rect(surface, (120, 176, 196), draw_rect, 3, border_radius=6)

    def _draw_lab_microscope(self, surface, camera_x, camera_y, sprites, collected, assembled):
        """Peças + bancada do microscópio do laboratório ESCONDIDO (ver
        _make_lab_microscope_parts/_make_lab_bench e a conversa sobre o
        elevador secreto) — reaproveita as MESMAS sprites do microscópio
        já usadas na Fase 1 (sprites["parts"]: lista de 4 imagens,
        sprites["complete"]: montado, ver
        Game._microscope_sprites_by_identity), só que como sistema
        independente de _draw_lab, pra não herdar nada da área
        subterrânea que está saindo de uso."""
        parts = sprites["parts"]
        for index, (item, _name) in enumerate(self.lab_microscope_parts):
            if index in collected:
                continue
            image = parts[index % len(parts)]
            surface.blit(image, (item.x - camera_x, item.y - camera_y))

        if self.lab_bench is None:
            return
        bench = self.lab_bench["rect"]

        # Arte de verdade da bancada (bancada_madeira/bancada_microscopio,
        # já mostra a mesa com o microscópio em cima quando montado) — cai
        # pro retângulo de placeholder só se o arquivo ainda não existir em
        # images/objects (ver Game._load_puzzle_sprites).
        bench_image = sprites.get("bench_assembled" if assembled else "bench_empty")
        if bench_image is not None:
            self._draw_lab_bench_image(surface, camera_x, camera_y, bench, bench_image)
            return

        bench_color = (102, 220, 160) if assembled else (168, 112, 67)
        pygame.draw.rect(
            surface, bench_color,
            (bench.x - camera_x, bench.y - camera_y, bench.width, bench.height),
            border_radius=8,
        )
        pygame.draw.rect(
            surface, (57, 42, 32),
            (bench.x - camera_x, bench.y - camera_y, bench.width, bench.height),
            3, border_radius=8,
        )
        if assembled:
            complete = sprites["complete"]
            surface.blit(
                complete,
                (
                    bench.centerx - complete.get_width() // 2 - camera_x,
                    bench.bottom - complete.get_height() - camera_y,
                ),
            )

    @staticmethod
    def _draw_lab_bench_image(surface, camera_x, camera_y, bench, image):
        """Escala mantendo a proporção da arte (pra não esticar/achatar o
        pixel art) pela LARGURA do objeto colocado no Tiled, e apoia a
        base da imagem no fundo do retângulo — mesmo esquema de "objeto
        cravado no chão" usado pelos outros props, então funciona
        independente do tamanho exato que a bancada_*.png tiver."""
        width, height = image.get_size()
        if width <= 0:
            return
        scale = bench.width / width
        scaled_size = (round(width * scale), round(height * scale))
        if scaled_size != (width, height):
            image = pygame.transform.scale(image, scaled_size)
        x = bench.centerx - image.get_width() // 2 - camera_x
        y = bench.bottom - image.get_height() - camera_y
        surface.blit(image, (x, y))

    # ~8 fps de animação (cientistas_idle.png) — ver LEIA-ME_cientistas.md.
    NPC_ANIMATION_TICKS_PER_FRAME = 7

    def _draw_npcs(self, surface, camera_x, camera_y, npc_frames):
        """O quadro desenhado pode ser maior que npc["rect"] (Game.NPC_SCALE
        amplia o sprite cru) — centraliza pelo mesmo formato usado nos
        inimigos: X centralizado, Y apoiado no chão da hitbox + GROUND_LIFT.

        `npc_frames` é nome -> lista de quadros (ver Game._build_npc_frames),
        não mais um índice de linha numa folha única: cada morador da vila
        tem folha própria, e a contagem de quadros varia de um pro outro."""
        tick = self.npc_animation // self.NPC_ANIMATION_TICKS_PER_FRAME
        for npc in self.npcs:
            frames = npc_frames.get(npc["name"])
            if not frames:
                # NPC sem arte ainda: continua interagível, só não é
                # desenhado (mesmo padrão de asset opcional do resto).
                continue
            frame = frames[tick % len(frames)]
            rect = npc["rect"]
            frame_w, frame_h = frame.get_size()
            offset_x = (frame_w - rect.width) // 2
            offset_y = frame_h - rect.height - self.NPC_GROUND_LIFT
            surface.blit(frame, (rect.x - offset_x - camera_x, rect.y - offset_y - camera_y))

    def _draw_school_platform(self, surface, platform, camera_x, camera_y, platform_sprite):
        """Repete apenas um tile de piso para cada plataforma, sem misturar estilos."""
        for offset in range(0, platform.width, 32):
            surface.blit(platform_sprite, (platform.x + offset - camera_x, platform.y - camera_y))



    def _draw_lab(self, surface, camera_x, camera_y, lever_on, sequence_progress,
                  sequence_solved, microscope_collected, microscope_assembled, puzzle_sprites, text_fn):
        # Alavanca única que resta: a do painel (as dos elevadores saíram
        # junto com eles — ver _build_tiled_underground_lab).
        if self.panel_lever is not None:
            lever = self.panel_lever
            image = self.lever_image("panel", puzzle_sprites)
            # Centraliza o sprite (maior que o rect da alavanca) e mantém
            # sua base na posição original.
            surface.blit(image, (lever.centerx - image.get_width() // 2 - camera_x,
                                 lever.bottom - image.get_height() - camera_y))
            text_fn(surface, "PAINEL [E]", (lever.x - 30 - camera_x, lever.y - 24 - camera_y), 14, "#f4e4a5")

        for index, button in enumerate(self.buttons):
            surface.blit(puzzle_sprites["buttons"][index], (button.x-camera_x, button.y-camera_y))
            if sequence_solved or index < sequence_progress:
                pygame.draw.rect(surface, (225, 255, 218),
                                 (button.x-camera_x, button.y-camera_y, button.width, button.height), 2, border_radius=5)
            text_fn(surface, self.BUTTON_NAMES[index], (button.centerx-camera_x, button.y-20-camera_y), 13, "#ffffff", True)

        # Peças ficam apagadas até a sequência do painel ser concluída. As
        # versões esmaecidas são cacheadas: antes eram image.copy() + fill()
        # nas 4 peças TODO QUADRO enquanto a sequência não fosse resolvida
        # (medido: 1.200 cópias de Surface em 300 quadros).
        parts = puzzle_sprites["microscope_parts"]
        if not sequence_solved:
            if self._dimmed_microscope_parts is None:
                self._dimmed_microscope_parts = []
                for image in parts:
                    dim = image.copy()
                    dim.fill((105, 105, 105, 145), special_flags=pygame.BLEND_RGBA_MULT)
                    self._dimmed_microscope_parts.append(dim)
            parts = self._dimmed_microscope_parts
        for index, (item, _) in enumerate(self.microscope_parts):
            if index in microscope_collected:
                continue
            surface.blit(parts[index], (item.x-camera_x, item.y-camera_y))

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
