"""Orquestra o ciclo de jogo, as interações e a renderização."""

import logging
import random

import pygame

import audio
from cutscene import IntroCutscene
from dialogue import DialogueBox
from elevator_cutscene import ElevatorCutscene
from hint import Hint
from hud import draw_ability_ui, draw_hud, draw_inventory, draw_text
from level import PHASES, VILLAGE, Level
from minigame import (
    MICROSCOPE_ORDER,
    WIRE_COLORS,
    EnergyBoxMinigame,
    MicroscopeMinigame,
    MinigameManager,
)
from player import Player
from render_state import WorldDrawState
from projectile import Projectile
from progress import SAVE_VERSION as PROGRESS_VERSION, read_progress, write_progress
from assets import Assets
from vfx import VFXManager
from settings import (
    ASSET_DIR,
    DATA_DIR,
    CAMERA_ZOOM,
    FPS,
    HEIGHT,
    MOTIVATION,
    PLAYER_HEIGHT,
    PLAYER_HITBOX_OFFSET_X,
    PLAYER_HITBOX_WIDTH,
    WIDTH,
)
from game_data import (
    TITLE,
    SETTINGS,
    INTRO,
    PLAYING,
    GAME_OVER,
    COMPLETE,
    PAUSED,
    STARTING_LIVES,
    MAX_LIVES,
    ITEM_DEFS,
    ITEM_ORDER,
    PHASE_REQUIRED_ITEMS,
    ITEM_USE_KEYS,
    BOSS_DROP_TABLE,
    BOSS_NAMES,
    BOSS_MUSIC,
    ENEMY_DROP_TABLE,
    DROP_PICKUP_RADIUS,
    ATTACK_DURATION,
    ATTACK_COOLDOWN,
    STANDARD_ATTACK_POWER,
    DASH_ATTACK_POWER,
    STANDARD_ATTACK_REACH,
    DASH_ATTACK_REACH,
    MOB_CONTACT_DAMAGE,
    BOSS_CONTACT_DAMAGE,
    COMBO_HIT_COUNT,
    COMBO_RESET_WINDOW,
    COMBO_FINISHER_POWER,
    PARRY_DAMAGE,
    PARRY_INVULN_FRAMES,
    PARRY_HITSTOP_FRAMES,
    HIT_STOP_FRAMES,
    PARRY_SHAKE_DURATION,
    PARRY_SHAKE_MAGNITUDE,
    BOSS_WAKE_SHAKE_DURATION,
    BOSS_WAKE_SHAKE_MAGNITUDE,
    BOSS_WAKE_DUST_COUNT,
    RANGED_ATTACK_POWER,
    RANGED_ATTACK_COOLDOWN,
    RANGED_PROJECTILE_SPEED,
    RANGED_PROJECTILE_RANGE,
    MESSAGE_DURATION,
    MESSAGE_DURATION_LONG,
    CAMERA_X_FOCUS,
    CAMERA_LOOK_AHEAD,
    CAMERA_X_SMOOTHING,
    CAMERA_Y_FOCUS,
    CAMERA_Y_SMOOTHING,
    SCIENCE_FACTS,
    DEFAULT_SCIENCE_FACT,
    ROOM_LORE,
    DEFAULT_ROOM_LORE,
    NPC_SPRITE_ROWS,
    VILLAGER_SPRITE_FILES,
    NPC_DIALOGUES,
    SCHOOL_PLATFORM_SPRITES,
)


