"""Ataques da Lia e resolução do combate com os inimigos.

Game mantém a ordem de atualização, vidas, respawn e efeitos de tela.
CombatSystem concentra os temporizadores de ataque e a lista de projéteis.
A referência à sessão permite comunicar dano, drops e efeitos sem importar
Game em tempo de execução nem alterar os pontos em que eles acontecem.
"""

from typing import TYPE_CHECKING

import pygame

import audio
from projectile import Projectile
from settings import PLAYER_HEIGHT, PLAYER_HITBOX_WIDTH
from game_data import (
    ATTACK_COOLDOWN,
    ATTACK_DURATION,
    ATTACK_FRAME_TICKS,
    BOSS_CONTACT_DAMAGE,
    BOSS_NAMES,
    COMBO_FINISHER_POWER,
    COMBO_HIT_COUNT,
    DASH_ATTACK_POWER,
    DASH_ATTACK_REACH,
    HIT_STOP_FRAMES,
    MOB_CONTACT_DAMAGE,
    PARRY_DAMAGE,
    PARRY_HITSTOP_FRAMES,
    PARRY_INVULN_FRAMES,
    PARRY_SHAKE_DURATION,
    PARRY_SHAKE_MAGNITUDE,
    RANGED_ATTACK_COOLDOWN,
    RANGED_ATTACK_POWER,
    RANGED_PROJECTILE_RANGE,
    RANGED_PROJECTILE_SPEED,
    STANDARD_ATTACK_POWER,
    STANDARD_ATTACK_REACH,
)

if TYPE_CHECKING:
    from game import Game


