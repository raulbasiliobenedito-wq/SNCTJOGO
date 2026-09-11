"""Minigames de arraste com o mouse (ver PLANO_MINIGAMES.md).

Cada minigame é uma tela que PAUSA a jogabilidade, recebe clique/arraste/
soltura de mouse repassados por main.py e main_web.py, e devolve um
resultado quando termina — o mesmo papel que Hint (hint.py) já cumpre
pra dicas, só que interativo em vez de só texto. Game.update dá
prioridade a `self.minigame.active` antes mesmo de `dialogue.active` (ver
game.py), e Game.draw desenha por cima de tudo, do mesmo jeito que
Hint.draw.

Nenhuma classe aqui chama `audio` diretamente — só game.py mexe com som
(mesma convenção de level.py/enemy.py/player.py). Um minigame concreto
pede efeitos enfileirando o nome em `self.sfx_queue` (ver
`_BaseMinigame.queue_sfx`); `MinigameManager.drain_sfx()` esvazia essa
fila a cada quadro pra quem chamou (Game._update_minigame) tocar de
verdade.

MinigameManager é o que Game guarda (`self.minigame`, ver game.py
Game.__init__). Ele não sabe nada sobre microscópio ou caixa de energia
— só repassa update/draw/eventos pro minigame concreto (`self.current`)
e observa `finished`/`result` pra saber quando fechar sozinho."""

import math

import pygame


class _BaseMinigame:
    """Interface comum. Subclasses sobrescrevem o que precisarem; os
    quatro métodos de evento (`on_click/on_drag/on_release`) e `update`
    são no-op por padrão pra quem não usa mouse (não existe hoje, mas
    evita builar tudo de novo se um dia tiver um minigame só de teclado)."""

    #: Chave curta que identifica o tipo de minigame (ver Game._update_minigame,
    #: que despacha pro handler de conclusão certo a partir disso).
    key = "base"

    def __init__(self):
        self.finished = False
        self.result = None
        self.sfx_queue = []

    def queue_sfx(self, name):
        self.sfx_queue.append(name)

    def finish(self, result):
        self.finished = True
        self.result = result

    def close(self):
        """Chamado ao fechar por ESC (sem ter terminado) — subclasses só
        precisam sobrescrever se tiverem algo a fazer além de largar a
        peça que porventura estava sendo arrastada (ver DragField.holding
        nas subclasses que usam DragField: o estado de progresso já mora
        num dict do próprio Game, passado por referência no construtor,
        então fechar no meio não perde nada)."""

    def update(self, dt):
        pass

    def draw(self, surface, text_fn):
        pass

    def on_click(self, pos):
        pass

    def on_drag(self, pos):
        pass

    def on_release(self, pos):
        pass


class MinigameManager:
    """Dono do minigame ativo (`Game.minigame`). Ver docstring do módulo."""

    def __init__(self):
        self.current = None

    @property
    def active(self):
        return self.current is not None

    def open(self, minigame):
        self.current = minigame

    def close(self):
        if self.current is not None:
            self.current.close()
        self.current = None

    def update(self, dt):
        if self.current is not None:
            self.current.update(dt)

    def draw(self, surface, text_fn):
        if self.current is not None:
            self.current.draw(surface, text_fn)

    def on_click(self, pos):
        if self.current is not None:
            self.current.on_click(pos)

    def on_drag(self, pos):
        if self.current is not None:
            self.current.on_drag(pos)

    def on_release(self, pos):
        if self.current is not None:
            self.current.on_release(pos)

    def drain_sfx(self):
        """Esvazia e devolve os efeitos pedidos pelo minigame ativo desde
        a última chamada (ver _BaseMinigame.queue_sfx) — quem chama toca
        de verdade via audio.play_sfx (só game.py faz isso, ver docstring
        do módulo)."""
        if self.current is None or not self.current.sfx_queue:
            return ()
        pending = self.current.sfx_queue
        self.current.sfx_queue = []
        return pending

    def pop_result(self):
        """Se o minigame ativo terminou sozinho (ver _BaseMinigame.finish),
        fecha e devolve (key, result) pra Game decidir o que fazer —
        None se nada terminou ainda neste quadro."""
        if self.current is None or not self.current.finished:
            return None
        key = self.current.key
        result = self.current.result
        self.current = None
        return key, result


class DragField:
    """Peças arrastáveis + encaixes num painel (ver PLANO_MINIGAMES.md
    §1). Não decide sozinho o que é "certo" — quem usa isto (ex.:
    MicroscopeMinigame) chama `release()` pra saber qual peça estava
    sendo largada e qual encaixe está sob o CENTRO dela (testar
    sobreposição de retângulos deixaria o encaixe grande demais e o
    jogador acertaria sem querer), decide se aceita, e chama `place()`
    ou `return_home()` de volta."""

    #: Quadros da animação de volta pro lugar de origem quando a peça é
    #: solta fora de qualquer encaixe (ou num encaixe recusado).
    RETURN_FRAMES = 8

    def __init__(self):
        self.pieces = []
        self.slots = []
        self.holding = None
        self.grab_offset = (0, 0)
        self._returning = []

    def add_piece(self, key, rect, image, label=""):
        self.pieces.append(
            {
                "key": key,
                "rect": rect.copy(),
                "home": rect.copy(),
                "image": image,
                "label": label,
                "placed": False,
            }
        )

    def add_slot(self, key, rect, label=""):
        self.slots.append({"key": key, "rect": rect.copy(), "filled": False, "label": label})

    def slot(self, key):
        for slot in self.slots:
            if slot["key"] == key:
                return slot
        return None

    def piece_at(self, pos):
        for piece in reversed(self.pieces):
            if not piece["placed"] and piece["rect"].collidepoint(pos):
                return piece
        return None

    def _slot_under_center(self, piece):
        center = piece["rect"].center
        for slot in self.slots:
            if slot["rect"].collidepoint(center):
                return slot
        return None

    def grab(self, pos):
        piece = self.piece_at(pos)
        if piece is None:
            return None
        self.holding = piece
        self.grab_offset = (pos[0] - piece["rect"].x, pos[1] - piece["rect"].y)
        return piece

    def drag_to(self, pos):
        if self.holding is None:
            return
        self.holding["rect"].x = pos[0] - self.grab_offset[0]
        self.holding["rect"].y = pos[1] - self.grab_offset[1]

    def release(self):
        """Solta a peça que estava sendo arrastada. Devolve (peça, encaixe
        sob o centro dela) — encaixe pode ser None (soltou fora de tudo).
        Não muda nada sozinho: quem chamou decide com place()/return_home()."""
        piece = self.holding
        self.holding = None
        if piece is None:
            return None, None
        return piece, self._slot_under_center(piece)

    def place(self, piece, slot):
        piece["placed"] = True
        piece["rect"].center = slot["rect"].center
        slot["filled"] = True

    def return_home(self, piece):
        self._returning.append([piece, piece["rect"].topleft, self.RETURN_FRAMES])

    def update(self):
        still_returning = []
        for entry in self._returning:
            piece, start, frames_left = entry
            frames_left -= 1
            progress = 1 - frames_left / self.RETURN_FRAMES
            home = piece["home"]
            piece["rect"].x = round(start[0] + (home.x - start[0]) * progress)
            piece["rect"].y = round(start[1] + (home.y - start[1]) * progress)
            if frames_left > 0:
                entry[2] = frames_left
                still_returning.append(entry)
            else:
                piece["rect"].topleft = home.topleft
        self._returning = still_returning

    def draw(self, surface):
        for slot in self.slots:
            color = (86, 138, 108) if slot["filled"] else (54, 58, 78)
            pygame.draw.rect(surface, color, slot["rect"], border_radius=10)
            border = (150, 214, 178) if slot["filled"] else (150, 150, 168)
            pygame.draw.rect(surface, border, slot["rect"], 2, border_radius=10)
        # A peça sendo arrastada desenha por último (fica por cima das outras).
        pieces_in_order = [p for p in self.pieces if p is not self.holding]
        if self.holding is not None:
            pieces_in_order.append(self.holding)
        for piece in pieces_in_order:
            image = piece["image"]
            surface.blit(image, image.get_rect(center=piece["rect"].center))


