"""TILESET DE CHAO - grama, terra e caminho, 32x32, emenda garantida.

COMO A EMENDA E GARANTIDA (e nao "testada no olho"): todo relevo sai de SOMAS DE
SENOS DE FREQUENCIA INTEIRA no periodo do tile. sin(2*pi*f*x/32) com f inteiro
vale exatamente o mesmo em x=32 e em x=0, entao a coluna 31 continua na coluna 0
do proximo tile POR CONSTRUCAO. O miolo de terra usa o mesmo truque tambem em y,
porque ele precisa emendar nos dois eixos.

DUAS REGRAS DE PLATFORMER QUE VALEM MAIS QUE O DESENHO:

  · TOPO RETO. A tentacao e ondular a linha de cima da grama. Nao se faz: essa
    linha e a colisao, e personagem andando sobre topo ondulado balanca 2 px por
    tile e parece bug. Toda a irregularidade vai para a fronteira grama/terra,
    que fica embaixo e nao afeta o andar. O caminho usa a MESMA linha de topo,
    entao trocar grama por terra no meio da rua nao muda a altura do chao.
  · CONTORNO PRETO SO ONDE HA SILHUETA - topo do chao, laterais expostas,
    fronteira grama/terra, e cada pedra grande. Contorno em volta do tile inteiro
    viraria uma grade preta no chao todo. Torrao de terra de 3 px NAO leva
    contorno: a 3 px o preto e maior que o torrao e ele lê como furo de bala.
"""
import numpy as np, math, os
from PIL import Image

T = 32
OUT = '/home/claude/output/assets16'
BLACK = (0, 0, 0)

GR_L = (166, 208, 112)
GR_M = (116, 170, 86)
GR_D = (74, 124, 64)
DI_L = (196, 160, 116)
DI_M = (162, 122, 82)
DI_D = (122, 88, 56)
ST_L = (196, 192, 184)
ST_M = (152, 148, 140)
ST_D = (104, 100, 96)
FLW = [(250, 240, 220), (240, 196, 84), (198, 96, 72), (172, 152, 216)]


def wav(x, base, terms):
    v = base
    for (f, a, ph) in terms:
        v += a * math.sin(2 * math.pi * (f * x / T + ph))
    return v


def gboundary(x):
    """Fronteira grama/terra. O termo `tufo` e um seno estreito elevado a 6: da
    lingueta longa de grama entrando na terra, em vez de onda mole."""
    # FASE ZERO de proposito: assim o seno vale 0 em x=0 e em x=31, e a lingueta
    # nunca nasce em cima da emenda. Com fase .21 ela subia 4 px entre a ultima e
    # a primeira coluna e o teste de emenda acusava na hora.
    tuf = max(0.0, math.sin(2 * math.pi * (2 * x / T))) ** 4
    return wav(x, 14.0, [(1, 2.0, .13), (2, 1.3, .61), (3, .8, .29)]) + 6.0 * tuf


def gpatch(x, y):
    """Variacao de tom DENTRO da grama - periodica, senao a mancha corta na
    emenda."""
    return (math.sin(2 * math.pi * (2 * x / T + .11)) * .8
            + math.sin(2 * math.pi * (3 * x / T + y / 9.0 + .44)) * .6)


def mott(x, y, ph=0.0):
    """Manchado da terra. Quatro termos com frequencias PRIMAS ENTRE SI: com tres
    termos de frequencia baixa o padrao fechava em faixas diagonais que apareciam
    na hora que a gente empilhava 6 fileiras de tile."""
    return (math.sin(2 * math.pi * (3 * x / T + 5 * y / T + ph))
            + .8 * math.sin(2 * math.pi * (5 * x / T - 2 * y / T + .37 + ph))
            + .6 * math.sin(2 * math.pi * (1 * x / T + 7 * y / T + .71 + ph))
            + .5 * math.sin(2 * math.pi * (7 * x / T + 3 * y / T + .19 + ph)))