class CombatSystem:
    """Estado transitório do combate pertencente a uma única sessão."""

    # Quadros relativos dentro da sequência 53-68 em que o punho está
    # estendido de verdade. Cada um abre uma janela curta de colisão.
    ATTACK_IMPACT_FRAMES = (4, 9, 11, 14)

    def __init__(self, game: "Game"):
        self.game = game
        self.reset()

    def reset(self):
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_power = STANDARD_ATTACK_POWER
        self.combo_count = 0
        self.attack_started_dashing = False
        self.attack_facing_right = True
        self._sounded_hit = None
        self._hit_targets = [set() for _ in range(COMBO_HIT_COUNT)]
        self.ranged_cooldown = 0
        self.projectiles = []

    def update_attack(self, attack_pressed):
        if self.attack_timer > 0:
            self.attack_timer -= 1
            if self.attack_timer == 0:
                self.attack_cooldown = ATTACK_COOLDOWN
                self.attack_power = STANDARD_ATTACK_POWER
                self.combo_count = 0
                self.attack_started_dashing = False
            else:
                self._update_attack_phase()
            return

        self.attack_cooldown = max(0, self.attack_cooldown - 1)
        if (
            attack_pressed
            and self.attack_cooldown == 0
            and self.game.player.hurt_timer <= 0
        ):
            self.attack_timer = ATTACK_DURATION
            self.attack_started_dashing = self.game.player.dashing
            self.attack_facing_right = self.game.player.facing_right
            self._sounded_hit = None
            self._hit_targets = [set() for _ in range(COMBO_HIT_COUNT)]
            self._update_attack_phase()

    @property
    def attacking(self):
        return self.attack_timer > 0

    def cancel_attack(self):
        """Hurt/death interrompem o combo, mas preservam a recarga."""
        if self.attack_timer > 0:
            self.attack_timer = 0
            self.attack_cooldown = max(self.attack_cooldown, ATTACK_COOLDOWN)
        self.attack_power = STANDARD_ATTACK_POWER
        self.combo_count = 0
        self.attack_started_dashing = False
        self._sounded_hit = None

    def attack_animation_index(self):
        if not self.attack_timer:
            return None
        elapsed = ATTACK_DURATION - self.attack_timer
        return min(len(self.game.player.ATTACK_FRAMES) - 1, elapsed // ATTACK_FRAME_TICKS)

    def attack_hit_index(self):
        animation_index = self.attack_animation_index()
        if animation_index is None:
            return None
        try:
            return self.ATTACK_IMPACT_FRAMES.index(animation_index)
        except ValueError:
            return None

    def _update_attack_phase(self):
        animation_index = self.attack_animation_index()
        if animation_index is None:
            return
        self.combo_count = min(COMBO_HIT_COUNT, animation_index // 4 + 1)
        hit_index = self.attack_hit_index()
        if hit_index is None:
            self.attack_power = STANDARD_ATTACK_POWER
            return
        if hit_index == COMBO_HIT_COUNT - 1:
            self.attack_power = COMBO_FINISHER_POWER
        elif hit_index == 0 and self.attack_started_dashing:
            self.attack_power = DASH_ATTACK_POWER
        else:
            self.attack_power = STANDARD_ATTACK_POWER
        if self._sounded_hit != hit_index:
            audio.play_sfx(f"punch.punch_{hit_index + 1}")
            self._sounded_hit = hit_index

    def apply_attack_frame(self):
        """Sobrepõe o frame calculado por Player.animate() enquanto o golpe
        tá ativo — combo_count já reflete o hit certo desse swing (definido
        em update_attack, antes desta chamada em Game._update_playing).
        Fora daí Player.animate() decide sozinho (parado/andando/pulando)."""
        if not self.attack_timer:
            return
        animation_index = self.attack_animation_index()
        if animation_index is not None:
            self.game.player.frame = self.game.player.ATTACK_FRAMES[animation_index]

    def update_ranged_attack(self, ranged_pressed):
        self.ranged_cooldown = max(0, self.ranged_cooldown - 1)
        if not (
            ranged_pressed
            and self.game.ranged_unlocked
            and self.ranged_cooldown == 0
            and not self.attacking
            and self.game.player.hurt_timer <= 0
        ):
            return
        self.ranged_cooldown = RANGED_ATTACK_COOLDOWN
        self.game.player.start_ranged_attack()
        audio.play_sfx("projectile_sound")
        direction = 1 if self.game.player.facing_right else -1
        # Nasce um pouco à frente da hitbox, na altura do peito — assim o
        # projétil não colide "dentro" da própria Lia no quadro em que nasce.
        origin_x = self.game.player.rect.centerx + direction * (PLAYER_HITBOX_WIDTH // 2 + 8)
        origin_y = self.game.player.rect.centery - 4
        self.projectiles.append(
            Projectile(
                origin_x, origin_y, direction,
                RANGED_PROJECTILE_SPEED, RANGED_ATTACK_POWER, RANGED_PROJECTILE_RANGE,
            )
        )

    def update_projectiles(self):
        """Move cada projétil e confere colisão contra os mesmos inimigos que
        check_enemies já usa pro ataque corpo a corpo (mesma interface
        take_hit/alive, incluindo chefes) — um acerto consome o projétil."""
        for projectile in self.projectiles:
            if not projectile.alive:
                continue
            projectile.update()
            if not projectile.alive:
                continue
            for enemy in self.game.level.enemies:
                if not enemy.alive:
                    continue
                if not projectile.rect.colliderect(enemy.rect):
                    continue
                if enemy.take_hit(projectile.power):
                    if not getattr(enemy, "uses_custom_hit_vfx", False):
                        self.game.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                    if not enemy.alive:
                        self.game.items.on_enemy_defeated(enemy)
                projectile.alive = False
                break
        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]

    def stomp_enemy_if_possible(self, player, previous_bottom):
        for enemy in self.game.level.enemies:
            # Chefes (BOSS_NAMES) ficam de fora do pulo-que-mata:
            # ficam de fora do pulo-que-mata: pousar na cabeça deles não pode
            # ser um jeito de matar em um golpe só uma luta pensada pra durar
            # vários acertos — pisar neles agora não faz nada de especial,
            # cai no contato normal (dano) tratado por check_enemies.
            if type(enemy).__name__ in BOSS_NAMES:
                continue
            if (
                enemy.alive
                and player.vy > 0
                and player.rect.colliderect(enemy.rect)
                and previous_bottom <= enemy.rect.top + 12
            ):
                enemy.stomp()
                self.game.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                self.game.items.on_enemy_defeated(enemy)
                player.y = enemy.rect.top - PLAYER_HEIGHT
                player.vy = -10.5
                return True
        return False

    def check_enemy_attack_hazards(self, player):
        """Feixe do jato do espécime, onda do Silêncio e tomos do Errata: os
        três alcançam além da hitbox do próprio inimigo (ver
        <Boss>.active_hazards nos módulos de cada chefe), então não bastam o teste de
        colisão corpo-a-corpo normal de check_enemies."""
        if self.game.invuln_timer > 0:
            return False
        for enemy in self.game.level.enemies:
            if not enemy.alive:
                continue
            get_hazards = getattr(enemy, "active_hazards", None)
            if not get_hazards:
                continue
            for hazard in get_hazards():
                if player.rect.colliderect(hazard):
                    # active_hazards só existe nos chefes (jato do Espécime,
                    # onda do Rei Slime, tomos/lâminas do Bibliotecário) —
                    # sempre dano de chefe, não precisa checar BOSS_DROP_TABLE.
                    self.game.take_damage(BOSS_CONTACT_DAMAGE)
                    return True
        return False

    def check_parries(self, player):
        """Parry (pedido do Raul): só hazards que "voam" — pedras/meteoros
        do Dragão ainda caindo, tomos mergulhando e lâminas do Bibliotecário,
        jato do Espécime (ver <Boss>.parryable_hazards no módulo do chefe) — nunca
        ondas no chão nem investidas corpo a corpo, essas classes nem
        definem o método, então getattr cai em None e passa reto. Sem botão
        novo: é o mesmo attack_box do ataque corpo a corpo normal
        (attack_box), só que testado ANTES de check_enemy_attack_hazards
        pra um parry bem-sucedido não também respawnar a Lia no mesmo
        quadro. Acerto certo: cancel() destrói o hazard específico e o dano
        volta pro chefe que o lançou via take_hit — mesma interface que o
        ataque à distância já usa pra furar melee_vulnerable."""
        attack_box = self.attack_box()
        if not attack_box:
            return False
        for enemy in self.game.level.enemies:
            if not enemy.alive:
                continue
            get_pairs = getattr(enemy, "parryable_hazards", None)
            if not get_pairs:
                continue
            for rect, cancel in get_pairs():
                if not attack_box.colliderect(rect):
                    continue
                cancel()
                self.game.vfx.spawn("parry_flash", rect.centerx, rect.centery)
                # 1s de invencibilidade (pedido do Raul) pra sobreviver ao
                # resto de um ataque com vários hits (ex.: as 5 lâminas do
                # Bibliotecário) depois de aparar só o primeiro — max() pra
                # nunca ENCURTAR um invuln maior já rolando (ex.: acabou de
                # respawnar). Hit-stop + shake dão o "peso" do acerto.
                self.game.invuln_timer = max(self.game.invuln_timer, PARRY_INVULN_FRAMES)
                self.game.hitstop_timer = PARRY_HITSTOP_FRAMES
                self.game._trigger_shake(PARRY_SHAKE_DURATION, PARRY_SHAKE_MAGNITUDE)
                audio.play_sfx("parry_sound")
                if enemy.take_hit(PARRY_DAMAGE) and not enemy.alive:
                    self.game.items.on_enemy_defeated(enemy)
                return True
        return False

    def check_enemies(self):
        """Verifica ataque, ataque reforçado durante dash e contato com slimes.
        `melee_vulnerable` (Librarian/Specimen em seus módulos — os
        inimigos comuns e o Rei Slime não definem isso, então getattr cai em
        True) deixa um chefe imune a corpo a corpo em certas fases (ex.:
        voando, escudo levantado, dentro do casulo); nesses momentos,
        acertar o corpo dele com a espada não causa dano — só o ataque à
        distância funciona — mas ainda dói tocar nele."""
        attack_box = self.attack_box()
        # O dano de contato era resolvido com um `return` no meio do laço:
        # ao encostar num inimigo, todos os que vinham DEPOIS dele na lista
        # não eram testados pro golpe de espada naquele quadro — com vários
        # mobs juntos, acertar quem estava atrás virava loteria. Agora o
        # laço vai até o fim e o contato é aplicado uma única vez no final
        # (o pior contato do quadro; ver `contact_damage`).
        contact_damage = 0
        for enemy in self.game.level.enemies:
            if not enemy.alive:
                continue
            is_boss = type(enemy).__name__ in BOSS_NAMES
            melee_hit = (
                attack_box
                and attack_box.colliderect(enemy.rect)
                and getattr(enemy, "melee_vulnerable", True)
            )
            if melee_hit:
                hit_index = self.attack_hit_index()
                target_key = id(enemy)
                already_hit = (
                    hit_index is None or target_key in self._hit_targets[hit_index]
                )
                if already_hit:
                    continue
                self._hit_targets[hit_index].add(target_key)
                if enemy.take_hit(self.attack_power, allow_hurt=True):
                    self.game.hitstop_timer = max(self.game.hitstop_timer, HIT_STOP_FRAMES)
                    if not getattr(enemy, "uses_custom_hit_vfx", False):
                        self.game.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                    if not enemy.alive:
                        self.game.items.on_enemy_defeated(enemy)
                    else:
                        audio.play_sfx("boss_hit_sound" if is_boss else "enemy_hit_sound")
            elif self.game.player.rect.colliderect(enemy.rect):
                damage = BOSS_CONTACT_DAMAGE if is_boss else MOB_CONTACT_DAMAGE
                contact_damage = max(contact_damage, damage)
        if contact_damage and self.game.invuln_timer <= 0:
            self.game.take_damage(contact_damage)

    def attack_box(self):
        hit_index = self.attack_hit_index()
        if hit_index is None:
            return None
        # Comparar poderes (`attack_power > STANDARD_ATTACK_POWER`) acoplava
        # "alcance" a "dano": bastou STANDARD_ATTACK_POWER virar 100 pra o
        # golpe de dash perder o alcance estendido sem ninguém notar. Agora
        # o alcance vem do que está acontecendo de fato.
        dash_impact = self.attack_started_dashing and hit_index == 0
        reach = DASH_ATTACK_REACH if dash_impact else STANDARD_ATTACK_REACH
        offset = (
            PLAYER_HITBOX_WIDTH
            if self.game.player.facing_right
            else -(24 + reach)
        )
        return self.game.player.rect.move(offset, 4).inflate(reach, 10)
