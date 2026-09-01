"""VILA - QUATRO FACHADAS DE CASA, vistas de frente.

Mesmo estilo chapado dos sprites de efeito: preenchimento solido, 2 ou 3 tons por
forma, contorno PRETO PURO de 1 px por forma (nao so na silhueta), alfa 0 ou 255.
Sem degrade, sem brilho, sem sombra projetada, sem chao embutido.

Quadro 64x64 por casa. O que faz as quatro lerem como "frente de casa" e sempre a
mesma pilha vertical: chamine > telhado com beiral saliente > testeira clara >
parede > janelas com cortina > porta com bandeira em arco > degrau. So a cor, a
textura da parede e o formato do telhado mudam - e o suficiente para parecerem
casas diferentes da MESMA vila.
"""
import numpy as np, math, os
from PIL import Image

W = H = 64
BLACK = (0, 0, 0)
OUT = '/home/claude/output/assets14'


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


def fill(c, m, rgb):
    for y, x in zip(*np.nonzero(m)):
        c.set(int(x), int(y), rgb)


def ink(c, m):
    """Contorno preto de 1 px em volta de UMA forma. Aplicado forma a forma: e o
    que separa a janela da parede e a parede do telhado sem precisar de sombra."""
    out = np.zeros_like(m)
    for (dy, dx) in ((1, 0), (-1, 0), (0, 1), (0, -1),
                     (1, 1), (1, -1), (-1, 1), (-1, -1)):
        out |= np.roll(np.roll(m, dy, 0), dx, 1)
    fill(c, out & ~m, BLACK)


# ══════════════════════════════════════════════════════════════════════════════
# PALETA - trim, vidro e cortina sao IGUAIS nas quatro. E o fio que amarra a vila:
# so parede, telhado e porta trocam de cor.
# ══════════════════════════════════════════════════════════════════════════════
TRIM = (245, 238, 222)
TRIMS = (198, 188, 166)
GLASS = (172, 208, 226)
GLASSD = (124, 166, 194)
CURT = (250, 240, 220)
CURTS = (214, 192, 162)
STONE = (178, 174, 166)
STONED = (128, 124, 118)
CHIM = (152, 92, 74)
CHIMS = (112, 62, 50)
CAP = (92, 86, 84)
KNOB = (240, 196, 84)

HOUSES = [
    dict(name='casa_tijolo', wall=(198, 96, 72), walls=(150, 60, 46),
         roof=(120, 70, 56), roofs=(88, 48, 38),
         door=(58, 112, 118), doors=(40, 82, 90),
         tex='tijolo', roofstyle='duas_aguas', windows=2, extra=None),
    dict(name='casa_amarela', wall=(244, 208, 114), walls=(206, 160, 74),
         roof=(104, 150, 112), roofs=(72, 110, 82),
         door=(200, 84, 66), doors=(156, 56, 44),
         tex='tabua_h', roofstyle='duas_aguas', windows=2, extra='sotao'),
    dict(name='casa_azul', wall=(146, 168, 190), walls=(102, 126, 152),
         roof=(76, 94, 130), roofs=(54, 68, 100),
         door=(228, 170, 70), doors=(184, 128, 44),
         tex='tabua_v', roofstyle='quatro_aguas', windows=1, extra=None),
    dict(name='casa_creme', wall=(240, 226, 198), walls=(202, 182, 150),
         roof=(200, 98, 66), roofs=(156, 66, 46),
         door=(78, 116, 172), doors=(52, 84, 132),
         tex='liso', roofstyle='duas_aguas', windows=2, extra='toldo'),
]


