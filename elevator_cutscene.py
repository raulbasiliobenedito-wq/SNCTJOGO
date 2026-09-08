"""Cutscene curta do elevador secreto do laboratório (Fase 1) — ver a
conversa sobre o "elevador chat": ao entrar num elevador já liberado (ver
fog.FogBarrier/Game._check_fog_barriers), toca uma animação rápida e NÃO
interativa simulando a descida antes de trocar pra sala escondida de
verdade (Game.enter_room). Ao voltar, a MESMA cutscene toca com
`reverse=True`, subindo em vez de descer, antes de chamar Game.exit_room.

Pedido do Raul: a Lia fica PARADA (sprite idle já existente, centralizada,
sem arte nova pra ela) — quem se move é o CENÁRIO ao redor dela (as
paredes do vão + as correntes deslizando pra cima/baixo), como se ela
estivesse de fato dentro do elevador olhando pro lado de fora andar.

Arte esperada, em DUAS camadas separadas (ver o prompt que mandei pro
Raul pedir isso à IA):
- images/cutscenes/elevador_lab_fundo.png: a textura das paredes do vão
  + correntes, pensada pra ser costurável verticalmente (o topo encaixa
  com a base) — é ISSO que rola pra cima/baixo pra simular o movimento.
  _draw_scrolling_background repete essa textura quantas vezes precisar
  pra cobrir a tela, então não precisa ser do tamanho exato da tela.
- images/cutscenes/elevador_lab_moldura.png (opcional): qualquer parte
  do primeiro plano que deva ficar PARADA por cima do fundo rolando
  (ex.: a estrutura/janela do próprio carrinho do elevador) — sem esse
  arquivo, nenhuma moldura extra é desenhada, só o fundo rolando + a Lia.

Sem nenhum dos dois arquivos ainda, cai num vão desenhado por código
(mesmo padrão de "funciona igual, fica bonito quando a arte chegar" do
resto do jogo) — mesma ideia de rolagem, só que com paredes/correntes
geométricas em vez de textura de verdade."""

import math

import pygame

from settings import ASSET_DIR, HEIGHT, WIDTH


