"""Carregamento e preparação das imagens; sem estado da partida."""

import pygame

from game_data import ITEM_DEFS, NPC_SPRITE_ROWS, SCHOOL_PLATFORM_SPRITES, VILLAGER_SPRITE_FILES
from minigame import WIRE_COLORS
from settings import ASSET_DIR, HEIGHT, WIDTH
from sprites import load_optional


class Assets:
    """Recursos de uma sessão, incluindo quadros de névoa sob demanda."""

    ANCIENT_GOLEM_SCALE = 1.5
    ANCIENT_GOLEM_VFX_SCALE = 1.5

    def __init__(self):
        self.tiles = self._load_platform_tiles()
        self._load_backgrounds()
        self.school_sprites = self._load_school_sprites()
        self.player_light = self._create_player_light()
        self.dash_trail_layers = self._create_dash_trail_layers()
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
        self.ancient_golem_sprites = self._load_ancient_golem_sprites()
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
    def _load_microscope_asset(filename, optional=False):
        """As 5 peças do microscópio (lens/base/light/ocular/complete/body)
        moraram soltas direto em images/objects, mas o Raul organizou numa
        subpasta própria (images/objects/microscope/). Tenta a subpasta
        primeiro e cai pro caminho antigo e achatado se não achar — assim
        funciona tanto antes quanto depois da mudança, sem depender de
        quando cada arquivo foi movido. `optional=True` devolve None se não
        achar em nenhum dos dois lugares (mesmo padrão de
        sprites.load_optional); do contrário, estoura — as 4 peças e o
        "montado" sempre existiram, então sumir é bug de verdade, não
        arte-que-ainda-não-chegou."""
        objects_dir = ASSET_DIR / "objects"
        for candidate in (objects_dir / "microscope" / filename, objects_dir / filename):
            if candidate.exists():
                return pygame.image.load(candidate).convert_alpha()
        if optional:
            return None
        raise FileNotFoundError(
            f"Peça de microscópio não encontrada em images/objects/microscope/ nem em "
            f"images/objects/: {filename}"
        )

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

    # O Campo ganhou cinco planos próprios, alinhados no mesmo canvas. As
    # velocidades crescem com a proximidade da câmera para criar profundidade
    # sem fazer o cenário "escorregar" depressa demais durante a fase.
    CAMPO_BACKGROUND_DIR = "backgrounds/campo"
    CAMPO_PARALLAX_LAYERS = (
        ("campo_01_ceu.png", 0.00, False),
        ("campo_02_montanhas.png", 0.06, True),
        ("campo_03_plantacao.png", 0.12, True),
        ("campo_04_cerca.png", 0.22, True),
        ("campo_05_gramado.png", 0.32, True),
    )
    # A composição estática aprovada continua disponível como fallback caso
    # uma das cinco camadas esteja ausente ou incompleta.
    CAMPO_BACKGROUND_PATH = "backgrounds/campo/campo_background_final.png"

    # A Escola usa apenas os três planos que se integram naturalmente ao
    # percurso: céu, árvores gigantes e névoa. Os PNGs da construção e da
    # vegetação continuam guardados na pasta, mas não são carregados nem
    # desenhados porque formavam faixas artificiais sobre as plataformas.
    # A névoa deriva devagar por conta própria, mesmo com Lia parada.
    SCHOOL_BACKGROUND_DIR = "backgrounds/escola"
    SCHOOL_PARALLAX_LAYERS = (
        {
            "name": "sky",
            "filename": "escola_ceu.png",
            "parallax_x": 0.00,
            "parallax_y": 0.00,
            "repeat_x": False,
            "scroll_speed_x": 0.0,
            "mirror_repeat": False,
        },
        {
            "name": "giant_trees",
            "filename": "escola_arvores_grandes.png",
            "parallax_x": 0.08,
            "parallax_y": 0.10,
            "repeat_x": False,
            "scroll_speed_x": 0.0,
            "mirror_repeat": False,
            # Repete apenas as fileiras externas fora da área visível. Isso
            # conserva a arte e o parallax, mas impede a câmera vertical de
            # alcançar o começo ou o fim físico do PNG.
            "vertical_edge_padding": 64,
        },
        {
            "name": "fog",
            "filename": "escola_nevoa_arvores.png",
            "parallax_x": 0.10,
            "parallax_y": 0.18,
            "repeat_x": True,
            "scroll_speed_x": 7.0,
            "mirror_repeat": True,
        },
    )

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
        self.campo_layers = self._load_campo_parallax_layers()
        self.school_layers = self._load_school_parallax_layers()
        campo_static_exists = (
            not self.campo_layers
            and (ASSET_DIR / self.CAMPO_BACKGROUND_PATH).exists()
        )
        campo_exists = bool(self.campo_layers) or campo_static_exists
        # O pack GrassLand antigo agora é apenas fallback: carregar seus
        # cinco fundos gigantes junto das cinco faixas do Campo desperdiçava
        # memória sem que eles fossem desenhados.
        self.village_layers = (
            [] if campo_exists else self._load_village_parallax_layers()
        )
        village_flat_exists = (
            not campo_exists
            and not self.village_layers
            and (ASSET_DIR / "backgrounds" / "ceu.png").exists()
        )
        specs = [
            ("university", "backgrounds/university_background.png", True),
            ("cave", "backgrounds/cave_background_v2.png", False),
            ("lab", "backgrounds/lab_background.png", True),
            ("library", "backgrounds/library_background.png", True),
        ]
        # O fundo antigo continua sendo fallback se qualquer uma das três
        # camadas novas não estiver presente, sem ficar residente à toa no
        # caminho normal.
        if not self.school_layers:
            specs.append(("school", "backgrounds/background_school.png", False))
        if village_flat_exists:
            specs.append(("village", "backgrounds/ceu.png", False))
        for key, path, is_university in specs:
            if not (ASSET_DIR / path).exists():
                continue
            raw = self._load_image(path, alpha=False)
            self.backgrounds[key] = {
                variant: self._scale_to_screen(self._tinted(raw, color))
                for variant, color in self._scene_tints(is_university).items()
            }
        if campo_static_exists:
            raw = self._load_image(self.CAMPO_BACKGROUND_PATH, alpha=False)
            # A referência tem praticamente a mesma proporção de 1920x1080.
            # Escalar direto preserva a composição completa, sem recortar as
            # casas das extremidades nem abrir faixas entre os planos.
            campo = pygame.transform.scale(raw, (WIDTH, HEIGHT)).convert()
            self.backgrounds["campo"] = {
                "normal": campo,
                "underground": campo,
            }
        self.background_mirror = {
            variant: pygame.transform.flip(image, True, False)
            for variant, image in self.backgrounds.get("university", {}).items()
        }

    def _load_school_parallax_layers(self):
        """Carrega os três planos ativos da Escola preservando pixel art e alpha.

        As imagens transparentes têm proporções diferentes, então são
        escaladas pela altura do canvas em vez de deformadas para 16:9. Só a
        margem vertical invisível é removida; ``draw_offset`` recoloca os
        pixels exatamente na posição original da composição.
        """
        paths = [
            ASSET_DIR / self.SCHOOL_BACKGROUND_DIR / spec["filename"]
            for spec in self.SCHOOL_PARALLAX_LAYERS
        ]
        if not all(path.exists() for path in paths):
            return []

        layers = []
        for spec, path in zip(self.SCHOOL_PARALLAX_LAYERS, paths):
            is_sky = spec["name"] == "sky"
            raw = pygame.image.load(path)
            if is_sky:
                # O céu é a única camada opaca e garante cobertura total.
                visible = pygame.transform.scale(raw, (WIDTH, HEIGHT)).convert()
                # A exportação termina num degradê quase branco/amarelo que
                # parece uma faixa vazia nos poços da fase. A parte inferior
                # passa a refletir uma faixa ainda azul do próprio céu: a
                # emenda começa na mesma fileira, portanto não abre corte.
                horizon_y = round(HEIGHT * 0.75)
                reflected_source_y = round(HEIGHT * 0.50)
                reflected = pygame.transform.flip(
                    visible.subsurface(
                        pygame.Rect(
                            0,
                            reflected_source_y,
                            WIDTH,
                            horizon_y - reflected_source_y,
                        )
                    ),
                    False,
                    True,
                )
                reflected = pygame.transform.scale(
                    reflected, (WIDTH, HEIGHT - horizon_y)
                )
                visible.blit(reflected, (0, horizon_y))
                tile_width = WIDTH
                draw_offset = (0, 0)
            else:
                raw = raw.convert_alpha()
                scale = HEIGHT / raw.get_height()
                scaled_width = max(1, round(raw.get_width() * scale))
                scaled = pygame.transform.scale(
                    raw, (scaled_width, HEIGHT)
                ).convert_alpha()
                tile_width = scaled_width
                # A exportação contém alguns pixels quase transparentes nas
                # margens. Ignorá-los evita superfícies enormes sem alterar o
                # desenho que de fato aparece na tela.
                content_rect = scaled.get_bounding_rect(min_alpha=8)
                if content_rect:
                    vertical_rect = pygame.Rect(
                        0, content_rect.y, scaled_width, content_rect.height
                    )
                    visible = scaled.subsurface(vertical_rect).copy().convert_alpha()
                    draw_offset = (0, content_rect.y)

                    edge_padding = spec.get("vertical_edge_padding", 0)
                    if edge_padding:
                        core = visible
                        extended = pygame.Surface(
                            (scaled_width, core.get_height() + 2 * edge_padding),
                            pygame.SRCALPHA,
                        ).convert_alpha()
                        top_edge = core.subsurface(
                            pygame.Rect(0, 0, scaled_width, 1)
                        )
                        bottom_edge = core.subsurface(
                            pygame.Rect(0, core.get_height() - 1, scaled_width, 1)
                        )
                        extended.blit(
                            pygame.transform.scale(
                                top_edge, (scaled_width, edge_padding)
                            ),
                            (0, 0),
                        )
                        extended.blit(core, (0, edge_padding))
                        extended.blit(
                            pygame.transform.scale(
                                bottom_edge, (scaled_width, edge_padding)
                            ),
                            (0, edge_padding + core.get_height()),
                        )
                        visible = extended
                        draw_offset = (
                            draw_offset[0], draw_offset[1] - edge_padding
                        )
                else:
                    visible = pygame.Surface((1, 1), pygame.SRCALPHA).convert_alpha()
                    draw_offset = (0, 0)

            layer = {
                **spec,
                "variants": {"normal": visible, "underground": visible},
                "tile_width": tile_width,
                "draw_offset": draw_offset,
                "base_offset": (0, 0),
                "reference_y": 0,
            }
            if spec["repeat_x"] and spec["mirror_repeat"]:
                mirror = pygame.transform.flip(visible, True, False)
                layer["mirrors"] = {"normal": mirror, "underground": mirror}
            layers.append(layer)
        return layers

    def _load_campo_parallax_layers(self):
        """Carrega os cinco planos do Campo já alinhados no mesmo canvas.

        O céu é opaco e sempre cobre a tela. Os demais PNGs preservam alpha;
        depois de escalados, suas margens transparentes são recortadas para
        reduzir o custo de blit. ``tile_width`` e ``draw_offset`` mantêm tanto
        o alinhamento aprovado quanto o período horizontal da repetição.
        """
        layers = []
        for filename, parallax, has_alpha in self.CAMPO_PARALLAX_LAYERS:
            path = f"{self.CAMPO_BACKGROUND_DIR}/{filename}"
            if not (ASSET_DIR / path).exists():
                return []
            raw = self._load_image(path, alpha=has_alpha)
            if has_alpha:
                scaled = pygame.transform.scale(raw, (WIDTH, HEIGHT)).convert_alpha()
                tile_width = WIDTH
                # Alpha 1–7 é ruído praticamente invisível deixado pela
                # exportação da IA, longe do desenho real de algumas camadas.
                content_rect = scaled.get_bounding_rect(min_alpha=8)
                if content_rect:
                    # Recortamos só verticalmente: manter a largura inteira
                    # permite espelhar o ladrilho sem deslocar suas bordas.
                    vertical_rect = pygame.Rect(
                        0, content_rect.y, WIDTH, content_rect.height
                    )
                    visible = scaled.subsurface(vertical_rect).copy().convert_alpha()
                    draw_offset = (0, content_rect.y)
                else:
                    visible = pygame.Surface((1, 1), pygame.SRCALPHA).convert_alpha()
                    draw_offset = (0, 0)
            else:
                visible = pygame.transform.scale(raw, (WIDTH, HEIGHT)).convert()
                tile_width = WIDTH
                draw_offset = (0, 0)
            layer = {
                "variants": {"normal": visible, "underground": visible},
                "parallax": parallax,
                "tile_width": tile_width,
                "draw_offset": draw_offset,
            }
            # O céu fica fixo e nunca alcança uma segunda repetição; não
            # mantemos uma cópia espelhada de tela cheia sem necessidade.
            if parallax:
                mirror = pygame.transform.flip(visible, True, False)
                layer["mirrors"] = {"normal": mirror, "underground": mirror}
            layers.append(layer)
        return layers

    # Cada item é (arquivo, velocidade de parallax, tem transparência de
    # verdade) — nessa ordem, do mais distante (céu) pro mais próximo (mato
    # alto), reproduzindo o guia oficial do pack (GrassLand_Background_
    # Guide.png). Só a camada 1 é opaca (céu sólido com nuvens já
    # desenhadas); as outras 4 têm área transparente por cima do relevo
    # pra deixar a camada de trás aparecer — é isso que dá profundidade.
    VILLAGE_PARALLAX_LAYERS = (
        ("GrassLand_Background_1.png", 0.05, False),
        ("GrassLand_Background_2.png", 0.15, True),
        ("GrassLand_Background_3.png", 0.30, True),
        ("GrassLand_Background_4.png", 0.45, True),
        ("GrassLand_Background_5.png", 0.65, True),
    )
    VILLAGE_BACKGROUND_DIR = "new_tilesets/Multi_Platformer_Tileset_Free/GrassLand/Background"

    def _load_village_parallax_layers(self):
        """Carrega as camadas de parallax novas da vila (ver
        VILLAGE_PARALLAX_LAYERS). Devolve uma lista vazia se o pack não
        estiver na pasta — nesse caso _load_backgrounds cai de volta pro
        ceu.png (uma camada só) ou pro preenchimento liso, sem quebrar.

        Só a camada 1 (opaca) recebe o tingimento BG_TINT de sempre, do
        mesmo jeito que os outros fundos — nas camadas com transparência,
        tingir aqui (compondo uma cor translúcida por cima de um destino
        que também tem alpha) preencheria de cor até as partes vazias, que
        deviam continuar 100% transparentes pra revelar a camada de trás.
        Como a camada 1 já cobre a tela inteira antes das outras serem
        desenhadas (ver _draw_village_parallax), o resultado visual do
        tingimento aparece do mesmo jeito — só que só no céu, que é a única
        parte que ficaria à mostra atrás do relevo mesmo com o tingimento
        certo."""
        layers = []
        for filename, parallax, has_alpha in self.VILLAGE_PARALLAX_LAYERS:
            path = f"{self.VILLAGE_BACKGROUND_DIR}/{filename}"
            if not (ASSET_DIR / path).exists():
                return []
            raw = self._load_image(path, alpha=has_alpha)
            if has_alpha:
                scaled = self._scale_to_screen_alpha(raw).convert_alpha()
                tile_width = scaled.get_width()
                content_rect = scaled.get_bounding_rect(min_alpha=1)
                # As camadas 2–5 têm grandes faixas 100% transparentes no
                # topo. Recortá-las evita que o blitter misture milhões de
                # pixels invisíveis por quadro. Guardamos a posição e a
                # largura anteriores ao recorte para preservar exatamente o
                # alinhamento vertical e o período horizontal do parallax.
                if content_rect:
                    visible = scaled.subsurface(content_rect).copy().convert_alpha()
                    draw_offset = content_rect.topleft
                else:
                    visible = pygame.Surface((1, 1), pygame.SRCALPHA).convert_alpha()
                    draw_offset = (0, 0)
                variants = {"normal": visible, "underground": visible}
            else:
                variants = {
                    variant: self._scale_to_screen(self._tinted(raw, color))
                    for variant, color in self._scene_tints(False).items()
                }
                tile_width = variants["normal"].get_width()
                draw_offset = (0, 0)
            layers.append({
                "variants": variants,
                "parallax": parallax,
                "tile_width": tile_width,
                "draw_offset": draw_offset,
            })
        return layers

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

    @staticmethod
    def _scale_to_screen_alpha(image):
        """Mesma ideia de _scale_to_screen, mas sem o .convert() final — ele
        joga fora o canal alpha, virando um retângulo opaco. Usado pelas
        camadas de parallax da vila que têm transparência de verdade (ver
        _load_village_parallax_layers)."""
        scale = HEIGHT / image.get_height()
        return pygame.transform.scale(image, (round(image.get_width() * scale), HEIGHT))

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

    @staticmethod
    def _create_dash_trail_layers():
        """Faixas do dash criadas uma vez, em vez de três Surfaces/quadro."""
        layers = []
        for alpha in (150, 95, 45):
            layer = pygame.Surface((42, 8), pygame.SRCALPHA)
            layer.fill((91, 220, 255, alpha))
            layers.append(layer)
        return tuple(layers)

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
                self._load_microscope_asset(f"microscope_{name}.png")
                for name in ("lens", "base", "light", "ocular")
            ],
            "microscope_complete": self._load_microscope_asset("microscope_complete.png"),
            # Peça "de fundo" (coluna/braço em C/platina/botões) pra
            # recompor o microscópio montado a partir das 4 peças de
            # verdade em vez de uma imagem solta (ver
            # minigame._compose_microscope). Opcional: sem o arquivo
            # ainda, MicroscopeMinigame cai pro microscope_complete.png.
            "microscope_body": self._load_microscope_asset("microscope_body.png", optional=True),
            # Bancada de verdade do laboratório escondido (ver
            # Level._draw_lab_microscope) — arte nova do Raul, já mostra a
            # mesa com/sem o microscópio montado em cima, então substitui o
            # retângulo colorido de placeholder. Opcional: sem os arquivos
            # ainda em images/objects/, cai pro retângulo de sempre.
            "lab_bench_empty": self._load_microscope_asset("bancada_madeira.png", optional=True),
            "lab_bench_assembled": self._load_microscope_asset("bancada_microscopio.png", optional=True),
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

    # slime_king.png já nasce grande (64x64); esta escala é só o empurrão
    # extra pedido no LEIA-ME pra ele ler como um dos maiores do jogo.
    SLIME_KING_SCALE = 1.3

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

    def _load_ancient_golem_sprites(self):
        """Corpo-base 92x92 ampliado a 1,5x e VFX dedicados do Golem.

        As folhas ficam separadas para que cada animação possa ter sua
        própria quantidade de quadros. O PNG mestre em ``spritesheets`` é
        somente a fonte de edição; o jogo carrega as folhas horizontais.
        """
        root = ASSET_DIR / "enemies" / "golem"
        animations = root / "golem_animations" / "spritesheets"
        vfx = root / "golem_vfx" / "spritesheets"

        def row(path, frame_size, count, scale=1.0):
            return self._load_grid_sheet(
                path, frame_size, frame_size, [count], scale=scale
            )[0]

        def body(filename, count):
            return row(
                animations / filename,
                92,
                count,
                self.ANCIENT_GOLEM_SCALE,
            )

        def effect(filename, frame_size, count):
            return row(
                vfx / filename,
                frame_size,
                count,
                self.ANCIENT_GOLEM_VFX_SCALE,
            )

        return {
            "idle": body("golem_idle_sheet.png", 11),
            "walk": body("golem_walking_sheet.png", 8),
            "charge": body("golem_charge_run_sheet.png", 16),
            "slam": body("golem_ground_crash_sheet.png", 17),
            "throw": body("golem_boulder_throwing_sheet.png", 16),
            "hurt": body("golem_taking_damage_sheet.png", 7),
            "dead": body("golem_death_sheet.png", 17),
            "vfx": {
                "rock_shockwave": effect("rock_shockwave_sheet.png", 64, 9),
                "ground_slam_impact": effect("ground_slam_impact_sheet.png", 64, 7),
                "charge_dust": effect("charge_dust_sheet.png", 48, 7),
                "charge_impact": effect("charge_impact_sheet.png", 64, 9),
                "projectile": effect("projectile_sheet.png", 64, 9),
                "boulder_explosion": effect("boulder_explosion_sheet.png", 64, 9),
                "damage_debris": effect("damage_debris_sheet.png", 64, 8),
            },
        }

    # Um pouco maiores que o quadro cru (48x48, igual à Lia) pra se
    # destacarem melhor perto dela sem deixar de ler como "gente", mesma
    # técnica de ampliação pós-recorte usada nos inimigos/chefes. O fator
    # anterior era 1.65; o novo tamanho é exatamente 1,25x maior.
    NPC_SCALE = 1.65 * 1.25

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
        PuzzleSystem.use_energy_box não abre o minigame. Mesmo padrão já
        usado pro céu da vila (village_background) e pro parry_flash.png: o jogo não
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

    def apply_fog(self, level):
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
