"""Orquestra o ciclo de jogo, as interações e a renderização."""

import pygame

from dialogue import DialogueBox
from hud import draw_ability_ui, draw_hud, draw_text
from level import PHASES, Level
from player import Player
from settings import (
    ASSET_DIR,
    FPS,
    HEIGHT,
    MOTIVATION,
    PLAYER_HEIGHT,
    PLAYER_HITBOX_OFFSET_X,
    PLAYER_HITBOX_WIDTH,
    WIDTH,
)


TITLE = "title"
PLAYING = "playing"
GAME_OVER = "game_over"
COMPLETE = "complete"

STARTING_LIVES = 3
ATTACK_DURATION = 11
ATTACK_COOLDOWN = 20
STANDARD_ATTACK_POWER = 1
DASH_ATTACK_POWER = 2
STANDARD_ATTACK_REACH = 22
DASH_ATTACK_REACH = 36

CAMERA_X_FOCUS = 0.42
CAMERA_X_SMOOTHING = 0.12
CAMERA_Y_FOCUS = 0.55
CAMERA_Y_SMOOTHING = 0.10

SCIENCE_FACTS = {
    "Curiosidade": "Marie Curie foi a primeira pessoa a receber dois Prêmios Nobel, em áreas científicas diferentes.",
    "Observação": "Bertha Lutz foi uma cientista brasileira e uma das grandes vozes pela participação das mulheres na sociedade.",
    "Hipótese": "Enedina Alves Marques foi a primeira mulher negra a se formar engenheira no Brasil.",
    "Experimento": "Jaqueline Goes de Jesus participou do sequenciamento do genoma do coronavírus no Brasil, em 2020.",
    "Registro": "Nise da Silveira transformou a psiquiatria brasileira com cuidado, arte e respeito às pessoas.",
    "Método": "Ada Lovelace é reconhecida por escrever um dos primeiros algoritmos para uma máquina.",
    "Dados": "Katherine Johnson calculou trajetórias essenciais para missões espaciais da NASA.",
    "Análise": "Sônia Guimarães foi a primeira mulher negra brasileira doutora em Física.",
    "Testes": "Rosalind Franklin produziu imagens de raios X que foram fundamentais para compreender a estrutura do DNA.",
    "Resultados": "Mayana Zatz é referência brasileira em genética humana e no estudo de doenças neuromusculares.",
    "Cura": "Johanna Döbereiner contribuiu para o estudo da fixação de nitrogênio, importante para a agricultura brasileira.",
    "Pesquisa completa": "A ciência avança quando muitas pessoas fazem perguntas, compartilham dados e persistem juntas.",
}
DEFAULT_SCIENCE_FACT = "Toda descoberta começa com uma pergunta e cresce com persistência."

SCHOOL_SPRITE_RECTS = {
    "chalkboard": (72, 54, 205, 124),
    "whiteboard": (281, 54, 190, 124),
    "clock": (600, 52, 112, 116),
    "bulletin": (494, 176, 184, 80),
    "exit": (415, 208, 74, 54),
    "plant": (694, 158, 93, 125),
    "desk_row": (912, 152, 310, 94),
    "locker": (1268, 246, 150, 188),
    "bookshelf": (478, 456, 196, 102),
    "door": (250, 554, 136, 190),
    "lab_table": (732, 610, 258, 126),
}
SCHOOL_PLATFORM_SPRITES = {
    "grass_tile": ((448, 756, 32, 64), (32, 32)),
    "wood_tile": ((768, 850, 32, 60), (32, 32)),
    "brick_tile": ((80, 286, 32, 64), (32, 32)),
    "cream_tile": ((80, 456, 32, 64), (32, 32)),
}


