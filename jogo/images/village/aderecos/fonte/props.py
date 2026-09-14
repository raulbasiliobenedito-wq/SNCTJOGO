"""DOZE ADEREÇOS DE VILA - poste, banco, arvores, arbustos, cerca, canteiro,
poco e placa. Mesma gramatica chapada das casas e do interior.

Quadro 64x64. A ULTIMA LINHA DESENHADA E y 62 - identica a das casas da vila.
Alinhando os dois no mesmo topo de terreno, casa e aderec,o encostam no chao sem
ajuste. O tile de chao tem 32 px, entao um quadro destes cobre exatamente 2 tiles
de largura e 2 de altura.

A CERCA e o unico quadro que vai de borda a borda: os travessoes tocam x 0 e x 63
e NAO levam tampa preta nas pontas, entao repetindo o quadro a cerca corre sem
emenda. `cerca_ponta` fecha a fileira.
"""
import numpy as np, math, os
from PIL import Image

W = H = 64
BASE = 61   # ultima linha PINTADA; o contorno preto cai em 62, igual as casas
BLACK = (0, 0, 0)
OUT = '/home/claude/output/assets17'

WD_L = (192, 150, 102)      # madeira - mesma familia do interior
WD_M = (150, 104, 66)
WD_D = (104, 68, 42)
IR_L = (110, 116, 128)      # ferro do poste
IR_M = (74, 78, 88)
IR_D = (44, 46, 56)
GLOW = (255, 226, 140)      # vidro do lampiao - tons SOLIDOS, sem bloom
GLOW2 = (246, 184, 74)
FL_L = (152, 198, 106)      # folhagem viva - continua o verde do tileset de chao
FL_M = (104, 158, 80)
FL_D = (64, 112, 58)
AU_L = (244, 186, 92)       # folhagem de outono
AU_M = (214, 124, 52)
AU_D = (148, 70, 36)
BU_L = (132, 184, 96)       # arbusto - um degrau mais claro que a arvore
BU_M = (86, 140, 74)
BU_D = (54, 98, 54)
ST_L = (196, 192, 184)      # pedra - identica a do chao e do degrau das casas
ST_M = (152, 148, 140)
ST_D = (104, 100, 96)
SOIL = (140, 100, 64)
SOILD = (104, 72, 44)
PETAL = [(250, 240, 220), (240, 196, 84), (198, 96, 72), (172, 152, 216)]
MIOLO = (250, 232, 150)


class Cv:
    def __init__(self):
        self.a = np.zeros((H, W, 4), np.uint8)

    def set(self, x, y, rgb):
        if 0 <= x < W and 0 <= y < H:
            self.a[y, x] = (rgb[0], rgb[1], rgb[2], 255)

    def img(self):
        return Image.fromarray(self.a, 'RGBA')


def rect(x0, y0, x1, y1):
    m = np.zeros((H, W), bool)
    m[max(0, y0):y1 + 1, max(0, x0):x1 + 1] = True
    return m


