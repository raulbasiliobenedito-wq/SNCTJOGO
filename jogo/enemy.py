"""Inimigos de chão e reexports das classes específicas."""

from enemy_common import GroundEnemy, PausingGroundEnemy
from enemy_librarian import Librarian
from enemy_slime_king import SlimeKing
from enemy_specimen import Specimen
from enemy_summons import SmallSlime
from enemy_wraith import DarkWraith
from sprites import flipped


class Slime(GroundEnemy):
    """Inimigo que patrulha somente a plataforma onde nasceu."""

    WIDTH = 40
    HEIGHT = 22
    # Pedido do Raul (Fase 1: slime afundando no chão da escola): o quadro
    # desenhado (_load_enemy_sheet recorta e AMPLIA cada frame pra 64x32,
    # sempre preenchendo a altura toda, mesmo já cortando a moldura
    # transparente via get_bounding_rect) é bem mais alto que a hitbox
    # (32px vs HEIGHT=22px) — draw() ancora o desenho em
    # "self.y + 2 - GROUND_LIFT", então com GROUND_LIFT=3 a base do
    # desenho ficava 9px ABAIXO da base de verdade da hitbox (34-3=31 de
    # desenho contra 22 da hitbox). No tileset antigo (rocha) isso não
    # aparecia porque a própria borda/textura do topo do tile escondia a
    # sobra; no chão liso da escola nova ficou visível. GROUND_LIFT=9
    # deixa só ~3px de sobreposição (efeito "pé apoiado", igual à
    # calibragem original), em vez de 9.
    GROUND_LIFT = 9
    HEALTH = 2
    SPEED = 1.15
    PLATFORM_MARGIN = 8
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 20
    DEATH_FRAME_TIME = 4
    DEATH_FRAMES = 9

    def update(self):
        self.animation += 1
        if self.state == self.DYING:
            self._update_death()
        elif self.state == self.DEAD:
            self._update_respawn()
        elif self.state == self.HURT:
            self._update_hurt()
        else:
            self._patrol()

    def _patrol(self):
        left = self.platform.rect.left + self.PLATFORM_MARGIN
        right = self.platform.rect.right - self.WIDTH - self.PLATFORM_MARGIN
        self.x += self.speed * self.direction
        if self.x <= left or self.x >= right:
            self.x = max(left, min(self.x, right))
            self.direction *= -1
        self.y = self.platform.rect.top - self.HEIGHT

    def draw(self, surface, camera_x, camera_y, sprites):
        if self.state == self.DEAD:
            return

        frames = sprites["dead" if self.state == self.DYING else self.state]
        frame = self._animation_frame(frames)
        if self.direction < 0:
            frame = flipped(frame)
        draw_y = self.y - camera_y + (14 if self.state == self.DYING else 2) - self.GROUND_LIFT
        surface.blit(frame, (self.x - 6 - camera_x, draw_y))

    def _animation_frame(self, frames):
        if self.state == self.DYING:
            return frames[min(self.death_frame, len(frames) - 1)]
        return frames[(self.animation // 8) % len(frames)]


class CrystalStag(PausingGroundEnemy):
    """Cervo de cristal: patrulha o chão como o Slime, mas para (repouso) em
    cada ponta antes de virar, e sua morte é uma mineralização de 14 quadros
    em vez do encolhimento simples do slime."""

    # Hitbox um pouco menor que o quadro desenhado (72x61, ver game.py
    # _load_stag_sprites) — WIDTH/HEIGHT maiores que o quadro cru original
    # (40x34) porque o sprite é ampliado 1.8x ao carregar, pra não ficar
    # pequeno demais perto da Lia/slime.
    WIDTH = 52
    HEIGHT = 46
    # Levanta o desenho alguns pixels em relação ao alinhamento "encostado no
    # chão" ingênuo — o tileset novo tem uma leve borda de textura no topo do
    # tile de rocha que fazia os pés parecerem afundados na pedra.
    GROUND_LIFT = 5
    HEALTH = 3
    SPEED = 1.5
    PLATFORM_MARGIN = 6
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 22
    DEATH_FRAME_TIME = 5
    DEATH_FRAMES = 14
    IDLE_DURATION = 55


class PossessedStudent(PausingGroundEnemy):
    """Estudante possuído da Fase 2: mesma patrulha com pausas do cervo de
    cristal (anda até a borda, para um instante, vira), parente visual da
    entidade sombria da Fase 3 (mesmo vocabulário de olhos que acendem antes
    do "ataque" — aqui só cosmético, o dano é por contato como os outros
    inimigos de chão)."""

    WIDTH = 26
    HEIGHT = 44
    GROUND_LIFT = 3
    HEALTH = 2
    SPEED = 1.3
    PLATFORM_MARGIN = 6
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 20
    DEATH_FRAME_TIME = 5
    DEATH_FRAMES = 12
    IDLE_DURATION = 50


class JanitorGuardian(PausingGroundEnemy):
    """Zelador guardião: mini-chefe da Fase 2. Mesma patrulha com pausas do
    estudante, só que maior, mais resistente e mais lento — a leitura de
    "chefe" vem da escala e do peso, não de um ataque à distância novo (ver
    LEIA-ME_fase2.md, seção Notas de Design)."""

    WIDTH = 34
    HEIGHT = 54
    GROUND_LIFT = 4
    HEALTH = 4
    SPEED = 0.9
    PLATFORM_MARGIN = 6
    RESPAWN_TIME = 20 * 60
    HURT_DURATION = 22
    DEATH_FRAME_TIME = 5
    DEATH_FRAMES = 12
    IDLE_DURATION = 60
