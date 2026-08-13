import pygame
from dialogue import DialogueBox
from hud import draw_ability_ui, draw_hud, draw_text
from level import PHASES, Level
from player import Player
from settings import (ASSET_DIR, HEIGHT, MOTIVATION, PLAYER_HEIGHT,
                      PLAYER_HITBOX_OFFSET_X, PLAYER_HITBOX_WIDTH, WIDTH)


# Fatos curtos mostrados ao encontrar cada livro de pesquisa.
SCIENCE_FACTS = {
    "Curiosidade": "Marie Curie foi a primeira pessoa a receber dois Pr\u00eamios Nobel, em \u00e1reas cient\u00edficas diferentes.",
    "Observa\u00e7\u00e3o": "Bertha Lutz foi uma cientista brasileira e uma das grandes vozes pela participa\u00e7\u00e3o das mulheres na sociedade.",
    "Hip\u00f3tese": "Enedina Alves Marques foi a primeira mulher negra a se formar engenheira no Brasil.",
    "Experimento": "Jaqueline Goes de Jesus participou do sequenciamento do genoma do coronav\u00edrus no Brasil, em 2020.",
    "Registro": "Nise da Silveira transformou a psiquiatria brasileira com cuidado, arte e respeito \u00e0s pessoas.",
    "M\u00e9todo": "Ada Lovelace \u00e9 reconhecida por escrever um dos primeiros algoritmos para uma m\u00e1quina.",
    "Dados": "Katherine Johnson calculou trajet\u00f3rias essenciais para miss\u00f5es espaciais da NASA.",
    "An\u00e1lise": "S\u00f4nia Guimar\u00e3es foi a primeira mulher negra brasileira doutora em F\u00edsica.",
    "Testes": "Rosalind Franklin produziu imagens de raios X que foram fundamentais para compreender a estrutura do DNA.",
    "Resultados": "Mayana Zatz \u00e9 refer\u00eancia brasileira em gen\u00e9tica humana e no estudo de doen\u00e7as neuromusculares.",
    "Cura": "Johanna D\u00f6bereiner contribuiu para o estudo da fixa\u00e7\u00e3o de nitrog\u00eanio, importante para a agricultura brasileira.",
    "Pesquisa completa": "A ci\u00eancia avan\u00e7a quando muitas pessoas fazem perguntas, compartilham dados e persistem juntas.",
}