# ── textura da parede ─────────────────────────────────────────────────────────
def texture(c, wall, kind, sh):
    if kind == 'tijolo':
        for i, y in enumerate(range(30, 62, 4)):
            fill(c, wall & rect(7, y, 56, y), sh)
            off = 0 if i % 2 else 4
            for x in range(7 + off, 57, 8):
                fill(c, wall & rect(x, y + 1, x, y + 3), sh)
    elif kind == 'tabua_h':
        for y in range(31, 62, 5):
            fill(c, wall & rect(7, y, 56, y), sh)
    elif kind == 'tabua_v':
        for x in range(11, 57, 7):
            fill(c, wall & rect(x, 26, x, 61), sh)
    else:                                   # liso: so o embasamento
        fill(c, wall & rect(7, 57, 56, 61), sh)


# ── janela ────────────────────────────────────────────────────────────────────
def window(c, x0, y0, x1, y1, cross=False):
    """Moldura + peitoril numa forma so (um contorno preto, nao dois colados),
    vidro em dois tons chapados, sanefa e dois panos de cortina."""
    frame = rect(x0, y0, x1, y1) | rect(x0 - 1, y1 - 1, x1 + 1, y1)
    ink(c, frame)
    fill(c, frame, TRIM)
    fill(c, rect(x0 - 1, y1, x1 + 1, y1), TRIMS)          # sombra do peitoril

    gx0, gy0, gx1, gy1 = x0 + 2, y0 + 2, x1 - 2, y1 - 3
    g = rect(gx0, gy0, gx1, gy1)
    ink(c, g)
    fill(c, g, GLASS)
    fill(c, g & rect(0, (gy0 + gy1) // 2 + 1, W, gy1), GLASSD)
    if cross:
        fill(c, g & rect((gx0 + gx1) // 2, gy0, (gx0 + gx1) // 2, gy1), TRIMS)

    hgt = gy1 - gy0
    fill(c, g & rect(gx0, gy0, gx1, gy0 + 1), CURT)       # sanefa
    for sx, sgn in ((gx0, 1), (gx1, -1)):
        drape = poly([(sx, gy0), (sx + sgn * 2, gy0),
                      (sx + sgn * 2, gy0 + hgt * .70),
                      (sx + sgn * 1, gy0 + hgt * .90),
                      (sx, gy0 + hgt * .76)])
        fill(c, g & drape, CURT)
        fill(c, g & drape & rect(sx + sgn, gy0, sx + sgn, gy1), CURTS)


# ── porta ────────────────────────────────────────────────────────────────────
def door(c, spec, x0, x1, y1):
    """Porta em arco pleno com bandeira de MEIA-LUA no topo. A primeira versao
    usava um circulo inteiro e a porta lia como espelho oval - a bandeira tem
    que ser meio disco, apoiado na travessa, senao nao lê como vidro da porta."""
    cx, r = (x0 + x1) / 2.0, (x1 - x0) / 2.0
    ay = 34 + int(round(r))                     # centro do arco / linha da travessa
    d = rect(x0, ay, x1, y1) | disc(cx, ay, r + .5, r + .5)
    ink(c, d)
    fill(c, d, spec['door'])

    fan = disc(cx, ay, r - 1.5, r - 1.5) & rect(x0, 0, x1, ay)
    ink(c, fan)
    fill(c, fan, GLASS)
    fill(c, fan & rect(0, ay - 1, W, ay), GLASSD)

    # UM almofadado vazado, nao dois cheios: em porta de 10 px dois paineis
    # solidos viram duas listras e a porta perde a leitura de madeira.
    p0, p1, p2, p3 = x0 + 2, ay + 3, x1 - 3, y1 - 4
    for m in (rect(p0, p1, p2, p1), rect(p0, p3, p2, p3),
              rect(p0, p1, p0, p3), rect(p2, p1, p2, p3)):
        fill(c, m & d, spec['doors'])
    fill(c, d & rect(x0, y1 - 2, x1, y1), spec['doors'])
    fill(c, rect(x1 - 1, ay + 7, x1 - 1, ay + 8), KNOB)


# ══════════════════════════════════════════════════════════════════════════════
def build(spec):
    c = Cv()

    # 1 · CHAMINE - desenhada antes do telhado, que come a base dela
    ch = rect(45, 8, 51, 19)
    ink(c, ch); fill(c, ch, CHIM); fill(c, ch & rect(49, 8, 51, 19), CHIMS)
    cap = rect(43, 8, 53, 10)
    ink(c, cap); fill(c, cap, CAP)

    # 2 · PAREDE
    wall = rect(7, 26, 56, 61)
    ink(c, wall); fill(c, wall, spec['wall'])
    texture(c, wall, spec['tex'], spec['walls'])
    fill(c, wall & rect(52, 26, 56, 61), spec['walls'])    # lateral na sombra
    fill(c, wall & rect(7, 28, 56, 30), spec['walls'])     # sombra do beiral

    # 3 · TELHADO - beiral saliente dos dois lados. E o beiral que faz a casa
    #     parecer casa e nao caixa: sem ele a silhueta vira um retangulo.
    if spec['roofstyle'] == 'duas_aguas':
        body = poly([(2, 25), (31.5, 5), (61, 25)])
    else:
        body = poly([(2, 25), (24, 8), (39, 8), (61, 25)])
    fascia = rect(2, 25, 61, 27)
    roof = body | fascia
    ink(c, roof)
    fill(c, body, spec['roof'])
    for y in range(9, 25, 4):                              # fiadas de telha
        fill(c, body & rect(0, y, W, y), spec['roofs'])
    fill(c, fascia, TRIM)
    fill(c, fascia & rect(0, 27, W, 27), TRIMS)

    # 4 · JANELAS
    if spec['windows'] == 2:
        window(c, 11, 33, 22, 44)
        window(c, 41, 33, 52, 44)
        dx0, dx1 = 27, 36
    else:
        window(c, 10, 33, 27, 44, cross=True)              # uma janela larga
        dx0, dx1 = 36, 45

    # 5 · EXTRAS
    if spec['extra'] == 'sotao':                           # oculo no frontao
        o = disc(31.5, 16.5, 4.2, 4.2)
        ink(c, o); fill(c, o, TRIM)
        gi = disc(31.5, 16.5, 2.6, 2.6)
        ink(c, gi); fill(c, gi, GLASS)
        fill(c, gi & rect(0, 17, W, 64), GLASSD)

    # 6 · PORTA + DEGRAU
    step = rect(dx0 - 4, 58, dx1 + 4, 61)
    ink(c, step); fill(c, step, STONE)
    fill(c, step & rect(0, 60, W, 61), STONED)
    door(c, spec, dx0, dx1, 57)
    if spec['extra'] == 'toldo':                           # toldo sobre a porta
        t = poly([(dx0 - 4, 34), (dx1 + 4, 34), (dx1 + 1, 30), (dx0 - 1, 30)])
        ink(c, t); fill(c, t, spec['roof'])
        for x in range(dx0 - 3, dx1 + 4, 4):
            fill(c, t & rect(x, 30, x + 1, 34), TRIM)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    sheet = Image.new('RGBA', (W * 4, H), (0, 0, 0, 0))
    for i, spec in enumerate(HOUSES):
        im = build(spec).img()
        im.save('%s/%s.png' % (OUT, spec['name']))
        sheet.paste(im, (i * W, 0), im)
    sheet.save('%s/vila_casas.png' % OUT)

    # pre-visualizacao: xadrez para provar que o fundo e transparente de verdade
    S = 6
    pv = Image.new('RGB', (W * 4 * S, H * S), (210, 210, 214))
    px = pv.load()
    for y in range(pv.size[1]):
        for x in range(pv.size[0]):
            if ((x // 12) + (y // 12)) % 2:
                px[x, y] = (188, 188, 194)
    big = sheet.resize((W * 4 * S, H * S), Image.NEAREST)
    pv.paste(big, (0, 0), big)
    pv.save('%s/_preview.png' % OUT)
    print('ok', sheet.size)


if __name__ == '__main__':
    main()