def draw_dashed_rect(surface, rect, color, dash=10, gap=6, width=2):
    """Retângulo tracejado — usado pra silhueta do slot vazio no painel do
    microscópio, no mesmo espírito de "desenhado por código" que o HUD já
    usa pra barras/painéis (ver hud.py)."""
    x, y, w, h = rect
    for start_x in range(x, x + w, dash + gap):
        end_x = min(start_x + dash, x + w)
        pygame.draw.line(surface, color, (start_x, y), (end_x, y), width)
        pygame.draw.line(surface, color, (start_x, y + h), (end_x, y + h), width)
    for start_y in range(y, y + h, dash + gap):
        end_y = min(start_y + dash, y + h)
        pygame.draw.line(surface, color, (x, start_y), (x, end_y), width)
        pygame.draw.line(surface, color, (x + w, start_y), (x + w, end_y), width)


PANEL_BG = (24, 27, 42)
PANEL_BORDER = (150, 150, 168)
DIM_COLOR = (4, 6, 12)
DIM_ALPHA = 205


def draw_modal_backdrop(surface, panel_rect, width, height):
    """Escurece a tela e desenha o painel de fundo — comum aos dois
    minigames. Opacidade fixa, sem fade de entrada (o minigame abre "de
    golpe" — não há necessidade de suavizar: quem abriu já sabe que vai
    interagir, ao contrário de uma dica que aparece sem aviso, ver
    hint.py)."""
    dim = pygame.Surface((width, height), pygame.SRCALPHA)
    dim.fill((*DIM_COLOR, DIM_ALPHA))
    surface.blit(dim, (0, 0))
    pygame.draw.rect(surface, PANEL_BG, panel_rect, border_radius=18)
    pygame.draw.rect(surface, PANEL_BORDER, panel_rect, 3, border_radius=18)


# ---------------------------------------------------------------------------
# Minigame 1 — montar o microscópio (ver PLANO_MINIGAMES.md §2)
# ---------------------------------------------------------------------------

#: Ordem de montagem de baixo pra cima — "como microscópio de verdade"
#: (ver PLANO_MINIGAMES.md §2). O índice na lista é a ordem de
#: pré-requisito: só dá pra encaixar a peça N se todas as anteriores já
#: estiverem no lugar.
MICROSCOPE_ORDER = ("base", "iluminador", "objetiva", "ocular")

MICROSCOPE_DISPLAY_NAME = {
    "base": "Base",
    "iluminador": "Iluminador",
    "objetiva": "Objetiva",
    "ocular": "Ocular",
}

#: Frase usada quando a peça certa cai no encaixe errado — explica a
#: função de verdade da peça em vez de só recusar (ver PLANO_MINIGAMES.md
#: §2: "ensina o nome e a função de cada parte do microscópio").
MICROSCOPE_FUNCTION_TEXT = {
    "base": "a base: é o pé que sustenta tudo. Ela vai embaixo.",
    "iluminador": "o iluminador: é a luz, fica logo acima da base.",
    "objetiva": "a objetiva: é a lente que fica perto da amostra.",
    "ocular": "a ocular: é por ela que se olha. Ela vai no topo.",
}

MICROSCOPE_NOUN = {
    "base": "a base",
    "iluminador": "o iluminador",
    "objetiva": "a objetiva",
    "ocular": "a ocular",
}

#: Deslocamento (em pixels NATIVOS, antes de qualquer escala) de cada
#: peça em relação ao canto superior-esquerdo do microscópio montado —
#: veio direto de quem gerou microscope_body.png + microscope_{lens,
#: ocular,light,base}.png recortando as MESMAS coordenadas do microscópio
#: já desenhado em bancada_microscopio.png (ver conversa no chat: 0px de
#: diferença por construção). Usado só pra recompor visualmente o
#: "montado" do minigame a partir das peças de verdade — ver
#: _compose_microscope — em vez de uma imagem solta desenhada à parte,
#: que podia ficar "parecida" mas não igual se algum dia uma peça mudar.
MICROSCOPE_PART_OFFSETS = {
    "objetiva": (21, 15),
    "ocular": (21, -1),
    "iluminador": (13, 36),
    "base": (0, 47),
}
MICROSCOPE_BODY_OFFSET = (3, 8)

#: Fator de ampliação aplicado ao conjunto JÁ composto (não peça por
#: peça) — pygame.transform.scale (nearest-neighbor, sem suavizar) pra
#: manter o pixel art nítido. Composto nativo fica pequeno (a objetiva
#: sozinha tem só 14x17), então precisa desse fator pra não sumir no
#: painel de 1080x680 do minigame.
MICROSCOPE_COMPOSE_SCALE = 4


def _compose_microscope(sprites_by_identity, body_sprite):
    """Recompõe o microscópio "montado" a partir de microscope_body.png +
    as 4 peças (as MESMAS imagens usadas nos encaixes/peças arrastáveis),
    cada uma no deslocamento nativo de MICROSCOPE_PART_OFFSETS/
    MICROSCOPE_BODY_OFFSET, e só então amplia o conjunto inteiro de uma
    vez (MICROSCOPE_COMPOSE_SCALE) — nunca peça por peça, senão
    arredondamentos diferentes por peça podem desalinhar 1px entre elas."""
    parts = [(body_sprite, MICROSCOPE_BODY_OFFSET)]
    parts += [
        (sprites_by_identity[identity], offset)
        for identity, offset in MICROSCOPE_PART_OFFSETS.items()
    ]
    min_x = min(x for _, (x, y) in parts)
    min_y = min(y for _, (x, y) in parts)
    max_x = max(x + img.get_width() for img, (x, y) in parts)
    max_y = max(y + img.get_height() for img, (x, y) in parts)
    native = pygame.Surface((max_x - min_x, max_y - min_y), pygame.SRCALPHA)
    for img, (x, y) in parts:
        native.blit(img, (x - min_x, y - min_y))
    size = (native.get_width() * MICROSCOPE_COMPOSE_SCALE, native.get_height() * MICROSCOPE_COMPOSE_SCALE)
    return pygame.transform.scale(native, size)