def poly(pts):
    m = np.zeros((H, W), bool)
    n = len(pts)
    for y in range(H):
        xs = []
        for i in range(n):
            (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for x in range(int(math.ceil(xs[i])), int(math.floor(xs[i + 1])) + 1):
                if 0 <= x < W:
                    m[y, x] = True
    return m


def ell(cx, cy, rx, ry):
    yy, xx = np.mgrid[0:H, 0:W]
    return (((xx - cx) / max(rx, .01)) ** 2 + ((yy - cy) / max(ry, .01)) ** 2) <= 1.0


def fill(c, m, rgb):
    for y, x in zip(*np.nonzero(m)):
        c.set(int(x), int(y), rgb)


def ink(c, m, sides=True):
    out = np.zeros_like(m)
    for (dy, dx) in ((1, 0), (-1, 0), (0, 1), (0, -1),
                     (1, 1), (1, -1), (-1, 1), (-1, -1)):
        out |= np.roll(np.roll(m, dy, 0), dx, 1)
    e = out & ~m
    if not sides:
        e[:, 0] = False
        e[:, -1] = False
    fill(c, e, BLACK)


def solid(c, m, base, sides=True):
    ink(c, m, sides); fill(c, m, base)


def shift(m, dy, dx):
    return np.roll(np.roll(m, dy, 0), dx, 1)


def edge_in(c, m, rgb, n=1):
    er = m.copy()
    for _ in range(n):
        k = er.copy()
        for (dy, dx) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k &= shift(er, dy, dx)
        er = k
    fill(c, m & ~er, rgb)


# ══ ARVORES ══════════════════════════════════════════════════════════════════
def tree(lobes, trunk_w, trunk_top, pal, lean=0, litter=None):
    """Copa = UNIAO de lobos com UM contorno so. Contornar lobo a lobo faria uma
    teia preta dentro da folhagem; o que separa os lobos por dentro e o arco
    escuro da base de cada um - e assim que copa de livro infantil se lê."""
    L, M, D = pal
    c = Cv()

    # tronco com raiz alargando na base
    tw = trunk_w
    tr = poly([(32 - tw + lean, trunk_top), (32 + tw + lean, trunk_top),
               (32 + tw + 3, BASE + 1), (32 - tw - 3, BASE + 1)])
    solid(c, tr, M if False else WD_M)
    fill(c, tr & rect(32 + 1 + lean, 0, W, H), WD_D)
    fill(c, tr & rect(0, 0, 32 - tw + lean + 1, H), WD_L)

    canopy = np.zeros((H, W), bool)
    for (cx, cy, rx, ry) in lobes:
        canopy |= ell(cx, cy, rx, ry)
    ink(c, canopy)
    fill(c, canopy, M)
    cx0 = sum(l[0] for l in lobes) / len(lobes)
    cy0 = sum(l[1] for l in lobes) / len(lobes)
    fill(c, canopy & ell(cx0 - 7, cy0 - 6, 15, 12), L)
    for (cx, cy, rx, ry) in lobes:            # arco escuro da base de cada lobo
        lo = ell(cx, cy, rx, ry)
        fill(c, canopy & lo & ~shift(lo, -2, 0), D)
    fill(c, canopy & ~shift(canopy, -2, -1) & rect(0, int(cy0), W, H), D)
    if litter:
        for (x, y) in litter:
            m = ell(x, y, 2.8, 1.4)
            ink(c, m); fill(c, m, M)
            fill(c, m & rect(0, y, W, H), D)
    return c


def arvore_verde():
    return tree([(32, 22, 17, 13), (20, 27, 11, 9), (44, 27, 11, 9),
                 (26, 14, 10, 8), (39, 15, 9, 7)],
                4, 30, (FL_L, FL_M, FL_D))


def arvore_outono():
    return tree([(33, 24, 11, 9), (22, 27, 9, 8), (44, 26, 9, 8),
                 (27, 15, 9, 8), (39, 16, 9, 8), (33, 9, 7, 6)],
                4, 32, (AU_L, AU_M, AU_D), lean=1,
                litter=[(16, 59), (48, 60), (24, 60)])


def arvore_pequena():
    return tree([(27, 30, 11, 10), (38, 27, 10, 9), (32, 20, 9, 8)],
                3, 38, (BU_L, BU_M, BU_D))


# ══ ARBUSTOS ═════════════════════════════════════════════════════════════════
def bush(lobes, flores=None):
    c = Cv()
    m = np.zeros((H, W), bool)
    for (cx, cy, rx, ry) in lobes:
        m |= ell(cx, cy, rx, ry)
    ink(c, m); fill(c, m, BU_M)
    cx0 = sum(l[0] for l in lobes) / len(lobes)
    cy0 = sum(l[1] for l in lobes) / len(lobes)
    fill(c, m & ell(cx0 - 5, cy0 - 4, 11, 8), BU_L)
    for (cx, cy, rx, ry) in lobes:
        lo = ell(cx, cy, rx, ry)
        fill(c, m & lo & ~shift(lo, -2, 0), BU_D)
    if flores:
        for (x, y, i) in flores:
            for (dx, dy) in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                c.set(x + dx, y + dy, BLACK)
            for (dx, dy) in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                pass
            c.set(x, y - 1, PETAL[i]); c.set(x - 1, y, PETAL[i])
            c.set(x + 1, y, PETAL[i]); c.set(x, y + 1, PETAL[i])
            c.set(x, y, MIOLO)
    return c


def arbusto_a():
    return bush([(26, 50, 12, 11), (40, 52, 10, 9), (33, 43, 9, 8)])


def arbusto_b():
    return bush([(23, 52, 10, 9), (36, 49, 12, 11), (46, 53, 8, 8)],
                flores=[(20, 47, 0), (33, 41, 2), (44, 48, 3), (28, 45, 1)])


# ══ POSTE ════════════════════════════════════════════════════════════════════
def poste():
    c = Cv()
    foot = poly([(23, BASE + 1), (41, BASE + 1), (38, 54), (26, 54)]) | rect(26, 50, 38, 55)
    solid(c, foot, IR_M)
    fill(c, foot & rect(33, 0, W, H), IR_D)
    fill(c, foot & rect(0, 0, 28, H), IR_L)

    col = rect(30, 24, 33, 51)
    solid(c, col, IR_M)
    fill(c, col & rect(32, 0, 33, H), IR_D)
    fill(c, col & rect(30, 0, 30, H), IR_L)
    for y in (28, 40):                       # aneis decorativos
        r = rect(28, y, 35, y + 1)
        ink(c, r); fill(c, r, IR_L)
        fill(c, rect(28, y + 1, 35, y + 1), IR_D)

    lant = poly([(24, 24), (40, 24), (37, 10), (27, 10)])
    solid(c, lant, IR_M)
    fill(c, lant & rect(34, 0, W, H), IR_D)
    glass = poly([(26, 22), (38, 22), (36, 12), (28, 12)])
    ink(c, glass); fill(c, glass, GLOW2)
    fill(c, glass & ell(32, 18, 3.2, 4.0), GLOW)
    for x in (30, 34):                       # so dois montantes: tres viravam grade
        fill(c, glass & rect(x, 0, x, H), IR_D)
    cap = poly([(23, 10), (41, 10), (36, 5), (28, 5)])
    solid(c, cap, IR_M)
    fill(c, cap & rect(33, 0, W, H), IR_D)
    fin = rect(31, 2, 32, 5)
    ink(c, fin); fill(c, fin, IR_L)
    return c


# ══ BANCO ════════════════════════════════════════════════════════════════════
def banco():
    """Banco de frente. Os montantes do encosto DESCEM ate o chao e viram as
    pernas de tras - e essa continuidade que faz ler como banco. Na 1a versao o
    encosto flutuava atras de um assento claro demais e o conjunto lia como mesa
    com uma tabua encostada."""
    c = Cv()
    for (x0, x1) in ((15, 19), (44, 48)):
        m = rect(x0, 24, x1, BASE)
        solid(c, m, WD_M)
        fill(c, m & rect(x1, 0, x1, H), WD_D)
        fill(c, m & rect(x0, 0, x0, H), WD_L)
    for y0 in (26, 31, 36):                       # tres ripas de encosto
        m = rect(13, y0, 50, y0 + 3)
        solid(c, m, WD_M)
        fill(c, m & rect(0, y0, W, y0), WD_L)
        fill(c, m & rect(0, y0 + 3, W, y0 + 3), WD_D)
    seat = rect(10, 41, 53, 45)
    solid(c, seat, WD_M)
    fill(c, seat & rect(0, 41, W, 41), WD_L)
    fill(c, seat & rect(0, 44, W, 45), WD_D)
    for (x0, x1) in ((17, 21), (42, 46)):         # pernas da frente
        m = poly([(x0, 45), (x1, 45), (x1 + 1, BASE + 1), (x0 - 1, BASE + 1)])
        solid(c, m, WD_M)
        fill(c, m & rect(x1 - 1, 0, W, H), WD_D)
    for (x0, x1) in ((9, 16), (47, 54)):          # bracos
        m = rect(x0, 36, x1, 39)
        solid(c, m, WD_L)
        fill(c, m & rect(0, 39, W, 39), WD_M)
    return c


# ══ CERCA ════════════════════════════════════════════════════════════════════
def cerca(ponta=False):
    """Travessoes de borda a borda SEM tampa preta nas pontas - e o que faz a
    cerca correr sem emenda quando o quadro se repete. `ponta` fecha a fileira."""
    c = Cv()
    posts = [(10, 15), (42, 47)] if not ponta else [(10, 15), (42, 47)]
    for y0 in (36, 47):
        r = rect(0, y0, W - 1, y0 + 4) if not ponta else rect(0, y0, 49, y0 + 4)
        # nunca tampar as pontas do travessao: e a ponta aberta que faz a cerca
        # correr sem emenda quando o quadro se repete
        solid(c, r, WD_M, sides=False)
        fill(c, r & rect(0, y0, W, y0), WD_L)
        fill(c, r & rect(0, y0 + 4, W, y0 + 4), WD_D)
    for (x0, x1) in posts:
        m = rect(x0, 28, x1, BASE) | poly([(x0, 28), (x1, 28), ((x0 + x1) / 2., 23)])
        solid(c, m, WD_M)
        fill(c, m & rect(x1 - 1, 0, x1, H), WD_D)
        fill(c, m & rect(x0, 0, x0, H), WD_L)
    if ponta:
        m = rect(50, 26, 56, BASE) | poly([(50, 26), (56, 26), (53, 20)])
        solid(c, m, WD_M)
        fill(c, m & rect(55, 0, 56, H), WD_D)
        fill(c, m & rect(50, 0, 50, H), WD_L)
    return c


# ══ CANTEIRO ═════════════════════════════════════════════════════════════════
def canteiro():
    c = Cv()
    box = rect(10, 46, 53, BASE)
    solid(c, box, WD_M)
    fill(c, box & rect(0, 46, W, 47), WD_L)
    fill(c, box & rect(0, BASE - 1, W, BASE), WD_D)
    soil = rect(13, 49, 50, 58)
    ink(c, soil); fill(c, soil, SOIL)
    for (x, y) in ((17, 52), (26, 55), (35, 51), (44, 54), (30, 57), (21, 57)):
        c.set(x, y, SOILD); c.set(x + 1, y, SOILD)
    # haste CURTA: com 12 px de talo as flores liam como pirulito no arame.
    for (x, ytop, i) in ((17, 41, 2), (25, 38, 1), (33, 40, 3), (41, 37, 0), (48, 42, 2)):
        for y in range(ytop + 3, 50):
            c.set(x, y, BU_D)
        for (dy, dx) in ((2, -2), (4, 2)):        # folhas no talo
            if ytop + 3 + dy < 49:
                c.set(x + dx, ytop + 3 + dy, BU_M)
                c.set(x + dx - (1 if dx < 0 else -1), ytop + 3 + dy, BU_M)
        for (dx, dy) in ((0, -2), (-1, -1), (1, -1), (-2, 0), (2, 0),
                         (-1, 1), (1, 1), (0, 2), (0, 0)):
            c.set(x + dx, ytop + dy, BLACK)
        for (dx, dy) in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            c.set(x + dx, ytop + dy, PETAL[i])
        c.set(x, ytop, MIOLO)
    return c


# ══ POCO ═════════════════════════════════════════════════════════════════════
def poco():
    c = Cv()
    wall = rect(16, 40, 47, BASE)
    solid(c, wall, ST_M)
    fill(c, wall & rect(0, 40, W, 41), ST_L)
    fill(c, wall & rect(43, 0, 47, H), ST_D)
    for i, y in enumerate(range(43, BASE, 5)):          # fiadas de pedra
        fill(c, wall & rect(0, y, W, y), ST_D)
        off = 0 if i % 2 else 6
        for x in range(17 + off, 47, 12):
            fill(c, wall & rect(x, y + 1, x, y + 4), ST_D)
    rim = rect(13, 36, 50, 41)
    solid(c, rim, ST_L)
    fill(c, rim & rect(0, 40, W, 41), ST_M)
    hole = rect(19, 37, 44, 39)
    ink(c, hole); fill(c, hole, (38, 34, 40))

    for x0 in (17, 43):                                  # postes do telhadinho
        m = rect(x0, 14, x0 + 3, 37)
        solid(c, m, WD_M)
        fill(c, m & rect(x0 + 2, 0, x0 + 3, H), WD_D)
    roof = poly([(8, 15), (32, 3), (56, 15), (56, 18), (8, 18)])
    solid(c, roof, WD_M)
    for y in range(6, 15, 3):
        fill(c, roof & rect(0, y, W, y), WD_D)
    fill(c, roof & rect(0, 15, W, 16), WD_L)

    rope = rect(31, 18, 32, 30)
    fill(c, rope, WD_D)
    bk = poly([(27, 30), (36, 30), (35, 38), (28, 38)])
    ink(c, bk); fill(c, bk, WD_L)
    fill(c, bk & rect(32, 0, W, H), WD_M)
    fill(c, bk & rect(0, 30, W, 31), WD_D)
    return c


# ══ PLACA ════════════════════════════════════════════════════════════════════
def placa():
    c = Cv()
    post = rect(30, 24, 34, BASE)
    solid(c, post, WD_M)
    fill(c, post & rect(33, 0, 34, H), WD_D)
    fill(c, post & rect(30, 0, 30, H), WD_L)
    board = poly([(12, 18), (44, 18), (51, 26), (44, 34), (12, 34)])
    solid(c, board, WD_L)
    fill(c, board & rect(0, 31, W, 34), WD_M)
    edge_in(c, board, WD_M)
    for (y, x0, x1) in ((23, 17, 39), (27, 17, 33)):     # "escrita" abstrata
        fill(c, board & rect(x0, y, x1, y + 1), WD_D)
    nail = ((15, 20), (15, 32), (41, 20), (41, 32))
    for (x, y) in nail:
        c.set(x, y, WD_D)
    st = rect(24, 58, 40, BASE)
    ink(c, st); fill(c, st, ST_M)
    fill(c, st & rect(0, BASE - 1, W, BASE), ST_D)
    return c


# ══════════════════════════════════════════════════════════════════════════════
ITEMS = [('arvore_verde', arvore_verde), ('arvore_outono', arvore_outono),
         ('arvore_pequena', arvore_pequena), ('poste', poste),
         ('banco', banco), ('poco', poco), ('placa', placa), ('canteiro', canteiro),
         ('arbusto_a', arbusto_a), ('arbusto_b', arbusto_b),
         ('cerca', lambda: cerca(False)), ('cerca_ponta', lambda: cerca(True))]


def main():
    os.makedirs(OUT, exist_ok=True)
    sheet = Image.new('RGBA', (W * 4, H * 3), (0, 0, 0, 0))
    imgs = {}
    for i, (name, fn) in enumerate(ITEMS):
        im = fn().img()
        imgs[name] = im
        im.save('%s/%s.png' % (OUT, name))
        sheet.paste(im, ((i % 4) * W, (i // 4) * H), im)
    sheet.save('%s/aderecos.png' % OUT)

    a = np.array(sheet)[..., 3]
    assert set(np.unique(a)) <= {0, 255}, 'alfa intermediario'
    for i, (name, _) in enumerate(ITEMS):
        k = a[(i // 4) * H:(i // 4 + 1) * H, (i % 4) * W:(i % 4 + 1) * W]
        assert not k[0].any() and not k[H - 1].any(), '%s toca topo/base' % name
        if not name.startswith('cerca'):
            assert not k[:, 0].any() and not k[:, -1].any(), '%s toca lateral' % name

    S = 5
    pv = Image.new('RGB', (W * 4 * S, H * 3 * S), (206, 208, 212))
    px = pv.load()
    for y in range(pv.size[1]):
        for x in range(pv.size[0]):
            if ((x // 10) + (y // 10)) % 2:
                px[x, y] = (186, 188, 194)
    big = sheet.resize((W * 4 * S, H * 3 * S), Image.NEAREST)
    pv.paste(big, (0, 0), big)
    pv.save('%s/_preview.png' % OUT)
    print('ok', sheet.size)


main()
