"""Neblina escura que bloqueia passagens até serem liberadas (ver conversa
sobre o elevador do laboratório secreto — Fase 1, campo de contenção antes
da arena do Rei Slime). Pensado pra ser genérico: QUALQUER passagem do jogo
que precise de um "bloqueio visual até X acontecer" usa a mesma classe,
sem saber nada sobre o que libera cada uma — quem chama de fora decide
quando chamar `release()`.

Pedido do Raul (com imagem de referência): NÃO é uma nuvem semitransparente
por igual — é um bloco sólido, sem gradiente nenhum, tipo "parede que não
dá pra ver através de jeito nenhum". A única parte "fofa"/de nuvem de
verdade é a BORDA de entrada, onde a neblina encontra o cenário normal —
ali sim tem manchas esfarrapadas se sobrepondo (algumas até vazando um
pouco pro lado livre), pra parecer que a névoa está "engolindo" o mundo.
Passado essa faixa de borda (EDGE_BAND), é 100% opaco até o fim do mapa —
zero transparência, zero manchas soltas com buraco mostrando o fundo.

A neblina cobre TUDO depois de onde ela é colocada — do topo até o fundo
do mapa, e dali até a borda direita (ver Level._make_fog_barriers, que
monta um rect assim a partir só do X do objeto no Tiled). Como isso pode
ser uma área enorme, só a FAIXA DE BORDA precisa de manchas (o resto é um
retângulo sólido, barato de desenhar) — daí as manchas aqui ficam
concentradas numa coluna estreita ao redor do início do rect, não
espalhadas pelo retângulo inteiro. `draw` também só monta a superfície do
pedaço realmente visível na câmera, então o custo por quadro não depende
do tamanho total da barreira.

Ao liberar (`release`), a faixa opaca recua e as manchas da borda fogem
e somem aos poucos — aí sim uma transição animada, o "sem gradiente" vale
só pro estado parado/bloqueando.

Sem `fog_cloud.png` (ver Game._load_fog_sprite) cai pro desenho por
código abaixo, mesmo padrão de arte opcional do resto do jogo: funciona
igual, só fica mais bonito quando a arte de verdade (com as caras/efeitos
da referência) chegar."""

import math
import random

import pygame


