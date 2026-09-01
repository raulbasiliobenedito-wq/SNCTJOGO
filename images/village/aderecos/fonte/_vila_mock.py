"""Maquete de conferencia: chao + casas + aderecos no MESMO terreno.
Existe so para provar que os tres conjuntos assentam sem ajuste."""
from PIL import Image
import os

G = '/home/claude/output/assets16'
C = '/home/claude/output/assets14'
P = '/home/claude/output/assets17'
T, TOP = 32, 160                      # topo solido do terreno
CW, CH = 22, 8


def g(n): return Image.open('%s/%s.png' % (G, n))
def c(n): return Image.open('%s/%s.png' % (C, n))
def p(n): return Image.open('%s/%s.png' % (P, n))


im = Image.new('RGBA', (CW * T, CH * T), (188, 222, 240, 255))

plan = ['grama_meio'] * CW
plan[0] = 'grama_esq'; plan[CW - 1] = 'grama_dir'
plan[4] = 'grama_flores'; plan[9] = 'trans_grama_caminho'
for k in (10, 11, 13, 14):
    plan[k] = 'caminho_meio'
plan[12] = 'caminho_pedras'
plan[15] = 'trans_caminho_grama'
plan[18] = 'grama_pedrinhas'; plan[6] = 'grama_tufo'
for x, n in enumerate(plan):
    t = g(n); im.paste(t, (x * T, TOP), t)
for y in range(TOP + T, CH * T, T):
    for x in range(CW):
        n = ('terra_esq' if x == 0 else 'terra_dir' if x == CW - 1
             else 'terra_pedras' if (x * 3 + y) % 11 == 0 else 'terra_meio')
        t = g(n); im.paste(t, (x * T, y), t)

Y = TOP - 63                          # ultima linha pintada (62) encosta no chao
for (img, x) in ((c('casa_tijolo'), 16), (c('casa_amarela'), 300),
                 (p('arvore_verde'), 96), (p('arbusto_a'), 168),
                 (p('arvore_pequena'), 210), (p('canteiro'), 232),
                 (p('poste'), 268), (p('cerca'), 384), (p('cerca_ponta'), 448),
                 (p('placa'), 366), (p('banco'), 516), (p('poco'), 570),
                 (p('arvore_outono'), 630), (p('arbusto_b'), 130)):
    im.paste(img, (x, Y), img)

im.resize((CW * T * 2, CH * T * 2), Image.NEAREST).convert('RGB').save(
    '%s/_maquete_vila.png' % P)
print('ok')