class ElevatorCutscene:
    #: Curta de propósito — é só uma transição, não uma cena narrativa;
    #: seguro perder alguns quadros de not-interactive sem incomodar.
    DURATION = 80

    #: Velocidade de rolagem do fundo (px/quadro) — dá pra sentir o
    #: movimento sem que passe rápido demais pra perceber.
    SCROLL_SPEED = 6

    BACKGROUND_PATH = ASSET_DIR / "cutscenes" / "elevador_lab_fundo.png"
    FRAME_PATH = ASSET_DIR / "cutscenes" / "elevador_lab_moldura.png"

    # Posição fixa da Lia na tela — ela não se move em nenhum momento da
    # cutscene, só o fundo rola ao redor dela.
    LIA_X_ANCHOR = 0.5
    LIA_Y_ANCHOR = 0.62

    def __init__(self, lia_frame):
        self.lia_frame = pygame.transform.scale(
            lia_frame, (lia_frame.get_width() * 3, lia_frame.get_height() * 3)
        )
        self.active = False
        self.reverse = False
        self.timer = 0
        self._on_finish = None

        self.background = None
        if self.BACKGROUND_PATH.exists():
            raw = pygame.image.load(str(self.BACKGROUND_PATH)).convert_alpha()
            # Redimensiona pra largura EXATA da tela, preservando a
            # proporção (a altura acompanha) — a arte pode ter vindo em
            # qualquer resolução, isso garante que a textura cobre a
            # largura toda ao repetir verticalmente (ver
            # _draw_scrolling_background), sem faixa sobrando dos lados.
            scale = WIDTH / raw.get_width()
            size = (WIDTH, max(1, round(raw.get_height() * scale)))
            # `scale` (vizinho mais próximo) em vez de `smoothscale` —
            # com a arte já nascendo em 1920px de largura o fator aqui é
            # ~1.0 (nenhum estiramento real), então isso só evita borrar
            # os pixels da pixel art caso a exportação venha com 1-2px de
            # folga em vez de suavizar um redimensionamento que não deveria
            # mais existir de verdade.
            self.background = pygame.transform.scale(raw, size)
        self.frame = None
        if self.FRAME_PATH.exists():
            self.frame = pygame.image.load(str(self.FRAME_PATH)).convert_alpha()

    def start(self, reverse=False, on_finish=None):
        """`on_finish` é chamado exatamente uma vez, no quadro em que a
        animação termina — Game passa `enter_room`/`exit_room` aqui (ver
        Game._use_secret_elevator)."""
        self.active = True
        self.reverse = reverse
        self.timer = 0
        self._on_finish = on_finish

    def update(self):
        if not self.active:
            return
        self.timer += 1
        if self.timer >= self.DURATION:
            self.active = False
            callback = self._on_finish
            self._on_finish = None
            if callback:
                callback()

    def draw(self, surface, text_fn):
        # Descendo: o mundo "sobe" ao redor da Lia. Subindo: o contrário.
        # scroll_offset cresce sempre no tempo; só o SINAL muda com a
        # direção — é o que dá a sensação de reverter o movimento.
        direction = -1 if not self.reverse else 1
        scroll_offset = self.timer * self.SCROLL_SPEED * direction

        if self.background is not None:
            self._draw_scrolling_background(surface, scroll_offset)
        else:
            self._draw_fallback_shaft(surface, scroll_offset)

        # A Lia fica sempre no mesmo lugar — quem se move é o cenário.
        lia_rect = self.lia_frame.get_rect(
            midbottom=(round(WIDTH * self.LIA_X_ANCHOR), round(HEIGHT * self.LIA_Y_ANCHOR))
        )
        surface.blit(self.lia_frame, lia_rect)

        if self.frame is not None:
            frame_rect = self.frame.get_rect(midbottom=(WIDTH // 2, HEIGHT))
            surface.blit(self.frame, frame_rect)

        label = "Subindo..." if self.reverse else "Descendo..."
        text_fn(surface, label, (WIDTH // 2 - 55, HEIGHT - 64), 20, "#cbd6e6", True)

    def _draw_scrolling_background(self, surface, scroll_offset):
        """Repete a textura vertical (paredes + correntes) quantas vezes
        precisar pra cobrir a tela, deslocada por `scroll_offset` — a
        própria imagem precisa ser costurável (topo bate com a base) pra
        a repetição não aparecer como uma "costura" visível."""
        tile_height = self.background.get_height()
        offset = scroll_offset % tile_height
        y = -offset - tile_height
        while y < HEIGHT:
            surface.blit(self.background, (0, y))
            y += tile_height

    # --- Fallback (só usado se elevador_lab_fundo.png não existir) ---

    def _draw_fallback_shaft(self, surface, scroll_offset):
        surface.fill((11, 13, 20))
        shaft_rect = pygame.Rect(WIDTH // 2 - 220, 0, 440, HEIGHT)
        pygame.draw.rect(surface, (23, 26, 37), shaft_rect)
        car_rect = shaft_rect.inflate(-80, 0)
        pygame.draw.rect(surface, (37, 41, 56), car_rect, border_radius=10)

        self._draw_chain(surface, car_rect.left + 6, scroll_offset)
        self._draw_chain(surface, car_rect.right - 6, scroll_offset)

    #: Espaçamento entre elos da corrente (px) — junto com scroll_offset,
    #: dá o "looping" contínuo do desenho por código.
    CHAIN_LINK_SPACING = 42

    def _draw_chain(self, surface, x, scroll_offset):
        spacing = self.CHAIN_LINK_SPACING
        shift = scroll_offset % spacing
        segments = HEIGHT // spacing + 3
        for i in range(-1, segments):
            y = round(i * spacing + shift)
            if y < -20 or y > HEIGHT + 20:
                continue
            # Leve balanço lateral por elo, só pra não ficar uma linha
            # reta demais — não depende do progresso da cutscene, é só
            # textura procedural.
            wobble = math.sin(y * 0.05) * 2
            pygame.draw.circle(surface, (126, 132, 146), (round(x + wobble), y), 5)
            pygame.draw.circle(surface, (70, 74, 88), (round(x + wobble), y), 5, 1)
