"""VILA - AS MESMAS QUATRO CASAS VISTAS POR TRAS.

Reaproveita as primitivas e a paleta de `houses.py`, entao os fundos sao
literalmente as mesmas casas: mesma linha de telhado (y 5-27), mesma testeira
creme, mesma parede (y 26-61), mesma base em y 62. Trocando a folha da frente
pela de tras a casa nao muda de tamanho nem de cor.

O QUE FAZ LER COMO "FUNDO" e nao como "frente sem porta":

  1. ASSIMETRIA. Fachada e simetrica e formal; fundo e irregular. Cada casa tem a
     janela num lugar diferente, fora do centro. E o sinal mais forte de todos.
  2. CHAMINE DO OUTRO LADO. Na frente ela esta a direita; aqui, a esquerda.
     A silhueta espelha e o olho registra "e a mesma casa, virada".
  3. CALHA descendo pelo canto ate o chao - peca que so existe no fundo.
  4. JANELA DE SERVICO: menor, sem cortina, com caixilho em cruz. Cortina e
     coisa de fachada; vidro dividido lê como area de servico.
  5. TRAMBOLHOS ENCOSTADOS: lenha, varal, barril, escada. Ninguem encosta lenha
     na frente da casa - so no fundo.
"""
import numpy as np, math, os
from PIL import Image
from houses import (Cv, rect, poly, disc, fill, ink, texture, HOUSES,
                    TRIM, TRIMS, GLASS, GLASSD, CURT, CURTS, STONE, STONED,
                    CHIM, CHIMS, CAP, W, H)

OUT = '/home/claude/output/assets14'
PIPE = (196, 190, 178)
PIPES = (150, 144, 132)
WOOD = (128, 88, 56)
WOODD = (92, 60, 38)
WOODL = (176, 136, 92)
ROPE = (86, 74, 62)
IRON = (96, 92, 96)


def seg(x0, y0, x1, y1, w):
    """Faixa de espessura w ao longo de um segmento - a espessura sai na
    PERPENDICULAR, nao em x, senao um segmento quase horizontal vira um risco."""
    yy, xx = np.mgrid[0:H, 0:W]
    dx, dy = x1 - x0, y1 - y0
    L2 = max(dx * dx + dy * dy, 1e-6)
    t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / L2, 0, 1)
    d = np.hypot(xx - (x0 + t * dx), yy - (y0 + t * dy))
    return d <= w / 2.0


