"""Inventário, uso de consumíveis e coleta dos itens do mundo.

As contagens atravessam fases e salas; os drops pertencem ao mapa atual.
Game coordena as transições, o save e o desenho, e mantém vidas, escudo e
progresso dos puzzles. As tabelas de itens e probabilidades ficam em game_data.
"""

import random
from typing import TYPE_CHECKING

import pygame

import audio
from game_data import (
    BOSS_DROP_TABLE,
    DROP_PICKUP_RADIUS,
    ENEMY_DROP_TABLE,
    ITEM_DEFS,
    ITEM_USE_KEYS,
    MAX_LIVES,
)

if TYPE_CHECKING:
    from game import Game


class InventorySystem:
    """Itens de uma sessão e estado das teclas de consumo."""

    def __init__(self, game: "Game"):
        self.game = game
        self.counts = {}
        self.reset_drops()
        self.reset_input()

    def reset_drops(self):
        """Descarta apenas os itens no chão ao mudar de mapa."""
        self.drops = []

    def reset_input(self):
        self.key_was_down = {}

    def read_item_use(self, keyboard):
        """Teclas 1/2/3 (ver ITEM_USE_KEYS) consomem um consumível do
        inventário. Itens de pesquisa nunca aparecem aqui, eles só
        destravam o avanço de fase ao serem coletados (ver
        Game._advance_level_if_ready)."""
        for key_name, item_key in ITEM_USE_KEYS.items():
            down = bool(getattr(keyboard, key_name, False))
            was_down = self.key_was_down.get(key_name, False)
            if down and not was_down:
                self.use_item(item_key)
            self.key_was_down[key_name] = down

    def use_item(self, item_key):
        count = self.counts.get(item_key, 0)
        if count <= 0:
            return
        definition = ITEM_DEFS[item_key]
        if definition["kind"] != "consumable":
            return
        heal = definition["heal"]
        shield = definition["shield"]
        if heal and not shield and self.game.lives >= MAX_LIVES:
            self.game.show_message("Vidas já estão cheias.")
            return
        self.counts[item_key] = count - 1
        if self.counts[item_key] <= 0:
            del self.counts[item_key]
        if heal:
            self.game.lives = min(MAX_LIVES, self.game.lives + heal)
        if shield:
            self.game.shield += shield
        self.game.show_message(f"{definition['name']} usado!")
        self.game.vfx.spawn("dust", self.game.player.rect.centerx, self.game.player.rect.centery)

    def on_enemy_defeated(self, enemy):
        """Chamado uma única vez, no quadro exato em que um inimigo morre
        (stomp() sempre mata; take_hit() só às vezes — ver CombatSystem.check_enemies).
        Chefe larga o item de pesquisa garantido (BOSS_DROP_TABLE); inimigo
        comum sorteia contra ENEMY_DROP_TABLE. Slimes pequenos da Cisão e
        os dois chefes de sala antigos sem entrada em nenhuma tabela não
        largam nada."""
        name = type(enemy).__name__
        quest_item = BOSS_DROP_TABLE.get(name)
        if quest_item:
            audio.play_sfx("boss_death_sound")
            self.spawn_drop(quest_item, enemy.rect.centerx, enemy.rect.centery)
            return
        audio.play_sfx("enemy_death_sound")
        entry = ENEMY_DROP_TABLE.get(name)
        if entry and random.random() < entry[1]:
            self.spawn_drop(entry[0], enemy.rect.centerx, enemy.rect.centery)

    def spawn_drop(self, item_key, x, y):
        self.drops.append({"item": item_key, "x": x, "y": y})

    def collect_drops(self, player):
        """Coleta por sobreposição; itens distantes mantêm a ordem na lista.

        Game descarta os drops ao carregar uma fase, entrar ou sair de sala.
        """
        if not self.drops:
            return
        remaining = []
        pickup = pygame.Rect(0, 0, DROP_PICKUP_RADIUS * 2, DROP_PICKUP_RADIUS * 2)
        for drop in self.drops:
            pickup.center = (drop["x"], drop["y"])
            if player.rect.colliderect(pickup):
                key = drop["item"]
                self.counts[key] = self.counts.get(key, 0) + 1
                self.game.show_message(f"Item obtido: {ITEM_DEFS[key]['name']}")
                audio.play_sfx("item_sound")
                self.game.vfx.spawn("dust", drop["x"], drop["y"])
            else:
                remaining.append(drop)
        self.drops = remaining

    def collect_tools(self, player):
        """Ferramentas largadas no mapa (hoje só a chave de fenda — ver
        Level._make_tool_pickups, PLANO_MINIGAMES.md §3.1). Mesmo padrão de
        índice de _collect_artifacts/_collect_research, mas vai pro
        inventário em vez de um set separado, porque a chave se comporta
        como qualquer outro item (aparece na barra, ver ITEM_DEFS)."""
        for index, (item, item_key) in enumerate(self.game.level.tool_pickups):
            if index in self.game.tools_collected or not player.rect.colliderect(item):
                continue
            self.game.tools_collected.add(index)
            self.counts[item_key] = self.counts.get(item_key, 0) + 1
            self.game.show_message(f"Item obtido: {ITEM_DEFS[item_key]['name']}")
            audio.play_sfx("item_sound")
