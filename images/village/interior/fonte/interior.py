"""INTERIOR - NOVE MOVEIS E OBJETOS DE CASA, mesma gramatica chapada da vila.

Grade unica de 48x48. Duas regras seguram a escala do conjunto:

  · LINHA DO CHAO em y 44 para tudo que fica no chao (cama, mesa, estante,
    tapete, luminaria, armario, vaso). Empilhando as celulas no mesmo piso, os
    sete assentam sozinhos.
  · ALTURA DE PAREDE fixa para o que e pendurado: janela y 6-32, quadro y 10-26.
    Sao as alturas certas em relacao a uma personagem de ~36 px.

A paleta NAO e nova: sai inteira da vila. Terracota do vaso = telhado da casa
creme; verde da planta = telhado da amarela; azul do armario = parede da azul;
vermelho da colcha = parede da casa de tijolo. E o que faz o dentro e o fora
parecerem a mesma casa.
"""
import numpy as np, math, os
from PIL import Image
from houses import (TRIM, TRIMS, GLASS, GLASSD, CURT, CURTS, STONE, STONED, KNOB)

W = H = 48
FL = 44                       # linha do chao
BLACK = (0, 0, 0)
OUT = '/home/claude/output/assets15'

WOOD = (150, 104, 66)
WOODD = (104, 68, 42)
WOODL = (192, 150, 102)
BLANK = (198, 96, 72)         # colcha - parede da casa de tijolo
BLANKD = (152, 60, 46)
LEAF = (104, 150, 112)        # planta - telhado da casa amarela
LEAFD = (68, 106, 78)
LEAFL = (146, 190, 142)
POT = (200, 98, 66)           # vaso - telhado da casa creme
POTD = (156, 66, 46)
CAB = (146, 168, 190)         # armario - parede da casa azul
CABD = (102, 126, 152)
RUG = (78, 116, 172)          # tapete - porta da casa creme
RUGD = (52, 84, 132)
SKY = (150, 200, 226)
HILL = (120, 168, 118)
SUN = (246, 214, 120)
IRON = (96, 92, 96)
SHADE = (248, 226, 168)       # cupula
SHADED = (214, 176, 108)


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


def disc(cx, cy, rx, ry):
    yy, xx = np.mgrid[0:H, 0:W]
    return (((xx - cx) / max(rx, .01)) ** 2 + ((yy - cy) / max(ry, .01)) ** 2) <= 1.0


def ell(cx, cy, a, b, ang):
    """Elipse INCLINADA. Folha precisa apontar na direcao do talo; disco redondo
    sem rotacao vira brocolis - foi exatamente o que aconteceu na 1a versao."""
    yy, xx = np.mgrid[0:H, 0:W]
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    u = (xx - cx) * ca + (yy - cy) * sa
    v = -(xx - cx) * sa + (yy - cy) * ca
    return (u / a) ** 2 + (v / b) ** 2 <= 1.0


def fill(c, m, rgb):
    for y, x in zip(*np.nonzero(m)):
        c.set(int(x), int(y), rgb)


def ink(c, m):
    out = np.zeros_like(m)
    for (dy, dx) in ((1, 0), (-1, 0), (0, 1), (0, -1),
                     (1, 1), (1, -1), (-1, 1), (-1, -1)):
        out |= np.roll(np.roll(m, dy, 0), dx, 1)
    fill(c, out & ~m, BLACK)


def solid(c, m, base, sh=None, shm=None):
    ink(c, m); fill(c, m, base)
    if sh is not None and shm is not None:
        fill(c, m & shm, sh)


def edge(c, m, rgb, inset=1):
    """Contorno INTERNO de uma forma, em cor - nao em preto. E o que da
    almofadado de porta, moldura de quadro e borda de tapete sem gastar 2 px."""
    er = m.copy()
    for _ in range(inset):
        k = er.copy()
        for (dy, dx) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k &= np.roll(np.roll(er, dy, 0), dx, 1)
        er = k
    fill(c, m & ~er, rgb)


