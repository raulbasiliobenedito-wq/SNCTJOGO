"""Prioridade das interações, portas, elevadores e conversas com NPCs."""

from typing import TYPE_CHECKING

import audio
from game_data import NPC_DIALOGUES, NPC_REPEAT

if TYPE_CHECKING:
    from game import Game


class InteractionSystem:
    DOOR_INTERACT_RANGE = 40
    SECRET_ELEVATOR_RANGE = 40
    NPC_INTERACT_RANGE = 40

    def __init__(self, game: "Game"):
        self.game = game
        self._visited_npcs = set()
        self.reset_dialogue()

    def reset_dialogue(self, *, clear_visits=False):
        """Descarta a conversa atual e, opcionalmente, o histórico de NPCs.

        O histórico só serve para escolher a fala curta numa segunda conversa;
        ele não faz parte do save. `Game.load_level` o limpa para que morrer,
        iniciar outro jogo ou carregar um progresso nunca pule diálogo principal.
        """
        self._dialogue_queue = []
        if clear_visits:
            self._visited_npcs.clear()

    @staticmethod
    def dialogue_beats(default_speaker, content):
        """Normaliza os três formatos aceitos para pares (falante, texto).

        Mantém compatibilidade com falas únicas e com as antigas tuplas de
        strings, além do formato novo que alterna o falante em cada beat.
        """
        if not content:
            return []
        if isinstance(content, str):
            return [(default_speaker, content)]

        beats = []
        for entry in content:
            if isinstance(entry, str):
                beats.append((default_speaker, entry))
                continue
            if (
                not isinstance(entry, (tuple, list))
                or len(entry) != 2
                or not all(isinstance(value, str) for value in entry)
            ):
                raise ValueError(f"Beat de diálogo inválido: {entry!r}")
            beats.append((entry[0], entry[1]))
        return beats

    def start_dialogue_sequence(self, default_speaker, content):
        """Abre o primeiro beat e deixa os seguintes para a mesma fila."""
        beats = self.dialogue_beats(default_speaker, content)
        self._dialogue_queue = list(beats[1:])
        if not beats:
            return False
        self.game.dialogue.start(*beats[0])
        return True

    def handle_interactions(self):
        """Processa portas (qualquer fase), a caixa de energia (sala do
        laboratório, Fase 2) e, na Fase 1 subterrânea, painel, botões e
        bancada do laboratório."""
        if not self.game.interact_pressed:
            return
        if self.use_doors():
            return
        if self.use_secret_elevator():
            return
        if self.talk_to_npc():
            return
        if self.game.level.room == "laboratorio" and self.game.puzzles.use_energy_box(self.game.player):
            return
        if self.game.level.room == "laboratorio_secreto" and self.game.puzzles.use_lab_microscope_bench(self.game.player):
            return
        if not self.game.level.is_underground or self.game.level.room:
            # "or self.game.level.room": o laboratório escondido tem
            # index==0 (is_underground True) mas não usa NADA do sistema
            # antigo abaixo (painel/botões/bancada do corredor) — sem
            # este corte, use_microscope_bench quebraria tentando usar
            # self.game.level.bench, que fica None numa sala
            # (ver Level._reset_lab_state).
            return

        player = self.game.player
        if self.game.puzzles.use_panel_lever(player):
            return
        if self.game.puzzles.use_sequence_button(player):
            return
        self.game.puzzles.use_microscope_bench(player)

    def use_doors(self):
        player = self.game.player
        for door in self.game.level.doors:
            if not player.rect.colliderect(door["rect"].inflate(self.DOOR_INTERACT_RANGE, self.DOOR_INTERACT_RANGE)):
                continue
            audio.play_sfx("door_sound")
            if door["target"] == "sair":
                self.game.exit_room()
            else:
                self.game.enter_room(door["target"])
            return True
        return False

    def use_secret_elevator(self):
        """Elevador secreto (objeto "elevador_lab" — ver
        Level._make_secret_elevators e a conversa sobre o "elevador
        chat"). Mesmo raio/formato de use_doors, mas a troca de sala só
        acontece depois de uma cutscene curta (ver
        elevator_cutscene.ElevatorCutscene): do lado de fora, o elevador
        só funciona depois da Lia esbarrar no bloqueio de neblina ligado
        a ele pela propriedade "chave" (ver _check_fog_barriers, que
        marca barrier.encountered) — do lado de dentro da sala (objeto
        sem "chave", destino "sair"), sempre funciona."""
        if self.game.elevator_cutscene.active:
            return False
        player = self.game.player
        for elevator in self.game.level.secret_elevators:
            if not player.rect.colliderect(
                elevator["rect"].inflate(self.SECRET_ELEVATOR_RANGE, self.SECRET_ELEVATOR_RANGE)
            ):
                continue
            if elevator["chave"] and not self.fog_barrier_encountered(elevator["chave"]):
                self.game.dialogue.start(
                    "Lia",
                    "Melhor eu não usar isso ainda — vou ver o que tem lá na frente primeiro.",
                )
                return True
            audio.play_sfx("door_sound")
            if elevator["destino"] == "sair":
                self.game.elevator_cutscene.start(reverse=True, on_finish=self.game.exit_room)
            else:
                target = elevator["destino"]
                self.game.elevator_cutscene.start(reverse=False, on_finish=lambda: self.game.enter_room(target))
            return True
        return False

    def fog_barrier_encountered(self, chave):
        return any(
            barrier.chave == chave and barrier.encountered
            for barrier in self.game.level.fog_barriers
        )

    def talk_to_npc(self):
        """Os NPCs nunca são consumidos — dá pra falar com eles quantas
        vezes quiser (ver NPC_DIALOGUES/NPC_REPEAT). Mesmo raio/padrão de
        detecção das portas, só que contra Level.npcs. Cada entrada pode ser
        string, sequência de strings antigas ou pares (falante, texto)."""
        player = self.game.player
        for npc in self.game.level.npcs:
            if not player.rect.colliderect(npc["rect"].inflate(self.NPC_INTERACT_RANGE, self.NPC_INTERACT_RANGE)):
                continue
            name = npc["name"]
            if name in self._visited_npcs and name in NPC_REPEAT:
                content = NPC_REPEAT[name]
            else:
                content = NPC_DIALOGUES.get(name)
            if self.start_dialogue_sequence(name, content):
                self._visited_npcs.add(name)
            return True
        return False

    def update_dialogue(self, dialogue_advance_pressed):
        # A animação da alavanca continua enquanto a mensagem é exibida.
        if self.game.level.is_underground:
            self.game.level.update_lever_animations()
        if dialogue_advance_pressed:
            audio.play_sfx("dialogue_sound")
            if self.game.dialogue.finished:
                if self._dialogue_queue:
                    # A fila já guarda o falante de cada beat, portanto serve
                    # tanto para NPCs quanto para pesquisa e achados.
                    self.game.dialogue.start(*self._dialogue_queue.pop(0))
                else:
                    self.game.dialogue.close()
            else:
                self.game.dialogue.reveal_all()
        else:
            self.game.dialogue.update()