class Game:
    """Mantém o estado de uma sessão de jogo e coordena seus componentes."""

    def __init__(self):
        self._load_assets()
        self.player = Player()
        self.dialogue = DialogueBox()
        self.lives = STARTING_LIVES
        self.camera_x = 0
        self.camera_y = 0
        self.game_over_fade = 0
        self.game_over_characters = 0
        self._reset_combat_state()
        self._reset_input_state()
        self.load_level(0)
        self.state = TITLE

    def _load_assets(self):
        self.tiles = self._load_platform_tiles()
        self.university_tiles = self._load_university_tiles()
        self.university_props = self._load_university_props()
        self._load_backgrounds()
        self.school_sprites = self._load_school_sprites()
        self._create_scene_filters()
        self.player_light = self._create_player_light()
        self.book = self._load_scaled_image("items/book.png", (30, 38))
        self.checkpoint_flag = self._load_image("objects/checkpoint_flag.png")
        self.puzzle_sprites = self._load_puzzle_sprites()
        self.slime_sprites = self._load_slime_sprites()

    @staticmethod
    def _load_image(relative_path, alpha=True):
        image = pygame.image.load(ASSET_DIR / relative_path)
        return image.convert_alpha() if alpha else image.convert()

    def _load_scaled_image(self, relative_path, size):
        return pygame.transform.smoothscale(self._load_image(relative_path), size)

    def _load_platform_tiles(self):
        return [
            self._load_image(f"tiles/platform{index}.png")
            for index in range(1, 5)
        ]

    def _load_university_tiles(self):
        sheet = self._load_image("tiles/university_sheet.png")
        return [
            [self._sheet_crop(sheet, (column * 32, row * 32, 32, 32)) for column in range(4)]
            for row in range(4)
        ]

    @staticmethod
    def _load_university_props():
        return {
            name: pygame.image.load(ASSET_DIR / "props" / f"{name}.png").convert_alpha()
            for name in ("plant_pot", "book_stack", "grad_cap", "banner", "bench", "bush")
        }

    # Fator de velocidade do fundo da caverna em relação à câmera: <1.0 faz o
    # fundo se mover mais devagar que o primeiro plano (efeito parallax).
    CAVE_BACKGROUND_PARALLAX = 0.35

    def _load_backgrounds(self):
        school_background = self._load_image("backgrounds/background_school.png", alpha=False)
        university_background = self._load_image("backgrounds/ifsp_background.png", alpha=False)
        cave_background = self._load_scaled_cave_background()
        self.backgrounds = [school_background, university_background, cave_background]
        self.background_mirror = pygame.transform.flip(university_background, True, False)

    def _load_scaled_cave_background(self):
        """A arte da caverna vem em baixa resolução (pensada para ladrilhar);
        aqui ela é ampliada até cobrir a altura do canvas, preservando a
        proporção, para servir de camada de fundo com parallax."""
        raw = self._load_image("backgrounds/cave_background_underwater.png", alpha=False)
        scale = HEIGHT / raw.get_height()
        size = (round(raw.get_width() * scale), HEIGHT)
        return pygame.transform.scale(raw, size)

    def _load_school_sprites(self):
        sheet = self._load_image("fase_escola_tileset/escola_sheet.png", alpha=False)
        sprites = {
            name: self._sheet_crop(sheet, rectangle)
            for name, rectangle in SCHOOL_SPRITE_RECTS.items()
        }
        sprites.update(
            {
                name: pygame.transform.scale(self._sheet_crop(sheet, rectangle), size)
                for name, (rectangle, size) in SCHOOL_PLATFORM_SPRITES.items()
            }
        )
        return sprites

    def _create_scene_filters(self):
        self.background_filter = self._solid_overlay((38, 53, 76, 72))
        self.university_filter = self._solid_overlay((55, 65, 80, 85))
        self.underground_filter = self._solid_overlay((8, 12, 27, 155))

    @staticmethod
    def _solid_overlay(color):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill(color)
        return overlay

    @staticmethod
    def _create_player_light():
        light_size = 280
        light = pygame.Surface((light_size, light_size), pygame.SRCALPHA)
        center = light_size // 2
        for radius in range(center, 0, -4):
            intensity = 1 - radius / center
            alpha = int(3 + 52 * intensity * intensity)
            pygame.draw.circle(light, (255, 239, 192, alpha), (center, center), radius)
        return light

    def _load_puzzle_sprites(self):
        objects_dir = ASSET_DIR / "objects"
        return {
            "lever_animation": [
                pygame.transform.scale(
                    pygame.image.load(objects_dir / f"alavanca_animation{frame}.png").convert_alpha(),
                    (86, 64),
                )
                for frame in range(1, 6)
            ],
            "microscope_parts": [
                pygame.image.load(objects_dir / f"microscope_{name}.png").convert_alpha()
                for name in ("lens", "base", "light", "ocular")
            ],
            "microscope_complete": pygame.image.load(
                objects_dir / "microscope_complete.png"
            ).convert_alpha(),
            "buttons": [
                pygame.transform.scale(
                    pygame.image.load(objects_dir / f"button_{color}.png").convert_alpha(),
                    (36, 20),
                )
                for color in ("blue", "green", "yellow", "red")
            ],
        }

    def _load_slime_sprites(self):
        enemies_dir = ASSET_DIR / "enemies"
        return {
            state: self._load_enemy_sheet(enemies_dir / f"slime_{state}.png")
            for state in ("walk", "jump", "dead", "hurt")
        }

    @staticmethod
    def _load_enemy_sheet(path):
        """Extrai e amplia os quadros retangulares das folhas de slime."""
        sheet = pygame.image.load(path).convert_alpha()
        frame_width = sheet.get_height() * 2
        frames = []
        for x in range(0, sheet.get_width(), frame_width):
            frame = sheet.subsurface(pygame.Rect(x, 0, frame_width, sheet.get_height()))
            content = frame.get_bounding_rect()
            if content.width and content.height:
                frame = frame.subsurface(content)
            frames.append(pygame.transform.scale(frame, (64, 32)))
        return frames

    @staticmethod
    def _sheet_crop(sheet, rectangle):
        """Copia um elemento do sprite sheet."""
        return sheet.subsurface(pygame.Rect(rectangle)).copy()

    def load_level(self, index):
        """Inicia uma fase sem modificar a quantidade atual de vidas."""
        self.level = Level(index)
        self.checkpoint = self.level.spawn
        self.player.reset(*self.checkpoint)
        self.collected = set()
        self.seen_dialogues = set()
        self.lever_on = False
        self.sequence_solved = False
        self.microscope_assembled = False
        self.sequence_progress = 0
        self.microscope_collected = set()
        self.riding_platform = None
        self._reset_combat_state()
        self._reset_input_state()
        self.camera_x = 0
        self.camera_y = 0
        self.message = self.level.data["subtitle"]
        self.message_timer = 0
        self.state = PLAYING

    def _reset_combat_state(self):
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_power = STANDARD_ATTACK_POWER
        self.mouse_attack_requested = False

    def _reset_input_state(self):
        self.interact_was_down = False
        self.attack_was_down = False
        self.dash_was_down = False
        self.dialogue_advance_was_down = False

    def respawn(self):
        self.lives -= 1
        if self.lives <= 0:
            self.state = GAME_OVER
            self.game_over_fade = 0
            self.game_over_characters = 0
            return

        self.player.reset(*self.checkpoint)
        self.riding_platform = None
        self.camera_y = 0
        self.message = MOTIVATION
        self.message_timer = 0

    def update(self, keyboard, dt=1 / FPS):
        dialogue_advance_pressed, attack_pressed, dash_pressed = self._read_input(keyboard)

        if self.state == TITLE:
            self._update_title(keyboard)
        elif self.state in (GAME_OVER, COMPLETE):
            self._update_end_state(keyboard)
        elif self.dialogue.active:
            self._update_dialogue(dialogue_advance_pressed)
        else:
            self._update_playing(keyboard, dash_pressed, attack_pressed, dt)

    def _read_input(self, keyboard):
        interaction_down = keyboard.e or keyboard.RETURN
        dialogue_advance_down = interaction_down or keyboard.space
        attack_down = keyboard.f
        dash_down = keyboard.q

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
        return dialogue_advance_pressed, attack_pressed, dash_pressed

    def _update_title(self, keyboard):
        if keyboard.space or keyboard.RETURN:
            self.lives = STARTING_LIVES
            self.state = PLAYING

    def _update_end_state(self, keyboard):
        if self.state == GAME_OVER:
            self.game_over_fade = min(60, self.game_over_fade + 1)
            if self.game_over_fade >= 18:
                self.game_over_characters += 0.75
        if keyboard.r:
            self.lives = STARTING_LIVES
            level_index = 0 if self.state == COMPLETE else self.level.index
            self.load_level(level_index)

    def _update_dialogue(self, dialogue_advance_pressed):
        # A animação da alavanca continua enquanto a mensagem é exibida.
        if self.level.is_underground:
            self.level.update_lever_animations()
        if dialogue_advance_pressed:
            if self.dialogue.finished:
                self.dialogue.close()
            else:
                self.dialogue.reveal_all()
        else:
            self.dialogue.update()

    def _update_playing(self, keyboard, dash_pressed, attack_pressed, dt):
        self.player.update_abilities()
        if dash_pressed and not self.player.swimming:
            self.player.start_dash()
        self.player.read_controls(keyboard)
        self._update_attack(attack_pressed)
        self.level.update()
        if self.level.tiled_map:
            # Avança a animação dos tiles do Tiled (ex.: água da Fase 3) em ms.
            self.level.tiled_map.update(dt * 1000)
        self._move_with_platform()
        self.move_player()
        self.player.animate()
        self._update_camera()
        self.message_timer = max(0, self.message_timer - 1)
        self.handle_interactions()
        self.check_events()

    def _update_attack(self, attack_pressed):
        self.attack_cooldown = max(0, self.attack_cooldown - 1)
        if attack_pressed and self.attack_cooldown == 0:
            self.attack_timer = ATTACK_DURATION
            self.attack_cooldown = ATTACK_COOLDOWN
            self.attack_power = (
                DASH_ATTACK_POWER if self.player.dashing else STANDARD_ATTACK_POWER
            )
        if self.attack_timer:
            self.attack_timer -= 1
            if self.attack_timer == 0:
                self.attack_power = STANDARD_ATTACK_POWER

    def _move_with_platform(self):
        if self.riding_platform:
            self.player.x += self.riding_platform.dx
            self.player.y += self.riding_platform.dy

    def _update_camera(self):
        target_x = self.player.x - WIDTH * CAMERA_X_FOCUS
        self.camera_x += (target_x - self.camera_x) * CAMERA_X_SMOOTHING
        self.camera_x = max(0, min(self.camera_x, self.level.world_width - WIDTH))

        target_y = self.player.y - HEIGHT * CAMERA_Y_FOCUS
        self.camera_y += (target_y - self.camera_y) * CAMERA_Y_SMOOTHING
        self.camera_y = max(
            self.level.world_top,
            min(self.camera_y, self.level.world_height - HEIGHT),
        )

    def request_mouse_attack(self):
        """Registra o clique; o ataque será iniciado no próximo update."""
        self.mouse_attack_requested = True

    # Quadros de tolerância após soltar o encosto na parede em que o wall
    # jump ainda é aceito (mesma ideia do coyote_time do chão). Sem isso, o
    # jogador solta a direção pra preparar o pulo, o encosto conta como
    # perdido no mesmo quadro e o wall jump falha de forma inconsistente.
    WALL_COYOTE_FRAMES = 8

    def move_player(self):
        """Resolve colisões horizontais, verticais e o pulo sobre inimigos."""
        player = self.player
        solids = self._all_solid_rectangles()
        player.wall_side = 0
        player.swimming = self._player_in_water(player)
        if player.swimming:
            player.cancel_dash()

        previous_x = player.x
        player.x += player.vx
        self._resolve_horizontal_collisions(player, solids, previous_x)

        if player.wall_side and not player.swimming:
            player.last_wall_side = player.wall_side
            player.wall_coyote_time = self.WALL_COYOTE_FRAMES
        else:
            player.wall_coyote_time = max(0, player.wall_coyote_time - 1)

        if player.swimming:
            player.apply_swim_gravity()
        else:
            player.apply_gravity()
            if player.wall_side and player.vy > player.WALL_SLIDE_SPEED:
                player.vy = player.WALL_SLIDE_SPEED

        previous_y = player.y
        previous_bottom = previous_y + PLAYER_HEIGHT
        player.y += player.vy

        if not player.swimming and self._stomp_enemy_if_possible(player, previous_bottom):
            return

        landed = self._resolve_vertical_collisions(player, previous_y, previous_bottom)
        if player.swimming:
            # Sem chão firme nem parede pra reaproveitar debaixo d'água.
            player.coyote_time = 0
            player.wall_jump_used = True
        else:
            player.coyote_time = 7 if landed else max(0, player.coyote_time - 1)
            if landed:
                player.wall_jump_used = False
        player.try_jump()

    def _player_in_water(self, player):
        return any(player.rect.colliderect(zone) for zone in self.level.water_zones)

    def _all_solid_rectangles(self):
        return (
            self.level.grounds
            + self.level.wall_blocks
            + [platform.rect for platform in self.level.platforms]
        )

    @staticmethod
    def _resolve_horizontal_collisions(player, solids, previous_x):
        for solid in solids:
            if not player.rect.colliderect(solid):
                continue

            previous_right = previous_x + PLAYER_HITBOX_OFFSET_X + PLAYER_HITBOX_WIDTH
            previous_left = previous_x + PLAYER_HITBOX_OFFSET_X
            if player.vx > 0 and previous_right <= solid.left:
                player.x = solid.left - PLAYER_HITBOX_WIDTH - PLAYER_HITBOX_OFFSET_X
                player.wall_side = 1
                player.cancel_dash()
            elif player.vx < 0 and previous_left >= solid.right:
                player.x = solid.right - PLAYER_HITBOX_OFFSET_X
                player.wall_side = -1
                player.cancel_dash()

    def _stomp_enemy_if_possible(self, player, previous_bottom):
        for enemy in self.level.enemies:
            if (
                enemy.alive
                and player.vy > 0
                and player.rect.colliderect(enemy.rect)
                and previous_bottom <= enemy.rect.top + 12
            ):
                enemy.stomp()
                player.y = enemy.rect.top - PLAYER_HEIGHT
                player.vy = -10.5
                return True
        return False

    def _resolve_vertical_collisions(self, player, previous_y, previous_bottom):
        landed = False
        self.riding_platform = None
        platform_solids = [
            (platform.rect, platform) for platform in self.level.platforms
        ]
        ground_solids = [(ground, None) for ground in self.level.grounds]
        wall_solids = [(wall, None) for wall in self.level.wall_blocks]

        for solid, moving_platform in platform_solids + ground_solids + wall_solids:
            if (
                player.rect.colliderect(solid)
                and player.vy >= 0
                and previous_bottom <= solid.top + 10
            ):
                player.y = solid.top - PLAYER_HEIGHT
                player.vy = 0
                landed = True
                if moving_platform:
                    self.riding_platform = moving_platform
            elif (
                player.rect.colliderect(solid)
                and player.vy < 0
                and previous_y >= solid.bottom - 10
            ):
                player.y = solid.bottom
                player.vy = 0
        return landed

    def check_events(self):
        player = self.player
        if player.y > self.level.world_height + 180:
            self.respawn()
            return

        if self._update_oxygen(player):
            return
        if self._check_hazards(player):
            return

        self.check_enemies()
        if self.state != PLAYING:
            return
        self._check_checkpoints(player)
        if self._collect_research(player):
            return
        self._collect_microscope_parts(player)
        if self._start_pending_dialogue(player):
            return
        self._advance_level_if_ready(player)

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
        player.oxygen = max(0, player.oxygen - player.OXYGEN_DRAIN_PER_FRAME)
        if player.oxygen <= 0:
            self.respawn()
            return True
        return False

    def _check_hazards(self, player):
        for hazard in self.level.hazards:
            if player.rect.colliderect(hazard):
                self.respawn()
                return True
        return False

    def _check_checkpoints(self, player):
        for checkpoint in self.level.checkpoints:
            if player.rect.colliderect(checkpoint):
                self.checkpoint = (checkpoint.x, checkpoint.bottom - PLAYER_HEIGHT)
                self.message = "Checkpoint: Centro de pesquisa alcançado!"
                self.message_timer = 130

    def _collect_research(self, player):
        for index, (item, name) in enumerate(self.level.research):
            if index in self.collected or not player.rect.colliderect(item):
                continue

            self.collected.add(index)
            self.message = f"Parte da pesquisa obtida: {name}"
            self.message_timer = 0
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

        needs_microscope = self.level.is_underground and not self.microscope_assembled
        if len(self.collected) < len(self.level.research) or needs_microscope:
            self.message = "Encontre todas as partes da pesquisa antes de avançar."
            self.message_timer = 0
            player.x = self.level.world_width - 160
        elif self.level.index == len(PHASES) - 1:
            self.state = COMPLETE
        else:
            self.load_level(self.level.index + 1)

    def check_enemies(self):
        """Verifica ataque, ataque reforçado durante dash e contato com slimes."""
        attack_box = self._attack_box()
        for enemy in self.level.enemies:
            if not enemy.alive:
                continue
            if attack_box and attack_box.colliderect(enemy.rect):
                enemy.take_hit(self.attack_power)
            elif self.player.rect.colliderect(enemy.rect):
                self.respawn()
                return

    def _attack_box(self):
        if not self.attack_timer:
            return None
        reach = DASH_ATTACK_REACH if self.attack_power > STANDARD_ATTACK_POWER else STANDARD_ATTACK_REACH
        offset = (
            PLAYER_HITBOX_WIDTH
            if self.player.facing_right
            else -(24 + reach)
        )
        return self.player.rect.move(offset, 4).inflate(reach, 10)

    def handle_interactions(self):
        """Processa elevadores, painel, botões e bancada do laboratório."""
        if not self.level.is_underground or not self.interact_pressed:
            return

        player = self.player
        if self._use_elevator_lever(player):
            return
        if self._use_panel_lever(player):
            return
        if self._use_sequence_button(player):
            return
        self._use_microscope_bench(player)

    def _use_elevator_lever(self, player):
        if self.level.top_lever and player.rect.colliderect(self.level.top_lever.inflate(55, 55)):
            self.level.call_elevator("down")
            return True
        if self.level.bottom_lever and player.rect.colliderect(self.level.bottom_lever.inflate(55, 55)):
            self.level.call_elevator("up")
            return True
        if (
            self.level.upper_bottom_lever
            and player.rect.colliderect(self.level.upper_bottom_lever.inflate(55, 55))
        ):
            self.level.call_upper_elevator("up")
            return True
        if (
            self.level.upper_top_lever
            and player.rect.colliderect(self.level.upper_top_lever.inflate(55, 55))
        ):
            self.level.call_upper_elevator("down")
            return True
        return False

    def _use_panel_lever(self, player):
        if not player.rect.colliderect(self.level.panel_lever.inflate(55, 55)):
            return False

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
                self.sequence_progress += 1
                if self.sequence_progress == len(self.level.buttons):
                    self.sequence_solved = True
                    self.dialogue.start(
                        "Painel",
                        "Sequência correta! As peças do microscópio foram liberadas.",
                    )
            else:
                self.sequence_progress = 0
                self.dialogue.start("Painel", "Sequência incorreta. O painel foi reiniciado.")
            return True
        return False

    def _use_microscope_bench(self, player):
        if not player.rect.colliderect(self.level.bench.inflate(70, 60)):
            return
        if len(self.microscope_collected) < len(self.level.microscope_parts):
            self.dialogue.start("Lia", "Ainda faltam peças para montar o microscópio.")
        elif not self.microscope_assembled:
            self.microscope_assembled = True
            self.level.activate_return_route()
            self.dialogue.start(
                "Lia",
                "Microscópio montado! As plataformas de retorno foram liberadas; preciso voltar pelo caminho acima.",
            )

    def draw(self, screen):
        surface = screen.surface
        surface.fill((6, 14, 29))
        self._draw_background(surface)
        self._draw_world(surface)
        self._draw_player_light(surface)
        self.draw_dash_trail(surface)
        self.player.draw(surface, self.camera_x, self.camera_y)
        self.draw_attack(surface)
        self._draw_interface(surface)
        self._draw_state_overlay(surface)

    def _draw_background(self, surface):
        if self.level.index == 0:
            self.draw_school_background(surface)
        elif self.level.index == 1:
            self.draw_university_background(surface)
        elif self.level.index == 2:
            self._draw_repeating_background(
                surface, self.backgrounds[2], parallax=self.CAVE_BACKGROUND_PARALLAX
            )
        else:
            self._draw_repeating_background(surface, self.backgrounds[self.level.index])

        surface.blit(self.background_filter, (0, 0))
        if self.level.index == 1:
            surface.blit(self.university_filter, (0, 0))
        if self.player.y > 780:
            surface.blit(self.underground_filter, (0, 0))

    def _draw_repeating_background(self, surface, background, parallax=1.0):
        """Ladrilha o fundo horizontalmente. Com parallax<1.0 o fundo anda
        mais devagar que a câmera, dando sensação de profundidade."""
        image_width = background.get_width()
        offset = int(self.camera_x * parallax)
        start_x = -offset % image_width - image_width
        for x in range(start_x, WIDTH, image_width):
            surface.blit(background, (x, 0))

    def _draw_world(self, surface):
        self.level.draw(
            surface,
            self.camera_x,
            self.camera_y,
            self.tiles,
            self.book,
            self.checkpoint_flag,
            self.checkpoint,
            self.collected,
            self.lever_on,
            self.sequence_progress,
            self.sequence_solved,
            self.microscope_collected,
            self.microscope_assembled,
            self.puzzle_sprites,
            self.slime_sprites,
            self.school_sprites,
            draw_text,
            self.university_tiles,
            self.university_props,
        )

    def _draw_player_light(self, surface):
        light_x = int(
            self.player.x
            - self.camera_x
            + PLAYER_HITBOX_WIDTH // 2
            - self.player_light.get_width() // 2
        )
        light_y = int(
            self.player.y
            - self.camera_y
            + PLAYER_HEIGHT // 2
            - self.player_light.get_height() // 2
        )
        surface.blit(self.player_light, (light_x, light_y))

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
        )
        draw_ability_ui(
            surface,
            self.player.dash_cooldown,
            self.player.DASH_COOLDOWN,
            self.attack_cooldown,
            ATTACK_COOLDOWN,
            not self.player.wall_jump_used,
        )
        self.dialogue.draw(surface, draw_text)

    def _draw_state_overlay(self, surface):
        if self.state == TITLE:
            self.overlay(surface, "Echoes of Life", "Pressione ESPAÇO para começar")
        elif self.state == GAME_OVER:
            self.draw_game_over_overlay(surface)
        elif self.state == COMPLETE:
            self.overlay(
                surface,
                "Pesquisa apresentada no congresso!",
                "Lia mostrou que ciência se faz com persistência.\nPressione R para jogar novamente",
            )

    def draw_university_background(self, surface):
        """Repete o pátio alternando cópias normais e espelhadas."""
        background = self.backgrounds[1]
        image_width = background.get_width()
        x = -int(self.camera_x) % image_width - image_width
        tile_number = (x + int(self.camera_x)) // image_width
        while x < WIDTH:
            image = self.background_mirror if tile_number % 2 else background
            surface.blit(image, (x, 0))
            x += image_width
            tile_number += 1

    def draw_school_background(self, surface):
        """Desenha salas e corredores com os recortes do sprite sheet da escola."""
        surface.fill((28, 42, 61))
        pygame.draw.rect(surface, (42, 63, 84), (0, 140, WIDTH, HEIGHT - 140))
        self._draw_school_tile_bands(surface)
        self._draw_school_rooms(surface)

    def _draw_school_tile_bands(self, surface):
        sprites = self.school_sprites
        tile_start = -int(self.camera_x * 0.16) % 32 - 32
        for x in range(tile_start, WIDTH + 32, 32):
            surface.blit(sprites["brick_tile"], (x, int(142 - self.camera_y * 0.15)))
            surface.blit(sprites["cream_tile"], (x, int(594 - self.camera_y * 0.42)))

    def _draw_school_rooms(self, surface):
        room_width = 1120
        first_room = int(self.camera_x // room_width) - 1
        last_room = int((self.camera_x + WIDTH) // room_width) + 1
        for room in range(first_room, last_room + 1):
            self._draw_school_room(surface, room, room * room_width - self.camera_x)

    def _draw_school_room(self, surface, room, origin_x):
        sprites = self.school_sprites

        def put(name, x, y):
            surface.blit(sprites[name], (int(x), int(y)))

        put("chalkboard", origin_x + 68, 190 - self.camera_y * 0.30)
        put("whiteboard", origin_x + 304, 190 - self.camera_y * 0.30)
        put("clock", origin_x + 548, 78 - self.camera_y * 0.16)
        put("bulletin", origin_x + 676, 190 - self.camera_y * 0.30)
        put("exit", origin_x + 898, 216 - self.camera_y * 0.30)

        room_variant = room % 3
        if room_variant == 0:
            put("bookshelf", origin_x + 60, 420 - self.camera_y * 0.48)
            put("plant", origin_x + 640, 393 - self.camera_y * 0.48)
            put("desk_row", origin_x + 755, 392 - self.camera_y * 0.48)
        elif room_variant == 1:
            put("door", origin_x + 94, 388 - self.camera_y * 0.48)
            put("locker", origin_x + 335, 375 - self.camera_y * 0.48)
            put("lab_table", origin_x + 620, 420 - self.camera_y * 0.48)
        else:
            put("desk_row", origin_x + 80, 385 - self.camera_y * 0.48)
            put("bookshelf", origin_x + 500, 420 - self.camera_y * 0.48)
            put("plant", origin_x + 926, 392 - self.camera_y * 0.48)

    def draw_attack(self, surface):
        """Desenha o efeito visual temporário do ataque."""
        if not self.attack_timer or self.state != PLAYING:
            return
        boosted = self.attack_power > STANDARD_ATTACK_POWER
        center_x = self.player.x - self.camera_x + (52 if self.player.facing_right else -20)
        center_y = self.player.y - self.camera_y + PLAYER_HEIGHT // 2
        color = (255, 158, 74) if boosted else (255, 236, 137)
        radius = 33 if boosted else 23
        pygame.draw.circle(
            surface,
            color,
            (int(center_x), int(center_y)),
            radius,
            4 if boosted else 3,
        )

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
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        layer.fill((5, 12, 28, alpha))
        surface.blit(layer, (0, 0))
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
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        layer.fill((5, 12, 28, alpha))
        surface.blit(layer, (0, 0))

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