# ══ 1 · CAMA ═════════════════════════════════════════════════════════════════
def cama():
    c = Cv()
    head = rect(5, 17, 9, FL)
    foot = rect(40, 25, 44, FL)
    for m in (head, foot):
        solid(c, m, WOOD)
    fill(c, head & rect(8, 17, 9, FL), WOODD)
    fill(c, foot & rect(43, 25, 44, FL), WOODD)
    fill(c, head & rect(5, 17, 9, 18), WOODL)
    fill(c, foot & rect(40, 25, 44, 26), WOODL)

    solid(c, rect(9, 31, 41, 38), WOODD)                 # estrado
    mat = rect(9, 26, 41, 32)
    solid(c, mat, TRIM, TRIMS, rect(0, 31, W, 32))

    # A colcha comeca DEPOIS do travesseiro e cai pelo lado. Duas dobras largas
    # dizem "tecido"; a primeira versao tinha listra a cada 5 px e lia como
    # colchao de circo.
    blk = rect(21, 25, 41, 32) | rect(21, 32, 40, 37)
    solid(c, blk, BLANK)
    fill(c, blk & rect(21, 25, 24, 37), BLANKD)          # virada da colcha
    fill(c, blk & rect(0, 36, W, 37), BLANKD)
    for x in (30, 36):
        fill(c, blk & rect(x, 26, x, 36), BLANKD)

    pil = rect(11, 21, 20, 27)
    solid(c, pil, TRIM, TRIMS, rect(0, 26, W, 27))
    fill(c, pil & rect(19, 21, 20, 27), TRIMS)
    return c


# ══ 2 · MESA COM DUAS CADEIRAS ═══════════════════════════════════════════════
def chair(c, x0, back_left):
    seat = rect(x0, 30, x0 + 8, 32)
    bx = x0 if back_left else x0 + 7
    back = rect(bx - (0 if back_left else 1), 18, bx + (2 if back_left else 1), 30)
    top = rect(bx - 2, 17, bx + 3, 19) if back_left else rect(bx - 3, 17, bx + 2, 19)
    legs = rect(x0 + 1, 32, x0 + 2, FL) | rect(x0 + 6, 32, x0 + 7, FL)
    m = seat | back | top | legs
    solid(c, m, WOOD)
    fill(c, m & rect(0, 32, W, 32), WOODD)
    fill(c, top, WOODL)
    fill(c, m & rect(0, FL - 1, W, FL), WOODD)


def mesa():
    c = Cv()
    # 2 px de folga em cada lado: encostado na borda o np.roll de `ink` faz o
    # contorno reaparecer do outro lado do quadro.
    chair(c, 4, True)
    chair(c, 36, False)
    top = rect(14, 24, 34, 27)
    legs = rect(17, 27, 19, FL) | rect(29, 27, 31, FL)
    bar = rect(19, 36, 29, 37)
    m = top | legs | bar
    solid(c, m, WOOD)
    fill(c, top & rect(0, 24, W, 24), WOODL)
    fill(c, top & rect(0, 27, W, 27), WOODD)
    fill(c, (legs | bar) & rect(0, 0, W, H) & np.roll(legs | bar, -1, 1), WOODD)
    return c


# ══ 3 · ESTANTE ══════════════════════════════════════════════════════════════
BOOKS = [(3, 12, BLANK), (2, 10, GLASS), (4, 13, LEAF), (2, 9, KNOB),
         (3, 11, RUG), (2, 12, CURT), (3, 10, POT), (2, 11, CABD),
         (4, 12, BLANKD), (2, 9, LEAFL), (3, 13, GLASSD), (2, 10, TRIM)]