# ── janela de servico: sem cortina, caixilho em cruz ─────────────────────────
def window_back(c, x0, y0, x1, y1):
    frame = rect(x0, y0, x1, y1) | rect(x0 - 1, y1 - 1, x1 + 1, y1)
    ink(c, frame); fill(c, frame, TRIM)
    fill(c, rect(x0 - 1, y1, x1 + 1, y1), TRIMS)
    gx0, gy0, gx1, gy1 = x0 + 2, y0 + 2, x1 - 2, y1 - 3
    g = rect(gx0, gy0, gx1, gy1)
    ink(c, g); fill(c, g, GLASS)
    fill(c, g & rect(0, (gy0 + gy1) // 2 + 1, W, gy1), GLASSD)
    mx, my = (gx0 + gx1) // 2, (gy0 + gy1) // 2
    fill(c, g & (rect(mx, gy0, mx, gy1) | rect(gx0, my, gx1, my)), TRIMS)


# ── calha ────────────────────────────────────────────────────────────────────
def downpipe(c, x, top=28, bot=61):
    p = rect(x, top, x + 1, bot - 3) | rect(x, bot - 3, x + 3, bot - 2)
    ink(c, p); fill(c, p, PIPE); fill(c, rect(x + 1, top, x + 1, bot - 2), PIPES)
    br = rect(x - 1, top + 6, x + 2, top + 7) | rect(x - 1, bot - 14, x + 2, bot - 13)
    fill(c, br, PIPES)


# ── grelha de ventilacao no frontao ──────────────────────────────────────────
def vent(c, cx, cy):
    v = rect(cx - 4, cy - 3, cx + 4, cy + 3)
    ink(c, v); fill(c, v, TRIM)
    for y in (cy - 2, cy, cy + 2):
        fill(c, rect(cx - 3, y, cx + 3, y), TRIMS)


# ── pilha de lenha ───────────────────────────────────────────────────────────
def woodpile(c, x0, ybase):
    """Uma forma so, com contorno unico. Se cada tora levasse contorno proprio,
    a 4 px de diametro o preto comeria a tora inteira."""
    logs, m = [], np.zeros((H, W), bool)
    for row, (n, off) in enumerate(((5, 0), (4, 2), (2, 4))):
        for i in range(n):
            cx, cy = x0 + off + i * 4.4, ybase - 2 - row * 4.2
            logs.append((cx, cy))
            m |= disc(cx, cy, 2.4, 2.4)
    ink(c, m); fill(c, m, WOODD)
    for (cx, cy) in logs:
        fill(c, disc(cx, cy, 1.7, 1.7), WOOD)
        fill(c, disc(cx, cy, .8, .8), WOODL)


# ── varal ────────────────────────────────────────────────────────────────────
def clothesline(c, x0, x1, y, spec):
    sag = 3.0
    pts = [(x0 + (x1 - x0) * t / 8.0,
            y + sag * math.sin(math.pi * t / 8.0)) for t in range(9)]
    for i in range(8):
        fill(c, seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 1.2), ROPE)
    for (px, py) in ((x0, y), (x1, y)):
        fill(c, rect(int(px) - 1, int(py) - 1, int(px) + 1, int(py) + 1), IRON)

    def hang(cx, top, wid, hgt, col, cold, sleeve=False):
        cx = int(cx)
        m = rect(cx - wid // 2, top, cx + wid // 2, top + hgt)
        if sleeve:
            m |= rect(cx - wid // 2 - 2, top + 1, cx + wid // 2 + 2, top + 3)
        ink(c, m); fill(c, m, col)
        fill(c, m & rect(0, top + hgt - 2, W, top + hgt), cold)
        fill(c, rect(cx, top - 1, cx, top - 1), ROPE)

    a = int(x0 + (x1 - x0) * .22)
    b = int(x0 + (x1 - x0) * .52)
    d = int(x0 + (x1 - x0) * .80)
    hang(a, y + 3, 7, 8, CURT, CURTS, sleeve=True)
    hang(b, y + 4, 9, 11, spec['door'], spec['doors'])
    hang(d, y + 3, 5, 6, GLASS, GLASSD)


# ── barril e caixote ─────────────────────────────────────────────────────────
def barrel(c, cx, ybase):
    b = poly([(cx - 4, ybase - 11), (cx + 4, ybase - 11), (cx + 5, ybase - 8),
              (cx + 5, ybase - 3), (cx + 4, ybase), (cx - 4, ybase),
              (cx - 5, ybase - 3), (cx - 5, ybase - 8)])
    ink(c, b); fill(c, b, WOOD)
    fill(c, b & (rect(0, ybase - 10, W, ybase - 10) | rect(0, ybase - 6, W, ybase - 6)
                 | rect(0, ybase - 1, W, ybase - 1)), IRON)
    fill(c, b & rect(cx + 2, 0, cx + 5, H), WOODD)


def crate(c, x0, ybase, s=9):
    k = rect(x0, ybase - s, x0 + s, ybase)
    ink(c, k); fill(c, k, WOODL)
    for i in range(s + 1):
        for (xx, yy) in ((x0 + i, ybase - s + i), (x0 + s - i, ybase - s + i)):
            fill(c, rect(xx, yy, xx, yy) & k, WOODD)
    fill(c, k & (rect(x0, ybase - s, x0 + s, ybase - s) | rect(x0, ybase, x0 + s, ybase)), WOOD)


# ── escada encostada ─────────────────────────────────────────────────────────
def ladder(c, bx, by, tx, ty, wid=10):
    """Montada linha a linha, nao por segmento com espessura. Duas razoes:
    o degrau sai perfeitamente horizontal (diagonal fina vira serrilha ilegivel a
    essa escala) e o VAO fica com 4x3 px - grande o bastante para sobreviver ao
    contorno preto de 1 px. Com vao menor que isso o preto fecha o buraco e a
    escada vira um tronco."""
    m = np.zeros((H, W), bool)

    def xl(y):
        t = (by - y) / float(by - ty)
        return int(round(bx + (tx - bx) * t))

    for y in range(ty, by + 1):
        m[y, xl(y):xl(y) + 2] = True
        m[y, xl(y) + wid - 2:xl(y) + wid] = True
    for y in range(ty + 3, by, 6):
        m[y, xl(y):xl(y) + wid] = True
    ink(c, m); fill(c, m, WOODL)
    r = np.zeros((H, W), bool)
    for y in range(ty, by + 1):
        r[y, xl(y) + wid - 2:xl(y) + wid] = True
    fill(c, r, WOOD)


# ══════════════════════════════════════════════════════════════════════════════
BACKS = [
    dict(win=(36, 33, 47, 44), pipe=8, vent=True, prop='lenha'),
    dict(win=(10, 32, 21, 43), pipe=7, vent=False, prop='varal'),
    dict(win=(23, 34, 34, 45), pipe=8, vent=False, prop='barril'),
    dict(win=(37, 32, 48, 43), pipe=53, vent=True, prop='escada'),
]


def build_back(spec, cfg):
    c = Cv()

    # 1 · CHAMINE - do lado ESQUERDO, espelhando a da frente
    ch = rect(13, 8, 19, 19)
    ink(c, ch); fill(c, ch, CHIM); fill(c, ch & rect(17, 8, 19, 19), CHIMS)
    cap = rect(11, 8, 21, 10)
    ink(c, cap); fill(c, cap, CAP)

    # 2 · PAREDE
    wall = rect(7, 26, 56, 61)
    ink(c, wall); fill(c, wall, spec['wall'])
    texture(c, wall, spec['tex'], spec['walls'])
    fill(c, wall & rect(52, 26, 56, 61), spec['walls'])
    fill(c, wall & rect(7, 28, 56, 30), spec['walls'])

    # 3 · TELHADO - mesma geometria da frente
    if spec['roofstyle'] == 'duas_aguas':
        body = poly([(2, 25), (31.5, 5), (61, 25)])
    else:
        body = poly([(2, 25), (24, 8), (39, 8), (61, 25)])
    fascia = rect(2, 25, 61, 27)
    ink(c, body | fascia)
    fill(c, body, spec['roof'])
    for y in range(9, 25, 4):
        fill(c, body & rect(0, y, W, y), spec['roofs'])
    fill(c, fascia, TRIM)
    fill(c, fascia & rect(0, 27, W, 27), TRIMS)

    if cfg['vent']:
        vent(c, 32, 16)

    # 4 · CALHA + JANELA DE SERVICO
    downpipe(c, cfg['pipe'])
    window_back(c, *cfg['win'])

    # 5 · TRAMBOLHO DO QUINTAL
    p = cfg['prop']
    if p == 'lenha':
        woodpile(c, 12, 61)
    elif p == 'varal':
        clothesline(c, 26, 52, 31, spec)
    elif p == 'barril':
        barrel(c, 41, 61)
        crate(c, 47, 61, 8)
    elif p == 'escada':
        ladder(c, 12, 61, 22, 29)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    sheet = Image.new('RGBA', (W * 4, H), (0, 0, 0, 0))
    for i, (spec, cfg) in enumerate(zip(HOUSES, BACKS)):
        im = build_back(spec, cfg).img()
        im.save('%s/%s_fundo.png' % (OUT, spec['name']))
        sheet.paste(im, (i * W, 0), im)
    sheet.save('%s/vila_casas_fundo.png' % OUT)

    a = np.array(sheet)[..., 3]
    assert not a[0].any() and not a[-1].any(), 'sprite encostando na borda do quadro'
    assert set(np.unique(a)) <= {0, 255}, 'alfa intermediario'


    S = 6
    pv = Image.new('RGB', (W * 4 * S, H * S), (210, 210, 214))
    px = pv.load()
    for y in range(pv.size[1]):
        for x in range(pv.size[0]):
            if ((x // 12) + (y // 12)) % 2:
                px[x, y] = (188, 188, 194)
    big = sheet.resize((W * 4 * S, H * S), Image.NEAREST)
    pv.paste(big, (0, 0), big)
    pv.save('%s/_preview_fundo.png' % OUT)
    print('ok', sheet.size)


main()
