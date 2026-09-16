"""Puzzles da sessão e integração com os minigames.

Game decide quando atualizar e reiniciar este componente. Os dicionários
passados aos minigames mantêm identidade durante fechamento e retomada.
"""

from typing import TYPE_CHECKING

import audio
from minigame import MICROSCOPE_ORDER, WIRE_COLORS, EnergyBoxMinigame, MicroscopeMinigame
from settings import WIDTH, HEIGHT

if TYPE_CHECKING:
    from game import Game


class PuzzleSystem:
    # Ordem dos sprites carregados, independente da ordem das peças no mapa.
    MICROSCOPE_SPRITE_IDENTITY_ORDER = ("objetiva", "base", "iluminador", "ocular")

    def __init__(self, game: "Game"):
        self.game = game
        self.reset()
        self.reset_input()

    def reset(self):
        """Reinicia ao carregar uma fase; entrar/sair de sala mantém progresso."""
        self.lever_on = False
        self.sequence_solved = False
        self.microscope_assembled = False
        self.sequence_progress = 0
        self.microscope_collected = set()
        self.microscope_slots = dict.fromkeys(MICROSCOPE_ORDER, False)
        self.energy_box_state = {"screws_removed": False, "wired": False}
        self.energy_box_wires = dict.fromkeys(WIRE_COLORS, False)

    def reset_input(self):
        self._minigame_escape_was_down = False

    def update_minigame(self, keyboard, dt):
        """Chamado por update() enquanto self.game.minigame.active — ver
        minigame.py. ESC fecha sem terminar (progresso já mora num
        atributo deste PuzzleSystem, passado por referência ao abrir, ver
        open_lab_microscope_minigame), com o mesmo debounce que Configurações
        usa (_escape_was_down) só que numa flag própria, pra não interferir
        com o ESC do menu."""
        escape_down = getattr(keyboard, "escape", False)
        if escape_down and not self._minigame_escape_was_down:
            self._minigame_escape_was_down = escape_down
            audio.play_sfx("select_sound")
            self.game.minigame.close()
            return
        self._minigame_escape_was_down = escape_down

        self.game.minigame.update(dt)
        for name in self.game.minigame.drain_sfx():
            audio.play_sfx(name)
        result = self.game.minigame.pop_result()
        if result is not None:
            self.finish_minigame(*result)

    def finish_minigame(self, key, result):
        if key == "microscope" and result == "completed":
            self.microscope_assembled = True
            audio.play_sfx("microscope_sound")
            libera = (self.game.level.lab_bench or {}).get("libera")
            if libera:
                self.game._release_fog_barrier(libera)
            self.game.dialogue.start(
                "Lia",
                "Microscópio montado! Acho que isso acabou de abrir alguma coisa lá fora.",
            )
        elif key == "energy_box":
            if result == "wired":
                audio.play_sfx("correct_sequence_sound")
                self.game.dialogue.start(
                    "Lia",
                    "A caixa de energia está ligada! Bom saber que funciona — ainda preciso descobrir o que"
                    " isso destrava por aqui.",
                )
            elif result == "closed_mistakes":
                self.game.dialogue.start(
                    "Lia",
                    "Uma faísca! Melhor conferir o diagrama de novo antes de tentar outra vez.",
                )

    def collect_lab_microscope_parts(self, player):
        """Coleta as peças do único microscópio obrigatório da Fase 1.

        Elas ficam no laboratório acessado pelo elevador; o progresso usa
        os atributos canônicos ``microscope_*`` para que HUD, conclusão da
        fase, desenho da bancada e minigame nunca consultem puzzles
        diferentes por engano.
        """
        for index, (item, _name) in enumerate(self.game.level.lab_microscope_parts):
            if index not in self.microscope_collected and player.rect.colliderect(item):
                self.microscope_collected.add(index)
                audio.play_sfx("item_sound")

    def use_lab_microscope_bench(self, player):
        """Bancada do laboratório escondido (ver Level._make_lab_bench) —
        É a bancada do único microscópio obrigatório da Fase 1 e libera
        uma fog.FogBarrier (propriedade "libera" do objeto
        "bancada_microscopio") ao ser concluída."""
        if self.game.level.lab_bench is None:
            return False
        if not player.rect.colliderect(self.game.level.lab_bench["rect"].inflate(70, 60)):
            return False
        if len(self.microscope_collected) < len(self.game.level.lab_microscope_parts):
            self.game.dialogue.start("Lia", "Ainda faltam peças para montar o microscópio.")
            return True
        if not self.microscope_assembled:
            self.open_lab_microscope_minigame()
        return True

    def open_lab_microscope_minigame(self):
        # "Montado" do minigame = a MESMA bancada_microscopio.png que
        # aparece no mundo depois de resolvido (ver
        # Level._draw_lab_microscope/lab_bench_assembled) — mais simples
        # que recompor de body+4 peças (ver _compose_microscope, mantido
        # como reserva) e ainda reforça visualmente "é essa bancada aqui".
        # Sem o arquivo ainda, cai pro microscope_complete.png de sempre.
        complete_sprite = self.game.assets.puzzle_sprites.get("lab_bench_assembled") or self.game.assets.puzzle_sprites["microscope_complete"]
        self.game.minigame.open(
            MicroscopeMinigame(
                WIDTH,
                HEIGHT,
                self.microscope_sprites_by_identity(),
                complete_sprite,
                self.microscope_slots,
            )
        )

    def lab_microscope_sprites(self):
        """Empacota as MESMAS sprites do microscópio (ver
        microscope_sprites_by_identity) no formato que
        Level._draw_lab_microscope espera — lista simples por posição em
        vez de dict por identidade, igual ao antigo puzzle_sprites[
        "microscope_parts"] já usava."""
        return {
            "parts": self.game.assets.puzzle_sprites["microscope_parts"],
            "complete": self.game.assets.puzzle_sprites["microscope_complete"],
            "bench_empty": self.game.assets.puzzle_sprites.get("lab_bench_empty"),
            "bench_assembled": self.game.assets.puzzle_sprites.get("lab_bench_assembled"),
        }

    def use_energy_box(self, player):
        """Caixa de energia (Fase 2, laboratório — ver PLANO_MINIGAMES.md
        §3.2/§3.3). self.game.level.energy_box é None em qualquer mapa sem o
        objeto "caixa_energia" ainda (ver Level._make_energy_box), e
        self.game.assets.energy_box_sprites é None enquanto faltar algum arquivo de
        arte (ver _load_energy_box_sprites) — os dois casos fazem esse
        método devolver False sem fazer nada, exatamente como se a caixa
        não existisse no jogo ainda."""
        if self.game.level.energy_box is None or self.game.assets.energy_box_sprites is None:
            return False
        if not player.rect.colliderect(self.game.level.energy_box.inflate(70, 60)):
            return False
        if self.energy_box_state["wired"]:
            self.game.dialogue.start("Lia", "A caixa de energia está funcionando normalmente.")
            return True
        if not self.energy_box_state["screws_removed"] and self.game.items.counts.get("chave_fenda", 0) <= 0:
            self.game.dialogue.start("Lia", "A tampa está parafusada. Preciso de uma chave de fenda.")
            return True
        self.game.minigame.open(
            EnergyBoxMinigame(
                WIDTH,
                HEIGHT,
                self.game.assets.energy_box_sprites,
                self.energy_box_state,
                self.energy_box_wires,
            )
        )
        return True

    def use_panel_lever(self, player):
        if not player.rect.colliderect(self.game.level.panel_lever.inflate(55, 55)):
            return False

        audio.play_sfx("lever_sound")
        self.lever_on = not self.lever_on
        self.game.level.set_lever_active("panel", self.lever_on)
        if self.lever_on:
            self.game.dialogue.start(
                "Lia",
                "A alavanca ligou o painel. A ordem é: azul, verde, amarelo e vermelho.",
            )
        else:
            self.sequence_progress = 0
            self.game.dialogue.start("Lia", "A alavanca desligou o painel.")
        return True

    def use_sequence_button(self, player):
        for index, button in enumerate(self.game.level.buttons):
            if not player.rect.colliderect(button.inflate(55, 55)):
                continue
            if not self.lever_on:
                self.game.dialogue.start(
                    "Painel",
                    "O painel está sem energia. Encontre e puxe a alavanca.",
                )
            elif self.sequence_solved:
                self.game.dialogue.start(
                    "Painel",
                    "Sequência concluída. As peças do microscópio foram liberadas.",
                )
            elif index == self.sequence_progress:
                audio.play_sfx("button_sound")
                self.sequence_progress += 1
                if self.sequence_progress == len(self.game.level.buttons):
                    self.sequence_solved = True
                    audio.play_sfx("correct_sequence_sound")
                    self.game.dialogue.start(
                        "Painel",
                        "Sequência correta! As peças do microscópio foram liberadas.",
                    )
            else:
                audio.play_sfx("wrong_sequence_sound")
                self.sequence_progress = 0
                self.game.dialogue.start("Painel", "Sequência incorreta. O painel foi reiniciado.")
            return True
        return False

    def microscope_sprites_by_identity(self):
        sprites = self.game.assets.puzzle_sprites["microscope_parts"]
        return dict(zip(self.MICROSCOPE_SPRITE_IDENTITY_ORDER, sprites))