def estante():
    c = Cv()
    case = rect(11, 8, 36, FL)
    solid(c, case, WOODD)
    edge(c, case, WOOD)
    shelves = [15, 23, 31, 39]
    for y in shelves:
        fill(c, rect(12, y, 35, y + 1), WOOD)
    k = 0
    for si, sy in enumerate(shelves[:-1]):
        x = 13
        while x < 34:
            w, h, col = BOOKS[k % len(BOOKS)]
            k += 1
            if x + w > 34:
                break
            top = shelves[si + 1] - 1 - min(h, shelves[si + 1] - sy - 3)
            b = rect(x, top, x + w - 1, shelves[si + 1] - 1)
            fill(c, b, col)
            fill(c, rect(x + w - 1, top, x + w - 1, shelves[si + 1] - 1), BLACK)
            fill(c, rect(x, top, x + w - 1, top), BLACK)
            x += w + 1
    # vao de cima: livros DEITADOS e um vasinho. Prateleira de topo vazia lê
    # como estante inacabada.
    for i, (y, wid, col) in enumerate(((13, 11, RUG), (11, 9, BLANK), (9, 10, LEAFD))):
        b = rect(14, y, 14 + wid, y + 1)
        ink(c, b); fill(c, b, col)
    pv = poly([(29, 11), (34, 11), (33, 14), (30, 14)])
    ink(c, pv); fill(c, pv, POT)
    fill(c, pv & rect(32, 0, 34, H), POTD)
    lv = ell(31, 10, 3.6, 1.6, -22) | ell(31, 10, 3.2, 1.5, 28)
    ink(c, lv); fill(c, lv, LEAF)
    fill(c, rect(12, FL - 1, 35, FL), WOODD)
    return c


# ══ 4 · TAPETE ═══════════════════════════════════════════════════════════════
def tapete():
    """OVAL, nao faixa. Visto de lado num platformer o tapete e a unica peca que
    fica no chao e nao encosta em parede nenhuma: se for retangulo reto ele lê
    como degrau ou plataforma. A elipse tira qualquer ambiguidade."""
    c = Cv()
    r = ell(24, 39, 18, 5.4, 0) & rect(0, 0, W, FL)
    tuf = np.zeros((H, W), bool)
    for y in (36, 38, 40, 42):
        xs = np.nonzero(r[y])[0]
        if len(xs):
            tuf |= rect(xs.min() - 3, y, xs.min() - 1, y)
            tuf |= rect(xs.max() + 1, y, xs.max() + 3, y)
    ink(c, r | tuf)
    fill(c, tuf, CURTS)
    fill(c, r, RUG)
    edge(c, r, RUGD, 2)
    edge(c, ell(24, 39, 14.5, 4.0, 0) & rect(0, 0, W, FL), CURT, 1)
    med = ell(24, 39, 6.5, 2.4, 0)
    fill(c, med & r, CURT)
    fill(c, ell(24, 39, 3.0, 1.2, 0) & r, RUGD)
    return c


# ══ 5 · JANELA COM CORTINAS ══════════════════════════════════════════════════
def janela():
    c = Cv()
    rod = rect(7, 5, 40, 6)                        # varao
    solid(c, rod, WOODL, WOOD, rect(0, 6, W, 6))
    for x in (9, 38):
        fill(c, disc(x, 5.5, 1.6, 1.6), IRON)

    fr = rect(11, 9, 36, 33) | rect(9, 32, 38, 34)   # caixilho + peitoril
    solid(c, fr, TRIM, TRIMS, rect(0, 34, W, 34))
    g = rect(14, 12, 33, 30)
    solid(c, g, SKY)
    fill(c, g & rect(0, 26, W, 30), HILL)          # paisagem la fora
    fill(c, disc(28, 17, 2.6, 2.6) & g, SUN)
    mx, my = 23, 21
    fill(c, g & (rect(mx, 12, mx + 1, 30) | rect(14, my, 33, my + 1)), TRIMS)

    # Cortina em COR PROPRIA, nao creme: creme sobre caixilho creme sumia. O
    # rosa da colcha da cama e o que amarra os dois moveis do mesmo comodo.
    for sx, sgn in ((11, 1), (36, -1)):
        d = poly([(sx, 7), (sx + sgn * 6, 7), (sx + sgn * 5, 16),
                  (sx + sgn * 6, 22), (sx + sgn * 4, 30), (sx, 30)])
        solid(c, d, BLANK)
        fill(c, d & rect(sx + sgn * 3, 0, sx + sgn * 6, H), BLANKD)
        fill(c, d & rect(min(sx, sx + sgn * 6), 19, max(sx, sx + sgn * 6), 20), BLANKD)
    return c