class MicroscopeMinigame(_BaseMinigame):
    """Painel central: à esquerda 4 encaixes empilhados (base embaixo,
    ocular no topo), à direita as peças embaralhadas. Peça certa, encaixe
    certo, fora de ordem = recusada explicando o que falta. Peça no
    encaixe errado = recusada explicando a função da peça. Ao encaixar as
    4, mostra o microscópio montado com os nomes por 2s e termina
    sozinho (`finish("completed")`).

    `slots_state` é um dict (`Game.microscope_slots`, ver game.py) que
    este minigame lê/escreve DIRETO — é por isso que fechar no meio com
    ESC não perde progresso: o dict já mora em Game, só é passado por
    referência aqui."""

    key = "microscope"

    PANEL_SIZE = (1080, 680)
    COMPLETE_HOLD_FRAMES = 120  # 2s a 60fps

    def __init__(self, width, height, sprites_by_identity, complete_sprite, slots_state, key=None, body_sprite=None):
        super().__init__()
        # `key` opcional: o laboratório escondido (ver a conversa sobre o
        # elevador) reaproveita esta MESMA classe pra uma segunda bancada,
        # separada da Fase 1 — sem isso, Game._finish_minigame não teria
        # como distinguir qual das duas terminou (ambas cairiam em
        # key == "microscope").
        if key:
            self.key = key
        self.width = width
        self.height = height
        self.sprites = sprites_by_identity
        if body_sprite is not None:
            # Recompõe do corpo + as 4 peças de verdade (ver
            # _compose_microscope) em vez da imagem solta
            # microscope_complete.png — o "montado" do minigame passa a
            # ser literalmente as mesmas peças que o jogador arrastou, não
            # uma arte parecida à parte. Sem microscope_body.png salvo
            # ainda em images/objects, cai pro complete_sprite de sempre.
            self.complete_sprite = _compose_microscope(sprites_by_identity, body_sprite)
        else:
            self.complete_sprite = complete_sprite
        self.slots_state = slots_state  # {"base": bool, ...} — persistido em Game

        panel_w, panel_h = self.PANEL_SIZE
        self.panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
        self.panel_rect.center = (width // 2, height // 2)

        self.field = DragField()
        self._build_slots()
        self._build_pieces()

        self._reject_message = ""
        self._reject_timer = 0
        self._complete_timer = 0
        self._all_filled = all(self.slots_state.values())

    def _build_slots(self):
        slot_w, slot_h, gap = 220, 120, 22
        top = self.panel_rect.y + 60
        x = self.panel_rect.x + 90
        # De cima pra baixo: ocular, objetiva, iluminador, base — a
        # ordem visual "de montagem" é o inverso (MICROSCOPE_ORDER é de
        # baixo pra cima).
        for row, identity in enumerate(reversed(MICROSCOPE_ORDER)):
            rect = pygame.Rect(x, top + row * (slot_h + gap), slot_w, slot_h)
            self.field.add_slot(identity, rect, MICROSCOPE_DISPLAY_NAME[identity])
            if self.slots_state.get(identity):
                # Já estava encaixada de uma sessão anterior (ESC no meio) —
                # entra direto como peça "placed", sem ficar arrastável.
                self.field.add_piece(identity, rect, self.sprites[identity], MICROSCOPE_DISPLAY_NAME[identity])
                self.field.pieces[-1]["placed"] = True
                self.field.slot(identity)["filled"] = True

    def _build_pieces(self):
        pending = [identity for identity in MICROSCOPE_ORDER if not self.slots_state.get(identity)]
        piece_w, piece_h, gap = 130, 130, 24
        start_x = self.panel_rect.right - 90 - piece_w
        start_y = self.panel_rect.y + 90
        # Embaralha visualmente (não por sorteio de verdade: a ordem em
        # MICROSCOPE_ORDER já não é a ordem de leitura de Level.
        # microscope_parts, então já sai "fora de ordem" sozinha; inverter
        # aqui só evita que o layout pareça óbvio demais quando nada foi
        # coletado fora de ordem por acaso).
        shuffled = list(reversed(pending))
        for index, identity in enumerate(shuffled):
            rect = pygame.Rect(
                start_x, start_y + index * (piece_h + gap), piece_w, piece_h
            )
            self.field.add_piece(identity, rect, self.sprites[identity], MICROSCOPE_DISPLAY_NAME[identity])

    def _missing_prereq(self, identity):
        index = MICROSCOPE_ORDER.index(identity)
        for prior in MICROSCOPE_ORDER[:index]:
            if not self.slots_state.get(prior):
                return prior
        return None

    def _reject(self, message):
        self._reject_message = message
        self._reject_timer = 150
        self.queue_sfx("wrong_sequence_sound")

    def update(self, dt):
        self.field.update()
        if self._reject_timer > 0:
            self._reject_timer -= 1
        if self._all_filled:
            self._complete_timer += 1
            if self._complete_timer >= self.COMPLETE_HOLD_FRAMES:
                self.finish("completed")

    def on_click(self, pos):
        if self._all_filled:
            return
        self.field.grab(pos)

    def on_drag(self, pos):
        if self._all_filled:
            return
        self.field.drag_to(pos)

    def on_release(self, pos):
        if self._all_filled:
            return
        piece, slot = self.field.release()
        if piece is None:
            return
        identity = piece["key"]
        if slot is None or slot["filled"]:
            self.field.return_home(piece)
            return
        if slot["key"] != identity:
            self._reject(f"Essa é {MICROSCOPE_FUNCTION_TEXT[identity]}")
            self.field.return_home(piece)
            return
        missing = self._missing_prereq(identity)
        if missing is not None:
            noun = MICROSCOPE_NOUN[identity]
            missing_noun = MICROSCOPE_NOUN[missing]
            self._reject(f"{noun.capitalize()} não tem onde se apoiar ainda — falta {missing_noun}.")
            self.field.return_home(piece)
            return
        self.field.place(piece, slot)
        self.slots_state[identity] = True
        self.queue_sfx("item_sound")
        if all(self.slots_state.values()):
            self._all_filled = True

    def draw(self, surface, text_fn):
        draw_modal_backdrop(surface, self.panel_rect, self.width, self.height)
        text_fn(
            surface, "Montar o microscópio",
            (self.panel_rect.centerx, self.panel_rect.y + 26), 26, "#f4e4a5", True,
        )

        if self._all_filled:
            self._draw_complete(surface, text_fn)
            return

        for slot in self.field.slots:
            if not slot["filled"]:
                draw_dashed_rect(surface, slot["rect"], (120, 120, 140))
        self.field.draw(surface)
        for slot in self.field.slots:
            if slot["filled"]:
                text_fn(
                    surface, slot["label"],
                    (slot["rect"].right + 70, slot["rect"].centery), 18, "#e7edf5", True,
                )

        text_fn(
            surface, "Arraste cada peça pro encaixe certo — de baixo pra cima.",
            (self.panel_rect.centerx, self.panel_rect.bottom - 56), 16, "#b9c4d4", True,
        )
        text_fn(
            surface, "[ESC] fechar (o progresso fica salvo)",
            (self.panel_rect.centerx, self.panel_rect.bottom - 28), 13, "#8b96a8", True,
        )

        if self._reject_timer > 0:
            text_fn(
                surface, self._reject_message,
                (self.panel_rect.centerx, self.panel_rect.bottom - 90), 17, "#ff9d9d", True,
            )

    def _draw_complete(self, surface, text_fn):
        image = self.complete_sprite
        center = (self.panel_rect.centerx, self.panel_rect.centery - 40)
        surface.blit(image, image.get_rect(center=center))
        text_fn(surface, "Microscópio montado!", (center[0], center[1] - image.get_height() // 2 - 40), 24, "#c8f5d6", True)
        names = " · ".join(MICROSCOPE_DISPLAY_NAME[identity] for identity in MICROSCOPE_ORDER)
        text_fn(surface, names, (center[0], center[1] + image.get_height() // 2 + 30), 16, "#e7edf5", True)


# ---------------------------------------------------------------------------
# Minigame 2 — caixa de energia (ver PLANO_MINIGAMES.md §3)
# ---------------------------------------------------------------------------

WIRE_COLORS = ("vermelho", "azul", "verde", "amarelo")

#: Cor do fio -> chave do terminal certo, segundo o diagrama impresso no
#: verso da tampa (ver PLANO_MINIGAMES.md §3.3). Fixado aqui em vez de
#: "lido" da arte de tampa_caixa.png (que é só decorativa) — o diagrama
#: que decide certo/errado É este dicionário; _draw_fios desenha a
#: legenda por cima como texto pra garantir que ela bate 100% com a regra,
#: em vez de depender do texto pintado dentro do PNG.
WIRE_TERMINAL = {
    "vermelho": "iluminacao",
    "azul": "ventilacao",
    "verde": "trava",
    "amarelo": "bomba",
}

TERMINAL_LABELS = {
    "iluminacao": "ILUMINAÇÃO",
    "ventilacao": "VENTILAÇÃO",
    "trava": "TRAVA DA PORTA",
    "bomba": "BOMBA",
}

#: Ordem de cima pra baixo dos 4 terminais no painel (ver _build_wires).
TERMINAL_ORDER = ("iluminacao", "ventilacao", "trava", "bomba")

#: Cor de desenho de cada fio elástico (ver EnergyBoxMinigame._draw_wire_band)
#: — só o preenchimento da "borracha"; o contorno preto de 1-2px por cima
#: segue a mesma convenção chapada do resto da arte do jogo.
WIRE_RGB = {
    "vermelho": (214, 68, 68),
    "azul": (76, 128, 214),
    "verde": (86, 178, 106),
    "amarelo": (224, 196, 64),
}


class EnergyBoxMinigame(_BaseMinigame):
    """Fase 2, laboratório. Dois modos na mesma sessão (ver
    PLANO_MINIGAMES.md §3.2/§3.3):

    "parafuso" — arrasta a chave de fenda (peça única, reaproveitada,
    nunca fica "presa" num encaixe — sempre volta pra casa depois de cada
    solta) até os 4 parafusos dos cantos da tampa. Sem penalidade, sem
    ordem exigida. Ao cair o 4º, troca sozinho pro modo "fios" — troca de
    `self.mode` por dentro, NÃO fecha o minigame (PLANO_MINIGAMES.md §3.2:
    "a tampa desliza e revela os fios").

    "fios" — 4 fios coloridos até 4 terminais rotulados, segundo o
    diagrama (WIRE_TERMINAL acima, desenhado como legenda de texto ao
    lado da arte da tampa). Errar solta faísca e devolve só aquele fio; ao
    3º erro fecha sozinho sem completar (`finish("closed_mistakes")` — ver
    PLANO_MINIGAMES.md §3.3, "não recomendo punir com dano"). Todos os 4
    certos = `finish("wired")`.

    `state` (`Game.energy_box_state`) e `wires_state`
    (`Game.energy_box_wires`) são dicts passados por referência — mutados
    direto, então fechar com ESC no meio do modo fios não perde progresso
    (mesmo truque do `slots_state` em MicroscopeMinigame). O modo parafuso
    de propósito NÃO persiste parafuso a parafuso: são 4 arrastes curtos
    sem penalidade, refazer do zero não pesa (ver PLANO_MINIGAMES.md §3.2,
    "tem que ser curto")."""

    key = "energy_box"

    PANEL_SIZE = (1200, 700)
    COMPLETE_HOLD_FRAMES = 120
    MISTAKE_LIMIT = 3
    SCREW_CORNERS = ("top_left", "top_right", "bottom_left", "bottom_right")

    #: Duração (em quadros) da animação de "chicote" quando um fio é solto
    #: fora do terminal certo — rápida e com 1-2 oscilações só (ver
    #: _update_wire_snaps).
    WIRE_SNAP_FRAMES = 20
    #: Duração do brilho de confirmação ao ligar um fio certo (ver
    #: _draw_connect_flash).
    WIRE_FLASH_FRAMES = 22

    #: Multiplicador de espessura do fio-sprite em cima da altura nativa
    #: do recorte de fio_corpo.png (ver _draw_wire_band_sprite). Comecei
    #: com 1.7 achando que ficaria fino demais, mas o Raul reportou que
    #: isso desproporcionava em relação à arte original — 1.0 respeita o
    #: tamanho nativo do arquivo; ajuste aqui se ainda quiser mais grosso.
    WIRE_SPRITE_THICKNESS_SCALE = 1.0

    #: Altura na tela (em pixels) da caixa no modo parafuso — bem maior
    #: que o tamanho nativo da arte, que fica pequena demais no painel de
    #: 1200x700 (ver _build_screws/_scaled_sprite).
    BOX_DISPLAY_HEIGHT = 380

    #: Quadros de cada fase da animação de desparafusar (ver
    #: _start_screw_unscrew/_update_screw_anim): a chave gira "in place"
    #: sobre o parafuso, depois ele cai com uma gravidade simples.
    SCREW_SPIN_FRAMES = 16
    SCREW_FALL_FRAMES = 22

    #: Quadros da tampa deslizando pro lado depois do 4º parafuso (ver
    #: _start_lid_slide/_update_lid_slide/_draw_abrindo).
    LID_SLIDE_FRAMES = 34

    #: Provisório do giro da chave enquanto chave_desparafusando.png não
    #: existir (ver _draw_screw_anim): correção fixa pra deixar
    #: chave_fenda_grande.png (desenhada na diagonal, pensada pra ser
    #: arrastada) "em pé", e um balanço pra lá e pra cá em vez de girar
    #: 360° feito cata-vento — mais perto de uma mão torcendo o pulso com
    #: a ponta presa no parafuso. Ajuste SCREW_TOOL_UPRIGHT_ANGLE se a
    #: ponta não ficar apontando pra baixo na sua arte.
    SCREW_TOOL_UPRIGHT_ANGLE = 40
    SCREW_TOOL_WIGGLE_DEGREES = 22
    SCREW_TOOL_WIGGLE_SPEED = 0.55

    def __init__(self, width, height, sprites, state, wires_state):
        super().__init__()
        self.width = width
        self.height = height
        self.sprites = sprites
        self.state = state
        self.wires_state = wires_state
        self.mode = "fios" if state.get("screws_removed") else "parafuso"

        panel_w, panel_h = self.PANEL_SIZE
        self.panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
        self.panel_rect.center = (width // 2, height // 2)
        self._box_center = (self.panel_rect.centerx, self.panel_rect.y + 240)

        self._spark_message = ""
        self._spark_timer = 0
        self.mistakes = 0
        self._all_wired = False
        self._complete_timer = 0
        self._screws_off = set()

        # Escala usada só no modo parafuso/abrindo pra desenhar a caixa
        # bem maior que o tamanho nativo (ver _scaled_sprite) — 1.0 até
        # _build_screws calcular de verdade a partir de BOX_DISPLAY_HEIGHT.
        self._box_scale = 1.0
        self._scaled_cache = {}

        # Animação de desparafusar em andamento (None = nenhuma) — ver
        # _start_screw_unscrew/_update_screw_anim/_draw_screw_anim.
        self._screw_anim = None
        self._screw_tool_piece = None
        # Posição final de cada parafuso já caído, pra continuar
        # desenhando ele largado no chão da caixa depois da animação.
        self._screw_landed_pos = {}

        # Quadros já passados da tampa deslizando (ver _start_lid_slide) —
        # só existe de verdade durante o modo "abrindo".
        self._lid_slide_elapsed = 0

        # Estado do efeito "fio elástico" (ver PLANO_MINIGAMES.md §3.3 e
        # _draw_wire_band/_update_wire_snaps): ponto fixo de onde cada fio
        # sai, comprimento de repouso pra medir a tensão ao esticar,
        # animação de chicote ao soltar errado, e o brilho de confirmação
        # ao acertar. Populados de verdade em _build_wires; ficam vazios
        # aqui pra existir mesmo enquanto o minigame ainda está no modo
        # "parafuso".
        self._wire_anchor = {}
        self._wire_rest = {}
        self._wire_snap = {}
        self._wire_flash = {}

        if self.mode == "parafuso":
            self._build_screws()
        else:
            self._build_wires()

    # -- modo parafuso ------------------------------------------------

    def _screw_corner_rects(self, box_rect):
        """Cantos calculados como fração do próprio tamanho da caixa (não
        pixel fixo) — funciona não importa em que resolução o Raul
        exportou caixa_energia_fechada.png."""
        inset_x = round(box_rect.width * 0.16)
        inset_y = round(box_rect.height * 0.16)
        size = max(28, round(min(box_rect.width, box_rect.height) * 0.18))
        half = size // 2
        return {
            "top_left": pygame.Rect(box_rect.x + inset_x - half, box_rect.y + inset_y - half, size, size),
            "top_right": pygame.Rect(box_rect.right - inset_x - half, box_rect.y + inset_y - half, size, size),
            "bottom_left": pygame.Rect(box_rect.x + inset_x - half, box_rect.bottom - inset_y - half, size, size),
            "bottom_right": pygame.Rect(box_rect.right - inset_x - half, box_rect.bottom - inset_y - half, size, size),
        }

    def _scaled_sprite(self, key):
        """Versão em escala (self._box_scale) de um sprite da caixa,
        cacheada — usada pro modo parafuso/abrindo desenharem a caixa bem
        maior que o tamanho nativo sem reescalar todo quadro."""
        cached = self._scaled_cache.get(key)
        if cached is not None:
            return cached
        raw = self.sprites[key]
        scaled = pygame.transform.scale(
            raw, (round(raw.get_width() * self._box_scale), round(raw.get_height() * self._box_scale))
        )
        self._scaled_cache[key] = scaled
        return scaled

    def _build_screws(self):
        self.field = DragField()
        raw = self.sprites["fechada"]
        self._box_scale = self.BOX_DISPLAY_HEIGHT / raw.get_height()
        self._scaled_cache = {}
        box_rect = self._scaled_sprite("fechada").get_rect(center=self._box_center)
        for corner, rect in self._screw_corner_rects(box_rect).items():
            self.field.add_slot(corner, rect)
        tool_rect = pygame.Rect(0, 0, 140, 140)
        tool_rect.center = (self.panel_rect.right - 170, self.panel_rect.bottom - 150)
        self.field.add_piece("chave", tool_rect, self.sprites["chave_grande"])

    def _on_release_parafuso(self):
        if self._screw_anim is not None:
            return
        piece, slot = self.field.release()
        if piece is None:
            return
        if slot is not None and slot["key"] not in self._screws_off and slot["key"] not in self._screw_landed_pos:
            self._start_screw_unscrew(piece, slot)
            return
        self.field.return_home(piece)

    def _start_screw_unscrew(self, piece, slot):
        """Em vez de trocar o parafuso na hora, prende a chave girando em
        cima dele por um instante (SCREW_SPIN_FRAMES) e só depois solta o
        parafuso pra cair (SCREW_FALL_FRAMES) — ver _update_screw_anim."""
        corner = slot["key"]
        kick = -1.3 if "left" in corner else 1.3
        self._screw_anim = {
            "corner": corner,
            "phase": "spin",
            "elapsed": 0,
            "fall_pos": [float(slot["rect"].centerx), float(slot["rect"].centery)],
            "fall_vel": [kick, -1.0],
        }
        piece["rect"].center = slot["rect"].center
        self._screw_tool_piece = piece
        self.queue_sfx("button_sound")

    def _update_screw_anim(self):
        anim = self._screw_anim
        if anim is None:
            return
        anim["elapsed"] += 1
        if anim["phase"] == "spin":
            if anim["elapsed"] >= self.SCREW_SPIN_FRAMES:
                anim["phase"] = "fall"
                anim["elapsed"] = 0
                self._screws_off.add(anim["corner"])
            return
        # Fase "fall": gravidade simples — acelera pra baixo a cada quadro.
        anim["fall_vel"][1] += 1.35
        anim["fall_pos"][0] += anim["fall_vel"][0]
        anim["fall_pos"][1] += anim["fall_vel"][1]
        if anim["elapsed"] < self.SCREW_FALL_FRAMES:
            return
        corner = anim["corner"]
        self._screw_landed_pos[corner] = (anim["fall_pos"][0], anim["fall_pos"][1])
        piece = self._screw_tool_piece
        self._screw_anim = None
        self._screw_tool_piece = None
        if piece is not None:
            self.field.return_home(piece)
        if len(self._screws_off) == len(self.SCREW_CORNERS):
            self.state["screws_removed"] = True
            self._start_lid_slide()

    def _draw_screw_anim(self, surface):
        """Se `chave_desparafusando.png`/`parafuso_caindo_anim.png` já
        existirem (ver game.py Game._load_energy_box_sprites), usa os
        quadros de verdade — melhor que rotacionar em tempo real, que
        borra a pixel art fora de múltiplos de 90°. Sem eles, cai pro
        giro/rotação por código de sempre."""
        anim = self._screw_anim
        slot_rect = self.field.slot(anim["corner"])["rect"]
        if anim["phase"] == "spin":
            frame = self.sprites["parafuso_no_lugar"]
            surface.blit(frame, frame.get_rect(center=slot_rect.center))
            spin_frames = self.sprites.get("chave_desparafusando")
            if spin_frames:
                step = max(1, self.SCREW_SPIN_FRAMES // len(spin_frames))
                index = min(len(spin_frames) - 1, anim["elapsed"] // step)
                tool_image = spin_frames[index]
            else:
                # Provisório: chave "em pé" (ver SCREW_TOOL_UPRIGHT_ANGLE)
                # balançando pra lá e pra cá — não é um giro completo, é
                # só o efeito de pulso torcendo com a ponta parada.
                wiggle = self.SCREW_TOOL_WIGGLE_DEGREES * math.sin(anim["elapsed"] * self.SCREW_TOOL_WIGGLE_SPEED)
                angle = self.SCREW_TOOL_UPRIGHT_ANGLE + wiggle
                tool_image = pygame.transform.rotate(self.sprites["chave_grande"], angle)
            surface.blit(tool_image, tool_image.get_rect(center=slot_rect.center))
        else:
            pos = (round(anim["fall_pos"][0]), round(anim["fall_pos"][1]))
            fall_frames = self.sprites.get("parafuso_caindo_anim")
            if fall_frames:
                step = max(1, self.SCREW_FALL_FRAMES // len(fall_frames))
                index = min(len(fall_frames) - 1, anim["elapsed"] // step)
                frame = fall_frames[index]
            else:
                angle = anim["elapsed"] * 24
                frame = pygame.transform.rotate(self.sprites["parafuso_caindo"], angle)
            surface.blit(frame, frame.get_rect(center=pos))

    # -- transição "abrindo" (tampa deslizando) --------------------------

    def _start_lid_slide(self):
        self.mode = "abrindo"
        self._lid_slide_elapsed = 0
        self.queue_sfx("button_sound")

    def _update_lid_slide(self):
        self._lid_slide_elapsed += 1
        if self._lid_slide_elapsed >= self.LID_SLIDE_FRAMES:
            self.mode = "fios"
            self._build_wires()

    def _draw_abrindo(self, surface, text_fn):
        """`tampa_caixa.png` é o cartão do diagrama (o verso da tampa, só
        usado como referência no modo fios) — NÃO é a arte da tampa em
        si, então quem "desliza pro lado" aqui é a própria caixa_fechada
        por cima da caixa_aberta: a versão fechada escorrega pra fora e
        revela a aberta, que já estava por baixo o tempo todo."""
        t = min(1.0, self._lid_slide_elapsed / self.LID_SLIDE_FRAMES)
        eased = t * t * (3 - 2 * t)  # smoothstep — sai rápido, assenta suave

        aberta = self._scaled_sprite("aberta")
        box_rect = aberta.get_rect(center=self._box_center)
        surface.blit(aberta, box_rect)

        fechada = self._scaled_sprite("fechada")
        fechada_rect = fechada.get_rect(center=self._box_center)
        fechada_rect.x += round(eased * (box_rect.width * 1.05))
        surface.blit(fechada, fechada_rect)

        text_fn(
            surface, "Abrindo a tampa...",
            (self.panel_rect.centerx, self.panel_rect.bottom - 56), 16, "#b9c4d4", True,
        )

    # -- modo fios ------------------------------------------------------

    def _build_wires(self):
        self.field = DragField()
        wire_w, wire_h, gap = 150, 86, 20
        wires_x = self.panel_rect.x + 480
        start_y = self.panel_rect.y + 110

        # Reinicia o estado do fio elástico (ver __init__) — se estiver
        # voltando de "parafuso" isso é a primeira vez que existe; se for
        # reconstrução (não acontece hoje, mas por segurança) fica limpo.
        self._wire_anchor = {}
        self._wire_rest = {}
        self._wire_snap = {}
        self._wire_flash = {}

        pieces_by_color = {}
        for index, color in enumerate(WIRE_COLORS):
            rect = pygame.Rect(wires_x, start_y + index * (wire_h + gap), wire_w, wire_h)
            self.field.add_piece(color, rect, self.sprites["fio_por_cor"][color], color)
            pieces_by_color[color] = self.field.pieces[-1]
            # Ponto fixo de onde o fio "sai" (o feixe dentro da caixa) —
            # um pouco à esquerda do repouso da peça, entre o diagrama e a
            # coluna de fios. A distância daqui até o repouso é o
            # "comprimento de repouso" usado pra medir tensão ao esticar
            # (ver _draw_wire_band).
            anchor = (wires_x - 26, rect.centery)
            self._wire_anchor[color] = anchor
            self._wire_rest[color] = math.hypot(rect.centerx - anchor[0], rect.centery - anchor[1]) or 1.0
            self._wire_flash[color] = 0

        term_w, term_h = 320, 86
        term_x = self.panel_rect.right - 60 - term_w
        slots_by_key = {}
        for index, terminal_key in enumerate(TERMINAL_ORDER):
            rect = pygame.Rect(term_x, start_y + index * (term_h + gap), term_w, term_h)
            self.field.add_slot(terminal_key, rect, TERMINAL_LABELS[terminal_key])
            slots_by_key[terminal_key] = self.field.slots[-1]

        # Retoma fios já ligados numa sessão anterior (ESC no meio).
        for color, connected in self.wires_state.items():
            if connected:
                target_slot = slots_by_key[WIRE_TERMINAL[color]]
                target_piece = pieces_by_color[color]
                self.field.place(target_piece, target_slot)
                target_piece["rect"].center = self._tomada_anchor(target_slot)
        if all(self.wires_state.values()):
            self._all_wired = True
            self.state["wired"] = True

    def _spark(self, color):
        self._spark_message = f"Faísca! O fio {color} não é essa ligação — confira o diagrama."
        self._spark_timer = 150
        self.queue_sfx("wrong_sequence_sound")

    def _wire_piece(self, color):
        for piece in self.field.pieces:
            if piece["key"] == color:
                return piece
        return None

    def _start_wire_snap(self, piece):
        """Solto no lugar errado (ou fora de tudo): em vez do return_home
        linear do DragField, guarda um "chicote" — a peça volta rápido
        pro repouso e passa um pouco por ele antes de assentar (ver
        _update_wire_snaps e _draw_wire_band, que usa isso pra dar um
        chacoalhão extra na borracha do fio enquanto anima)."""
        color = piece["key"]
        start = piece["rect"].center
        home = piece["home"].center
        stretch = math.hypot(start[0] - home[0], start[1] - home[1])
        self._wire_snap[color] = {"start": start, "elapsed": 0, "duration": self.WIRE_SNAP_FRAMES, "stretch": stretch}

    def _update_wire_snaps(self):
        if not self._wire_snap:
            return
        finished = []
        for color, anim in self._wire_snap.items():
            piece = self._wire_piece(color)
            anim["elapsed"] += 1
            t = anim["elapsed"] / anim["duration"]
            if piece is None or t >= 1:
                if piece is not None:
                    piece["rect"].center = piece["home"].center
                finished.append(color)
                continue
            start = anim["start"]
            home = piece["home"].center
            # Decaimento exponencial * cosseno = "boing" elástico: começa
            # no ponto onde foi solto (mult=1), passa do repouso pro outro
            # lado (mult negativo) e assenta rápido — poucas oscilações,
            # condizente com "leve oscilação elástica".
            mult = math.exp(-6.5 * t) * math.cos(3.2 * math.pi * t)
            piece["rect"].centerx = round(home[0] + (start[0] - home[0]) * mult)
            piece["rect"].centery = round(home[1] + (start[1] - home[1]) * mult)
        for color in finished:
            del self._wire_snap[color]

    def _wire_wobble(self, color):
        """Ondulação lateral extra (efeito chicote) enquanto o fio está
        voltando de um solto errado — some rápido, some de vez quando a
        animação termina (ver _draw_wire_band)."""
        anim = self._wire_snap.get(color)
        if not anim:
            return 0.0
        t = anim["elapsed"] / anim["duration"]
        return anim["stretch"] * 0.16 * math.exp(-7 * t) * math.sin(11 * t)

    def _draw_wire_band(self, surface, color, piece):
        """A "borracha" do fio: uma tira do ponto fixo (_wire_anchor) até
        a ponta que o jogador está segurando/soltando (piece["rect"].
        center — que já é atualizado em tempo real por DragField.drag_to
        e por _update_wire_snaps). Se `fio_esticado.png` já existir (ver
        game.py Game._load_energy_box_sprites), usa a sprite de verdade
        esticada/rotacionada; senão cai pro desenho por código de sempre
        (_draw_wire_band_procedural) — mesmo padrão de "arte opcional" do
        resto do jogo."""
        esticado = self.sprites.get("fio_esticado_por_cor")
        if esticado is not None and color in esticado:
            self._draw_wire_band_sprite(surface, color, piece, esticado[color])
        else:
            self._draw_wire_band_procedural(surface, color, piece)

    def _draw_wire_band_sprite(self, surface, color, piece, frame):
        """Versão com arte de verdade: estica (escala) o quadro reto de
        `frame` pro comprimento exato entre âncora e ponta, afina um
        pouco quando a tensão é alta, e rotaciona pro ângulo certo — o
        chacoalho de _wire_wobble vira um tremor no ângulo em vez de
        deslocar a curva (não há curva; o sprite é sempre um segmento
        reto, condizente com "fio esticado"). WIRE_SPRITE_THICKNESS_SCALE
        engorda o traço em cima da altura nativa do recorte — sem isso
        ficava fino demais pra enxergar de longe."""
        anchor = self._wire_anchor.get(color)
        if anchor is None:
            return
        ax, ay = anchor
        tx, ty = piece["rect"].center
        dx, dy = tx - ax, ty - ay
        length = math.hypot(dx, dy) or 1.0
        angle_deg = -math.degrees(math.atan2(dy, dx))
        base_thickness = frame.get_height() * self.WIRE_SPRITE_THICKNESS_SCALE

        if piece["placed"]:
            thickness = max(8, round(base_thickness))
            stretched = pygame.transform.scale(frame, (round(length), thickness))
            image = pygame.transform.rotate(stretched, angle_deg)
            surface.blit(image, image.get_rect(center=((ax + tx) / 2, (ay + ty) / 2)))
            return

        rest = self._wire_rest.get(color, length) or 1.0
        tension = min(1.0, max(0.0, (length - rest) / 170))
        thickness = max(6, round(base_thickness * (1 - 0.35 * tension)))
        wobble_deg = self._wire_wobble(color) * 0.9  # pixels -> graus, só um tremor leve
        stretched = pygame.transform.scale(frame, (round(length), thickness))
        image = pygame.transform.rotate(stretched, angle_deg + wobble_deg)
        surface.blit(image, image.get_rect(center=((ax + tx) / 2, (ay + ty) / 2)))

    def _draw_wire_band_procedural(self, surface, color, piece):
        """Fallback desenhado por código (círculos ao longo de uma curva
        de Bézier) enquanto `fio_esticado.png` não existir — ver
        _draw_wire_band."""
        anchor = self._wire_anchor.get(color)
        if anchor is None:
            return
        base_color = WIRE_RGB.get(color, (200, 200, 200))
        outline = (18, 18, 24)
        ax, ay = anchor
        tx, ty = piece["rect"].center

        if piece["placed"]:
            pygame.draw.line(surface, outline, (ax, ay), (tx, ty), 21)
            pygame.draw.line(surface, base_color, (ax, ay), (tx, ty), 16)
            pygame.draw.circle(surface, outline, (round(ax), round(ay)), 10)
            pygame.draw.circle(surface, base_color, (round(ax), round(ay)), 8)
            return

        dx, dy = tx - ax, ty - ay
        length = math.hypot(dx, dy) or 1.0
        rest = self._wire_rest.get(color, length) or 1.0
        tension = min(1.0, max(0.0, (length - rest) / 170))
        nx, ny = -dy / length, dx / length
        sag = 16 * (1 - tension)
        offset = sag + self._wire_wobble(color)
        mid_x = (ax + tx) / 2 + nx * offset
        mid_y = (ay + ty) / 2 + ny * offset

        segments = 14
        base_width = 17
        min_width = 7
        for i in range(segments + 1):
            t = i / segments
            x = (1 - t) ** 2 * ax + 2 * (1 - t) * t * mid_x + t ** 2 * tx
            y = (1 - t) ** 2 * ay + 2 * (1 - t) * t * mid_y + t ** 2 * ty
            taper = math.sin(math.pi * t)  # 0 nas pontas, 1 no meio
            width = base_width - (base_width - min_width) * tension * taper
            radius = max(2, round(width / 2))
            pygame.draw.circle(surface, outline, (round(x), round(y)), radius + 2)
            pygame.draw.circle(surface, base_color, (round(x), round(y)), radius)
        pygame.draw.circle(surface, outline, (round(ax), round(ay)), 8)
        pygame.draw.circle(surface, base_color, (round(ax), round(ay)), 6)

    def _draw_connect_flash(self, surface, center, frames_left):
        """Brilho rápido (aditivo) no ponto de conexão ao acertar o
        terminal certo — "se fixar firmemente com um pequeno brilho de
        confirmação"."""
        progress = 1 - frames_left / self.WIRE_FLASH_FRAMES
        radius = round(10 + progress * 26)
        alpha = round(255 * (1 - progress))
        if radius <= 0 or alpha <= 0:
            return
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 255, 210, alpha), (radius, radius), radius)
        surface.blit(glow, (center[0] - radius, center[1] - radius), special_flags=pygame.BLEND_RGBA_ADD)

    def _terminal_frame(self, filled):
        """Sprite da tomada de cada terminal — usa `tomada.png` de
        verdade se já existir (ver game.py Game._load_energy_box_sprites),
        senão cai pros quadros de terminal.png que já sempre carregam."""
        if filled:
            return self.sprites.get("tomada_conectada", self.sprites["terminal_conectado"])
        return self.sprites.get("tomada_vazia", self.sprites["terminal_vazio"])

    def _tomada_anchor(self, slot):
        """Ponto onde o fio deve terminar visualmente ao conectar — o
        centro do ÍCONE da tomada (desenhado em
        midright=(slot.x-10, slot.centery), ver _draw_fios), não o centro
        do retângulo largo do terminal. Sem isso o fio "parava no ar"
        antes de chegar na tomada de verdade."""
        frame = self._terminal_frame(True)
        return (slot["rect"].x - 10 - frame.get_width() / 2, slot["rect"].centery)

    def _connected_wire_color(self, terminal_key):
        for color, terminal in WIRE_TERMINAL.items():
            if terminal == terminal_key and self.wires_state.get(color):
                return color
        return None

    def _draw_indicator_light(self, surface, slot):
        """Luzinha redonda embaixo de cada terminal — apagada/cinza
        enquanto vazio, acesa (na cor do fio ligado, com um leve brilho)
        assim que o terminal certo é conectado."""
        center = (slot["rect"].centerx, slot["rect"].bottom + 16)
        if not slot["filled"]:
            pygame.draw.circle(surface, (18, 18, 24), center, 8)
            pygame.draw.circle(surface, (60, 64, 78), center, 6)
            return
        color = self._connected_wire_color(slot["key"])
        rgb = WIRE_RGB.get(color, (140, 230, 170))
        glow = pygame.Surface((28, 28), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*rgb, 90), (14, 14), 14)
        surface.blit(glow, (center[0] - 14, center[1] - 14), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, (18, 18, 24), center, 8)
        pygame.draw.circle(surface, rgb, center, 6)

    def _on_release_fios(self):
        piece, slot = self.field.release()
        if piece is None:
            return
        color = piece["key"]
        if slot is None or slot["filled"]:
            self._start_wire_snap(piece)
            return
        if slot["key"] != WIRE_TERMINAL[color]:
            self._spark(color)
            self._start_wire_snap(piece)
            self.mistakes += 1
            if self.mistakes >= self.MISTAKE_LIMIT:
                self.finish("closed_mistakes")
            return
        self.field.place(piece, slot)
        piece["rect"].center = self._tomada_anchor(slot)
        self.wires_state[color] = True
        self._wire_flash[color] = self.WIRE_FLASH_FRAMES
        self.queue_sfx("item_sound")
        if all(self.wires_state.values()):
            self._all_wired = True
            self.state["wired"] = True

    # -- interface comum --------------------------------------------------

    def update(self, dt):
        self.field.update()
        if self.mode == "parafuso":
            self._update_screw_anim()
        elif self.mode == "abrindo":
            self._update_lid_slide()
        elif self.mode == "fios":
            self._update_wire_snaps()
            for color in self._wire_flash:
                if self._wire_flash[color] > 0:
                    self._wire_flash[color] -= 1
        if self._spark_timer > 0:
            self._spark_timer -= 1
        if self._all_wired:
            self._complete_timer += 1
            if self._complete_timer >= self.COMPLETE_HOLD_FRAMES:
                self.finish("wired")

    def on_click(self, pos):
        if self._all_wired or self.mode == "abrindo":
            return
        if self.mode == "parafuso" and self._screw_anim is not None:
            return
        piece = self.field.grab(pos)
        # Pegar o fio de novo cancela qualquer chicote em andamento pra
        # ele não brigar com o arraste manual (ver _start_wire_snap).
        if piece is not None and self.mode == "fios":
            self._wire_snap.pop(piece["key"], None)

    def on_drag(self, pos):
        if self._all_wired or self.mode == "abrindo":
            return
        self.field.drag_to(pos)

    def on_release(self, pos):
        if self._all_wired or self.mode == "abrindo":
            return
        if self.mode == "parafuso":
            self._on_release_parafuso()
        else:
            self._on_release_fios()

    def draw(self, surface, text_fn):
        draw_modal_backdrop(surface, self.panel_rect, self.width, self.height)
        titles = {"parafuso": "Caixa de energia", "abrindo": "Abrindo a caixa", "fios": "Ligar os fios"}
        text_fn(surface, titles[self.mode], (self.panel_rect.centerx, self.panel_rect.y + 26), 26, "#f4e4a5", True)
        if self.mode == "parafuso":
            self._draw_parafuso(surface, text_fn)
        elif self.mode == "abrindo":
            self._draw_abrindo(surface, text_fn)
        else:
            self._draw_fios(surface, text_fn)

    def _draw_parafuso(self, surface, text_fn):
        box_image = self._scaled_sprite("fechada")
        box_rect = box_image.get_rect(center=self._box_center)
        surface.blit(box_image, box_rect)

        anim = self._screw_anim
        for corner in self.SCREW_CORNERS:
            if anim is not None and anim["corner"] == corner:
                continue  # desenhada à parte em _draw_screw_anim
            slot_rect = self.field.slot(corner)["rect"]
            if corner in self._screws_off:
                pos = self._screw_landed_pos.get(corner, slot_rect.center)
                frame = self.sprites["parafuso_caindo"]
                surface.blit(frame, frame.get_rect(center=pos))
            else:
                frame = self.sprites["parafuso_no_lugar"]
                surface.blit(frame, frame.get_rect(center=slot_rect.center))

        if anim is not None:
            self._draw_screw_anim(surface)
        else:
            tool_piece = self.field.pieces[0]
            surface.blit(tool_piece["image"], tool_piece["image"].get_rect(center=tool_piece["rect"].center))

        text_fn(
            surface, "Arraste a chave de fenda até cada parafuso.",
            (self.panel_rect.centerx, self.panel_rect.bottom - 56), 16, "#b9c4d4", True,
        )
        text_fn(
            surface, "[ESC] fechar",
            (self.panel_rect.centerx, self.panel_rect.bottom - 28), 13, "#8b96a8", True,
        )

    def _draw_fios(self, surface, text_fn):
        diagram_rect = pygame.Rect(
            self.panel_rect.x + 40, self.panel_rect.y + 80, 400, self.panel_rect.height - 150
        )
        pygame.draw.rect(surface, (18, 20, 32), diagram_rect, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, diagram_rect, 2, border_radius=10)
        text_fn(
            surface, "Diagrama (verso da tampa)",
            (diagram_rect.centerx, diagram_rect.y + 18), 13, "#9de3bb", True,
        )
        # Sem legenda em texto de propósito — o esquema de cores já está
        # pintado dentro da própria arte da tampa (ver WIRE_TERMINAL); o
        # jogador tem que ler a sprite, não uma cópia em texto dela. Por
        # isso ela é ampliada pra caber quase todo o painel do diagrama.
        tampa_raw = self.sprites["tampa"]
        tampa_scale = min(
            (diagram_rect.width - 40) / tampa_raw.get_width(),
            (diagram_rect.height - 70) / tampa_raw.get_height(),
        )
        tampa = pygame.transform.scale(
            tampa_raw, (round(tampa_raw.get_width() * tampa_scale), round(tampa_raw.get_height() * tampa_scale))
        )
        tampa_rect = tampa.get_rect(midtop=(diagram_rect.centerx, diagram_rect.y + 40))
        surface.blit(tampa, tampa_rect)

        for slot in self.field.slots:
            frame = self._terminal_frame(slot["filled"])
            surface.blit(frame, frame.get_rect(midright=(slot["rect"].x - 10, slot["rect"].centery)))
            border = (150, 214, 178) if slot["filled"] else (80, 84, 100)
            pygame.draw.rect(surface, border, slot["rect"], 2, border_radius=8)
            text_fn(surface, slot["label"], slot["rect"].center, 15, "#e7edf5", True)
            self._draw_indicator_light(surface, slot)

        # A "borracha" de cada fio, do ponto fixo até a peça — desenhada
        # ANTES do conector, pra ele ficar visualmente preso na ponta dela
        # (ver _draw_wire_band: segue o mouse em tempo real, afina no meio
        # quando esticado, e chacoalha ao voltar de um erro).
        for piece in self.field.pieces:
            self._draw_wire_band(surface, piece["key"], piece)

        # A pontinha (fio_por_cor) só aparece enquanto o fio ainda não
        # está ligado — uma vez conectado, a "borracha" grossa terminando
        # em cima da tomada já conta a história sozinha; manter o ícone
        # ali só duplicava em cima do texto do terminal (ver _tomada_anchor).
        pieces_in_order = [p for p in self.field.pieces if p is not self.field.holding and not p["placed"]]
        if self.field.holding is not None:
            pieces_in_order.append(self.field.holding)
        for piece in pieces_in_order:
            image = piece["image"]
            surface.blit(image, image.get_rect(center=piece["rect"].center))
            if not piece["placed"]:
                text_fn(
                    surface, piece["label"].upper(),
                    (piece["rect"].centerx, piece["rect"].bottom + 16), 12, "#b9c4d4", True,
                )

        # Brilho de confirmação ao acertar (ver _on_release_fios/_draw_connect_flash).
        for color, frames_left in self._wire_flash.items():
            if frames_left <= 0:
                continue
            piece = self._wire_piece(color)
            if piece is not None:
                self._draw_connect_flash(surface, piece["rect"].center, frames_left)

        text_fn(
            surface, "Arraste cada fio até o terminal certo — confira o diagrama à esquerda.",
            (self.panel_rect.centerx, self.panel_rect.bottom - 56), 15, "#b9c4d4", True,
        )
        text_fn(
            surface, f"[ESC] fechar     erros: {self.mistakes}/{self.MISTAKE_LIMIT}",
            (self.panel_rect.centerx, self.panel_rect.bottom - 28), 13, "#8b96a8", True,
        )
        if self._spark_timer > 0:
            text_fn(
                surface, self._spark_message,
                (self.panel_rect.centerx, self.panel_rect.bottom - 90), 16, "#ff9d9d", True,
            )
        if self._all_wired:
            text_fn(
                surface, "Caixa ligada!",
                (self.panel_rect.centerx, self.panel_rect.y + 60), 18, "#c8f5d6", True,
            )