class Game:
    def __init__(self):
        self.tiles = [pygame.image.load(ASSET_DIR / "tiles" / f"platform{i}.png").convert_alpha() for i in range(1, 5)]
        # Sheet com 4 estilos de plataforma da universidade (pátio, madeira, lab, lab móvel).
        university_sheet = pygame.image.load(
            ASSET_DIR / "tiles" / "university_sheet.png"
        ).convert_alpha()
        self.university_tiles = [
            [self._sheet_crop(university_sheet, (col * 32, row * 32, 32, 32)) for col in range(4)]
            for row in range(4)
        ]
        self.university_props = self._load_university_props()
        # Cada fase pode ter sua própria ambientação.
        school_background = pygame.image.load(
            ASSET_DIR / "backgrounds" / "background_school.png"
        ).convert()
        university_background = pygame.image.load(
            ASSET_DIR / "backgrounds" / "ifsp_background.png"
        ).convert()
        self.backgrounds = [school_background, university_background, school_background]
        # Cópia espelhada: alternar cópia normal/espelhada esconde a costura da repetição.
        self.background_mirror = pygame.transform.flip(university_background, True, False)
        school_sheet = pygame.image.load(
            ASSET_DIR / "fase_escola_tileset" / "escola_sheet.png"
        ).convert()
        # Recortes do novo sheet. Ele é a única arte usada para montar a escola.
        self.school_sprites = {
            "chalkboard": self._sheet_crop(school_sheet, (72, 54, 205, 124)),
            "whiteboard": self._sheet_crop(school_sheet, (281, 54, 190, 124)),
            "clock": self._sheet_crop(school_sheet, (600, 52, 112, 116)),
            "bulletin": self._sheet_crop(school_sheet, (494, 176, 184, 80)),
            "exit": self._sheet_crop(school_sheet, (415, 208, 74, 54)),
            "plant": self._sheet_crop(school_sheet, (694, 158, 93, 125)),
            "desk_row": self._sheet_crop(school_sheet, (912, 152, 310, 94)),
            "locker": self._sheet_crop(school_sheet, (1268, 246, 150, 188)),
            "bookshelf": self._sheet_crop(school_sheet, (478, 456, 196, 102)),
            "door": self._sheet_crop(school_sheet, (250, 554, 136, 190)),
            "lab_table": self._sheet_crop(school_sheet, (732, 610, 258, 126)),
            # Cada recorte abaixo é um único tipo de piso para as plataformas.
            "grass_tile": pygame.transform.scale(self._sheet_crop(school_sheet, (448, 756, 32, 64)), (32, 32)),
            "wood_tile": pygame.transform.scale(self._sheet_crop(school_sheet, (768, 850, 32, 60)), (32, 32)),
            "brick_tile": pygame.transform.scale(self._sheet_crop(school_sheet, (80, 286, 32, 64)), (32, 32)),
            "cream_tile": pygame.transform.scale(self._sheet_crop(school_sheet, (80, 456, 32, 64)), (32, 32)),
        }
        self.background_filter = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.background_filter.fill((38, 53, 76, 72))
        self.university_filter = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.university_filter.fill((55, 65, 80, 85))
        self.underground_filter = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.underground_filter.fill((8, 12, 27, 155))
        # Halo suave que acompanha a Lia: ilumina o caminho sem esconder o cenário.
        light_size = 280
        self.player_light = pygame.Surface((light_size, light_size), pygame.SRCALPHA)
        light_center = light_size // 2
        for radius in range(light_center, 0, -4):
            intensity = 1 - radius / light_center
            alpha = int(3 + 52 * intensity * intensity)
            pygame.draw.circle(
                self.player_light, (255, 239, 192, alpha),
                (light_center, light_center), radius
            )
        self.book = pygame.transform.smoothscale(
            pygame.image.load(ASSET_DIR / "items" / "book.png").convert_alpha(), (30, 38)
        )
        self.checkpoint_flag = pygame.image.load(
            ASSET_DIR / "objects" / "checkpoint_flag.png"
        ).convert_alpha()
        objects_dir = ASSET_DIR / "objects"
        self.puzzle_sprites = {
            # Os cinco arquivos representam os estados consecutivos da alavanca.
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
                pygame.transform.scale(pygame.image.load(objects_dir / f"button_{color}.png").convert_alpha(), (36, 20))
                for color in ("blue", "green", "yellow", "red")
            ],
        }
        enemies_dir = ASSET_DIR / "enemies"
        self.slime_sprites = {
            state: self._load_enemy_sheet(enemies_dir / f"slime_{state}.png")
            for state in ("walk", "jump", "dead", "hurt")
        }
        self.player = Player()
        self.dialogue = DialogueBox()
        self.lives, self.camera_x, self.camera_y = 3, 0, 0
        self.game_over_fade = self.game_over_characters = 0
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_power = 1
        self.attack_was_down = False
        self.dash_was_down = False
        self.dialogue_advance_was_down = False
        self.mouse_attack_requested = False
        self.load_level(0)
        self.state = "title"

    @staticmethod
    def _load_university_props():
        props_dir = ASSET_DIR / "props"
        return {
            name: pygame.image.load(props_dir / f"{name}.png").convert_alpha()
            for name in ("plant_pot", "book_stack", "grad_cap", "banner", "bench", "bush")
        }

    @staticmethod
    def _load_enemy_sheet(path):
        sheet = pygame.image.load(path).convert_alpha()
        # As folhas fornecidas têm células retangulares de 128x64 (não 64x64).
        # Dividir por 64 cortava cada slime ao meio e gerava as animações deformadas.
        frame_width = sheet.get_height() * 2
        frames = []
        for x in range(0, sheet.get_width(), frame_width):
            frame = sheet.subsurface(pygame.Rect(x, 0, frame_width, sheet.get_height()))
            # As artes do slime ocupam uma pequena parte de cada célula 64x64.
            # Recortar a transparência antes de ampliar elimina o efeito de slime minúsculo.
            content = frame.get_bounding_rect()
            if content.width and content.height:
                frame = frame.subsurface(content)
            frames.append(pygame.transform.scale(frame, (64, 32)))
        return frames

    @staticmethod
    def _sheet_crop(sheet, rectangle):
        """Copia um elemento do sheet, evitando que a imagem inteira fique em memória em cada sprite."""
        return sheet.subsurface(pygame.Rect(rectangle)).copy()

    def load_level(self, index):
        self.level = Level(index)
        # O ponto de nascimento da Fase 1 vem do objeto ``spawn`` no Tiled.
        self.checkpoint = self.level.spawn
        self.player.reset(*self.checkpoint)
        self.collected, self.seen_dialogues = set(), set()
        self.lever_on = self.sequence_solved = self.microscope_assembled = False
        self.sequence_progress = 0
        self.microscope_collected = set()
        self.riding_platform = None
        self.interact_was_down = False
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_power = 1
        self.attack_was_down = False
        self.dash_was_down = False
        self.dialogue_advance_was_down = False
        self.mouse_attack_requested = False
        self.camera_x = self.camera_y = 0
        self.message, self.message_timer = self.level.data["subtitle"], 0
        self.state = "playing"

    def respawn(self):
        self.lives -= 1
        if self.lives <= 0:
            self.state = "game_over"
            self.game_over_fade = 0
            self.game_over_characters = 0
        else:
            self.player.reset(*self.checkpoint)
            self.riding_platform = None
            self.camera_y = 0
            self.message, self.message_timer = MOTIVATION, 0

    def update(self, keyboard):
        interaction_down = keyboard.e or keyboard.RETURN
        dialogue_advance_down = interaction_down or keyboard.space
        attack_down = keyboard.f
        dash_down = keyboard.q
        self.interact_pressed = interaction_down and not self.interact_was_down
        self.interact_was_down = interaction_down
        dialogue_advance_pressed = dialogue_advance_down and not self.dialogue_advance_was_down
        self.dialogue_advance_was_down = dialogue_advance_down
        attack_pressed = (attack_down and not self.attack_was_down) or self.mouse_attack_requested
        self.attack_was_down = attack_down
        self.mouse_attack_requested = False
        dash_pressed = dash_down and not self.dash_was_down
        self.dash_was_down = dash_down
        if self.state == "title":
            if keyboard.space or keyboard.RETURN:
                self.lives, self.state = 3, "playing"
            return
        if self.state in ("game_over", "complete"):
            if self.state == "game_over":
                self.game_over_fade = min(60, self.game_over_fade + 1)
                if self.game_over_fade >= 18:
                    self.game_over_characters += 0.75
            if keyboard.r:
                self.lives = 3
                self.load_level(0 if self.state == "complete" else self.level.index)
            return
        if self.dialogue.active:
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
            return
        self.player.update_abilities()
        if dash_pressed:
            self.player.start_dash()
        self.player.read_controls(keyboard)
        self.attack_cooldown = max(0, self.attack_cooldown - 1)
        if attack_pressed and self.attack_cooldown == 0:
            self.attack_timer = 11
            self.attack_cooldown = 20
            self.attack_power = 2 if self.player.dashing else 1
        if self.attack_timer:
            self.attack_timer -= 1
            if self.attack_timer == 0:
                self.attack_power = 1
        self.level.update()
        if self.riding_platform:
            self.player.x += self.riding_platform.dx
            self.player.y += self.riding_platform.dy
        self.move_player()
        self.player.animate()
        self.camera_x += ((self.player.x - WIDTH * .42) - self.camera_x) * .12
        self.camera_x = max(0, min(self.camera_x, self.level.world_width - WIDTH))
        target_y = self.player.y - HEIGHT * .55
        self.camera_y += (target_y - self.camera_y) * .10
        self.camera_y = max(self.level.world_top, min(self.camera_y, self.level.world_height - HEIGHT))
        self.message_timer = max(0, self.message_timer - 1)
        self.handle_interactions()
        self.check_events()

    def request_mouse_attack(self):
        """Chamado por main.py quando o botÃ£o esquerdo do mouse Ã© pressionado."""
        self.mouse_attack_requested = True

    def move_player(self):
        p = self.player
        solids = (self.level.grounds + self.level.wall_blocks
                  + [platform.rect for platform in self.level.platforms])
        p.wall_side = 0
        previous_x = p.x
        p.x += p.vx
        for solid in solids:
            if p.rect.colliderect(solid):
                # Só bloqueia lateralmente quando Lia realmente atravessou uma borda.
                # Isso evita deslocá-la para o lado ao saltar sob uma plataforma.
                previous_right = previous_x + PLAYER_HITBOX_OFFSET_X + PLAYER_HITBOX_WIDTH
                previous_left = previous_x + PLAYER_HITBOX_OFFSET_X
                if p.vx > 0 and previous_right <= solid.left:
                    p.x = solid.left - PLAYER_HITBOX_WIDTH - PLAYER_HITBOX_OFFSET_X
                    p.wall_side = 1
                    p.cancel_dash()
                elif p.vx < 0 and previous_left >= solid.right:
                    p.x = solid.right - PLAYER_HITBOX_OFFSET_X
                    p.wall_side = -1
                    p.cancel_dash()
        p.apply_gravity()
        if p.wall_side and p.vy > p.WALL_SLIDE_SPEED:
            p.vy = p.WALL_SLIDE_SPEED
        previous_y = p.y
        previous_bottom = previous_y + PLAYER_HEIGHT
        p.y += p.vy
        landed = False
        self.riding_platform = None
        # Pisar no topo de um slime é um ataque: Lia quica e o inimigo é derrotado.
        for enemy in self.level.enemies:
            if (enemy.alive and p.vy > 0 and p.rect.colliderect(enemy.rect)
                    and previous_bottom <= enemy.rect.top + 12):
                enemy.stomp()
                p.y = enemy.rect.top - PLAYER_HEIGHT
                p.vy = -10.5
                return
        platform_solids = [(platform.rect, platform) for platform in self.level.platforms]
        ground_solids = [(ground, None) for ground in self.level.grounds]
        wall_solids = [(wall, None) for wall in self.level.wall_blocks]
        for solid, moving_platform in platform_solids + ground_solids + wall_solids:
            if p.rect.colliderect(solid) and p.vy >= 0 and previous_bottom <= solid.top + 10:
                p.y, p.vy, landed = solid.top - PLAYER_HEIGHT, 0, True
                if moving_platform:
                    self.riding_platform = moving_platform
            elif p.rect.colliderect(solid) and p.vy < 0 and previous_y >= solid.bottom - 10:
                # Impacto pela parte de baixo: interrompe o salto no teto.
                p.y, p.vy = solid.bottom, 0
        p.coyote_time = 7 if landed else max(0, p.coyote_time - 1)
        if landed:
            p.wall_jump_used = False
        p.try_jump()

    def check_events(self):
        p = self.player
        # Assim que Lia sai da tela, a queda termina: não há sprites no vazio.
        if p.y > self.level.world_height + 180:
            self.respawn()
            return
        self.check_enemies()
        if self.state != "playing":
            return
        for cp in self.level.checkpoints:
            if p.rect.colliderect(cp):
                # A base da bandeira coincide com o topo da plataforma.
                self.checkpoint = (cp.x, cp.bottom - PLAYER_HEIGHT)
                self.message, self.message_timer = "Checkpoint: Centro de pesquisa alcançado!", 130
        for index, (item, name) in enumerate(self.level.research):
            if index not in self.collected and p.rect.colliderect(item):
                self.collected.add(index)
                self.message, self.message_timer = f"Parte da pesquisa obtida: {name}", 0
                fact = SCIENCE_FACTS.get(name, "Toda descoberta come\u00e7a com uma pergunta e cresce com persist\u00eancia.")
                self.dialogue.start("Ci\u00eancia Delas", fact)
                return
        if self.level.is_underground and self.sequence_solved:
            for index, (item, _) in enumerate(self.level.microscope_parts):
                if index not in self.microscope_collected and p.rect.colliderect(item):
                    self.microscope_collected.add(index)
        for index, (position, speaker, text) in enumerate(self.level.data["dialogues"]):
            if index not in self.seen_dialogues and p.x >= position:
                self.seen_dialogues.add(index)
                self.dialogue.start(speaker, text)
                return
        if p.x >= self.level.world_width - 100:
            needs_microscope = self.level.is_underground and not self.microscope_assembled
            if len(self.collected) < len(self.level.research) or needs_microscope:
                self.message, self.message_timer = "Encontre todas as partes da pesquisa antes de avançar.", 0
                p.x = self.level.world_width - 160
            elif self.level.index == len(PHASES) - 1:
                self.state = "complete"
            else:
                self.load_level(self.level.index + 1)

    def check_enemies(self):
        """Ataque (F), ataque reforçado durante dash e contato com os slimes."""
        attack_box = None
        if self.attack_timer:
            reach = 36 if self.attack_power > 1 else 22
            offset = PLAYER_HITBOX_WIDTH if self.player.facing_right else -(24 + reach)
            attack_box = self.player.rect.move(offset, 4).inflate(reach, 10)
        for enemy in self.level.enemies:
            if not enemy.alive:
                continue
            if attack_box and attack_box.colliderect(enemy.rect):
                enemy.take_hit(self.attack_power)
            elif self.player.rect.colliderect(enemy.rect):
                self.respawn()
                return

    def handle_interactions(self):
        """Alavanca, sequência de botões e bancada do laboratório subterrâneo."""
        if not self.level.is_underground or not self.interact_pressed:
            return
        player = self.player
        if self.level.top_lever and player.rect.colliderect(self.level.top_lever.inflate(55, 55)):
            self.level.call_elevator("down")
            return
        if self.level.bottom_lever and player.rect.colliderect(self.level.bottom_lever.inflate(55, 55)):
            self.level.call_elevator("up")
            return
        if self.level.upper_bottom_lever and player.rect.colliderect(self.level.upper_bottom_lever.inflate(55, 55)):
            self.level.call_upper_elevator("up")
            return
        if self.level.upper_top_lever and player.rect.colliderect(self.level.upper_top_lever.inflate(55, 55)):
            self.level.call_upper_elevator("down")
            return
        if player.rect.colliderect(self.level.panel_lever.inflate(55, 55)):
            self.lever_on = not self.lever_on
            self.level.set_lever_active("panel", self.lever_on)
            if self.lever_on:
                self.dialogue.start("Lia", "A alavanca ligou o painel. A ordem é: azul, verde, amarelo e vermelho.")
            else:
                self.sequence_progress = 0
                self.dialogue.start("Lia", "A alavanca desligou o painel.")
            return
        for index, button in enumerate(self.level.buttons):
            if player.rect.colliderect(button.inflate(55, 55)):
                if not self.lever_on:
                    self.dialogue.start("Painel", "O painel está sem energia. Encontre e puxe a alavanca.")
                elif self.sequence_solved:
                    self.dialogue.start("Painel", "Sequência concluída. As peças do microscópio foram liberadas.")
                elif index == self.sequence_progress:
                    self.sequence_progress += 1
                    if self.sequence_progress == len(self.level.buttons):
                        self.sequence_solved = True
                        self.dialogue.start("Painel", "Sequência correta! As peças do microscópio foram liberadas.")
                else:
                    self.sequence_progress = 0
                    self.dialogue.start("Painel", "Sequência incorreta. O painel foi reiniciado.")
                return
        if player.rect.colliderect(self.level.bench.inflate(70, 60)):
            if len(self.microscope_collected) < len(self.level.microscope_parts):
                self.dialogue.start("Lia", "Ainda faltam peças para montar o microscópio.")
            elif not self.microscope_assembled:
                self.microscope_assembled = True
                self.level.activate_return_route()
                self.dialogue.start(
                    "Lia",
                    "Microscópio montado! As plataformas de retorno foram liberadas; preciso voltar pelo caminho acima."
                )

    def draw(self, screen):
        surface = screen.surface
        # Limpa toda a janela, inclusive a área adicionada na resolução maior.
        surface.fill((6, 14, 29))
        if self.level.index == 0:
            self.draw_school_background(surface)
        elif self.level.index == 1:
            self.draw_university_background(surface)
        else:
            background = self.backgrounds[self.level.index]
            image_width = background.get_width()
            for x in range(-int(self.camera_x) % image_width - image_width, WIDTH, image_width):
                surface.blit(background, (x, 0))
        # Atenua o cenário antes dos elementos jogáveis serem desenhados.
        surface.blit(self.background_filter, (0, 0))
        if self.level.index == 1:
            # Reduz o contraste do fundo da universidade sem escurecer as plataformas.
            surface.blit(self.university_filter, (0, 0))
        if self.player.y > 780:
            surface.blit(self.underground_filter, (0, 0))
        self.level.draw(
            surface, self.camera_x, self.camera_y, self.tiles, self.book, self.checkpoint_flag,
            self.checkpoint, self.collected, self.lever_on, self.sequence_progress,
            self.sequence_solved, self.microscope_collected, self.microscope_assembled,
            self.puzzle_sprites, self.slime_sprites, self.school_sprites, draw_text,
            self.university_tiles, self.university_props
        )
        # A luz fica atrás da personagem para preservar as cores da sprite.
        light_x = int(self.player.x - self.camera_x + PLAYER_HITBOX_WIDTH // 2
                      - self.player_light.get_width() // 2)
        light_y = int(self.player.y - self.camera_y + PLAYER_HEIGHT // 2
                      - self.player_light.get_height() // 2)
        surface.blit(self.player_light, (light_x, light_y))
        self.draw_dash_trail(surface)
        self.player.draw(surface, self.camera_x, self.camera_y)
        self.draw_attack(surface)
        draw_hud(surface, self.level.data["name"], self.lives, len(self.collected), len(self.level.research),
                 self.message, self.message_timer, len(self.microscope_collected),
                 len(self.level.microscope_parts), self.microscope_assembled)
        draw_ability_ui(surface, self.player.dash_cooldown, self.player.DASH_COOLDOWN,
                        self.attack_cooldown, 20, not self.player.wall_jump_used)
        self.dialogue.draw(surface, draw_text)
        if self.state == "title":
            self.overlay(surface, "Echoes of Life", "Pressione ESPAÇO para começar")
        elif self.state == "game_over":
            self.draw_game_over_overlay(surface)
        elif self.state == "complete":
            self.overlay(surface, "Pesquisa apresentada no congresso!", "Lia mostrou que ciência se faz com persistência.\nPressione R para jogar novamente")

    def draw_university_background(self, surface):
        """Repete o pátio da universidade espelhando cada cópia alternada, para que a
        emenda entre repetições vire uma reflexão simétrica em vez de um corte visível."""
        background = self.backgrounds[1]
        image_width = background.get_width()
        x = -int(self.camera_x) % image_width - image_width
        # Índice absoluto do tile (relativo a x=0 do mundo) para saber se espelha.
        tile_number = (x + int(self.camera_x)) // image_width
        while x < WIDTH:
            image = self.background_mirror if (tile_number % 2) else background
            surface.blit(image, (x, 0))
            x += image_width
            tile_number += 1

    def draw_school_background(self, surface):
        """Salas e corredores da escola, inteiramente construídos com escola_sheet.png."""
        surface.fill((28, 42, 61))
        # Luz suave de sala: o fundo é menos contrastado que as plataformas jogáveis.
        pygame.draw.rect(surface, (42, 63, 84), (0, 140, WIDTH, HEIGHT - 140))
        sprites = self.school_sprites
        def put(name, x, y):
            surface.blit(sprites[name], (int(x), int(y)))

        room_width = 1120
        first_room = int(self.camera_x // room_width) - 1
        last_room = int((self.camera_x + WIDTH) // room_width) + 1
        # Faixas de tijolos discretas unem os ambientes sem simular um chão com colisão.
        tile_start = -int(self.camera_x * .16) % 32 - 32
        for x in range(tile_start, WIDTH + 32, 32):
            surface.blit(sprites["brick_tile"], (x, int(142 - self.camera_y * .15)))
            surface.blit(sprites["cream_tile"], (x, int(594 - self.camera_y * .42)))
        for room in range(first_room, last_room + 1):
            origin_x = room * room_width - self.camera_x
            # Quadros, relógios e murais caracterizam cada sala.
            put("chalkboard", origin_x + 68, 190 - self.camera_y * .30)
            put("whiteboard", origin_x + 304, 190 - self.camera_y * .30)
            put("clock", origin_x + 548, 78 - self.camera_y * .16)
            put("bulletin", origin_x + 676, 190 - self.camera_y * .30)
            put("exit", origin_x + 898, 216 - self.camera_y * .30)
            # Cada corredor recebe um ponto de interesse diferente; tudo fica atrás do percurso.
            if room % 3 == 0:
                put("bookshelf", origin_x + 60, 420 - self.camera_y * .48)
                put("plant", origin_x + 640, 393 - self.camera_y * .48)
                put("desk_row", origin_x + 755, 392 - self.camera_y * .48)
            elif room % 3 == 1:
                put("door", origin_x + 94, 388 - self.camera_y * .48)
                put("locker", origin_x + 335, 375 - self.camera_y * .48)
                put("lab_table", origin_x + 620, 420 - self.camera_y * .48)
            else:
                put("desk_row", origin_x + 80, 385 - self.camera_y * .48)
                put("bookshelf", origin_x + 500, 420 - self.camera_y * .48)
                put("plant", origin_x + 926, 392 - self.camera_y * .48)

    def draw_attack(self, surface):
        """Efeito visual temporário; pode ser trocado pela sprite de ataque depois."""
        if not self.attack_timer or self.state != "playing":
            return
        boosted = self.attack_power > 1
        center_x = self.player.x - self.camera_x + (52 if self.player.facing_right else -20)
        center_y = self.player.y - self.camera_y + PLAYER_HEIGHT // 2
        color = (255, 158, 74) if boosted else (255, 236, 137)
        radius = 33 if boosted else 23
        pygame.draw.circle(surface, color, (int(center_x), int(center_y)), radius, 4 if boosted else 3)

    def draw_dash_trail(self, surface):
        """Rastro simples para deixar o dash legível antes da sprite especial existir."""
        if not self.player.dashing:
            return
        direction = 1 if self.player.dash_direction > 0 else -1
        start_x = self.player.x - self.camera_x + PLAYER_HITBOX_WIDTH // 2 - direction * 12
        center_y = self.player.y - self.camera_y + PLAYER_HEIGHT // 2
        for offset, alpha in ((0, 150), (12, 95), (24, 45)):
            layer = pygame.Surface((42, 8), pygame.SRCALPHA)
            layer.fill((91, 220, 255, alpha))
            x = start_x - direction * (offset + (42 if direction < 0 else 0))
            surface.blit(layer, (int(x), int(center_y - 4)))

    def overlay(self, surface, title, body, alpha=210):
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        layer.fill((5, 12, 28, alpha)); surface.blit(layer, (0, 0))
        draw_text(surface, title, (WIDTH//2, HEIGHT//2-65), 42, "#ffe477", True)
        for line_number, line in enumerate(body.split("\n")):
            draw_text(surface, line, (WIDTH//2, HEIGHT//2+5+line_number*34), 24, "white", True)

    def draw_game_over_overlay(self, surface):
        """Fade escuro e textos revelados em sequência, como nos diálogos."""
        alpha = int(210 * self.game_over_fade / 60)
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        layer.fill((5, 12, 28, alpha))
        surface.blit(layer, (0, 0))

        title = "Você consegue, Lia!"
        message = MOTIVATION
        restart = "Pressione R para tentar de novo"
        remaining = int(self.game_over_characters)

        visible_title = title[:max(0, min(len(title), remaining))]
        remaining -= len(title)
        visible_message = message[:max(0, min(len(message), remaining))]
        remaining -= len(message)
        visible_restart = restart[:max(0, min(len(restart), remaining))]

        draw_text(surface, visible_title, (WIDTH//2, HEIGHT//2-65), 42, "#ffe477", True)
        draw_text(surface, visible_message, (WIDTH//2, HEIGHT//2+5), 24, "white", True)
        draw_text(surface, visible_restart, (WIDTH//2, HEIGHT//2+39), 24, "white", True)