class FogBarrier:
    """Um bloqueio de neblina — normalmente um objeto tipado "neblina" no
    Tiled (ver Level._make_fog_barriers), com uma propriedade "chave" que
    liga essa neblina a QUALQUER coisa que deva liberá-la (ver
    Game._check_fog_barriers/_release_fog_barrier)."""

    #: Duração (em quadros) da animação de dissipar — rápido o bastante
    #: pra não segurar o jogador parado esperando, devagar o bastante pra
    #: dar pra ver a nuvem se desfazendo de verdade.
    DISSIPATE_FRAMES = 50

    #: Largura (px) da faixa de transição "nuvem esfarrapada" a partir do
    #: início do rect — depois dela é bloco sólido, sem manchas soltas.
    EDGE_BAND = 220

    #: Quanto (px) as manchas da borda podem vazar pro lado LIVRE (antes
    #: do rect.x) — dá a sensação de névoa "engolindo" o cenário em vez de
    #: parar numa linha reta.
    EDGE_BLEED = 70

    #: Espaçamento vertical entre manchas na faixa de borda (px) e faixa
    #: de raio (px) — fixos em pixels, não fração do retângulo.
    BLOB_SPACING = 70
    BLOB_RADIUS_RANGE = (70, 130)

    #: Cor sólida da névoa (sem gradiente/camadas) — roxo bem escuro,
    #: quase preto, no clima da referência que o Raul mandou.
    FOG_COLOR = (20, 10, 30)

    #: Margem (px) além da tela visível em que uma mancha ainda é
    #: desenhada — evita ela "cortar" bruscamente saindo/entrando da
    #: borda da câmera.
    CULL_MARGIN = 140

    #: Fração (0..1) da largura NATIVA (480px, ver build_pixel_anim.py) em
    #: que fica a "linha de base" da curva ondulada da borda (constante 89
    #: em edge_x()) — usada pra ancorar o quadro animado de verdade no X
    #: real da barreira, não importa em que resolução ele foi carregado.
    FRAME_EDGE_ANCHOR_FRACTION = 89 / 480

    #: Quadros por segundo do loop de verdade (ver animacao.json/"fps").
    FRAME_FPS = 12

    def __init__(self, rect, chave, mensagem=None, sprite=None):
        self.rect = rect.copy()
        self.chave = chave
        self.mensagem = mensagem
        self.sprite = sprite  # opcional: textura de nuvem única (fog_cloud.png)
        # Opcional (melhor que `sprite`): a animação de verdade em 24
        # quadros (ver Game._load_fog_frame_sequence/_apply_fog_sprite) —
        # `frames` tem os rostos, `frames_corpo` é a mesma massa sem rosto
        # (pra repetir na vertical/horizontal sem duplicar cara nenhuma).
        # Sem nenhum dos dois, cai pro desenho procedural abaixo.
        self.frames = None
        self.frames_corpo = None
        # Cache de _scaled_frame: no máximo duas entradas (rostos e corpo).
        self._frame_cache = {}
        self.blocked = True
        self.encountered = False  # já mostrou a fala/gatilho de "esbarrou"?
        self._dissipating = False
        self._dissipate_elapsed = 0
        self._time = 0.0
        self._blobs = self._build_blobs()

    def _build_blobs(self):
        # Gerador com seed fixa por instância (id do objeto) — cada
        # neblina tem seu próprio arranjo, mas SEMPRE o mesmo entre um
        # quadro e outro. As manchas ficam só na coluna estreita da faixa
        # de borda (de -EDGE_BLEED até +EDGE_BAND, relativo ao rect.x),
        # cobrindo toda a ALTURA do rect — o resto vira bloco sólido em
        # `draw`, não precisa de mancha nenhuma.
        rng = random.Random(id(self))
        rows = max(1, round(self.rect.height / self.BLOB_SPACING))
        row_h = self.rect.height / rows
        blobs = []
        for row in range(rows):
            for _ in range(2):  # 2 manchas por linha, posições soltas
                blobs.append(
                    {
                        # "x" relativo ao rect.x — pode ser negativo
                        # (vazando pro lado livre) até EDGE_BLEED.
                        "x": rng.uniform(-self.EDGE_BLEED, self.EDGE_BAND),
                        "y": (row + rng.uniform(0.15, 0.85)) * row_h,
                        "radius": rng.uniform(*self.BLOB_RADIUS_RANGE),
                        "phase": rng.uniform(0, math.tau),
                        "speed": rng.uniform(0.3, 0.7),
                        "drift": rng.uniform(4, 9),
                        # Direção de fuga ao dissipar — cada mancha
                        # "explode" pra um lado diferente em vez de todas
                        # encolherem pro mesmo centro.
                        "flee_angle": rng.uniform(0, math.tau),
                    }
                )
        return blobs

    def release(self):
        """Chamado por quem for (ver Game._release_fog_barrier) quando o
        que quer que libere essa passagem acontecer — começa a dissipar
        em vez de sumir na hora."""
        if not self.blocked or self._dissipating:
            return
        self._dissipating = True
        self._dissipate_elapsed = 0

    def solid(self):
        """Pra quem usa isto como obstáculo de colisão (ver
        Game._all_solid_rectangles): já para de bloquear de verdade a
        partir da metade da animação, não só no fim — não faz sentido a
        Lia ainda trombar em algo que já está visualmente quase
        transparente."""
        if not self.blocked:
            return False
        if self._dissipating:
            return self._dissipate_elapsed < self.DISSIPATE_FRAMES // 2
        return True

    def update(self, dt):
        self._time += dt
        if self._dissipating:
            self._dissipate_elapsed += 1
            if self._dissipate_elapsed >= self.DISSIPATE_FRAMES:
                self.blocked = False
                self._dissipating = False

    def draw(self, surface, camera_x, camera_y):
        if not self.blocked:
            return
        # Recorte de verdade: a barreira cobre do X dela até a borda direita
        # do mapa, então na maior parte da fase ela está inteiramente fora da
        # câmera. _draw_animated não tinha essa saída — com a câmera em x=0 e
        # a névoa começando em x=6800 ela ainda ampliava e blitava DOIS
        # quadros de tela cheia por quadro de jogo, invisíveis. (_draw_procedural
        # já recortava sozinho via draw_rect.clip, mas sair aqui é mais barato.)
        if not self.rect.colliderect(
            pygame.Rect(camera_x, camera_y, surface.get_width(), surface.get_height())
        ):
            return
        if self.frames:
            self._draw_animated(surface, camera_x, camera_y)
        else:
            self._draw_procedural(surface, camera_x, camera_y)

    def _scaled_frame(self, frames, index, size):
        """Devolve `frames[index]` ampliado pra `size`, com cache.

        Os quadros passaram a ser guardados no tamanho NATIVO (480x270) em
        vez de já ampliados pra 1920x1080 — eram 380 MB residentes, 63% da
        memória do processo, para um efeito que só existe na Fase 1 (ver
        Game._load_fog_frame_sequence). O custo se paga aqui: como a
        animação roda a FRAME_FPS=12 e o jogo a 60, o mesmo quadro é pedido
        ~5 vezes seguidas, e são no máximo duas listas em uso ao mesmo tempo
        (rostos e corpo). Um cache com essas duas entradas transforma "um
        transform.scale de tela cheia por quadro" em ~24 por segundo.

        A cópia ampliada é nossa, então o set_alpha de _draw_animated não
        mexe mais no quadro carregado do disco (antes mexia)."""
        cache = self._frame_cache
        key = id(frames)
        entry = cache.get(key)
        if entry is not None and entry[0] == index and entry[1] == size:
            return entry[2]
        dest = entry[2] if entry is not None and entry[1] == size else None
        if dest is None:
            dest = pygame.Surface(size, pygame.SRCALPHA).convert_alpha()
        # `dest` reaproveitado entre trocas de quadro: alocar um Surface de
        # 1920x1080 a cada upscale custava ~22% a mais do que escrever num
        # buffer que já existe (medido).
        pygame.transform.scale(frames[index], size, dest)
        cache[key] = (index, size, dest)
        return dest

    def _draw_animated(self, surface, camera_x, camera_y):
        """Desenha a animação de verdade (ver módulo/build_pixel_anim.py).
        Os quadros vêm em 480x270 nativo e são ampliados pra o tamanho da
        superfície de mundo (1920x1080) na hora de desenhar, via
        _scaled_frame — o resultado é o mesmo de quando eles já vinham
        ampliados do carregamento, e a conta de ladrilho abaixo continua
        toda em cima do tamanho AMPLIADO, não do nativo. Ancora o quadro
        com ROSTOS bem no canto superior da barreira (linha de base da
        curva em rect.x), e ladrilha o resto (pra cobrir uma barreira maior
        que uma tela) só com `frames_corpo` (sem rosto) — assim nenhuma
        cara se repete."""
        frame_w, frame_h = surface.get_size()
        anchor_x = self.rect.x - round(frame_w * self.FRAME_EDGE_ANCHOR_FRACTION)
        # Level._make_fog_barriers estica rect.top bem pra cima do topo
        # real do mapa (SKY_MARGIN, pra não sobrar brecha de céu acima da
        # parede) — "linha 0" nem sempre é onde o jogador realmente
        # encontra a névoa. `anchor_row` acha a linha que cai o mais perto
        # possível de y=0 (o topo de verdade do mapa) pra mostrar os
        # rostos ali, não lá em cima na margem de céu que quase nunca
        # aparece na câmera.
        anchor_row = round(-self.rect.top / frame_h)

        idx = int(self._time * self.FRAME_FPS) % len(self.frames)
        progress = (self._dissipate_elapsed / self.DISSIPATE_FRAMES) if self._dissipating else 0.0
        alpha = round(255 * (1 - progress))
        if alpha <= 0:
            return

        screen_w, screen_h = surface.get_size()
        view = pygame.Rect(camera_x, camera_y, screen_w, screen_h)

        # Colunas/linhas de ladrilho que realmente cruzam a tela — nunca
        # menos que zero (não tem nada pra desenhar à esquerda da borda de
        # verdade, essa área já é o lado livre).
        col_start = max(0, (view.left - anchor_x) // frame_w)
        col_end = min(5, max(0, (min(view.right, self.rect.right) - anchor_x) // frame_w))
        row_start = max(0, (view.top - self.rect.top) // frame_h)
        row_end = min(5, max(0, (min(view.bottom, self.rect.bottom) - self.rect.top) // frame_h))

        for row in range(int(row_start), int(row_end) + 1):
            tile_y = self.rect.top + row * frame_h
            if tile_y >= self.rect.bottom:
                continue
            for col in range(int(col_start), int(col_end) + 1):
                tile_x = anchor_x + col * frame_w
                if tile_x >= self.rect.right:
                    continue
                # Só o ladrilho da linha-âncora (perto de y=0, a entrada
                # de verdade) na primeira coluna mostra os rostos; o resto
                # usa a massa lisa pra não repetir a mesma cara em vários
                # lugares (inclusive na margem de céu lá em cima).
                source = self.frames if (row == anchor_row and col == 0) else (self.frames_corpo or self.frames)
                frame_img = self._scaled_frame(source, idx, (frame_w, frame_h))
                frame_img.set_alpha(alpha)
                surface.blit(frame_img, (tile_x - camera_x, tile_y - camera_y))

    def _draw_procedural(self, surface, camera_x, camera_y):
        # Só monta/desenha o pedaço que cabe na tela — o retângulo real
        # pode cobrir o mapa inteiro de altura, então construir uma
        # superfície do tamanho dele inteiro TODO quadro seria caro à
        # toa quando a Lia está longe (ver comentário do módulo).
        # `draw_rect` estica um pouco pra ESQUERDA do rect real porque as
        # manchas da borda podem vazar até EDGE_BLEED px pro lado livre.
        screen_w, screen_h = surface.get_size()
        margin = self.CULL_MARGIN
        view = pygame.Rect(
            camera_x - margin, camera_y - margin, screen_w + margin * 2, screen_h + margin * 2
        )
        draw_rect = self.rect.copy()
        draw_rect.x -= self.EDGE_BLEED
        draw_rect.width += self.EDGE_BLEED
        visible = draw_rect.clip(view)
        if visible.width <= 0 or visible.height <= 0:
            return

        progress = (self._dissipate_elapsed / self.DISSIPATE_FRAMES) if self._dissipating else 0.0
        # Parado (progress=0): 255 = totalmente opaco, sem gradiente nenhum,
        # exatamente o "literalmente escuro" pedido. Só ao liberar isso
        # esmaece — aí é uma transição animada, não o estado de repouso.
        base_alpha = round(255 * (1 - progress))
        if base_alpha <= 0:
            return

        # offset pra converter "posição relativa ao rect.x/rect.y" (tanto
        # das manchas quanto da faixa sólida) pra "posição dentro da
        # superfície pequena que estamos montando agora".
        origin_x = visible.x - self.rect.x
        origin_y = visible.y - self.rect.y

        fog_surface = pygame.Surface((visible.width, visible.height), pygame.SRCALPHA)
        color = (*self.FOG_COLOR, base_alpha)

        # 1) Núcleo sólido: um retângulo opaco só, sem camadas, cobrindo
        # tudo a partir da faixa de borda até o fim da barreira. Ao
        # liberar, essa fronteira recua pra dentro (some primeiro perto
        # da entrada), acompanhando as manchas fugindo.
        solid_left_local = (self.EDGE_BAND + self.rect.width * progress * 0.6) - origin_x
        solid_left_local = max(0, round(solid_left_local))
        if solid_left_local < visible.width:
            pygame.draw.rect(
                fog_surface, color,
                pygame.Rect(solid_left_local, 0, visible.width - solid_left_local, visible.height),
            )

        # 2) Franja de nuvem na borda: manchas SÓLIDAS (mesma cor/alpha do
        # núcleo, sem blur em camadas) que se sobrepõem — onde não cobrem,
        # o cenário aparece por trás, dando a beirada esfarrapada de
        # nuvem da referência, sem nenhuma transparência no meio do caminho.
        for blob in self._blobs:
            drift_x = math.sin(self._time * blob["speed"] + blob["phase"]) * blob["drift"]
            drift_y = math.cos(self._time * blob["speed"] * 0.7 + blob["phase"]) * blob["drift"] * 0.6
            flee_x = math.cos(blob["flee_angle"]) * 260 * progress
            flee_y = math.sin(blob["flee_angle"]) * 140 * progress

            radius = blob["radius"] * (1 + progress * 0.5)
            cx = blob["x"] + drift_x + flee_x - origin_x
            cy = blob["y"] + drift_y + flee_y - origin_y

            # Descarta cedo qualquer mancha fora da superfície pequena —
            # é o que faz o custo por quadro depender só do que está na
            # tela, não do tamanho total da neblina.
            if (
                cx < -radius or cx > visible.width + radius
                or cy < -radius or cy > visible.height + radius
            ):
                continue

            if self.sprite is not None:
                scale = (radius * 2) / self.sprite.get_height()
                size = (round(self.sprite.get_width() * scale), round(radius * 2))
                if size[0] > 0 and size[1] > 0:
                    frame = pygame.transform.scale(self.sprite, size)
                    frame = frame.copy()
                    frame.set_alpha(base_alpha)
                    fog_surface.blit(frame, frame.get_rect(center=(cx, cy)))
                continue

            pygame.draw.circle(fog_surface, color, (round(cx), round(cy)), round(radius))

        surface.blit(fog_surface, (visible.x - camera_x, visible.y - camera_y))