class Tile:
    def __init__(self):
        self.a = np.zeros((T, T, 4), np.uint8)
        self.a[..., 3] = 255

    def set(self, x, y, rgb):
        if 0 <= x < T and 0 <= y < T:
            self.a[y, x] = (rgb[0], rgb[1], rgb[2], 255)

    def img(self):
        return Image.fromarray(self.a, 'RGBA')


def dirt(t, x, y, ph=0.0):
    m = mott(x, y, ph)
    t.set(x, y, DI_D if m > 1.95 else (DI_L if m < -2.00 else DI_M))


def clod(t, cx, cy, w=3, h=2):
    """Torrao: borrao irregular, SEM ponto claro por cima. Na 1a versao ele tinha
    2 px claros nas pontas e o conjunto lia como um colchete tipografico repetido
    pela terra inteira."""
    for y in range(cy, cy + h):
        for x in range(cx, cx + w - (y - cy)):
            t.set((x + (y - cy)) % T, y, DI_D)


def grass_col(t, x, cap=False):
    b = int(round(gboundary(x)))
    t.set(x, 0, BLACK)
    for y in range(1, T):
        if y <= 2:
            t.set(x, y, GR_L)
        elif y < b - 2:
            t.set(x, y, GR_L if gpatch(x, y) > 1.05 else GR_M)
        elif y < b:
            t.set(x, y, GR_D)
        elif y == b:
            t.set(x, y, BLACK)
        else:
            dirt(t, x, y)
    return b