class Game:
    """Mantém o estado de uma sessão de jogo e coordena seus componentes."""

    def __init__(self):
        self._load_assets()
        self.player = Player()
        self.dialogue = DialogueBox()
        # Fila de falas restantes de uma conversa de NPC com múltiplos
        # beats (ex.: Sra. Amélia na vila, ver NPC_DIALOGUES/_talk_to_npc/
        # _update_dialogue) — vazia pra NPCs de fala única (a maioria).
        self._npc_dialogue_queue = []
        self._npc_dialogue_speaker = None
        # Cutscene inicial (mãe de Lia no hospital) — reaproveita a mesma
        # DialogueBox acima pro texto e o quadro parado de Lia pro retrato,
        # ver cutscene.IntroCutscene. Só toca entre TITLE e PLAYING.
        self.intro = IntroCutscene(self.dialogue, self.player.frames[0])
        # Cutscene curta do elevador secreto do laboratório (Fase 1, ver
        # elevator_cutscene.ElevatorCutscene e Level._make_secret_elevators)
        # — mesma ideia do Hint/minigame abaixo: pausa o jogo, mas sem
        # precisar de um estado (self.state) novo, já que ela só acontece
        # durante PLAYING (ver update()/draw()).
        self.elevator_cutscene = ElevatorCutscene(self.player.frames[0])
        # Dicas contextuais (vinheta + texto, ver hint.Hint) — pausam o jogo
        # igual à DialogueBox, mas não são conversas com NPC, são avisos de
        # mecânica (ex.: painel do elevador na Fase 1). hints_shown mora em
        # load_level (reseta por fase, igual seen_dialogues).
        self.hint = Hint()
        # Minigames de arraste com mouse (montar o microscópio, e no futuro
        # a caixa de energia — ver minigame.py e PLANO_MINIGAMES.md). Mesmo
        # padrão de pausa do Hint acima: Game.update dá prioridade a
        # minigame.active antes até do dialogue.active (ver update()).
        self.minigame = MinigameManager()
        # Ataque à distância (ver RANGED_* acima e _advance_level_if_ready):
        # desbloqueia ao concluir a Fase 1 e, como inventário/escudo, atravessa
        # trocas de fase normais — só reseta num Game() novo de verdade (não
        # em load_level, que roda a cada avanço de fase).
        self.ranged_unlocked = False
        self.lives = STARTING_LIVES
        # Inventário e escudo atravessam trocas de fase normais (Lia não
        # perde os itens ao avançar) — só zeram ao reiniciar o jogo do zero
        # (ver _update_end_state). self.pending_drops é o oposto: reseta a
        # cada load_level/enter_room/exit_room, porque um item largado no
        # chão de uma sala não faz sentido reaparecer em outro mapa.
        self.inventory = {}
        self.shield = 0
        self.pending_drops = []
        self.camera_x = 0
        self.camera_y = 0
        # Surface intermediária pro zoom da câmera (ver _blit_zoomed_world) —
        # criada só uma vez (não a cada quadro) e reaproveitada.
        self._world_surface = None
        # Pano de fundo estático do menu (ver draw/_render_world_snapshot).
        # Invalidado em load_level, pra o menu nunca mostrar o mundo de uma
        # fase anterior depois de um reinício.
        self._menu_snapshot = None
        self.game_over_fade = 0
        self.game_over_characters = 0
        # Menu de título/Configurações (ver handle_menu_click/_drag/
        # _release, _title_buttons, _settings_widgets): qual slider está
        # sendo arrastado agora (None = nenhum) e pra onde "Voltar" no
        # menu de Configurações deve retornar — sempre TITLE por enquanto
        # (não existe menu de pausa ainda; se um dia existir, é só apontar
        # isso pra PLAYING antes de abrir Configurações a partir dele).
        self._dragging_slider = None
        self._settings_return_state = TITLE
        self._reset_combat_state()
        self._reset_input_state()
        self.load_level(0)
        self.state = TITLE

    def _load_assets(self):
        self.assets = Assets()
        self.vfx = VFXManager(
            ASSET_DIR / "vfx" / "vfx.png",
            {
                "fase2": ASSET_DIR / "vfx" / "vfx_university.png",
                "lab": ASSET_DIR / "vfx" / "vfx_lab.png",
                "library": ASSET_DIR / "vfx" / "vfx_library.png",
                # parry_flash.png ainda não foi salvo pelo Raul nessa pasta —
                # VFXManager ignora sozinho uma folha extra que não existe
                # ainda (ver __init__/spawn em vfx.py), então isso não
                # derruba o jogo enquanto o arquivo não chega.
                "parry": ASSET_DIR / "vfx" / "parry_flash.png",
            },
        )

    def load_level(self, index):
        """Inicia uma fase sem modificar a quantidade atual de vidas."""
        self.level = Level(index)
        self.assets.apply_fog(self.level)
        self.checkpoint = self.level.spawn
        self.player.reset(*self.checkpoint)
        self.collected = set()
        self._artifacts_by_room = {}
        # Enquanto self._base_level não for None, self.level aponta pra uma
        # sala (biblioteca/laboratório) e self._base_level guarda a fase
        # principal, intacta, pra restaurar ao sair — ver enter_room/exit_room.
        self._base_level = None
        self._base_state = None
        self.seen_dialogues = set()
        self._npc_dialogue_queue = []
        self._npc_dialogue_speaker = None
        self.hints_shown = set()
        self.lever_on = False
        self.sequence_solved = False
        self.microscope_assembled = False
        self.sequence_progress = 0
        self.microscope_collected = set()
        # Progresso do minigame de montagem (ver minigame.MicroscopeMinigame
        # e _open_microscope_minigame) — dict identidade->bool, começa tudo
        # False. Passado por referência pro minigame, então fechar com ESC
        # no meio não perde peça já encaixada; reseta aqui junto com
        # microscope_collected porque os dois nascem de novo a cada troca
        # de fase (só existe de verdade na Fase 1).
        self.microscope_slots = dict.fromkeys(MICROSCOPE_ORDER, False)
        # Segunda bancada de microscópio, independente da acima — a do
        # laboratório ESCONDIDO (ver Level._make_lab_bench/
        # _make_lab_microscope_parts e a conversa sobre o elevador
        # secreto). Mesmo esquema de estado (set de índices coletados +
        # dict de encaixes), só que sem nenhuma ligação com is_underground/
        # sequence_progress/buttons do sistema antigo.
        self.lab_microscope_collected = set()
        self.lab_microscope_assembled = False
        self.lab_microscope_slots = dict.fromkeys(MICROSCOPE_ORDER, False)
        # Ferramentas largadas no mapa (hoje só a chave de fenda, na sala do
        # laboratório da Fase 2 — ver Level._make_tool_pickups,
        # PLANO_MINIGAMES.md §3.1) e progresso da caixa de energia (mesmo
        # esquema de referência mutável do microscope_slots acima: fechar
        # com ESC no meio do modo fios não perde progresso). Nenhum dos
        # dois faz nada visível enquanto self.level.energy_box/tool_pickups
        # estiverem vazios (sem o objeto no Tiled ainda) ou enquanto
        # self.assets.energy_box_sprites for None (arte ainda não chegou).
        self.tools_collected = set()
        self.energy_box_state = {"screws_removed": False, "wired": False}
        self.energy_box_wires = dict.fromkeys(WIRE_COLORS, False)
        self.minigame.close()
        self.riding_platform = None
        self.pending_drops = []
        self._reset_combat_state()
        self._reset_input_state()
        self._reset_vfx_state()
        self._reset_status_state()
        self.camera_x = 0
        self.camera_y = 0
        self._menu_snapshot = None
        self.show_message(self.level.data["subtitle"], MESSAGE_DURATION_LONG)
        self.state = PLAYING

    @property
    def artifacts_collected(self):
        """Cada mapa tem seus próprios índices, preservados ao revisitar a sala."""
        key = (self.level.index, self.level.room)
        return self._artifacts_by_room.setdefault(key, set())

    def enter_room(self, room_key):
        """Troca para uma sala secundária (porta interativa no corredor),
        preservando a fase principal intacta (inimigos, pesquisa coletada)
        pra restaurar exatamente como estava ao sair — ver exit_room."""
        self._base_level = self.level
        self._base_state = (self.player.x, self.player.y, self.camera_x, self.camera_y)
        self.level = Level(self.level.index, room=room_key)
        self.assets.apply_fog(self.level)
        self.player.reset(*self.level.spawn)
        self.riding_platform = None
        self.pending_drops = []
        self.camera_x = self.camera_y = 0
        # Suprime o [E] desta troca de tela: sem isso, segurar a tecla ao
        # atravessar a porta reaciona a interação do outro lado no mesmo
        # quadro (ex.: entrar e sair de novo instantaneamente).
        self.interact_was_down = True
        self.show_message(self.level.data["subtitle"], MESSAGE_DURATION_LONG)

    def exit_room(self):
        """Volta da sala pra fase principal, no ponto exato de onde Lia
        entrou pela porta."""
        if self._base_level is None:
            return
        self.level = self._base_level
        self._base_level = None
        player_x, player_y, camera_x, camera_y = self._base_state
        self._base_state = None
        self.player.reset(player_x, player_y)
        self.riding_platform = None
        self.pending_drops = []
        self.camera_x, self.camera_y = camera_x, camera_y
        self.interact_was_down = True

    # Progresso salvo em disco. Mesmo padrão já provado por
    # audio_settings.json: JSON simples na raiz, gravado em pontos
    # discretos (checkpoint e fim de fase) e lido uma vez na abertura.
    # Nada de auto-save por quadro.
    SAVE_PATH = DATA_DIR / "save.json"
    SAVE_VERSION = PROGRESS_VERSION

    def save_progress(self):
        """Grava de forma atômica; registra falhas sem interromper a partida."""
        if self.level.room:
            # Dentro de uma sala não há checkpoint; o ponto de retorno de
            # verdade é o do corredor, que já foi salvo ao entrar nele.
            return
        try:
            write_progress(self.SAVE_PATH, {
                "version": self.SAVE_VERSION,
                "level": self.level.index,
                "checkpoint": list(self.checkpoint),
                "lives": self.lives,
                "shield": self.shield,
                "inventory": self.inventory,
                "ranged_unlocked": self.ranged_unlocked,
                "collected": sorted(self.collected),
            })
        except (OSError, ValueError, TypeError):
            logging.getLogger(__name__).warning("Não foi possível gravar o progresso", exc_info=True)

    def load_progress(self):
        """Valida o save antes de retomar; dados inválidos preservam a sessão."""
        try:
            data = read_progress(self.SAVE_PATH, (VILLAGE, *range(len(PHASES))))
        except FileNotFoundError:
            return False
        except (OSError, ValueError, TypeError):
            logging.getLogger(__name__).warning("Save inválido; sessão preservada", exc_info=True)
            return False
        self.load_level(data["level"])
        self.checkpoint = data["checkpoint"]
        self.player.reset(*self.checkpoint)
        self.lives = data["lives"]
        self.shield = data["shield"]
        self.inventory = data["inventory"]
        self.ranged_unlocked = data["ranged_unlocked"]
        self.collected = {i for i in data["collected"] if i < len(self.level.research)}
        return True

    def has_save(self):
        return self.SAVE_PATH.exists()

    def show_message(self, text, duration=MESSAGE_DURATION):
        """Único ponto de entrada da caixa de mensagem da HUD.

        Existe porque oito lugares diferentes setavam self.message junto com
        `message_timer = 0`, e hud.draw_hud só desenha a caixa com
        `if message_timer:` — a mensagem era escrita e nunca aparecia. O caso
        mais grave era o de _advance_level_if_ready: o jogador chegava no fim
        da fase, era empurrado 60px pra trás e não recebia NENHUMA explicação
        na tela. Concentrar tudo aqui evita que o próximo `= 0` volte."""
        self.message = text
        self.message_timer = duration

    def _reset_combat_state(self):
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_power = STANDARD_ATTACK_POWER
        self.combo_count = 0
        self.combo_timer = 0
        self.mouse_attack_requested = False
        self.ranged_cooldown = 0
        self.projectiles = []

    def _reset_input_state(self):
        self.interact_was_down = False
        self.attack_was_down = False
        self.dash_was_down = False
        self.ranged_was_down = False
        self.dialogue_advance_was_down = False
        # Debounce do ESC no menu de Configurações (ver _update_settings) —
        # mesma ideia dos *_was_down acima, só que pra uma tecla que não
        # passa por _read_input.
        self._escape_was_down = False
        self._minigame_escape_was_down = False
        self._item_key_was_down = {}

    def _reset_vfx_state(self):
        self.vfx.active = []
        self.dust_timer = 0
        self.was_swimming = False
        self.player_grounded = False

    # Quadros de invencibilidade após renascer: sem isso, se o checkpoint (ou
    # o próprio spawn) ficar perto de um espinho/inimigo, o toque volta a
    # acontecer nos quadros seguintes e consome as 3 vidas quase instantaneamente
    # — parecendo "morte direta" mesmo cada toque só custando 1 vida.
    INVULN_FRAMES = 90

    # Quadros dos 2 frames de morte (Player.DEATH_FRAMES, pedido do Raul)
    # parada no lugar onde ela morreu, antes do reposicionamento de verdade
    # (ver _finish_respawn) — metade do tempo em cada quadro.
    DEATH_POSE_DURATION = 24

    def _reset_status_state(self):
        self.invuln_timer = 0
        self.hitstop_timer = 0
        self.shake_timer = 0
        self.shake_duration = 0
        self.shake_magnitude = 0
        self.death_pose_timer = 0

    def _lose_life(self, amount=1):
        """Núcleo comum de qualquer perda de vida (pedido do Raul: dano de
        contato deixou de reposicionar — ver take_damage/respawn abaixo).
        `amount` é em corações (1 = coração inteiro, 0.5 = meio coração —
        ver MOB_CONTACT_DAMAGE/BOSS_CONTACT_DAMAGE) — self.lives virou
        fracionário por causa disso, e o HUD (hud.draw_hud/_draw_hearts)
        já sabe desenhar meio coração. Escudo absorve primeiro (Carcaça de
        robô/Dark Crystal, ver ITEM_DEFS — vale pra qualquer fonte e
        qualquer tamanho de dano: espinho, chefe, queda, afogar). Devolve
        True só quando vida foi perdida DE VERDADE (não absorvida pelo
        escudo e ainda sobrou vida) — quem chamou decide o que fazer
        depois disso (respawn reposiciona, take_damage não)."""
        if self.shield > 0:
            self.shield -= 1
            self.invuln_timer = self.INVULN_FRAMES
            self.vfx.spawn("impact", self.player.rect.centerx, self.player.rect.centery)
            self.show_message("O escudo absorveu o dano!")
            audio.play_sfx("shield_sound")
            return False
        # Na universidade, o "toque que machuca" costuma ser vidro quebrado
        # ou a poça química — o estilhaço de vidro combina melhor com o
        # tema do que o impacto genérico usado nas outras fases.
        if self.level.room == "laboratorio":
            vfx_kind = "acid_burn"
        elif self.level.room == "biblioteca":
            vfx_kind = "ink_splash"
        elif self.level.index == 1:
            vfx_kind = "glass"
        else:
            vfx_kind = "impact"
        self.vfx.spawn(vfx_kind, self.player.rect.centerx, self.player.rect.centery)
        audio.play_sfx("damage_sound")
        # max(0, ...) em vez de só subtrair: sem isso um chefe (1 coração
        # inteiro) batendo com meio coração sobrando deixaria self.lives
        # negativo, o que o HUD não sabe desenhar.
        self.lives = max(0, self.lives - amount)
        self.invuln_timer = self.INVULN_FRAMES
        if self.lives <= 0:
            self.state = GAME_OVER
            self.game_over_fade = 0
            self.game_over_characters = 0
            audio.play_sfx("death_sound")
            return False
        return True

    def take_damage(self, amount=1):
        """Dano de contato (inimigo, espinho, lava, ataque à distância de
        chefe, afogamento) — pedido do Raul: NÃO reposiciona mais a Lia,
        só tira `amount` corações e dá 1s de invencibilidade
        (INVULN_FRAMES). Ela continua exatamente onde apanhou. Só cair no
        vazio ainda reposiciona de verdade — ver respawn()."""
        self._lose_life(amount)

    def respawn(self):
        """Reservado pra quando a Lia cai no vazio (ver check_events, a
        única chamada que sobrou) — continua reposicionando de verdade:
        perde 1 coração inteiro, congela na pose de morte, e só depois
        volta pro checkpoint/saída de sala (ver _finish_respawn)."""
        if self._lose_life():
            # Reposicionar (exit_room/checkpoint) fica pra depois — ver
            # _finish_respawn, chamado por _update_playing quando
            # death_pose_timer chega a 0. Isso dá tempo dos 2 frames de
            # morte (Player.DEATH_FRAMES) aparecerem parada no lugar onde
            # ela morreu, em vez dela sumir/reaparecer instantaneamente.
            self.death_pose_timer = self.DEATH_POSE_DURATION

    def _apply_death_frame(self):
        elapsed = self.DEATH_POSE_DURATION - self.death_pose_timer
        index = 1 if elapsed >= self.DEATH_POSE_DURATION / 2 else 0
        self.player.frame = self.player.DEATH_FRAMES[index]

    def _finish_respawn(self):
        """A parte de respawn() que reposiciona de verdade — adiada até o
        fim da pose de morte (ver respawn/_apply_death_frame)."""
        if self._base_level is not None:
            # Machucar-se numa sala te tira dela: mais simples e mais
            # temático (Lia cambaleia de volta pro corredor) do que tentar
            # achar um checkpoint dentro de um espaço tão pequeno. exit_room
            # já restaura a câmera exata de antes da porta, então não zera
            # camera_y como no respawn normal por checkpoint.
            self.exit_room()
        else:
            self.player.reset(*self.checkpoint)
            self.camera_y = 0
        self.riding_platform = None
        self.show_message(MOTIVATION, MESSAGE_DURATION_LONG)

    def update(self, keyboard, dt=1 / FPS):
        self._update_music()
        dialogue_advance_pressed, attack_pressed, dash_pressed, ranged_pressed = self._read_input(keyboard)

        if self.state == TITLE:
            self._update_title(keyboard)
        elif self.state == SETTINGS:
            self._update_settings(keyboard)
        elif self.state == INTRO:
            self._update_intro(keyboard, dialogue_advance_pressed)
        elif self.state == PAUSED:
            self._update_paused(keyboard)
        elif self.state in (GAME_OVER, COMPLETE):
            self._update_end_state(keyboard)
        elif self.minigame.active:
            self._update_minigame(keyboard, dt)
        elif self.elevator_cutscene.active:
            self.elevator_cutscene.update()
        elif self.dialogue.active:
            self._update_dialogue(dialogue_advance_pressed)
        elif self.hint.active:
            self._update_hint(dialogue_advance_pressed)
        else:
            if self._escape_pressed(keyboard):
                # Pausa: o comentário de _settings_return_state já previa
                # isso ("se um dia existir um menu de pausa, é só apontar
                # isso pra PLAYING antes de abrir Configurações a partir
                # dele") — só faltava o estado existir.
                audio.play_sfx("select_sound")
                self.state = PAUSED
                self._menu_snapshot = None
                return
            self._read_item_use(keyboard)
            self._update_playing(keyboard, dash_pressed, attack_pressed, ranged_pressed, dt)

    def _read_input(self, keyboard):
        interaction_down = keyboard.e or keyboard.RETURN
        dialogue_advance_down = interaction_down or keyboard.space
        attack_down = keyboard.f
        dash_down = keyboard.q
        ranged_down = keyboard.r

        self.interact_pressed = interaction_down and not self.interact_was_down
        self.interact_was_down = interaction_down

        dialogue_advance_pressed = (
            dialogue_advance_down and not self.dialogue_advance_was_down
        )
        self.dialogue_advance_was_down = dialogue_advance_down

        attack_pressed = (
            attack_down and not self.attack_was_down
        ) or self.mouse_attack_requested
        self.attack_was_down = attack_down
        self.mouse_attack_requested = False

        dash_pressed = dash_down and not self.dash_was_down
        self.dash_was_down = dash_down

        ranged_pressed = ranged_down and not self.ranged_was_down
        self.ranged_was_down = ranged_down
        return dialogue_advance_pressed, attack_pressed, dash_pressed, ranged_pressed

    def _read_item_use(self, keyboard):
        """Teclas 1/2/3 (ver ITEM_USE_KEYS) consomem um consumível do
        inventário — os 4 itens de pesquisa nunca aparecem aqui, eles só
        destravam o avanço de fase ao serem coletados (ver
        _advance_level_if_ready)."""
        for key_name, item_key in ITEM_USE_KEYS.items():
            down = bool(getattr(keyboard, key_name, False))
            was_down = self._item_key_was_down.get(key_name, False)
            if down and not was_down:
                self._use_item(item_key)
            self._item_key_was_down[key_name] = down

    def _use_item(self, item_key):
        count = self.inventory.get(item_key, 0)
        if count <= 0:
            return
        definition = ITEM_DEFS[item_key]
        if definition["kind"] != "consumable":
            return
        heal = definition["heal"]
        shield = definition["shield"]
        if heal and not shield and self.lives >= MAX_LIVES:
            self.show_message("Vidas já estão cheias.")
            return
        self.inventory[item_key] = count - 1
        if self.inventory[item_key] <= 0:
            del self.inventory[item_key]
        if heal:
            self.lives = min(MAX_LIVES, self.lives + heal)
        if shield:
            self.shield += shield
        self.show_message(f"{definition['name']} usado!")
        self.vfx.spawn("dust", self.player.rect.centerx, self.player.rect.centery)

    def _update_title(self, keyboard):
        # Atalho de teclado (histórico, de antes do menu com botões
        # existir) continua funcionando junto com clicar em "JOGAR" — ver
        # handle_menu_click.
        if keyboard.space or keyboard.RETURN:
            self._start_game()

    def _start_game(self):
        audio.play_sfx("select_sound")
        self.lives = STARTING_LIVES
        self.state = INTRO
        self.intro.start()

    def _escape_pressed(self, keyboard):
        """ESC com debounce, compartilhado por pausa e configurações (antes
        cada um tinha sua própria flag *_was_down espalhada)."""
        down = bool(getattr(keyboard, "escape", False))
        pressed = down and not self._escape_was_down
        self._escape_was_down = down
        return pressed

    def _update_paused(self, keyboard):
        """ESC volta pro jogo; os botões do menu de pausa são tratados por
        handle_menu_click, igual ao título."""
        if self._escape_pressed(keyboard):
            audio.play_sfx("select_sound")
            self.state = PLAYING

    def _pause_buttons(self):
        button_width, button_height = 360, 74
        center_x = WIDTH // 2
        return {
            "resume": pygame.Rect(0, 0, button_width, button_height).move(
                center_x - button_width // 2, HEIGHT // 2 - 30
            ),
            "settings": pygame.Rect(0, 0, button_width, button_height).move(
                center_x - button_width // 2, HEIGHT // 2 + 64
            ),
        }

    def _update_settings(self, keyboard):
        # Interação é toda por mouse (ver handle_menu_click/_drag/
        # _release) — ESC aqui é só um atalho extra pra voltar sem
        # precisar acertar o botão "Voltar" na tela.
        if self._escape_pressed(keyboard):
            audio.play_sfx("select_sound")
            self.state = self._settings_return_state

    def _title_buttons(self):
        """Retângulos dos botões do menu de título, em coordenadas de
        tela (mesmo espaço de WIDTH x HEIGHT usado por draw_text/pygame —
        ver Game.draw/_blit_zoomed_world: a janela real abre exatamente
        nesse tamanho, então a posição do mouse do Pygame Zero já chega
        nessas mesmas coordenadas, sem precisar converter nada)."""
        button_width, button_height = 360, 74
        center_x = WIDTH // 2
        top = HEIGHT // 2 - (94 if self.has_save() else 10)
        buttons = {}
        if self.has_save():
            # Só aparece se existir save.json — quem nunca jogou não vê um
            # botão morto.
            buttons["continue"] = pygame.Rect(0, 0, button_width, button_height).move(
                center_x - button_width // 2, top
            )
            top += 94
        buttons["play"] = pygame.Rect(0, 0, button_width, button_height).move(
            center_x - button_width // 2, top
        )
        buttons["settings"] = pygame.Rect(0, 0, button_width, button_height).move(
            center_x - button_width // 2, top + 94
        )
        return buttons

    SETTINGS_BAR_WIDTH = 480
    SETTINGS_BAR_HEIGHT = 16
    # Área clicável de cada slider é mais alta que a barra visual (ver
    # _draw_slider em vez desse comentário se quiser conferir o desenho)
    # só pra facilitar acertar com o mouse sem precisar caprichar no pixel.
    SETTINGS_BAR_HIT_HEIGHT = 44

    # Ordem dos sliders na tela: (chave, rótulo, getter, setter).
    SETTINGS_SLIDERS = (
        ("music_bar", "Volume da Música", lambda: audio.music_volume, audio.set_music_volume),
        ("sfx_bar", "Volume dos Efeitos", lambda: audio.sfx_volume, audio.set_sfx_volume),
        ("shake_bar", "Tremor de Tela", lambda: audio.shake_scale, audio.set_shake_scale),
        ("text_bar", "Velocidade do Texto", lambda: audio.text_speed / 2.0,
         lambda ratio: audio.set_text_speed(ratio * 2.0)),
    )
    SETTINGS_ROW_SPACING = 88

    def _settings_widgets(self):
        center_x = WIDTH // 2
        bar_x = center_x - self.SETTINGS_BAR_WIDTH // 2
        top = HEIGHT // 2 - 165
        widgets = {}
        for index, (key, _label, _get, _set) in enumerate(self.SETTINGS_SLIDERS):
            widgets[key] = pygame.Rect(
                bar_x,
                top + index * self.SETTINGS_ROW_SPACING - self.SETTINGS_BAR_HIT_HEIGHT // 2,
                self.SETTINGS_BAR_WIDTH,
                self.SETTINGS_BAR_HIT_HEIGHT,
            )
        widgets["back"] = pygame.Rect(0, 0, 260, 64).move(
            center_x - 130, top + len(self.SETTINGS_SLIDERS) * self.SETTINGS_ROW_SPACING + 10
        )
        return widgets

    @staticmethod
    def _slider_ratio_at(bar_rect, x):
        if bar_rect.width <= 0:
            return 0.0
        return min(1.0, max(0.0, (x - bar_rect.x) / bar_rect.width))

    def handle_menu_click(self, pos):
        """Chamado por main.py (on_mouse_down) só quando self.state é
        TITLE ou SETTINGS — cliques durante o jogo em si continuam indo
        pro ataque (ver request_mouse_attack), não passam por aqui."""
        if self.state == TITLE:
            buttons = self._title_buttons()
            if "continue" in buttons and buttons["continue"].collidepoint(pos):
                audio.play_sfx("select_sound")
                if not self.load_progress():
                    self._start_game()
            elif buttons["play"].collidepoint(pos):
                self._start_game()
            elif buttons["settings"].collidepoint(pos):
                audio.play_sfx("select_sound")
                self._settings_return_state = TITLE
                self.state = SETTINGS
        elif self.state == PAUSED:
            buttons = self._pause_buttons()
            if buttons["resume"].collidepoint(pos):
                audio.play_sfx("select_sound")
                self.state = PLAYING
            elif buttons["settings"].collidepoint(pos):
                audio.play_sfx("select_sound")
                self._settings_return_state = PAUSED
                self.state = SETTINGS
        elif self.state == SETTINGS:
            widgets = self._settings_widgets()
            if widgets["back"].collidepoint(pos):
                audio.play_sfx("select_sound")
                self.state = self._settings_return_state
            else:
                for key, _label, _get, setter in self.SETTINGS_SLIDERS:
                    if widgets[key].collidepoint(pos):
                        self._dragging_slider = key
                        setter(self._slider_ratio_at(widgets[key], pos[0]))
                        if key == "sfx_bar":
                            audio.play_sfx("select_sound")
                        break

    def handle_menu_drag(self, pos):
        """Chamado por main.py (on_mouse_move) todo quadro em que o mouse
        se move — só faz algo se um slider está sendo arrastado (ver
        handle_menu_click/_release)."""
        if self._dragging_slider is None:
            return
        widgets = self._settings_widgets()
        bar = widgets[self._dragging_slider]
        ratio = self._slider_ratio_at(bar, pos[0])
        for key, _label, _get, setter in self.SETTINGS_SLIDERS:
            if key == self._dragging_slider:
                setter(ratio)
                break

    def handle_menu_release(self):
        """Chamado por main.py (on_mouse_up) — grava em disco só ao
        soltar o slider (ver audio.save_settings), não a cada pixel
        arrastado."""
        if self._dragging_slider is not None:
            self._dragging_slider = None
            audio.save_settings()

    def _update_minigame(self, keyboard, dt):
        """Chamado por update() enquanto self.minigame.active — ver
        minigame.py. ESC fecha sem terminar (progresso já mora num
        atributo do próprio Game, passado por referência ao abrir, ver
        _open_microscope_minigame), com o mesmo debounce que Configurações
        usa (_escape_was_down) só que numa flag própria, pra não interferir
        com o ESC do menu."""
        escape_down = getattr(keyboard, "escape", False)
        if escape_down and not self._minigame_escape_was_down:
            self._minigame_escape_was_down = escape_down
            audio.play_sfx("select_sound")
            self.minigame.close()
            return
        self._minigame_escape_was_down = escape_down

        self.minigame.update(dt)
        for name in self.minigame.drain_sfx():
            audio.play_sfx(name)
        result = self.minigame.pop_result()
        if result is not None:
            self._finish_minigame(*result)

    def _finish_minigame(self, key, result):
        if key == "microscope" and result == "completed":
            self.microscope_assembled = True
            audio.play_sfx("microscope_sound")
            self.level.activate_return_route()
            self.dialogue.start(
                "Lia",
                "Microscópio montado! As plataformas de retorno foram liberadas; preciso voltar pelo caminho acima.",
            )
        elif key == "lab_microscope" and result == "completed":
            self.lab_microscope_assembled = True
            audio.play_sfx("microscope_sound")
            libera = (self.level.lab_bench or {}).get("libera")
            if libera:
                self._release_fog_barrier(libera)
            # O laboratório escondido virou O microscópio da Fase 1 (ver
            # _advance_level_if_ready/needs_microscope) — o antigo puzzle
            # subterrâneo (parte_microscopio/bancada) saiu do .tmx, então
            # é aqui, e não mais lá, que a Rota Retorno é liberada.
            self.level.activate_return_route()
            self.dialogue.start(
                "Lia",
                "Microscópio montado! Acho que isso acabou de abrir alguma coisa lá fora.",
            )
        elif key == "energy_box":
            if result == "wired":
                audio.play_sfx("correct_sequence_sound")
                self.dialogue.start(
                    "Lia",
                    "A caixa de energia está ligada! Bom saber que funciona — ainda preciso descobrir o que"
                    " isso destrava por aqui.",
                )
            elif result == "closed_mistakes":
                self.dialogue.start(
                    "Lia",
                    "Uma faísca! Melhor conferir o diagrama de novo antes de tentar outra vez.",
                )

    def handle_minigame_click(self, pos):
        """Chamado por main.py/main_web.py (mouse down) quando
        self.minigame.active é True — ver PLANO_MINIGAMES.md §0/§1."""
        self.minigame.on_click(pos)

    def handle_minigame_drag(self, pos):
        self.minigame.on_drag(pos)

    def handle_minigame_release(self, pos):
        self.minigame.on_release(pos)

    def _update_intro(self, keyboard, dialogue_advance_pressed):
        """A mãe de Lia no hospital (ver cutscene.IntroCutscene) — ESC pula
        direto pra vila, senão a cena avança do mesmo jeito que qualquer
        outro diálogo do jogo (E/Enter/Espaço). Dali ela vai pra vila (ver
        PLANO_VILA.md/level.VILLAGE) antes da Fase 1 — não direto pra
        Fase 1 como antes."""
        if getattr(keyboard, "escape", False):
            self.intro.skip()
        else:
            self.intro.update(dialogue_advance_pressed)
        if not self.intro.active:
            self.load_level(VILLAGE)

    def _update_end_state(self, keyboard):
        if self.state == GAME_OVER:
            self.game_over_fade = min(60, self.game_over_fade + 1)
            if self.game_over_fade >= 18:
                self.game_over_characters += 0.75
        if keyboard.r:
            audio.play_sfx("select_sound")
            self.lives = STARTING_LIVES
            self.shield = 0
            if self.state == COMPLETE:
                self.inventory = {}
            level_index = 0 if self.state == COMPLETE else self.level.index
            self.load_level(level_index)

    def _update_dialogue(self, dialogue_advance_pressed):
        # A animação da alavanca continua enquanto a mensagem é exibida.
        if self.level.is_underground:
            self.level.update_lever_animations()
        if dialogue_advance_pressed:
            audio.play_sfx("dialogue_sound")
            if self.dialogue.finished:
                if self._npc_dialogue_queue:
                    # Conversa de vários beats (ex.: Sra. Amélia, ver
                    # _talk_to_npc) — próxima fala em vez de fechar.
                    next_text = self._npc_dialogue_queue.pop(0)
                    self.dialogue.start(self._npc_dialogue_speaker, next_text)
                else:
                    self.dialogue.close()
            else:
                self.dialogue.reveal_all()
        else:
            self.dialogue.update()

    def _update_playing(self, keyboard, dash_pressed, attack_pressed, ranged_pressed, dt):
        self._update_shake()
        if self.hitstop_timer > 0:
            # Congela a simulação (pedido do Raul: hit-stop no parry, ver
            # _check_parries) — o shake continua contando acima pra já estar
            # decaindo quando a simulação voltar, em vez de só começar depois.
            self.hitstop_timer -= 1
            return
        if self.death_pose_timer > 0:
            # Congela do mesmo jeito que o hit-stop, mas pra mostrar os 2
            # frames de morte (ver respawn/_apply_death_frame) parada onde
            # ela caiu antes de reaparecer no checkpoint/porta.
            self.death_pose_timer -= 1
            self._apply_death_frame()
            if self.death_pose_timer == 0:
                self._finish_respawn()
            return
        self.player.update_abilities()
        if dash_pressed and not self.player.swimming:
            if self.player.start_dash():
                audio.play_sfx("dash_sound")
        self.player.read_controls(keyboard)
        self._update_attack(attack_pressed)
        self._update_ranged_attack(ranged_pressed)
        self._maybe_wake_bosses()
        self._face_bosses_at_player()
        self.level.update(dt)
        self._check_fog_barriers()
        if self.level.tiled_map:
            # Avança a animação dos tiles do Tiled (ex.: água da Fase 3) em ms.
            self.level.tiled_map.update(dt * 1000)
        self._move_with_platform()
        self.move_player()
        self._apply_boss_arena_clamp()
        self.player.animate()
        self._apply_attack_frame()
        self._update_vfx()
        self._update_camera()
        self.message_timer = max(0, self.message_timer - 1)
        self.handle_interactions()
        self.check_events()

    def _update_hint(self, dialogue_advance_pressed):
        # A alavanca continua animando durante a dica, igual acontece durante
        # um diálogo (ver _update_dialogue) — evita ela "congelar" no meio de
        # um movimento se a dica disparar bem na hora de puxar a alavanca.
        if self.level.is_underground:
            self.level.update_lever_animations()
        self.hint.update()
        if dialogue_advance_pressed:
            self.hint.close()

    # Raio (px, medido centro-a-centro) em que um chefe dormente acorda ao
    # se aproximar a Lia (ver enemy.py: SlimeKing/Librarian/Specimen
    # nascem em DORMANT e só saem desse estado via wake_up()). Generoso o
    # bastante pra acordar antes da Lia encostar nele, cedo o suficiente pra
    # não ficar sendo golpeado "de graça" enquanto ainda dorme, mas sem
    # acordar assim que a fase carrega — estilo Silksong, onde o chefe fica
    # parado até o jogador chegar perto da arena.
    BOSS_WAKE_RADIUS = 420

    def _maybe_wake_bosses(self):
        """Confere todo inimigo vivo da fase (não só os de boss_arenas —
        Librarian/Specimen não têm arena gerada por código, só a sala fixa
        do Tiled, então checar self.level.enemies direto cobre os 4 chefes
        com o mesmo código). Uma vez acordado (wake_up), o chefe nunca volta
        a dormir, mesmo que a Lia se afaste — combina com o resto do jogo,
        onde nenhum chefe "reseta" sozinho."""
        player_center = self.player.rect.center
        for enemy in self.level.enemies:
            wake_up = getattr(enemy, "wake_up", None)
            if wake_up is None or enemy.state != getattr(enemy, "DORMANT", None):
                continue
            dx = enemy.rect.centerx - player_center[0]
            dy = enemy.rect.centery - player_center[1]
            if dx * dx + dy * dy <= self.BOSS_WAKE_RADIUS * self.BOSS_WAKE_RADIUS:
                wake_up()
                audio.play_sfx("boss_wake_sound")
                self._boss_wake_impact(enemy)

    def _boss_wake_impact(self, boss):
        """Tremor de tela + poeira caindo do teto no instante em que o chefe
        acorda (IDEIAS_FUTURAS.md). A poeira nasce espalhada ao longo do
        TOPO DA TELA acima da arena, não no chefe: a ideia é a masmorra
        reagindo, não um efeito de impacto nele."""
        self._trigger_shake(BOSS_WAKE_SHAKE_DURATION, BOSS_WAKE_SHAKE_MAGNITUDE)
        left = int(self.camera_x)
        top = int(self.camera_y)
        for _ in range(BOSS_WAKE_DUST_COUNT):
            self.vfx.spawn(
                "dust",
                random.randint(left, left + WIDTH),
                top + random.randint(0, HEIGHT // 4),
            )

    def _face_bosses_at_player(self):
        """Chefes sempre virados pra Lia (pedido do Raul: eles às vezes
        ficavam olhando pro lado errado e os ataques saíam desalinhados) —
        cada classe decide sozinha quando é seguro virar (ver
        enemy.<Boss>.face_player/FACING_STATES: nunca no meio da própria
        patrulha nem de um ataque já em execução, só parado ou ainda na
        antecipação — assim a direção já está certa bem antes do golpe
        de verdade sair)."""
        player_x = self.player.rect.centerx
        for enemy in self.level.enemies:
            face_player = getattr(enemy, "face_player", None)
            if face_player:
                face_player(player_x)

    def _update_attack(self, attack_pressed):
        self.attack_cooldown = max(0, self.attack_cooldown - 1)
        self.combo_timer = max(0, self.combo_timer - 1)
        if attack_pressed and self.attack_cooldown == 0:
            self.attack_timer = ATTACK_DURATION
            self.attack_cooldown = ATTACK_COOLDOWN
            # Combo (pedido do Raul): ainda dentro da janela do golpe
            # anterior avança pro próximo hit (ciclando 1-4); passou da
            # janela, volta pro 1 — ver COMBO_RESET_WINDOW.
            if self.combo_timer > 0:
                self.combo_count += 1
                if self.combo_count > COMBO_HIT_COUNT:
                    self.combo_count = 1
            else:
                self.combo_count = 1
            self.combo_timer = COMBO_RESET_WINDOW
            # 4 variações gravadas (sounds/punch/punch_1..4, ver
            # PLANO_AUDIO.md) — uma pra cada hit do combo, em vez de tocar
            # sempre o mesmo som de soco.
            audio.play_sfx(f"punch.punch_{self.combo_count}")
            if self.player.dashing:
                self.attack_power = DASH_ATTACK_POWER
            elif self.combo_count == COMBO_HIT_COUNT:
                self.attack_power = COMBO_FINISHER_POWER
            else:
                self.attack_power = STANDARD_ATTACK_POWER
        if self.attack_timer:
            self.attack_timer -= 1
            if self.attack_timer == 0:
                self.attack_power = STANDARD_ATTACK_POWER

    def _apply_attack_frame(self):
        """Sobrepõe o frame calculado por Player.animate() enquanto o golpe
        tá ativo — combo_count já reflete o hit certo desse swing (definido
        em _update_attack, sempre antes disso rodar, ver _update_playing).
        Fora daí Player.animate() decide sozinho (parado/andando/pulando)."""
        if not self.attack_timer:
            return
        self.player.frame = self.player.ATTACK_FRAMES[self.combo_count - 1]

    def _update_ranged_attack(self, ranged_pressed):
        self.ranged_cooldown = max(0, self.ranged_cooldown - 1)
        if not (ranged_pressed and self.ranged_unlocked and self.ranged_cooldown == 0):
            return
        self.ranged_cooldown = RANGED_ATTACK_COOLDOWN
        audio.play_sfx("projectile_sound")
        direction = 1 if self.player.facing_right else -1
        # Nasce um pouco à frente da hitbox, na altura do peito — assim o
        # projétil não colide "dentro" da própria Lia no quadro em que nasce.
        origin_x = self.player.rect.centerx + direction * (PLAYER_HITBOX_WIDTH // 2 + 8)
        origin_y = self.player.rect.centery - 4
        self.projectiles.append(
            Projectile(
                origin_x, origin_y, direction,
                RANGED_PROJECTILE_SPEED, RANGED_ATTACK_POWER, RANGED_PROJECTILE_RANGE,
            )
        )

    def _update_projectiles(self):
        """Move cada projétil e confere colisão contra os mesmos inimigos que
        check_enemies já usa pro ataque corpo a corpo (mesma interface
        take_hit/alive, incluindo chefes) — um acerto consome o projétil."""
        for projectile in self.projectiles:
            if not projectile.alive:
                continue
            projectile.update()
            if not projectile.alive:
                continue
            for enemy in self.level.enemies:
                if not enemy.alive:
                    continue
                if not projectile.rect.colliderect(enemy.rect):
                    continue
                if enemy.take_hit(projectile.power):
                    self.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                    if not enemy.alive:
                        self._on_enemy_defeated(enemy)
                projectile.alive = False
                break
        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]

    def _move_with_platform(self):
        if self.riding_platform:
            self.player.x += self.riding_platform.dx
            self.player.y += self.riding_platform.dy

    def _active_boss_arena(self):
        """Zona do chefe que Lia está atravessando agora, com o chefe ainda
        vivo (ver Level._make_boss_arenas: Rei Slime na Fase 1, Dragão na
        Fase 3) — None fora dela, ou depois do chefe morrer, o que libera a
        câmera/o limite horizontal de volta ao normal automaticamente."""
        for arena in getattr(self.level, "boss_arenas", ()):
            if arena["enemy"].alive and self.player.rect.colliderect(arena["zone"]):
                return arena["zone"]
        return None

    def _apply_boss_arena_clamp(self):
        """Enquanto dentro da arena de um chefe vivo, Lia não sai pelos
        lados (LEIA-ME_bosses_e_itens.md: "que Lia não consiga sair daquele
        campo de visão") — mesma ideia de trava de câmera de outros jogos,
        aqui aplicada também ao próprio jogador, não só à câmera."""
        zone = self._active_boss_arena()
        if not zone:
            return
        min_x = zone.left - PLAYER_HITBOX_OFFSET_X
        max_x = zone.right - PLAYER_HITBOX_OFFSET_X - PLAYER_HITBOX_WIDTH
        if max_x < min_x:
            max_x = min_x
        self.player.x = max(min_x, min(self.player.x, max_x))

    def _update_shake(self):
        self.shake_timer = max(0, self.shake_timer - 1)

    def _trigger_shake(self, duration, magnitude):
        """Genérico de propósito (não só do parry) — guarda a duração junto
        pra _shake_offset saber a proporção certa de decaimento, já que
        shake_timer sozinho não diz se começou em 14 quadros ou em 40."""
        self.shake_timer = duration
        self.shake_duration = duration
        self.shake_magnitude = magnitude

    def _shake_offset(self):
        if self.shake_timer <= 0 or self.shake_duration <= 0:
            return 0, 0
        # audio.shake_scale é a preferência de acessibilidade (0 desliga).
        magnitude = (
            self.shake_magnitude
            * (self.shake_timer / self.shake_duration)
            * audio.shake_scale
        )
        if magnitude <= 0:
            return 0, 0
        return random.uniform(-magnitude, magnitude), random.uniform(-magnitude, magnitude)

    def _update_camera(self):
        arena_zone = self._active_boss_arena()
        if arena_zone:
            self._update_boss_camera(arena_zone)
            return
        # Câmera antecipatória: desloca o alvo na direção pra onde a Lia
        # olha, então o jogador enxerga o caminho ANTES de chegar nele em
        # vez de ficar sempre centralizado. Como o alvo passa pela mesma
        # suavização de sempre (CAMERA_X_SMOOTHING), virar de lado desliza
        # em vez de dar um salto.
        look_ahead = CAMERA_LOOK_AHEAD * (1 if self.player.facing_right else -1)
        target_x = self.player.x + look_ahead - WIDTH * CAMERA_X_FOCUS
        self.camera_x += (target_x - self.camera_x) * CAMERA_X_SMOOTHING
        self.camera_x = max(0, min(self.camera_x, self.level.world_width - WIDTH))

        target_y = self.player.y - HEIGHT * CAMERA_Y_FOCUS
        self.camera_y += (target_y - self.camera_y) * CAMERA_Y_SMOOTHING
        self.camera_y = max(
            self.level.world_top,
            min(self.camera_y, self.level.world_height - HEIGHT),
        )

    def _update_boss_camera(self, zone):
        """Foca a arena inteira na tela (as duas são bem mais estreitas que
        WIDTH) em vez de seguir Lia — é isso que lê como "a câmera focou no
        chefe" em vez do scroll normal continuar."""
        if zone.width <= WIDTH:
            target_x = zone.centerx - WIDTH / 2
        else:
            target_x = self.player.x - WIDTH * CAMERA_X_FOCUS
        target_x = max(0, min(target_x, self.level.world_width - WIDTH))
        self.camera_x += (target_x - self.camera_x) * CAMERA_X_SMOOTHING

        target_y = self.player.y - HEIGHT * CAMERA_Y_FOCUS
        self.camera_y += (target_y - self.camera_y) * CAMERA_Y_SMOOTHING
        self.camera_y = max(
            self.level.world_top,
            min(self.camera_y, self.level.world_height - HEIGHT),
        )

    # Distância mínima entre poeiras consecutivas enquanto anda (em quadros).
    DUST_INTERVAL = 10

    def _update_vfx(self):
        """Avança as partículas ativas e dispara poeira ao andar / respingo
        ao entrar na água. O impacto (dano) é disparado nos próprios pontos
        onde o dano acontece — ver respawn() e check_enemies()."""
        self.vfx.update()
        player = self.player

        walking = (
            not player.swimming
            and self.player_grounded
            and abs(player.vx) > 0.2
        )
        if walking:
            self.dust_timer -= 1
            if self.dust_timer <= 0:
                self.vfx.spawn("dust", player.rect.centerx, player.rect.bottom)
                self.dust_timer = self.DUST_INTERVAL
        else:
            self.dust_timer = 0

        if player.swimming and not self.was_swimming:
            self.vfx.spawn("splash", player.rect.centerx, player.rect.centery)
        self.was_swimming = player.swimming

        # Poeira levantada pelo dash: reaproveita a partícula que já existe
        # em vez de mais retângulos azuis (draw_dash_trail continua, é o
        # rastro; isto é o pó que fica pra trás). Só no chão — debaixo
        # d'água o dash nem acontece (ver _update_playing).
        if player.dashing and self.player_grounded and player.dash_timer % 3 == 0:
            self.vfx.spawn("dust", player.rect.centerx, player.rect.bottom)

    def request_mouse_attack(self):
        """Registra o clique; o ataque será iniciado no próximo update."""
        self.mouse_attack_requested = True

    def move_player(self):
        """Resolve colisões horizontais, verticais e o pulo sobre inimigos."""
        player = self.player
        solids = self._all_solid_rectangles()
        player.swimming = self._player_in_water(player)
        if player.swimming:
            player.cancel_dash()

        previous_x = player.x
        player.x += player.vx
        self._resolve_horizontal_collisions(player, solids, previous_x)

        if player.swimming:
            player.apply_swim_gravity()
        else:
            player.apply_gravity()

        previous_y = player.y
        previous_bottom = previous_y + PLAYER_HEIGHT
        player.y += player.vy

        if not player.swimming and self._stomp_enemy_if_possible(player, previous_bottom):
            return

        landed = self._resolve_vertical_collisions(player, previous_y, previous_bottom)
        landed = self._resolve_ramp_collisions(player, landed)
        # Pouso: só no quadro em que ela ENCOSTA (não enquanto fica parada).
        if landed and not self.player_grounded and not player.swimming:
            player.start_squash("squash")
        self.player_grounded = landed
        # Espelha no próprio Player (pedido do Raul: pulo de 3 fases —
        # subindo/no ar/caindo — ver Player.animate) porque animate() roda
        # dentro da classe Player, sem acesso direto a self.player_grounded
        # daqui.
        player.grounded = landed
        if player.swimming:
            # Sem chão firme pra reaproveitar debaixo d'água.
            player.coyote_time = 0
        else:
            player.coyote_time = 7 if landed else max(0, player.coyote_time - 1)
        if player.try_jump():
            player.start_squash("stretch")
            audio.play_sfx("jump")

    def _player_in_water(self, player):
        return any(player.rect.colliderect(zone) for zone in self.level.water_zones)

    def _check_fog_barriers(self):
        """Fala de "bloqueio" na primeira vez que a Lia esbarra numa
        neblina ainda sólida (ver fog.FogBarrier) — só a fala; a neblina
        continua bloqueando fisicamente do mesmo jeito (ver
        _all_solid_rectangles), quem libera de verdade é
        _release_fog_barrier. barrier.encountered marca isso pra sempre
        nesta passagem pela fase (mesmo objeto Level entre entrar/sair de
        uma sala — ver enter_room/exit_room —, então não repete a fala à
        toa), e também é o que outro sistema (ex.: o elevador do
        laboratório escondido) pode checar pra saber se já pode ser usado."""
        if self.dialogue.active:
            return
        for barrier in self.level.fog_barriers:
            if barrier.encountered or not barrier.solid():
                continue
            if self.player.rect.colliderect(barrier.rect.inflate(12, 12)):
                barrier.encountered = True
                self.dialogue.start(
                    "Lia",
                    barrier.mensagem
                    or "Tem um campo de contenção aqui, não dá pra passar assim... preciso achar outro caminho.",
                )
                break

    def _release_fog_barrier(self, chave):
        """Chamado por quem completar o que libera uma neblina (ex.: o
        microscópio do laboratório escondido — ver
        minigame.MicroscopeMinigame/_finish_minigame) — inicia a
        animação de dissipar (fog.FogBarrier.release) em vez de sumir na
        hora. Sem efeito se nenhuma neblina desta fase tiver essa chave.
        A neblina vive no corredor principal, não na sala — se quem
        chamou isso estiver dentro de uma sala (self._base_level not
        None, ver enter_room), procura lá, não em self.level."""
        target_level = self._base_level if self._base_level is not None else self.level
        for barrier in target_level.fog_barriers:
            if barrier.chave == chave:
                barrier.release()

    def _all_solid_rectangles(self):
        # solids_near em vez de self.level.grounds inteiro: numa
        # fase grande (Fase 3, 315x100 tiles) essas listas passam de mil
        # retângulos, e checar todos 2x por quadro (colisão horizontal e
        # vertical) era o motivo real do lag reportado lá — ver
        # Level.solids_near/_build_solid_chunks.
        return (
            self.level.solids_near(self.player.rect)
            + [platform.rect for platform in self.level.platforms]
            + [barrier.rect for barrier in self.level.fog_barriers if barrier.solid()]
        )

    @staticmethod
    def _resolve_horizontal_collisions(player, solids, previous_x):
        """Pedido do Raul (melhorar colisões — às vezes dava pra entrar
        dentro de bloco): o teste antigo exigia `previous_right <=
        solid.left` (zero de tolerância) pra empurrar a Lia de volta pra
        fora. Isso só funciona se o quadro anterior tiver a hitbox
        COMPLETAMENTE fora do bloco — em qualquer situação que já comece
        um pouco embromada pra dentro (dash a 14px/quadro, ou o empurrão
        extra de uma plataforma móvel somado ao próprio vx no mesmo
        quadro, ver Game._move_with_platform, que roda ANTES daqui e já
        desloca previous_x), o teste falhava silenciosamente e ela ficava
        atravessando o bloco quadro após quadro sem nunca ser reposicionada.
        Comparar contra a borda OPOSTA do bloco (`solid.right`/`solid.left`)
        em vez da borda de entrada resolve isso: só deixa de empurrar pra
        fora quando ela já tiver saído por completo do outro lado (um
        "atravessou de ponta a ponta num quadro só" de verdade, que exigiria
        mais de ~32px de deslocamento horizontal num único quadro — bem
        acima de qualquer velocidade que a Lia atinge hoje)."""
        for solid in solids:
            if not player.rect.colliderect(solid):
                continue

            previous_right = previous_x + PLAYER_HITBOX_OFFSET_X + PLAYER_HITBOX_WIDTH
            previous_left = previous_x + PLAYER_HITBOX_OFFSET_X
            if player.vx > 0 and previous_right <= solid.right:
                player.x = solid.left - PLAYER_HITBOX_WIDTH - PLAYER_HITBOX_OFFSET_X
                player.cancel_dash()
            elif player.vx < 0 and previous_left >= solid.left:
                player.x = solid.right - PLAYER_HITBOX_OFFSET_X
                player.cancel_dash()

    def _stomp_enemy_if_possible(self, player, previous_bottom):
        for enemy in self.level.enemies:
            # Chefes (BOSS_DROP_TABLE = SlimeKing/Librarian/Specimen)
            # ficam de fora do pulo-que-mata: pousar na cabeça deles não pode
            # ser um jeito de matar em um golpe só uma luta pensada pra durar
            # vários acertos — pisar neles agora não faz nada de especial,
            # cai no contato normal (dano) tratado por check_enemies.
            if type(enemy).__name__ in BOSS_DROP_TABLE:
                continue
            if (
                enemy.alive
                and player.vy > 0
                and player.rect.colliderect(enemy.rect)
                and previous_bottom <= enemy.rect.top + 12
            ):
                enemy.stomp()
                self.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                self._on_enemy_defeated(enemy)
                player.y = enemy.rect.top - PLAYER_HEIGHT
                player.vy = -10.5
                return True
        return False

    def _on_enemy_defeated(self, enemy):
        """Chamado uma única vez, no quadro exato em que um inimigo morre
        (stomp() sempre mata; take_hit() só às vezes — ver check_enemies).
        Chefe larga o item de pesquisa garantido (BOSS_DROP_TABLE); inimigo
        comum sorteia contra ENEMY_DROP_TABLE. Slimes pequenos da Cisão e
        os dois chefes de sala antigos sem entrada em nenhuma tabela não
        largam nada."""
        name = type(enemy).__name__
        quest_item = BOSS_DROP_TABLE.get(name)
        if quest_item:
            audio.play_sfx("boss_death_sound")
            self._spawn_drop(quest_item, enemy.rect.centerx, enemy.rect.centery)
            return
        audio.play_sfx("enemy_death_sound")
        entry = ENEMY_DROP_TABLE.get(name)
        if entry and random.random() < entry[1]:
            self._spawn_drop(entry[0], enemy.rect.centerx, enemy.rect.centery)

    def _spawn_drop(self, item_key, x, y):
        self.pending_drops.append({"item": item_key, "x": x, "y": y})

    def _collect_drops(self, player):
        """Itens largados no chão (ver _spawn_drop) somem da lista assim que
        Lia encosta neles e entram no inventário — igual à pesquisa/achados,
        mas numa lista à parte (pending_drops), porque um item largado numa
        sala não deve reaparecer depois de sair dela (ver enter_room/
        exit_room/load_level, que zeram essa lista)."""
        if not self.pending_drops:
            return
        remaining = []
        for drop in self.pending_drops:
            pickup = pygame.Rect(0, 0, DROP_PICKUP_RADIUS * 2, DROP_PICKUP_RADIUS * 2)
            pickup.center = (drop["x"], drop["y"])
            if player.rect.colliderect(pickup):
                key = drop["item"]
                self.inventory[key] = self.inventory.get(key, 0) + 1
                self.show_message(f"Item obtido: {ITEM_DEFS[key]['name']}")
                audio.play_sfx("item_sound")
                self.vfx.spawn("dust", drop["x"], drop["y"])
            else:
                remaining.append(drop)
        self.pending_drops = remaining

    def _resolve_vertical_collisions(self, player, previous_y, previous_bottom):
        """Mesma correção de _resolve_horizontal_collisions (pedido do
        Raul — atravessar plataforma às vezes): a tolerância antiga de
        "+10"/"-10" era um número mágico fixo, sem relação com a espessura
        de verdade da plataforma/bloco — uma plataforma móvel fina ou uma
        queda rápida o bastante podia passar direto sem os 10px darem
        conta. Comparar contra a borda OPOSTA do sólido (`solid.bottom`/
        `solid.top`, igual ao equivalente horizontal) usa a espessura real
        dele como tolerância em vez de um valor fixo — só deixa de
        resolver quando ela já tiver atravessado o bloco INTEIRO num
        quadro só.

        Pedido do Raul (Fase 1 lagando muito depois de pintar chão de
        verdade): esta função ainda montava ground_solids a partir de
        self.level.grounds INTEIRO — TODO tile sólido do mapa, sem
        nenhum filtro — e testava colisão contra a lista toda a cada
        quadro. Isso passou despercebido no ajuste de lag da Fase 3
        porque na época só o lado horizontal (_all_solid_rectangles,
        chamado por move_player) tinha sido trocado pra usar
        Level.solids_near (chunks perto da Lia); o vertical continuou
        com a lista cheia, só que ninguém tinha chão pintado o
        suficiente pra sentir o custo — a Fase 1 só expôs o bug de
        verdade quando ganhou terreno real na camada Colisão. Mesmo
        remédio aqui: solids_near em vez da lista inteira."""
        landed = False
        self.riding_platform = None
        platform_solids = [
            (platform.rect, platform) for platform in self.level.platforms
        ]
        ground_solids = [
            (ground, None) for ground in self.level.solids_near(player.rect)
        ]

        for solid, moving_platform in platform_solids + ground_solids:
            if (
                player.rect.colliderect(solid)
                and player.vy >= 0
                and previous_bottom <= solid.bottom
            ):
                player.y = solid.top - PLAYER_HEIGHT
                player.vy = 0
                landed = True
                if moving_platform:
                    self.riding_platform = moving_platform
            elif (
                player.rect.colliderect(solid)
                and player.vy < 0
                and previous_y >= solid.top
            ):
                player.y = solid.bottom
                player.vy = 0
        return landed

    def _resolve_ramp_collisions(self, player, landed):
        """Colisão SAT de verdade pras rampas (pedido do Raul), separada
        da lista de sólidos genérica em AABB (_all_solid_rectangles):
        toda rampa (ver ramp.Ramp) tem um canto vazio dentro do próprio
        retângulo delimitador (a ponta baixa dela) que NÃO pode bloquear
        nada — só o triângulo de verdade bloqueia. Por isso cada rampa
        roda seu próprio teste (Ramp.resolve, Separating Axis Theorem
        entre a hitbox retangular da Lia e o triângulo), em vez de entrar
        na lista tratada como bloco cheio.

        O broad-phase (`colliderect` contra o retângulo delimitador, bem
        mais barato que o SAT) evita rodar o teste de verdade pra rampas
        longe dela. Quando há colisão de fato, o vetor devolvido (dx, dy)
        já é o suficiente pra reposicionar — dy negativo (empurrada pra
        cima) conta como pouso igual a uma plataforma normal (zera vy,
        libera pulo/coyote time do jeito de sempre); dx dominante (bateu
        de lado, ex.: a perna vertical no topo de uma rampa "\\" andando
        da direita) cancela o dash, mesmo tratamento de uma parede."""
        for ramp in self.level.ramps:
            if not player.rect.colliderect(ramp.rect):
                continue
            mtv = ramp.resolve(player.rect)
            if mtv is None:
                continue
            dx, dy = mtv
            player.x += dx
            player.y += dy
            if dy < 0 and player.vy >= 0:
                player.vy = 0
                landed = True
            elif dy > 0 and player.vy < 0:
                player.vy = 0
            if abs(dx) > abs(dy):
                player.cancel_dash()
        return landed

    def check_events(self):
        player = self.player
        if player.y > self.level.world_height + 180:
            self.respawn()
            return

        self.invuln_timer = max(0, self.invuln_timer - 1)
        if self._update_oxygen(player):
            return
        if self._check_hazards(player):
            return
        self._check_parries(player)
        if self._check_enemy_attack_hazards(player):
            return

        self.check_enemies()
        self._update_projectiles()
        if self.state != PLAYING:
            return
        self._collect_drops(self.player)
        if self.level.room:
            # Dentro de uma sala secundária não há checkpoint, pesquisa
            # obrigatória nem avanço de fase — só o achado opcional, as
            # peças do microscópio do laboratório escondido (se for o
            # caso, ver Level.lab_microscope_parts) e a porta de saída
            # (tratada em handle_interactions).
            self._collect_artifacts(player)
            self._collect_tools(player)
            self._collect_lab_microscope_parts(player)
            return
        self._check_checkpoints(player)
        if self._collect_research(player):
            return
        self._collect_microscope_parts(player)
        if self._start_pending_dialogue(player):
            return
        self._advance_level_if_ready(player)

    def _collect_artifacts(self, player):
        for index, (item, name) in enumerate(self.level.artifacts):
            if index in self.artifacts_collected or not player.rect.colliderect(item):
                continue
            self.artifacts_collected.add(index)
            self.show_message(f"Achado: {name}")
            audio.play_sfx("item_sound")
            lore = ROOM_LORE.get(name, DEFAULT_ROOM_LORE)
            self.dialogue.start("Lia", lore)
            return True
        return False

    def _collect_tools(self, player):
        """Ferramentas largadas no mapa (hoje só a chave de fenda — ver
        Level._make_tool_pickups, PLANO_MINIGAMES.md §3.1). Mesmo padrão de
        índice de _collect_artifacts/_collect_research, mas vai pro
        inventário em vez de um set separado, porque a chave se comporta
        como qualquer outro item (aparece na barra, ver ITEM_DEFS)."""
        for index, (item, item_key) in enumerate(self.level.tool_pickups):
            if index in self.tools_collected or not player.rect.colliderect(item):
                continue
            self.tools_collected.add(index)
            self.inventory[item_key] = self.inventory.get(item_key, 0) + 1
            self.show_message(f"Item obtido: {ITEM_DEFS[item_key]['name']}")
            audio.play_sfx("item_sound")

    def _update_oxygen(self, player):
        """Consome o fôlego enquanto a cabeça está submersa em alguma zona de
        água (Level.water_zones); recarrega assim que ela sai. Como o rect da
        cabeça só limpa a zona onde o teto tem uma folga acima da superfície
        (bolsão de ar), isso já implementa naturalmente os bolsões de ar da
        caverna submersa sem precisar de geometria especial por bolsão."""
        head = player.head_rect
        breathing = not any(head.colliderect(zone) for zone in self.level.water_zones)
        if breathing:
            player.oxygen = min(player.OXYGEN_MAX_FRAMES, player.oxygen + player.OXYGEN_REFILL_PER_FRAME)
            return False
        # Sem esse guard, ela tomaria dano TODO quadro parada embaixo
        # d'água sem ar (não reposiciona mais pra fora da água — ver
        # take_damage) — o mesmo guard que _check_hazards/
        # _check_enemy_attack_hazards já usavam, só que esse aqui não
        # existia porque antes respawn() sempre tirava ela dali na hora.
        if self.invuln_timer > 0:
            return False
        player.oxygen = max(0, player.oxygen - player.OXYGEN_DRAIN_PER_FRAME)
        if player.oxygen <= 0:
            # Afogar não é "chefe" nem "mob" — cai no mesmo balde dos
            # hazards ambientais (MOB_CONTACT_DAMAGE), não no dano cheio de
            # chefe.
            self.take_damage(MOB_CONTACT_DAMAGE)
            return True
        return False

    def _check_hazards(self, player):
        if self.invuln_timer > 0:
            return False
        # Espinho/lava são hazard ambiental, não "chefe" — mesmo dano de
        # mob comum (ver MOB_CONTACT_DAMAGE).
        for hazard in self.level.hazards:
            if player.rect.colliderect(hazard):
                self.take_damage(MOB_CONTACT_DAMAGE)
                return True
        for lake in self.level.lava_lakes:
            if player.rect.colliderect(lake):
                self.take_damage(MOB_CONTACT_DAMAGE)
                return True
        return False

    def _check_enemy_attack_hazards(self, player):
        """Feixe do jato do espécime, onda do Silêncio e tomos do Errata: os
        três alcançam além da hitbox do próprio inimigo (ver
        Enemy.active_hazards em enemy.py), então não bastam o teste de
        colisão corpo-a-corpo normal de check_enemies."""
        if self.invuln_timer > 0:
            return False
        for enemy in self.level.enemies:
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
                    self.take_damage(BOSS_CONTACT_DAMAGE)
                    return True
        return False

    def _check_parries(self, player):
        """Parry (pedido do Raul): só hazards que "voam" — pedras/meteoros
        do Dragão ainda caindo, tomos mergulhando e lâminas do Bibliotecário,
        jato do Espécime (ver <Boss>.parryable_hazards em enemy.py) — nunca
        ondas no chão nem investidas corpo a corpo, essas classes nem
        definem o método, então getattr cai em None e passa reto. Sem botão
        novo: é o mesmo attack_box do ataque corpo a corpo normal
        (_attack_box), só que testado ANTES de _check_enemy_attack_hazards
        pra um parry bem-sucedido não também respawnar a Lia no mesmo
        quadro. Acerto certo: cancel() destrói o hazard específico e o dano
        volta pro chefe que o lançou via take_hit — mesma interface que o
        ataque à distância já usa pra furar melee_vulnerable."""
        attack_box = self._attack_box()
        if not attack_box:
            return False
        for enemy in self.level.enemies:
            if not enemy.alive:
                continue
            get_pairs = getattr(enemy, "parryable_hazards", None)
            if not get_pairs:
                continue
            for rect, cancel in get_pairs():
                if not attack_box.colliderect(rect):
                    continue
                cancel()
                self.vfx.spawn("parry_flash", rect.centerx, rect.centery)
                # 1s de invencibilidade (pedido do Raul) pra sobreviver ao
                # resto de um ataque com vários hits (ex.: as 5 lâminas do
                # Bibliotecário) depois de aparar só o primeiro — max() pra
                # nunca ENCURTAR um invuln maior já rolando (ex.: acabou de
                # respawnar). Hit-stop + shake dão o "peso" do acerto.
                self.invuln_timer = max(self.invuln_timer, PARRY_INVULN_FRAMES)
                self.hitstop_timer = PARRY_HITSTOP_FRAMES
                self._trigger_shake(PARRY_SHAKE_DURATION, PARRY_SHAKE_MAGNITUDE)
                audio.play_sfx("parry_sound")
                if enemy.take_hit(PARRY_DAMAGE) and not enemy.alive:
                    self._on_enemy_defeated(enemy)
                return True
        return False

    def _check_checkpoints(self, player):
        for checkpoint in self.level.checkpoints:
            if player.rect.colliderect(checkpoint):
                new_checkpoint = (checkpoint.x, checkpoint.bottom - PLAYER_HEIGHT)
                if new_checkpoint != self.checkpoint:
                    audio.play_sfx("checkpoint_sound")
                    self.checkpoint = new_checkpoint
                    self.save_progress()
                self.checkpoint = new_checkpoint
                self.show_message("Checkpoint: Centro de pesquisa alcançado!")

    def _collect_research(self, player):
        for index, (item, name) in enumerate(self.level.research):
            if index in self.collected or not player.rect.colliderect(item):
                continue

            self.collected.add(index)
            self.show_message(f"Parte da pesquisa obtida: {name}")
            audio.play_sfx("item_sound")
            fact = SCIENCE_FACTS.get(name, DEFAULT_SCIENCE_FACT)
            self.dialogue.start("Ciência Delas", fact)
            return True
        return False

    def _collect_microscope_parts(self, player):
        if not (self.level.is_underground and self.sequence_solved):
            return
        for index, (item, _) in enumerate(self.level.microscope_parts):
            if index not in self.microscope_collected and player.rect.colliderect(item):
                self.microscope_collected.add(index)
                audio.play_sfx("item_sound")

    def _collect_lab_microscope_parts(self, player):
        """Peças do microscópio do laboratório ESCONDIDO (ver
        Level._make_lab_microscope_parts) — sem nenhuma condição prévia
        (ao contrário de _collect_microscope_parts, que exige a
        sequência antiga resolvida): a sala em si só é alcançável depois
        do elevador liberado, isso já é gate suficiente."""
        for index, (item, _name) in enumerate(self.level.lab_microscope_parts):
            if index not in self.lab_microscope_collected and player.rect.colliderect(item):
                self.lab_microscope_collected.add(index)
                audio.play_sfx("item_sound")

    def _use_lab_microscope_bench(self, player):
        """Bancada do laboratório escondido (ver Level._make_lab_bench) —
        mesmo formato de _use_microscope_bench, mas totalmente
        independente: progresso próprio (lab_microscope_*) e libera uma
        fog.FogBarrier (propriedade "libera" do objeto "bancada_
        microscopio") em vez de ativar rota de retorno nenhuma."""
        if self.level.lab_bench is None:
            return False
        if not player.rect.colliderect(self.level.lab_bench["rect"].inflate(70, 60)):
            return False
        if len(self.lab_microscope_collected) < len(self.level.lab_microscope_parts):
            self.dialogue.start("Lia", "Ainda faltam peças para montar o microscópio.")
            return True
        if not self.lab_microscope_assembled:
            self._open_lab_microscope_minigame()
        return True

    def _open_lab_microscope_minigame(self):
        # "Montado" do minigame = a MESMA bancada_microscopio.png que
        # aparece no mundo depois de resolvido (ver
        # Level._draw_lab_microscope/lab_bench_assembled) — mais simples
        # que recompor de body+4 peças (ver _compose_microscope, mantido
        # como reserva) e ainda reforça visualmente "é essa bancada aqui".
        # Sem o arquivo ainda, cai pro microscope_complete.png de sempre.
        complete_sprite = self.assets.puzzle_sprites.get("lab_bench_assembled") or self.assets.puzzle_sprites["microscope_complete"]
        self.minigame.open(
            MicroscopeMinigame(
                WIDTH,
                HEIGHT,
                self._microscope_sprites_by_identity(),
                complete_sprite,
                self.lab_microscope_slots,
                key="lab_microscope",
            )
        )

    def _lab_microscope_sprites(self):
        """Empacota as MESMAS sprites do microscópio (ver
        _microscope_sprites_by_identity) no formato que
        Level._draw_lab_microscope espera — lista simples por posição em
        vez de dict por identidade, igual ao antigo puzzle_sprites[
        "microscope_parts"] já usava."""
        return {
            "parts": self.assets.puzzle_sprites["microscope_parts"],
            "complete": self.assets.puzzle_sprites["microscope_complete"],
            "bench_empty": self.assets.puzzle_sprites.get("lab_bench_empty"),
            "bench_assembled": self.assets.puzzle_sprites.get("lab_bench_assembled"),
        }

    def _start_pending_dialogue(self, player):
        for index, (position, speaker, text) in enumerate(self.level.data["dialogues"]):
            if index not in self.seen_dialogues and player.x >= position:
                self.seen_dialogues.add(index)
                self.dialogue.start(speaker, text)
                return True
        return False

    def _advance_level_if_ready(self, player):
        if player.x < self.level.world_width - 100:
            return

        needs_microscope = (
            self.level.is_underground and not self.level.room and not self.lab_microscope_assembled
        )
        missing_items = [
            key for key in PHASE_REQUIRED_ITEMS.get(self.level.index, ())
            if self.inventory.get(key, 0) <= 0
        ]
        if len(self.collected) < len(self.level.research) or needs_microscope:
            self.show_message(
                "Encontre todas as partes da pesquisa antes de avançar.",
                MESSAGE_DURATION_LONG,
            )
            player.x = self.level.world_width - 160
        elif missing_items:
            names = ", ".join(ITEM_DEFS[key]["name"] for key in missing_items)
            self.show_message(f"Ainda falta: {names}.", MESSAGE_DURATION_LONG)
            player.x = self.level.world_width - 160
        elif self.level.index == VILLAGE:
            # Fim da rua da vila = caminho pra floresta → Fase 1 (ver
            # PLANO_VILA.md). Não é "fase+1" porque VILLAGE não é um índice
            # numérico — cai fora de PHASES de propósito.
            self.load_level(0)
            self.save_progress()
        elif self.level.index == len(PHASES) - 1:
            self.state = COMPLETE
        else:
            finished_index = self.level.index
            self.load_level(finished_index + 1)
            # load_level já sobrescreveu self.message com o subtítulo da fase
            # nova (message_timer=0, ver load_level) — o aviso de desbloqueio
            # entra DEPOIS de propósito, pra não ser apagado por ele.
            if finished_index == 0 and not self.ranged_unlocked:
                self.ranged_unlocked = True
                self.show_message(
                    "Novo poder: Ataque à Distância [R] desbloqueado!",
                    MESSAGE_DURATION_LONG,
                )
            self.save_progress()

    def check_enemies(self):
        """Verifica ataque, ataque reforçado durante dash e contato com slimes.
        `melee_vulnerable` (Librarian/Specimen em enemy.py — os
        inimigos comuns e o Rei Slime não definem isso, então getattr cai em
        True) deixa um chefe imune a corpo a corpo em certas fases (ex.:
        voando, escudo levantado, dentro do casulo); nesses momentos,
        acertar o corpo dele com a espada não causa dano — só o ataque à
        distância funciona — mas ainda dói tocar nele."""
        attack_box = self._attack_box()
        # O dano de contato era resolvido com um `return` no meio do laço:
        # ao encostar num inimigo, todos os que vinham DEPOIS dele na lista
        # não eram testados pro golpe de espada naquele quadro — com vários
        # mobs juntos, acertar quem estava atrás virava loteria. Agora o
        # laço vai até o fim e o contato é aplicado uma única vez no final
        # (o pior contato do quadro; ver `contact_damage`).
        contact_damage = 0
        for enemy in self.level.enemies:
            if not enemy.alive:
                continue
            is_boss = type(enemy).__name__ in BOSS_DROP_TABLE
            melee_hit = (
                attack_box
                and attack_box.colliderect(enemy.rect)
                and getattr(enemy, "melee_vulnerable", True)
            )
            if melee_hit:
                if enemy.take_hit(self.attack_power):
                    self.hitstop_timer = max(self.hitstop_timer, HIT_STOP_FRAMES)
                    self.vfx.spawn("impact", enemy.rect.centerx, enemy.rect.centery)
                    if not enemy.alive:
                        self._on_enemy_defeated(enemy)
                    else:
                        audio.play_sfx("boss_hit_sound" if is_boss else "enemy_hit_sound")
            elif self.player.rect.colliderect(enemy.rect):
                damage = BOSS_CONTACT_DAMAGE if is_boss else MOB_CONTACT_DAMAGE
                contact_damage = max(contact_damage, damage)
        if contact_damage and self.invuln_timer <= 0:
            self.take_damage(contact_damage)

    def _attack_box(self):
        if not self.attack_timer:
            return None
        # Comparar poderes (`attack_power > STANDARD_ATTACK_POWER`) acoplava
        # "alcance" a "dano": bastou STANDARD_ATTACK_POWER virar 100 pra o
        # golpe de dash perder o alcance estendido sem ninguém notar. Agora
        # o alcance vem do que está acontecendo de fato.
        reach = DASH_ATTACK_REACH if self.player.dashing else STANDARD_ATTACK_REACH
        offset = (
            PLAYER_HITBOX_WIDTH
            if self.player.facing_right
            else -(24 + reach)
        )
        return self.player.rect.move(offset, 4).inflate(reach, 10)

    def handle_interactions(self):
        """Processa portas (qualquer fase), a caixa de energia (sala do
        laboratório, Fase 2) e, na Fase 1 subterrânea, painel, botões e
        bancada do laboratório."""
        if not self.interact_pressed:
            return
        if self._use_doors():
            return
        if self._use_secret_elevator():
            return
        if self._talk_to_npc():
            return
        if self.level.room == "laboratorio" and self._use_energy_box(self.player):
            return
        if self.level.room == "laboratorio_secreto" and self._use_lab_microscope_bench(self.player):
            return
        if not self.level.is_underground or self.level.room:
            # "or self.level.room": o laboratório escondido tem
            # index==0 (is_underground True) mas não usa NADA do sistema
            # antigo abaixo (painel/botões/bancada do corredor) — sem
            # este corte, _use_microscope_bench quebraria tentando usar
            # self.level.bench, que fica None numa sala
            # (ver Level._reset_lab_state).
            return

        player = self.player
        if self._use_panel_lever(player):
            return
        if self._use_sequence_button(player):
            return
        self._use_microscope_bench(player)

    def _use_energy_box(self, player):
        """Caixa de energia (Fase 2, laboratório — ver PLANO_MINIGAMES.md
        §3.2/§3.3). self.level.energy_box é None em qualquer mapa sem o
        objeto "caixa_energia" ainda (ver Level._make_energy_box), e
        self.assets.energy_box_sprites é None enquanto faltar algum arquivo de
        arte (ver _load_energy_box_sprites) — os dois casos fazem esse
        método devolver False sem fazer nada, exatamente como se a caixa
        não existisse no jogo ainda."""
        if self.level.energy_box is None or self.assets.energy_box_sprites is None:
            return False
        if not player.rect.colliderect(self.level.energy_box.inflate(70, 60)):
            return False
        if self.energy_box_state["wired"]:
            self.dialogue.start("Lia", "A caixa de energia está funcionando normalmente.")
            return True
        if not self.energy_box_state["screws_removed"] and self.inventory.get("chave_fenda", 0) <= 0:
            self.dialogue.start("Lia", "A tampa está parafusada. Preciso de uma chave de fenda.")
            return True
        self.minigame.open(
            EnergyBoxMinigame(
                WIDTH,
                HEIGHT,
                self.assets.energy_box_sprites,
                self.energy_box_state,
                self.energy_box_wires,
            )
        )
        return True

    DOOR_INTERACT_RANGE = 40

    def _use_doors(self):
        player = self.player
        for door in self.level.doors:
            if not player.rect.colliderect(door["rect"].inflate(self.DOOR_INTERACT_RANGE, self.DOOR_INTERACT_RANGE)):
                continue
            audio.play_sfx("door_sound")
            if door["target"] == "sair":
                self.exit_room()
            else:
                self.enter_room(door["target"])
            return True
        return False

    SECRET_ELEVATOR_RANGE = 40

    def _use_secret_elevator(self):
        """Elevador secreto (objeto "elevador_lab" — ver
        Level._make_secret_elevators e a conversa sobre o "elevador
        chat"). Mesmo raio/formato de _use_doors, mas a troca de sala só
        acontece depois de uma cutscene curta (ver
        elevator_cutscene.ElevatorCutscene): do lado de fora, o elevador
        só funciona depois da Lia esbarrar no bloqueio de neblina ligado
        a ele pela propriedade "chave" (ver _check_fog_barriers, que
        marca barrier.encountered) — do lado de dentro da sala (objeto
        sem "chave", destino "sair"), sempre funciona."""
        if self.elevator_cutscene.active:
            return False
        player = self.player
        for elevator in self.level.secret_elevators:
            if not player.rect.colliderect(
                elevator["rect"].inflate(self.SECRET_ELEVATOR_RANGE, self.SECRET_ELEVATOR_RANGE)
            ):
                continue
            if elevator["chave"] and not self._fog_barrier_encountered(elevator["chave"]):
                self.dialogue.start(
                    "Lia",
                    "Melhor eu não usar isso ainda — vou ver o que tem lá na frente primeiro.",
                )
                return True
            audio.play_sfx("door_sound")
            if elevator["destino"] == "sair":
                self.elevator_cutscene.start(reverse=True, on_finish=self.exit_room)
            else:
                target = elevator["destino"]
                self.elevator_cutscene.start(reverse=False, on_finish=lambda: self.enter_room(target))
            return True
        return False

    def _fog_barrier_encountered(self, chave):
        return any(
            barrier.chave == chave and barrier.encountered
            for barrier in self.level.fog_barriers
        )

    NPC_INTERACT_RANGE = 40

    def _talk_to_npc(self):
        """Os NPCs nunca são consumidos — dá pra falar com eles quantas
        vezes quiser (ver NPC_DIALOGUES). Mesmo raio/padrão de detecção das
        portas, só que contra Level.npcs. NPC_DIALOGUES[nome] pode ser uma
        string (fala única, a maioria) ou uma tupla (várias falas em
        sequência, ex.: Sra. Amélia na vila) — nesse caso só a primeira
        entra aqui; o resto é consumido por _update_dialogue a cada [E]
        seguinte, via self._npc_dialogue_queue."""
        player = self.player
        for npc in self.level.npcs:
            if not player.rect.colliderect(npc["rect"].inflate(self.NPC_INTERACT_RANGE, self.NPC_INTERACT_RANGE)):
                continue
            text = NPC_DIALOGUES.get(npc["name"])
            if isinstance(text, tuple):
                if text:
                    self._npc_dialogue_speaker = npc["name"]
                    self._npc_dialogue_queue = list(text[1:])
                    self.dialogue.start(npc["name"], text[0])
            elif text:
                self._npc_dialogue_queue = []
                self.dialogue.start(npc["name"], text)
            return True
        return False

    

    def _use_panel_lever(self, player):
        if not player.rect.colliderect(self.level.panel_lever.inflate(55, 55)):
            return False

        audio.play_sfx("lever_sound")
        self.lever_on = not self.lever_on
        self.level.set_lever_active("panel", self.lever_on)
        if self.lever_on:
            self.dialogue.start(
                "Lia",
                "A alavanca ligou o painel. A ordem é: azul, verde, amarelo e vermelho.",
            )
        else:
            self.sequence_progress = 0
            self.dialogue.start("Lia", "A alavanca desligou o painel.")
        return True

    def _use_sequence_button(self, player):
        for index, button in enumerate(self.level.buttons):
            if not player.rect.colliderect(button.inflate(55, 55)):
                continue
            if not self.lever_on:
                self.dialogue.start(
                    "Painel",
                    "O painel está sem energia. Encontre e puxe a alavanca.",
                )
            elif self.sequence_solved:
                self.dialogue.start(
                    "Painel",
                    "Sequência concluída. As peças do microscópio foram liberadas.",
                )
            elif index == self.sequence_progress:
                audio.play_sfx("button_sound")
                self.sequence_progress += 1
                if self.sequence_progress == len(self.level.buttons):
                    self.sequence_solved = True
                    audio.play_sfx("correct_sequence_sound")
                    self.dialogue.start(
                        "Painel",
                        "Sequência correta! As peças do microscópio foram liberadas.",
                    )
            else:
                audio.play_sfx("wrong_sequence_sound")
                self.sequence_progress = 0
                self.dialogue.start("Painel", "Sequência incorreta. O painel foi reiniciado.")
            return True
        return False

    def _use_microscope_bench(self, player):
        # Puzzle antigo (área subterrânea) — objetos "parte_microscopio"/
        # "bancada" saíram do fase1_escola.tmx, então sem peça nenhuma
        # cadastrada não tem bancada de verdade pra usar (sem essa guarda,
        # "0 peças coletadas < 0 peças no mapa" dá False e abriria o
        # minigame à toa perto do retângulo de fallback de Level.bench).
        if not self.level.microscope_parts:
            return
        if not player.rect.colliderect(self.level.bench.inflate(70, 60)):
            return
        if len(self.microscope_collected) < len(self.level.microscope_parts):
            self.dialogue.start("Lia", "Ainda faltam peças para montar o microscópio.")
        elif not self.microscope_assembled:
            self._open_microscope_minigame()

    # Ordem fixa de carregamento em _load_puzzle_sprites (lens, base,
    # light, ocular) — não tem relação com a ordem de Level.microscope_parts
    # (que é sobre onde as peças nascem largadas no mapa, não sobre qual
    # sprite é qual peça), então esse mapeamento é sempre o mesmo,
    # independente de fase/room/Tiled.
    MICROSCOPE_SPRITE_IDENTITY_ORDER = ("objetiva", "base", "iluminador", "ocular")

    def _microscope_sprites_by_identity(self):
        sprites = self.assets.puzzle_sprites["microscope_parts"]
        return dict(zip(self.MICROSCOPE_SPRITE_IDENTITY_ORDER, sprites))

    def _open_microscope_minigame(self):
        self.minigame.open(
            MicroscopeMinigame(
                WIDTH,
                HEIGHT,
                self._microscope_sprites_by_identity(),
                self.assets.puzzle_sprites["microscope_complete"],
                self.microscope_slots,
                body_sprite=self.assets.puzzle_sprites.get("microscope_body"),
            )
        )

    def draw(self, screen):
        real_surface = screen.surface
        # Os dois fill((6,14,29)) que ficavam aqui e logo abaixo saíram:
        # _draw_background sempre cobre a superfície inteira (ladrilha ou
        # preenche) e _blit_zoomed_world sempre cobre a tela inteira. Eram
        # ~1,6 ms por quadro pintando pixels sobrescritos no blit seguinte.
        # Se um dia entrar um estado novo que NÃO cubra a tela toda, ele
        # precisa preencher o fundo por conta própria.
        if self.state == INTRO:
            self.intro.draw(real_surface, draw_text)
            return
        if self.elevator_cutscene.active:
            self.elevator_cutscene.draw(real_surface, draw_text)
            return
        if self.state in (TITLE, SETTINGS, PAUSED):
            # O mundo inteiro era desenhado (~7 ms/quadro medidos) só pra
            # ficar embaixo de um _dim_background(alpha=210) quase opaco. Um
            # instantâneo tirado uma vez dá exatamente o mesmo visual de
            # graça — nada se move atrás do menu, já que update() nesses dois
            # estados só roda _update_title/_update_settings.
            if self._menu_snapshot is None:
                # Já sai ESCURECIDO: no título e nas configurações o alpha é
                # sempre o mesmo (MENU_DIM_ALPHA), então compor uma vez evita
                # também o blit translúcido de tela cheia por quadro.
                snapshot = self._render_world_snapshot()
                self._dim_background(snapshot, self.MENU_DIM_ALPHA)
                self._menu_snapshot = snapshot
            real_surface.blit(self._menu_snapshot, (0, 0))
            self._draw_state_overlay(real_surface)
            return
        # Mundo inteiro continua desenhado do jeito de sempre, só que numa
        # surface separada do mesmo tamanho (WIDTH x HEIGHT) em vez de ir
        # direto pra tela — _blit_zoomed_world recorta uma janela menor
        # centrada na Lia e amplia pro tamanho da tela (ver CAMERA_ZOOM em
        # settings.py). Isso dá o efeito de zoom sem precisar mexer em
        # nenhuma conta de câmera/parallax/HUD já existente.
        if self._world_surface is None:
            self._world_surface = pygame.Surface((WIDTH, HEIGHT)).convert()
        surface = self._world_surface
        # Shake (ver _trigger_shake/_update_shake) só desloca o mundo — a
        # câmera some pro valor de verdade logo antes do HUD, senão a barra
        # de vida do chefe e o resto da interface também tremeriam junto,
        # o que fica ilegível em vez de impactante.
        shake_x, shake_y = self._shake_offset()
        self.camera_x += shake_x
        self.camera_y += shake_y
        self._draw_background(surface)
        self._draw_world(surface)
        self._draw_door_prompts(surface)
        self._draw_npc_prompts(surface)
        self._draw_player_light(surface)
        self.draw_dash_trail(surface)
        self.player.draw(surface, self.camera_x, self.camera_y)
        self._draw_world_foreground(surface)
        self.vfx.draw(surface, self.camera_x, self.camera_y)
        for projectile in self.projectiles:
            projectile.draw(surface, self.camera_x, self.camera_y)
        self.camera_x -= shake_x
        self.camera_y -= shake_y
        self._blit_zoomed_world(real_surface, surface)
        self._draw_interface(real_surface)
        self._draw_state_overlay(real_surface)
        self.hint.draw(real_surface, draw_text)
        self.minigame.draw(real_surface, draw_text)

    def _render_world_snapshot(self):
        """Desenha o mundo uma única vez numa Surface própria, pro menu usar
        como pano de fundo estático (ver draw). Reaproveita exatamente o
        mesmo caminho de desenho do jogo, então o visual é idêntico ao que o
        menu mostrava antes — só que calculado uma vez em vez de 60x/s."""
        snapshot = pygame.Surface((WIDTH, HEIGHT)).convert()
        world = pygame.Surface((WIDTH, HEIGHT)).convert()
        self._draw_background(world)
        self._draw_world(world)
        self._draw_player_light(world)
        self.player.draw(world, self.camera_x, self.camera_y)
        self._draw_world_foreground(world)
        self._blit_zoomed_world(snapshot, world)
        self._draw_interface(snapshot)
        return snapshot

    def _blit_zoomed_world(self, real_surface, world_surface):
        """Recorta uma janela CAMERA_ZOOM vezes menor que a tela, centrada
        na Lia, e amplia de volta pro tamanho cheio — o mesmo truque de
        "recorta e amplia" que usamos pro tamanho do sprite dela, só que
        aplicado no frame inteiro. Roda uma vez por quadro (pygame.transform
        .scale é C puro, não pesa)."""
        if CAMERA_ZOOM == 1:
            real_surface.blit(world_surface, (0, 0))
            return
        crop_width = max(1, round(WIDTH / CAMERA_ZOOM))
        crop_height = max(1, round(HEIGHT / CAMERA_ZOOM))
        player_screen_x = self.player.rect.centerx - self.camera_x
        player_screen_y = self.player.rect.centery - self.camera_y
        crop_x = round(player_screen_x - crop_width / 2)
        crop_y = round(player_screen_y - crop_height / 2)
        crop_x = max(0, min(crop_x, WIDTH - crop_width))
        crop_y = max(0, min(crop_y, HEIGHT - crop_height))
        cropped = world_surface.subsurface(
            pygame.Rect(crop_x, crop_y, crop_width, crop_height)
        )
        scaled = pygame.transform.scale(cropped, (WIDTH, HEIGHT))
        real_surface.blit(scaled, (0, 0))

    # Y a partir do qual o cenário conta como "subterrâneo". Calibrado pro
    # mapa antigo da Fase 1 — reajustar quando o laboratório novo existir de
    # verdade no .tmx (ver PLANO_FASE1.md, item 1).
    UNDERGROUND_Y = 780

    # Fator de parallax por fundo (<1.0 anda mais devagar que a câmera).
    PARALLAX = {
        "school": 0.3, "village": 0.3, "cave": 0.35,
        "university": 1.0, "lab": 1.0, "library": 1.0,
    }

    def _draw_background(self, surface):
        """Um único blit opaco por ladrilho, sem nenhum overlay depois — a
        cor de cena já veio composta na imagem (ver _load_backgrounds)."""
        variant = self._background_variant()
        key = self._background_key()
        if key == "village" and self.assets.village_layers:
            self._draw_village_parallax(surface, variant)
            return
        images = self.assets.backgrounds.get(key)
        if images is None:
            # Nenhuma arte de fundo disponível pra este contexto (hoje só a
            # vila sem ceu.png nem o pack GrassLand) — céu liso, que também
            # cobre a tela toda.
            surface.fill(self.assets.VILLAGE_PLACEHOLDER_SKY)
            return
        image = images[variant]
        if key == "university":
            self.draw_university_background(surface, image, variant)
        else:
            self._draw_repeating_background(
                surface, image, parallax=self.PARALLAX.get(key, 1.0)
            )

    def _draw_village_parallax(self, surface, variant):
        """5 camadas do GrassLand, cada uma ladrilhada na sua própria
        velocidade de parallax (ver VILLAGE_PARALLAX_LAYERS) — a 1 (céu,
        opaca) cobre a tela inteira primeiro, então as de cima já blitam
        transparência sobre um fundo opaco, sem risco de "vazar" cor onde
        deveria ficar vazio (ver _load_village_parallax_layers)."""
        for layer in self.assets.village_layers:
            image = layer["variants"][variant]
            self._draw_repeating_background(surface, image, parallax=layer["parallax"])

    def _background_key(self):
        """Qual fundo este contexto usa. A ordem reproduz exatamente a
        cascata de ifs que existia em _draw_background."""
        if self.level.room in ("laboratorio", "laboratorio_secreto"):
            # O laboratório ESCONDIDO da Fase 1 não estava nesta cascata: caía
            # no `return "village"` lá embaixo e a sala inteira aparecia com o
            # CÉU AZUL da Fase 1 atrás das paredes. Usa a mesma arte da sala de
            # laboratório da Fase 2 (lab_background.png), sem arte nova.
            return "lab"
        if self.level.room == "biblioteca":
            return "library"
        if self.level.index == 1:
            return "university"
        if self.level.index == 2:
            return "cave"
        # Fase 1 e vila compartilham o céu novo (pedido do Raul: "vai ficar
        # melhor"); sem as camadas do GrassLand nem ceu.png, a Fase 1 cai no
        # fundo antigo da escola e a vila no preenchimento liso.
        if self.assets.village_layers or "village" in self.assets.backgrounds:
            return "village"
        return "school" if self.level.index == 0 else None

    # Salas que são subterrâneas por definição, independente do y da Lia: o
    # teste de UNDERGROUND_Y foi feito pro corredor da Fase 1 (que é o mesmo
    # mapa em cima e embaixo), mas o laboratório escondido é um mapa próprio
    # cujo chão fica em y=544 — pelo teste de altura ele passaria por "de dia"
    # e levaria a variante clara.
    ALWAYS_UNDERGROUND_ROOMS = ("laboratorio_secreto",)

    def _background_variant(self):
        if self.level.room in self.ALWAYS_UNDERGROUND_ROOMS:
            return "underground"
        return "underground" if self.player.y > self.UNDERGROUND_Y else "normal"

    def _draw_repeating_background(self, surface, background, parallax=1.0):
        """Ladrilha o fundo horizontalmente. Com parallax<1.0 o fundo anda
        mais devagar que a câmera, dando sensação de profundidade."""
        image_width = background.get_width()
        offset = int(self.camera_x * parallax)
        start_x = -offset % image_width - image_width
        for x in range(start_x, WIDTH, image_width):
            surface.blit(background, (x, 0))

    def _draw_world(self, surface):
        state = WorldDrawState(
            collected=self.collected,
            lever_on=self.lever_on,
            sequence_progress=self.sequence_progress,
            sequence_solved=self.sequence_solved,
            microscope_collected=self.microscope_collected,
            microscope_assembled=self.microscope_assembled,
            artifact_image=self._current_artifact_image(),
            artifacts_collected=self.artifacts_collected,
            tools_collected=self.tools_collected,
            energy_box_state=self.energy_box_state,
            lab_microscope_sprites=self._lab_microscope_sprites(),
            lab_microscope_collected=self.lab_microscope_collected,
            lab_microscope_assembled=self.lab_microscope_assembled,
        )
        self.level.draw(surface, self.camera_x, self.camera_y, self.assets, state, draw_text)

    def _draw_world_foreground(self, surface):
        """Camada "Frente" do Tiled (pedido do Raul, Fase 1 — ver
        TiledMap.draw_foreground/_is_foreground_layer): chamado DEPOIS de
        self.player.draw() em draw(), então esse cenário fica na frente da
        Lia. Sem isso, ela ficaria sempre por cima de qualquer tile,
        mesmo os pensados como primeiro plano. Guard de tiled_map porque
        fases sem mapa do Tiled (percurso gerado por código) não têm essa
        camada."""
        if self.level.tiled_map:
            self.level.tiled_map.draw_foreground(surface, self.camera_x, self.camera_y)
        self._draw_drops(surface)

    def _draw_drops(self, surface):
        """Itens largados no chão (ver _spawn_drop/_collect_drops) — ícone
        de items.png com um pulso leve, pra ficar claramente "pegável" e não
        parecer decoração ou parte do cenário."""
        if not self.pending_drops:
            return
        pulse = 3 * abs((pygame.time.get_ticks() % 900) / 450 - 1)
        for drop in self.pending_drops:
            icon = self.assets.item_icons.get(drop["item"])
            if not icon:
                continue
            x = drop["x"] - icon.get_width() / 2 - self.camera_x
            y = drop["y"] - icon.get_height() / 2 - self.camera_y - pulse
            surface.blit(icon, (x, y))

    def _current_artifact_image(self):
        if self.level.room == "biblioteca":
            return self.assets.artifact_library_image
        return self.assets.artifact_image


    DOOR_PROMPT_RANGE = 60

    def _draw_door_prompts(self, surface):
        """Mostra "[E] ENTRAR"/"[E] SAIR" só quando Lia está perto o
        bastante da porta pra interagir — mesmo raio usado em _use_doors."""
        player_rect = self.player.rect
        for door in self.level.doors:
            if not player_rect.colliderect(door["rect"].inflate(self.DOOR_PROMPT_RANGE, self.DOOR_PROMPT_RANGE)):
                continue
            label = "[E] SAIR" if door["target"] == "sair" else "[E] ENTRAR"
            rect = door["rect"]
            draw_text(
                surface,
                label,
                (rect.centerx - self.camera_x, rect.top - 22 - self.camera_y),
                14,
                "#f4e4a5",
                True,
            )

    NPC_PROMPT_RANGE = 60

    def _draw_npc_prompts(self, surface):
        """"APERTE E PARA FALAR" acima da cientista, só quando Lia está perto
        o bastante pra falar com ela — mesmo raio/padrão de _draw_door_
        prompts, contra Level.npcs em vez de Level.doors."""
        player_rect = self.player.rect
        for npc in self.level.npcs:
            rect = npc["rect"]
            if not player_rect.colliderect(rect.inflate(self.NPC_PROMPT_RANGE, self.NPC_PROMPT_RANGE)):
                continue
            draw_text(
                surface,
                "APERTE E PARA FALAR",
                (rect.centerx - self.camera_x, rect.top - 22 - self.camera_y),
                14,
                "#f4e4a5",
                True,
            )

    def _draw_player_light(self, surface):
        light_x = int(
            self.player.x
            - self.camera_x
            + PLAYER_HITBOX_WIDTH // 2
            - self.assets.player_light.get_width() // 2
        )
        light_y = int(
            self.player.y
            - self.camera_y
            + PLAYER_HEIGHT // 2
            - self.assets.player_light.get_height() // 2
        )
        surface.blit(self.assets.player_light, (light_x, light_y))

    def _active_boss(self):
        """Chefe em luta agora — vivo e já acordado (ver enemy.py DORMANT/
        wake_up e Game._maybe_wake_bosses) — None enquanto ele ainda dorme,
        depois que morre, ou se não há nenhum chefe na fase. Usado só pra
        decidir se a barra de vida aparece."""
        for enemy in self.level.enemies:
            if type(enemy).__name__ not in BOSS_DROP_TABLE:
                continue
            if not enemy.alive:
                continue
            if enemy.state == getattr(enemy, "DORMANT", None):
                continue
            return enemy
        return None

    def _update_music(self):
        """Roda uma vez por quadro (ver update()); audio.play_music já
        ignora a chamada se o nome pedido é o mesmo que já está tocando,
        então isso é barato mesmo rodando todo quadro — muito mais simples
        que espalhar play_music em cada ponto de transição de estado
        (trocar de fase, entrar/sair de sala, chefe acordar/morrer, ganhar/
        perder), que são muitos e fáceis de esquecer um. Mesma ideia de
        _draw_background: decide o resultado a partir do estado atual, sem
        guardar histórico de transições."""
        audio.play_music(self._desired_music_track())

    def _desired_music_track(self):
        """Nome da faixa (ver PLANO_AUDIO.md pro arquivo esperado em
        music/) que deveria estar tocando agora, dado o estado atual."""
        if self.state == GAME_OVER:
            return "derrota_music"
        if self.state == COMPLETE:
            return "vitoria_music"
        if self.state in (TITLE, SETTINGS):
            # Configurações só é alcançável a partir do título por
            # enquanto (ver _settings_return_state) — mesma trilha dos
            # dois, senão a música trocaria pra da Fase 1 ao só abrir o
            # menu de volume.
            return "menu_music"
        if self.state == INTRO:
            return "intro_music"
        boss = self._active_boss()
        if boss is not None:
            return BOSS_MUSIC.get(type(boss).__name__)
        if self.level.room == "laboratorio":
            return "laboratorio_music"
        if self.level.room == "biblioteca":
            return "biblioteca_music"
        if self.level.index == VILLAGE:
            return "vila_music"
        return f"fase_{self.level.index + 1}_music"

    BOSS_HEALTH_BAR_WIDTH = 520
    BOSS_HEALTH_BAR_HEIGHT = 20

    def _draw_boss_health_bar(self, surface):
        """Barra de vida no topo da tela (estilo Cuphead) enquanto um chefe
        está acordado — some de novo assim que ele morre ou some da fase
        (ver _active_boss). BOSS_NAMES só existe pro rótulo; a vida de
        verdade continua vindo de boss.health/HEALTH, igual sempre foi.
        y=80 fica abaixo da caixa de mensagem central (_draw_message, y
        18-66) de propósito, pra não sobrepor se as duas aparecerem juntas
        (ex.: mensagem de item pego durante a luta)."""
        boss = self._active_boss()
        if boss is None:
            return
        name = BOSS_NAMES.get(type(boss).__name__, "Chefe")
        ratio = max(0, boss.health) / boss.HEALTH if boss.HEALTH else 0
        width, height = self.BOSS_HEALTH_BAR_WIDTH, self.BOSS_HEALTH_BAR_HEIGHT
        x = WIDTH // 2 - width // 2
        y = 80
        draw_text(surface, name, (WIDTH // 2, y), 17, "#ffd9d9", True)
        bar = pygame.Rect(x, y + 16, width, height)
        pygame.draw.rect(surface, (12, 8, 10), bar.inflate(6, 6), border_radius=8)
        pygame.draw.rect(surface, (46, 16, 20), bar, border_radius=6)
        pygame.draw.rect(
            surface, (214, 58, 58), (bar.x, bar.y, int(bar.width * ratio), bar.height), border_radius=6
        )
        pygame.draw.rect(surface, (250, 214, 214), bar, 2, border_radius=6)

    def _draw_interface(self, surface):
        show_oxygen = bool(self.level.water_zones) and (
            self.player.swimming or self.player.oxygen < self.player.OXYGEN_MAX_FRAMES
        )
        oxygen_ratio = (
            self.player.oxygen / self.player.OXYGEN_MAX_FRAMES if show_oxygen else None
        )
        draw_hud(
            surface,
            self.level.data["name"],
            self.lives,
            len(self.collected),
            len(self.level.research),
            self.message,
            self.message_timer,
            len(self.microscope_collected),
            len(self.level.microscope_parts),
            self.microscope_assembled,
            oxygen_ratio,
            self.shield,
        )
        self._draw_boss_health_bar(surface)
        draw_inventory(surface, self.inventory, self.assets.item_icons, ITEM_ORDER)
        draw_ability_ui(
            surface,
            self.player.dash_cooldown,
            self.player.DASH_COOLDOWN,
            self.attack_cooldown,
            ATTACK_COOLDOWN,
            self.ranged_unlocked,
            self.ranged_cooldown,
            RANGED_ATTACK_COOLDOWN,
        )
        self.dialogue.draw(surface, draw_text)

    def _draw_state_overlay(self, surface):
        if self.state == TITLE:
            self._draw_title_menu(surface)
        elif self.state == SETTINGS:
            self._draw_settings_menu(surface)
        elif self.state == PAUSED:
            self._draw_pause_menu(surface)
        elif self.state == GAME_OVER:
            self.draw_game_over_overlay(surface)
        elif self.state == COMPLETE:
            self.overlay(
                surface,
                "Pesquisa apresentada no congresso!",
                "Lia corre pra contar tudo pra mãe: a pesquisa vai continuar,\n"
                "e agora ela sabe que não está sozinha nisso.\nPressione R para jogar novamente",
            )

    # Paleta compartilhada dos botões/sliders do menu (mesmo estilo dos
    # painéis do HUD em hud.py — retângulo escuro arredondado + borda
    # azul clara) — BUTTON_HOVER_* fica um pouco mais claro, pra dar
    # feedback de "isso é clicável" sem precisar de nenhuma imagem nova.
    BUTTON_FILL = (12, 25, 43)
    BUTTON_FILL_HOVER = (22, 42, 68)
    BUTTON_BORDER = (101, 184, 228)
    BUTTON_BORDER_HOVER = (150, 216, 255)

    # Camadas escuras já prontas, uma por valor de alpha usado. Antes
    # _dim_background criava um Surface SRCALPHA de tela cheia A CADA
    # QUADRO — no título e nas configurações isso rodava eternamente, e na
    # tela de game over o alpha varia de 0 a 210 durante o fade, então são
    # (o alpha varia de 0 a 210 durante o fade da tela de game over), então
    # a camada é criada uma vez e só o set_alpha muda entre quadros.
    _DIM_LAYER = None

    def _dim_background(self, surface, alpha=210):
        """Camada escura translúcida por cima do mundo (que continua
        sendo desenhado atrás — ver draw()), usada por todo overlay de
        estado (título, configurações, game over, vitória)."""
        if Game._DIM_LAYER is None:
            # OPACA (convert(), sem SRCALPHA) de propósito: com alpha por
            # pixel, set_alpha obriga o pygame a combinar os dois alphas e
            # cai num caminho de blit bem mais lento (medido: 10,6 ms contra
            # 1,1 ms por quadro). Como a camada é uma cor chapada, alpha
            # uniforme dá exatamente o mesmo resultado pela via rápida.
            layer = pygame.Surface((WIDTH, HEIGHT)).convert()
            layer.fill((5, 12, 28))
            Game._DIM_LAYER = layer
        layer = Game._DIM_LAYER
        layer.set_alpha(alpha)
        surface.blit(layer, (0, 0))

    def _draw_menu_button(self, surface, rect, label, sublabel=None):
        """Um botão clicável do menu — hover checado direto por
        pygame.mouse.get_pos() (disponível sempre via `import pygame`,
        sem depender de nenhum evento/global do Pygame Zero) porque é só
        pra pintar o botão mais claro embaixo do cursor; o clique de
        verdade continua vindo de handle_menu_click (main.py/
        on_mouse_down), não daqui."""
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        fill = self.BUTTON_FILL_HOVER if hovered else self.BUTTON_FILL
        border = self.BUTTON_BORDER_HOVER if hovered else self.BUTTON_BORDER
        pygame.draw.rect(surface, fill, rect, border_radius=14)
        pygame.draw.rect(surface, border, rect, 3, border_radius=14)
        label_y = rect.centery - (10 if sublabel else 0)
        draw_text(surface, label, (rect.centerx, label_y), 26, "#ffe477", True)
        if sublabel:
            draw_text(surface, sublabel, (rect.centerx, rect.centery + 18), 14, "#9fb4c9", True)

    def _draw_slider(self, surface, bar_rect, ratio, label):
        """Barra + alça arrastável de um volume (0.0-1.0). `bar_rect` é a
        área CLICÁVEL (mais alta que a barra visual, ver
        SETTINGS_BAR_HIT_HEIGHT/_settings_widgets) — a barra desenhada de
        verdade fica centralizada dentro dela, mais fina."""
        draw_text(
            surface,
            f"{label} — {round(ratio * 100)}%",
            (bar_rect.centerx, bar_rect.top - 22),
            20,
            "white",
            True,
        )
        track = pygame.Rect(
            bar_rect.x,
            bar_rect.centery - self.SETTINGS_BAR_HEIGHT // 2,
            bar_rect.width,
            self.SETTINGS_BAR_HEIGHT,
        )
        pygame.draw.rect(surface, (30, 45, 66), track, border_radius=8)
        filled = pygame.Rect(track.x, track.y, round(track.width * ratio), track.height)
        pygame.draw.rect(surface, (95, 201, 255), filled, border_radius=8)
        handle_x = track.x + round(track.width * ratio)
        pygame.draw.circle(surface, "white", (handle_x, track.centery), 14)
        pygame.draw.circle(surface, (95, 201, 255), (handle_x, track.centery), 14, 3)

    # Escurecimento fixo do título/configurações (ver draw: já vem composto
    # no instantâneo, por isso _draw_title_menu/_draw_settings_menu não
    # chamam mais _dim_background — se chamassem, escureceria duas vezes).
    MENU_DIM_ALPHA = 210

    def _draw_title_menu(self, surface):
        draw_text(surface, "Echoes of Life", (WIDTH // 2, HEIGHT // 2 - 140), 54, "#ffe477", True)
        buttons = self._title_buttons()
        if "continue" in buttons:
            self._draw_menu_button(surface, buttons["continue"], "CONTINUAR", "retoma o último checkpoint")
        self._draw_menu_button(surface, buttons["play"], "JOGO NOVO" if "continue" in buttons else "JOGAR",
                               "ou pressione ESPAÇO")
        self._draw_menu_button(surface, buttons["settings"], "CONFIGURAÇÕES")

    def _draw_pause_menu(self, surface):
        draw_text(surface, "Pausado", (WIDTH // 2, HEIGHT // 2 - 140), 48, "#ffe477", True)
        buttons = self._pause_buttons()
        self._draw_menu_button(surface, buttons["resume"], "CONTINUAR", "ou pressione ESC")
        self._draw_menu_button(surface, buttons["settings"], "CONFIGURAÇÕES")

    def _draw_settings_menu(self, surface):
        draw_text(surface, "Configurações", (WIDTH // 2, HEIGHT // 2 - 260), 44, "#ffe477", True)
        widgets = self._settings_widgets()
        for key, label, getter, _set in self.SETTINGS_SLIDERS:
            self._draw_slider(surface, widgets[key], getter(), label)
        self._draw_menu_button(surface, widgets["back"], "VOLTAR")

    def draw_university_background(self, surface, background, variant="normal"):
        """Repete o pátio alternando cópias normais e espelhadas. Recebe a
        imagem já tingida de fora (ver _draw_background) em vez de buscar em
        self.assets.backgrounds[1] — o dicionário agora é por nome + variante."""
        mirror = self.assets.background_mirror[variant]
        image_width = background.get_width()
        x = -int(self.camera_x) % image_width - image_width
        tile_number = (x + int(self.camera_x)) // image_width
        while x < WIDTH:
            image = mirror if tile_number % 2 else background
            surface.blit(image, (x, 0))
            x += image_width
            tile_number += 1

    def draw_dash_trail(self, surface):
        """Desenha o rastro que torna o dash legível."""
        if not self.player.dashing:
            return
        direction = 1 if self.player.dash_direction > 0 else -1
        start_x = (
            self.player.x
            - self.camera_x
            + PLAYER_HITBOX_WIDTH // 2
            - direction * 12
        )
        center_y = self.player.y - self.camera_y + PLAYER_HEIGHT // 2
        for offset, alpha in ((0, 150), (12, 95), (24, 45)):
            layer = pygame.Surface((42, 8), pygame.SRCALPHA)
            layer.fill((91, 220, 255, alpha))
            x = start_x - direction * (offset + (42 if direction < 0 else 0))
            surface.blit(layer, (int(x), int(center_y - 4)))

    def overlay(self, surface, title, body, alpha=210):
        self._dim_background(surface, alpha)
        draw_text(surface, title, (WIDTH // 2, HEIGHT // 2 - 65), 42, "#ffe477", True)
        for line_number, line in enumerate(body.split("\n")):
            draw_text(
                surface,
                line,
                (WIDTH // 2, HEIGHT // 2 + 5 + line_number * 34),
                24,
                "white",
                True,
            )

    def draw_game_over_overlay(self, surface):
        """Desenha o fade escuro e os textos revelados em sequência."""
        alpha = int(210 * self.game_over_fade / 60)
        self._dim_background(surface, alpha)

        title = "Você consegue, Lia!"
        message = MOTIVATION
        restart = "Pressione R para tentar de novo"
        visible_title, visible_message, visible_restart = self._game_over_text(
            title,
            message,
            restart,
        )

        draw_text(surface, visible_title, (WIDTH // 2, HEIGHT // 2 - 65), 42, "#ffe477", True)
        draw_text(surface, visible_message, (WIDTH // 2, HEIGHT // 2 + 5), 24, "white", True)
        draw_text(surface, visible_restart, (WIDTH // 2, HEIGHT // 2 + 39), 24, "white", True)

    def _game_over_text(self, title, message, restart):
        remaining = int(self.game_over_characters)
        visible_title = title[:max(0, min(len(title), remaining))]
        remaining -= len(title)
        visible_message = message[:max(0, min(len(message), remaining))]
        remaining -= len(message)
        visible_restart = restart[:max(0, min(len(restart), remaining))]
        return visible_title, visible_message, visible_restart
