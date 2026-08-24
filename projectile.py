"""Projétil do ataque à distância — desbloqueado ao concluir a Fase 1 (ver
Game._advance_level_if_ready) e, por enquanto, o único jeito de causar dano
que vai existir quando os chefes ganharem fases imunes a ataque corpo a
corpo (ver conversa sobre aumentar/dificultar os chefes — isso ainda não
está implementado, só a arma em si). Trajetória reta e simples: nasce na
direção que a Lia estava olhando, anda até acertar um inimigo ou até
percorrer RANGED_PROJECTILE_RANGE (ver game.py), sem gravidade nem curva —
mesmo estilo direto do ataque corpo a corpo, só que à distância.
"""

import pygame


class Projectile:
    RADIUS = 7
    CORE_COLOR = (223, 247, 255)
    GLOW_COLOR = (95, 201, 255)

    def __init__(self, x, y, direction, speed, power, max_range):
        self.x = x
        self.y = y
        self.direction = direction  # 1 = direita, -1 = esquerda
        self.speed = speed
        self.power = power
        self.traveled = 0
        self.max_range = max_range
        self.alive = True

    @property
    def rect(self):
        return pygame.Rect(
            round(self.x) - self.RADIUS, round(self.y) - self.RADIUS,
            self.RADIUS * 2, self.RADIUS * 2,
        )

    def update(self):
        step = self.speed * self.direction
        self.x += step
        self.traveled += abs(step)
        if self.traveled >= self.max_range:
            self.alive = False

    def draw(self, surface, camera_x, camera_y):
        draw_x = round(self.x - camera_x)
        draw_y = round(self.y - camera_y)
        # Sem arte própria ainda (nenhum sprite novo foi desenhado pra isso)
        # — desenhado por código por enquanto, mesmo espírito de placeholder
        # que o brilho de cutscene.py/hint.py usam: dois círculos translúcidos
        # (brilho externo) + um núcleo sólido, na cor de destaque do dash/
        # fôlego no HUD (#5fc9ff), pra já ler visualmente como "habilidade da
        # Lia" mesmo sem sprite. Trocar por um sprite de verdade depois é só
        # substituir este método.
        size = self.RADIUS * 4
        glow = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size // 2, size // 2)
        pygame.draw.circle(glow, (*self.GLOW_COLOR, 80), center, self.RADIUS * 2)
        pygame.draw.circle(glow, (*self.GLOW_COLOR, 150), center, int(self.RADIUS * 1.3))
        surface.blit(glow, (draw_x - size // 2, draw_y - size // 2))
        pygame.draw.circle(surface, self.CORE_COLOR, (draw_x, draw_y), self.RADIUS)