def stone(t, cx, cy, rx, ry, outline=True, tone=(ST_M, ST_L, ST_D), wrap_y=False):
    """Distancia com VOLTA nos eixos, disponivel mas usada com criterio.

    Pedra atravessando a emenda so funciona em tile que SEMPRE se repete. Num
    tile de VARIACAO, usado salteado, a metade que atravessa vira meia pedra orfa
    encostada num vizinho que nao tem a outra metade - apareceu exatamente assim
    no primeiro teste de cena. Por isso toda pedra de tile de variacao fica
    inteira dentro do quadro."""
    yy, xx = np.mgrid[0:T, 0:T]
    dx = (xx - cx + T // 2) % T - T // 2
    dy = (yy - cy + T // 2) % T - T // 2 if wrap_y else (yy - cy)
    m = ((dx / rx) ** 2 + (dy / ry) ** 2) <= 1.0
    # Pedra pequena NAO leva contorno. Com rx < 3 o anel preto tem mais pixel que
    # o miolo e a pedra lê como retangulo vazado - foi o que apareceu no primeiro
    # teste de cena, espalhado por toda a terra.
    if rx < 3.0:
        outline = False
    if outline:
        out = np.zeros_like(m)
        for (dy, dx) in ((1, 0), (-1, 0), (0, 1), (0, -1),
                         (1, 1), (1, -1), (-1, 1), (-1, -1)):
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
        for y, x in zip(*np.nonzero(out & ~m)):
            t.set(int(x), int(y), BLACK)
    for y, x in zip(*np.nonzero(m)):
        t.set(int(x), int(y), tone[0])
    hi = m & ~np.roll(np.roll(m, 1, 0), 1, 1)          # aresta superior esquerda
    lo = m & ~np.roll(np.roll(m, -1, 0), -1, 1)        # aresta inferior direita
    for y, x in zip(*np.nonzero(lo)):
        t.set(int(x), int(y), tone[2])
    for y, x in zip(*np.nonzero(hi)):
        t.set(int(x), int(y), tone[1])


def flower(t, x, y, col, mio=(250, 240, 220)):
    """Corola em CRUZ de 5 px, nao um pixel unico. A 1 px o contorno preto era
    maior que a flor e ela lia como faisca, nao como flor. Fica sempre dentro da
    faixa de grama: flor passando da linha de topo entraria na colisao."""
    pet = [(0, -1), (-1, 0), (1, 0), (0, 1)]
    for k in range(1, 4):
        t.set(x % T, y + 1 + k, GR_D)
    ring = set()
    for (dx, dy) in pet + [(0, 0)]:
        for (ex, ey) in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            ring.add((dx + ex, dy + ey))
    for (dx, dy) in ring - set(pet) - {(0, 0)}:
        t.set((x + dx) % T, y + dy, BLACK)
    for (dx, dy) in pet:
        t.set((x + dx) % T, y + dy, col)
    t.set(x % T, y, mio)


# ══ SUPERFICIE ═══════════════════════════════════════════════════════════════
def bridge(t, bs):
    """Costura VERTICAL do contorno da fronteira. Sem isso, onde a lingueta cai
    3 px de uma coluna para a outra o pixel preto de cada coluna fica solto e a
    fronteira lê como pente de dentes soltos em vez de linha continua. O preto
    entra sempre na coluna MAIS RASA, que ali e terra - assim ele fecha o contorno
    sem comer grama."""
    for x in range(T):
        b0, b1 = bs[x - 1], bs[x]
        if b1 > b0:
            for y in range(b0 + 1, b1 + 1):
                t.set((x - 1) % T, y, BLACK)
        elif b0 > b1:
            for y in range(b1 + 1, b0 + 1):
                t.set(x, y, BLACK)


def grama(cap_l=False, cap_r=False, deco=None):
    t = Tile()
    bs = [grass_col(t, x) for x in range(T)]
    bridge(t, bs)
    for (cx, cy) in ((6, 24), (20, 28), (27, 21), (13, 20), (2, 29)):
        clod(t, cx, cy)
    if deco:
        deco(t)
    for (do, xe, xi) in ((cap_l, 0, 1), (cap_r, T - 1, T - 2)):
        if not do:
            continue
        b = int(round(gboundary(xe)))
        for y in range(T):
            t.set(xe, y, BLACK)
            if y > b:
                t.set(xi, y, DI_D)
            elif 0 < y <= b:
                t.set(xi, y, GR_D)
    return t


def deco_flores(t):
    for (x, y, i) in ((6, 6, 1), (14, 9, 2), (21, 5, 3), (28, 8, 1)):
        flower(t, x, y, FLW[i], (250, 240, 220) if i != 1 else (240, 160, 60))


def deco_pedrinhas(t):
    stone(t, 8, 8, 3.4, 2.1)
    stone(t, 18, 10, 2.6, 1.7)
    stone(t, 26, 6, 3.8, 2.3)


def deco_tufo(t):
    """Tufo DENTRO da faixa - laminas escuras curvadas. Nao sobe acima da linha
    de topo de proposito: o tile continua opaco e a colisao continua reta."""
    for (bx, h, lean) in ((10, 9, -2), (13, 12, -1), (16, 13, 1), (19, 10, 2), (22, 8, 3)):
        for k in range(h):
            f = k / float(h - 1)
            x = bx + int(round(lean * f * f))
            y = 12 - k
            if y >= 1:
                t.set(x, y, GR_D if k > h - 5 else GR_M)
                t.set(x + 1, y, GR_D)


def deco_pedra(t):
    stone(t, 14, 8, 5.2, 3.4)
    stone(t, 23, 11, 3.2, 2.0)


# ══ MIOLO DE TERRA ═══════════════════════════════════════════════════════════
def terra(cap_l=False, cap_r=False, pedras=False):
    t = Tile()
    for y in range(T):
        for x in range(T):
            dirt(t, x, y)
    for (cx, cy) in ((5, 6), (18, 12), (11, 21), (25, 26), (30, 3), (2, 17)):
        clod(t, cx, cy)
    if pedras:
        for (cx, cy, rx, ry) in ((9, 9, 3.6, 2.4), (24, 16, 4.2, 2.8),
                                 (16, 27, 3.2, 2.2), (5, 24, 2.8, 1.9)):
            stone(t, cx, cy, rx, ry, wrap_y=True)
    for (do, xe, xi) in ((cap_l, 0, 1), (cap_r, T - 1, T - 2)):
        if do:
            for y in range(T):
                t.set(xe, y, BLACK)
                t.set(xi, y, DI_D)
    return t


# ══ CAMINHO ══════════════════════════════════════════════════════════════════
def path_col(t, x):
    """Mesma linha de topo da grama - so o material muda."""
    t.set(x, 0, BLACK)
    d = int(round(wav(x, 8.0, [(1, 1.0, .41), (3, .7, .07)])))
    for y in range(1, T):
        t.set(x, y, DI_L) if y <= d else dirt(t, x, y, .5)


def caminho(pedras=False):
    t = Tile()
    for x in range(T):
        path_col(t, x)
    if pedras:
        # todas as pedras a >=3 px das bordas: pedra cortada na borda denuncia
        # a emenda mais que qualquer diferenca de tom.
        # calcamento: duas fiadas com juntas desencontradas, pedras chatas e
        # espacadas. Amontoado no meio do tile lê como pilha de entulho.
        for (cx, cy, rx, ry) in ((6, 4, 4.2, 2.0), (16, 4, 4.8, 2.1), (26, 4, 4.2, 2.0),
                                 (10, 11, 4.6, 2.1), (21, 11, 4.4, 2.0), (30, 11, 1.6, 1.6)):
            stone(t, cx, cy, rx, ry)
    else:
        for (cx, cy) in ((9, 10), (22, 12), (16, 17), (30, 6)):
            clod(t, cx, cy, 3, 2)
        for (cx, cy) in ((5, 14), (27, 18)):
            clod(t, cx, cy, 2, 1)
    return t


def transicao(grass_left=True):
    """Meia grama, meio caminho. A borda vertical ondula, mas as colunas 0 e 31
    sao 100% de UM material - e o que deixa este tile encaixar tanto no tile de
    grama quanto no de caminho sem emenda visivel."""
    t = Tile()
    bs, gx = {}, []
    for x in range(T):
        u = x if grass_left else (T - 1 - x)
        e = 16.0 + 4.0 * math.sin(2 * math.pi * (1 * u / T + .18)) \
            + 1.5 * math.sin(2 * math.pi * (3 * u / T + .55))
        if u < e:
            bs[x] = grass_col(t, x)
            gx.append(x)
        else:
            path_col(t, x)
            if u - e < 2.5:
                for y in range(1, 4):
                    t.set(x, y, DI_M)
    for i in range(1, len(gx)):             # costura so entre colunas de grama
        a, b_ = gx[i - 1], gx[i]
        if bs[b_] > bs[a]:
            for y in range(bs[a] + 1, bs[b_] + 1):
                t.set(a, y, BLACK)
        elif bs[a] > bs[b_]:
            for y in range(bs[b_] + 1, bs[a] + 1):
                t.set(b_, y, BLACK)
    # aresta vertical entre grama e caminho: preto, como toda silhueta do estilo
    ex = (max(gx) + 1) if grass_left else (min(gx) - 1)
    if 0 <= ex < T:
        for y in range(1, bs[max(gx) if grass_left else min(gx)] + 1):
            t.set(ex, y, BLACK)
    for (cx, cy) in (((22, 8),) if grass_left else ((7, 8),)):
        clod(t, cx, cy)
    return t


# ══════════════════════════════════════════════════════════════════════════════
TILES = [
    ('grama_esq', lambda: grama(cap_l=True)),
    ('grama_meio', lambda: grama()),
    ('grama_dir', lambda: grama(cap_r=True)),
    ('grama_sozinha', lambda: grama(cap_l=True, cap_r=True)),

    ('terra_esq', lambda: terra(cap_l=True)),
    ('terra_meio', lambda: terra()),
    ('terra_dir', lambda: terra(cap_r=True)),
    ('terra_pedras', lambda: terra(pedras=True)),

    ('trans_grama_caminho', lambda: transicao(True)),
    ('caminho_meio', lambda: caminho()),
    ('trans_caminho_grama', lambda: transicao(False)),
    ('caminho_pedras', lambda: caminho(pedras=True)),

    ('grama_flores', lambda: grama(deco=deco_flores)),
    ('grama_pedrinhas', lambda: grama(deco=deco_pedrinhas)),
    ('grama_tufo', lambda: grama(deco=deco_tufo)),
    ('grama_pedra', lambda: grama(deco=deco_pedra)),
]


def jump(col_a, col_b):
    return int(np.abs(col_a.astype(int) - col_b.astype(int)).max())


def seam_report(imgs):
    """Teste de emenda POR COMPARACAO, nao por tolerancia inventada: a emenda so
    e boa se o salto de cor entre a ultima coluna de A e a primeira de B for
    menor ou igual ao maior salto que ja existe ENTRE COLUNAS VIZINHAS dentro do
    proprio tile. Se for, a emenda e literalmente indistinguivel do miolo."""
    out = []
    for (na, nb, axis) in (('grama_meio', 'grama_meio', 'x'),
                           ('terra_meio', 'terra_meio', 'x'),
                           ('terra_meio', 'terra_meio', 'y'),
                           ('grama_meio', 'terra_meio', 'y'),
                           ('grama_meio', 'trans_grama_caminho', 'x'),
                           ('trans_grama_caminho', 'caminho_meio', 'x'),
                           ('caminho_meio', 'trans_caminho_grama', 'x'),
                           ('trans_caminho_grama', 'grama_meio', 'x'),
                           ('grama_meio', 'grama_flores', 'x'),
                           ('grama_meio', 'grama_tufo', 'x'),
                           ('grama_meio', 'grama_pedra', 'x')):
        A, B = np.array(imgs[na])[..., :3], np.array(imgs[nb])[..., :3]
        if axis == 'x':
            s = jump(A[:, -1], B[:, 0])
            inner = max(jump(A[:, i], A[:, i + 1]) for i in range(T - 1))
        else:
            s = jump(A[-1, :], B[0, :])
            inner = max(jump(A[i, :], A[i + 1, :]) for i in range(T - 1))
        out.append((na, nb, axis, s, inner, s <= inner))
    return out


def scene(imgs):
    CW, CH = 14, 6
    im = Image.new('RGBA', (CW * T, CH * T), (196, 226, 240, 255))
    plan = ['grama_meio'] * CW
    plan[0] = 'grama_esq'; plan[CW - 1] = 'grama_dir'
    plan[2] = 'grama_tufo'; plan[3] = 'grama_flores'
    plan[5] = 'trans_grama_caminho'; plan[6] = 'caminho_meio'
    plan[7] = 'caminho_pedras'; plan[8] = 'caminho_meio'
    plan[9] = 'trans_caminho_grama'; plan[11] = 'grama_pedrinhas'
    plan[12] = 'grama_pedra'
    for x, n in enumerate(plan):
        im.paste(imgs[n], (x * T, 2 * T), imgs[n])
    for y in range(3, CH):
        for x in range(CW):
            n = ('terra_esq' if x == 0 else 'terra_dir' if x == CW - 1
                 else 'terra_pedras' if (x + y) % 7 == 0 else 'terra_meio')
            im.paste(imgs[n], (x * T, y * T), imgs[n])
    im.resize((CW * T * 3, CH * T * 3), Image.NEAREST).convert('RGB').save('%s/_teste.png' % OUT)


def main():
    os.makedirs(OUT, exist_ok=True)
    sheet = Image.new('RGBA', (T * 4, T * 4), (0, 0, 0, 0))
    imgs = {}
    for i, (name, fn) in enumerate(TILES):
        im = fn().img()
        imgs[name] = im
        im.save('%s/%s.png' % (OUT, name))
        sheet.paste(im, ((i % 4) * T, (i // 4) * T), im)
    sheet.save('%s/chao.png' % OUT)

    for (na, nb, ax, s, inner, ok) in seam_report(imgs):
        print('%-22s -> %-22s %s  salto %3d  vs miolo %3d  %s'
              % (na, nb, ax, s, inner, 'OK' if ok else 'ABRE'))
    scene(imgs)
    sheet.resize((T * 4 * 5, T * 4 * 5), Image.NEAREST).convert('RGB').save('%s/_preview.png' % OUT)
    print('ok', sheet.size)


main()