# ══ 6 · LUMINARIA ════════════════════════════════════════════════════════════
def luminaria():
    c = Cv()
    base = poly([(17, FL), (31, FL), (29, FL - 3), (19, FL - 3)])
    solid(c, base, WOOD, WOODD, rect(0, FL - 1, W, FL))
    stem = rect(23, 22, 24, FL - 3)
    solid(c, stem, WOODL, WOOD, rect(24, 0, 24, H))
    sh = poly([(16, 21), (32, 21), (29, 9), (19, 9)])
    solid(c, sh, SHADE)
    fill(c, sh & rect(0, 19, W, 21), SHADED)       # aba de baixo, tom solido
    fill(c, sh & rect(27, 0, 32, H), SHADED)
    fill(c, rect(20, 8, 28, 8), WOODD)             # topo
    return c


# ══ 7 · ARMARIO DE COZINHA ═══════════════════════════════════════════════════
def armario():
    """Bancada a 25 px do chao. Contra uma personagem de 45 px isso da altura de
    cintura, que e onde bancada de cozinha fica. Na 1a versao estava a 29 px -
    altura de peito - e o movel lia como armario alto, nao como pia."""
    c = Cv()
    body = rect(9, 22, 38, FL)
    solid(c, body, CAB)
    fill(c, body & rect(34, 22, 38, FL), CABD)
    top = rect(7, 19, 40, 22)
    solid(c, top, STONE, STONED, rect(0, 21, W, 22))
    dr = rect(11, 24, 36, 28)
    ink(c, dr); fill(c, dr, CAB); edge(c, dr, CABD)
    fill(c, rect(21, 25, 26, 26), KNOB)
    for x0 in (11, 24):
        d = rect(x0, 30, x0 + 12, FL - 3)
        ink(c, d); fill(c, d, CAB); edge(c, d, CABD)
        fill(c, rect(x0 + 2, 32, x0 + 10, 32), CABD)
    fill(c, rect(21, 33, 22, 36), KNOB)
    fill(c, rect(25, 33, 26, 36), KNOB)
    fill(c, body & rect(9, FL - 2, 38, FL), CABD)
    return c


# ══ 8 · QUADRO ═══════════════════════════════════════════════════════════════
def quadro():
    c = Cv()
    fr = rect(13, 9, 34, 27)
    solid(c, fr, WOOD)
    edge(c, fr, WOODL)
    mat = rect(15, 11, 32, 25)
    ink(c, mat); fill(c, mat, TRIM)
    pic = rect(17, 13, 30, 23)
    ink(c, pic); fill(c, pic, SKY)
    fill(c, pic & rect(0, 19, W, 23), HILL)
    fill(c, pic & poly([(17, 20), (23, 15), (30, 20), (30, 23), (17, 23)]), LEAFD)
    fill(c, disc(21, 16, 2.0, 2.0) & pic, SUN)
    fill(c, rect(23, 7, 24, 8), IRON)              # preguinho
    return c


# ══ 9 · VASO COM PLANTA ══════════════════════════════════════════════════════
LEAVES = [(-90, 13, 6.0), (-124, 11, 5.2), (-56, 11, 5.2),
          (-152, 8, 4.4), (-28, 8, 4.4)]


def vaso():
    c = Cv()
    ox, oy = 23.5, 33.0
    stems, blades = np.zeros((H, W), bool), []
    for (ang, d, ln) in LEAVES:
        a = math.radians(ang)
        bx, by = ox + math.cos(a) * d, oy + math.sin(a) * d
        for t in np.linspace(0, 1, 30):
            stems |= rect(int(round(ox + (bx - ox) * t)), int(round(oy + (by - oy) * t)),
                          int(round(ox + (bx - ox) * t)), int(round(oy + (by - oy) * t)))
        cx, cy = ox + math.cos(a) * (d + ln * .55), oy + math.sin(a) * (d + ln * .55)
        blades.append((cx, cy, ln, ang))

    body = stems.copy()
    for (cx, cy, ln, ang) in blades:
        body |= ell(cx, cy, ln, ln * .46, ang)
    ink(c, body)
    fill(c, body, LEAF)
    for (cx, cy, ln, ang) in blades:
        e = ell(cx, cy, ln, ln * .46, ang)
        fill(c, e & np.roll(np.roll(e, 2, 0), 1, 1), LEAFD)   # meia-folha na sombra
        fill(c, ell(cx, cy, ln * .74, ln * .12, ang), LEAFD)  # nervura
    fill(c, stems & ~np.roll(stems, 1, 1), LEAFD)

    p = poly([(17, 32), (30, 32), (28, FL), (19, FL)])
    ink(c, p); fill(c, p, POT)
    fill(c, p & rect(25, 0, 30, H), POTD)
    rim = rect(16, 30, 31, 33)
    ink(c, rim); fill(c, rim, POT)
    fill(c, rim & rect(0, 32, W, 33), POTD)
    return c


# ══════════════════════════════════════════════════════════════════════════════
ITEMS = [('cama', cama), ('mesa_cadeiras', mesa), ('estante', estante),
         ('tapete', tapete), ('janela', janela), ('luminaria', luminaria),
         ('armario', armario), ('quadro', quadro), ('vaso_planta', vaso)]


def room(sheet):
    """Maquete, NAO e asset: existe so para provar a escala. Todas as celulas
    sao coladas em y 0 e mesmo assim os moveis assentam no mesmo piso - e o que
    a linha do chao em y 44 garante."""
    RW, RH = 336, 58
    im = Image.new('RGBA', (RW, RH), (238, 224, 202, 255))
    d = np.array(im)
    d[45:, :] = (176, 136, 92, 255)
    d[45, :] = (0, 0, 0, 255)
    im = Image.fromarray(d, 'RGBA')
    idx = {n: i for i, (n, _) in enumerate(ITEMS)}

    def put(name, x):
        i = idx[name]
        cell = sheet.crop(((i % 3) * W, (i // 3) * H, (i % 3 + 1) * W, (i // 3 + 1) * H))
        im.paste(cell, (x, 0), cell)

    for n, x in (('estante', 0), ('armario', 48), ('janela', 96), ('tapete', 128),
                 ('mesa_cadeiras', 140), ('luminaria', 192), ('cama', 232),
                 ('quadro', 258), ('vaso_planta', 288)):
        put(n, x)
    im.resize((RW * 4, RH * 4), Image.NEAREST).save('%s/_maquete.png' % OUT)


def main():
    os.makedirs(OUT, exist_ok=True)
    sheet = Image.new('RGBA', (W * 3, H * 3), (0, 0, 0, 0))
    for i, (name, fn) in enumerate(ITEMS):
        im = fn().img()
        im.save('%s/%s.png' % (OUT, name))
        sheet.paste(im, ((i % 3) * W, (i // 3) * H), im)
    sheet.save('%s/interior.png' % OUT)

    a = np.array(sheet)[..., 3]
    assert set(np.unique(a)) <= {0, 255}, 'alfa intermediario'
    for i in range(len(ITEMS)):
        k = a[(i // 3) * H:(i // 3 + 1) * H, (i % 3) * W:(i % 3 + 1) * W]
        assert not k[0].any() and not k[-1].any() and not k[:, 0].any() \
            and not k[:, -1].any(), 'celula %s encosta na borda' % ITEMS[i][0]

    room(sheet)

    S = 8
    pv = Image.new('RGB', (W * 3 * S, H * 3 * S), (210, 210, 214))
    px = pv.load()
    for y in range(pv.size[1]):
        for x in range(pv.size[0]):
            if ((x // 16) + (y // 16)) % 2:
                px[x, y] = (188, 188, 194)
    big = sheet.resize((W * 3 * S, H * 3 * S), Image.NEAREST)
    pv.paste(big, (0, 0), big)
    pv.save('%s/_preview.png' % OUT)
    print('ok', sheet.size)


main()
