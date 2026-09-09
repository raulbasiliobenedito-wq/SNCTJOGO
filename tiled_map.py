"""Leitor de mapas TMX ortogonais criados no Tiled.

O projeto usa o formato XML/TMX nativo do Tiled, sem depender de bibliotecas
extras. Camadas de tiles podem ser visuais ou gerar colisões; grupos de
objetos continuam descrevendo entidades interativas.
"""

from __future__ import annotations

import base64
import gzip
from pathlib import Path
import struct
import unicodedata
import xml.etree.ElementTree as ET
import zlib

import pygame


FLIPPED_GID_MASK = 0x1FFFFFFF
# Bits que o Tiled liga no gid quando o tile é espelhado/girado no editor.
# Eram MASCARADOS e jogados fora: um tile espelhado no Tiled aparecia sem
# espelho no jogo, em silêncio. Agora são lidos e aplicados em
# _oriented_image.
FLIPPED_HORIZONTALLY = 0x80000000
FLIPPED_VERTICALLY = 0x40000000
FLIPPED_DIAGONALLY = 0x20000000
ORTHOGONAL = "orthogonal"


def _normalise(value):
    """Normaliza nomes de camadas, ignorando acentos e maiúsculas."""
    text = unicodedata.normalize("NFD", str(value).casefold())
    return "".join(character for character in text if character.isalnum())


class TiledMap:
    """Mapa TMX com tilesets externos TSX e objetos retangulares."""

    def __init__(self, path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Mapa do Tiled não encontrado: {self.path}")

        root = ET.parse(self.path).getroot()
        if root.get("orientation", ORTHOGONAL) != ORTHOGONAL:
            raise ValueError("Este jogo aceita apenas mapas ortogonais do Tiled.")

        self.width = int(root.get("width", 0))
        self.height = int(root.get("height", 0))
        self.tile_width = int(root.get("tilewidth", 64))
        self.tile_height = int(root.get("tileheight", 64))
        self.pixel_width = self.width * self.tile_width
        self.pixel_height = self.height * self.tile_height
        self.properties = self._properties(root)
        self.tilesets = self._load_tilesets(root)
        self.tiles = []
        self.animated_tiles = []
        # Camada "Frente" (pedido do Raul, Fase 1): fica separada de
        # self.tiles/animated_tiles de propósito — draw() normal nunca
        # encosta nela; só draw_foreground() (chamado por Game.draw DEPOIS
        # de desenhar a Lia) percorre essas duas listas. É assim que dá pra
        # ter cenário passando na FRENTE dela sem duplicar nenhuma lógica
        # de tile/animação — mesmo _read_tile_layer, só escolhendo a lista
        # certa (ver _is_foreground_layer).
        self.foreground_tiles = []
        self.foreground_animated_tiles = []
        self.tile_collisions = []
        self.object_groups = {}
        self.elapsed_ms = 0.0
        # Cache de tiles espelhados/girados (ver _oriented_image).
        self._oriented_cache = {}
        self._read_layers(root)
        # Chunks de CHUNK_TILES x CHUNK_TILES tiles: o draw() só percorre os
        # tiles dos chunks que cruzam a câmera, em vez de checar a
        # visibilidade de TODO tile do mapa a cada quadro. Numa fase grande
        # (300x100 tiles, várias camadas), isso corta a lista percorrida por
        # quadro de milhares de tiles pra só uma centena.
        self._tile_chunks = self._build_chunks(self.tiles)
        self._animated_chunks = self._build_chunks(self.animated_tiles)
        self._foreground_tile_chunks = self._build_chunks(self.foreground_tiles)
        self._foreground_animated_chunks = self._build_chunks(self.foreground_animated_tiles)
        # Imagem atual de cada animação (uma por par tileset+local_id, não
        # uma por instância de tile) — recalculada uma vez em update(), não a
        # cada tile animado desenhado. Populada já aqui pra existir mesmo se
        # draw() rodar antes do primeiro update().
        self._current_frames = {}
        self._recompute_animation_frames()

    CHUNK_TILES = 8

    def _build_chunks(self, entries):
        """Indexa cada tile nos chunks que ele REALMENTE cruza.

        Antes só o chunk do canto superior esquerdo era usado; um tile maior
        que o grid (casa de 128px numa grade de 32px) ficava registrado num
        chunk só e dependia da margem de +-1 chunk de _draw_chunks pra
        aparecer — funcionava por acidente, e deixaria de funcionar com
        qualquer arte maior que CHUNK_TILES * tile_size."""
        chunk_w = self.CHUNK_TILES * self.tile_width
        chunk_h = self.CHUNK_TILES * self.tile_height
        chunks = {}
        for entry in entries:
            x, y = entry[0], entry[1]
            # Largura/altura são sempre os DOIS ÚLTIMOS campos: as tuplas de
            # tile normal são (x, y, imagem, w, h) e as de tile animado são
            # (x, y, tileset, local_id, w, h) — indexar por posição fixa
            # pegaria o local_id no lugar da largura.
            width, height = entry[-2], entry[-1]
            first_col = int(x // chunk_w)
            last_col = int((x + width - 1) // chunk_w)
            first_row = int(y // chunk_h)
            last_row = int((y + height - 1) // chunk_h)
            for row in range(first_row, last_row + 1):
                for col in range(first_col, last_col + 1):
                    chunks.setdefault((col, row), []).append(entry)
        return chunks

    def update(self, dt_ms):
        """Avança o relógio das animações de tile (ex.: água) em milissegundos."""
        self.elapsed_ms += dt_ms
        self._recompute_animation_frames()

    def _recompute_animation_frames(self):
        """Resolve o quadro atual de CADA animação (poucas dezenas no máximo)
        uma única vez por quadro de jogo. draw() só faz uma busca O(1) nesse
        cache pra cada instância de tile animado, em vez de recalcular o
        quadro (e refatiar a imagem) tile por tile."""
        for tileset in self.tilesets:
            frames_by_id = tileset["animation_frames"]
            for local_id, frames in frames_by_id.items():
                self._current_frames[(id(tileset), local_id)] = self._resolve_frame(frames)

    def _resolve_frame(self, frames):
        total_duration = sum(duration for _, duration in frames)
        if total_duration <= 0:
            return frames[0][0]
        elapsed = self.elapsed_ms % total_duration
        for image, duration in frames:
            if elapsed < duration:
                return image
            elapsed -= duration
        return frames[-1][0]

    @staticmethod
    def _properties(element):
        """Retorna as propriedades do Tiled usando seus nomes originais."""
        return {
            node.get("name", ""): node.get("value", node.text or "")
            for node in element.findall("./properties/property")
        }

    def _load_tilesets(self, root):
        tilesets = []
        for entry in root.findall("tileset"):
            tileset = self._load_tileset(entry)
            if tileset:
                tilesets.append(tileset)
        return tilesets

    def _load_tileset(self, entry):
        first_gid = int(entry.get("firstgid", 1))
        source = entry.get("source")
        tileset_path = self.path.parent / source if source else None
        tileset_root = ET.parse(tileset_path).getroot() if tileset_path else entry
        base_dir = tileset_path.parent if tileset_path else self.path.parent
        image = tileset_root.find("image")
        if image is None:
            return None

        image_path = base_dir / image.get("source", "")
        surface = pygame.image.load(image_path).convert_alpha()
        columns = int(tileset_root.get("columns", 1))
        tile_w = int(tileset_root.get("tilewidth", self.tile_width))
        tile_h = int(tileset_root.get("tileheight", self.tile_height))
        # O Tiled às vezes deixa um tilecount desatualizado depois de trocar o
        # tamanho do tile — aconteceu com escola_tileset_64x64.tsx, que
        # declarava 480 numa imagem que só comporta 120. Confiar no declarado
        # faz o tileset "reivindicar" GIDs que pertencem a outros e leva a
        # subsurface() fora dos limites do atlas (crash no carregamento do
        # mapa). Usar o menor entre o declarado e o que a imagem realmente
        # comporta protege qualquer tileset futuro contra o mesmo erro.
        declared = int(tileset_root.get("tilecount", 0))
        real = max(0, (surface.get_width() // tile_w) * (surface.get_height() // tile_h))
        if declared and declared != real:
            print(
                f"[TiledMap] aviso: {source or image_path.name} declara "
                f"tilecount={declared} mas a imagem {surface.get_size()} com tiles "
                f"de {tile_w}x{tile_h} comporta {real} — usando {min(declared, real)}."
            )
        tile_count = min(declared, real) if declared else real
        tileset = {
            "first_gid": first_gid,
            "last_gid": first_gid + tile_count - 1,
            "image": surface,
            "columns": columns,
            "tile_width": tile_w,
            "tile_height": tile_h,
            "animations": self._load_animations(tileset_root),
            # "escala" (propriedade opcional do tileset no Tiled): amplia o
            # recorte de cada tile desse tileset na hora de desenhar, sem
            # mexer no tamanho real da arte nem no grid do mapa — usado pra
            # deixar as casas da vila maiores (ver casas_vila.tsx). Ancorado
            # embaixo/centralizado em _read_tile_layer, então a casa cresce
            # "pra cima" mantendo a base encostada no chão.
            "scale": float(self._properties(tileset_root).get("escala", 1)),
        }
        # Pré-recorta o quadro de cada passo de animação uma única vez aqui
        # (em vez de fatiar a mesma imagem de novo a cada instância de tile
        # animado, todo quadro — ver _current_frame_image). Numa fase com
        # centenas de tiles de água/lava, isso evita centenas de subsurface()
        # redundantes por quadro, já que todas as instâncias do mesmo tile
        # (ex.: "água - corpo") compartilham a mesma imagem em cada instante.
        tileset["animation_frames"] = {
            local_id: [
                (self._tile_image(tileset, frame_id), duration)
                for frame_id, duration in frames
            ]
            for local_id, frames in tileset["animations"].items()
        }
        return tileset

    @staticmethod
    def _load_animations(tileset_root):
        """Lê as animações de tile do Tiled (ex.: água), quadro a quadro.

        No editor: selecione o tile no tileset, aba "Tile Animation Editor",
        monte a sequência de quadros e salve o .tsx. Cada quadro guarda o id
        local do tile e sua duração em milissegundos.
        """
        animations = {}
        for tile in tileset_root.findall("tile"):
            animation = tile.find("animation")
            if animation is None:
                continue
            local_id = int(tile.get("id", 0))
            frames = [
                (int(frame.get("tileid", 0)), int(frame.get("duration", 100)))
                for frame in animation.findall("frame")
            ]
            if frames:
                animations[local_id] = frames
        return animations

    def _read_layers(self, root):
        """Percorre camadas e grupos de objetos RECURSIVAMENTE.

        Antes só olhava os filhos diretos do <map>: agrupar camadas no
        Tiled (um <group>, que é o jeito natural de organizar um mapa
        grande) fazia tudo dentro do grupo sumir do jogo sem erro nenhum.
        A ordem de leitura continua sendo a ordem do arquivo, então a
        pilha de desenho não muda pros mapas que já existem."""
        for node in root:
            if node.tag == "layer":
                self._read_tile_layer(node)
            elif node.tag == "objectgroup":
                self._read_object_group(node)
            elif node.tag == "group":
                self._read_layers(node)

    def _read_tile_layer(self, layer):
        values = self._tile_values(layer)
        layer_width = int(layer.get("width", self.width))
        layer_x = int(layer.get("x", 0))
        layer_y = int(layer.get("y", 0))
        creates_collision = self._is_collision_layer(layer)
        # Camada "Frente" (ver comentário em __init__): tiles dela vão pras
        # listas foreground_*, desenhadas à parte por draw_foreground().
        is_foreground = self._is_foreground_layer(layer)
        tiles = self.foreground_tiles if is_foreground else self.tiles
        animated_tiles = self.foreground_animated_tiles if is_foreground else self.animated_tiles
        for index, raw_gid in enumerate(values):
            gid = raw_gid & FLIPPED_GID_MASK
            if not gid:
                continue
            flags = raw_gid & ~FLIPPED_GID_MASK
            column = index % layer_width + layer_x
            row = index // layer_width + layer_y
            x = column * self.tile_width
            y = row * self.tile_height
            if creates_collision:
                self.tile_collisions.append(
                    pygame.Rect(x, y, self.tile_width, self.tile_height)
                )
            tileset, local_id = self._tileset_for_gid(gid)
            if tileset is None:
                continue
            # Alinhamento igual ao do próprio Tiled: quando a arte do tile é
            # maior que o grid do mapa (ex.: casas_vila, 128x128 num grid de
            # 32x32), o Tiled ancora a imagem embaixo-à-esquerda da célula
            # onde ela foi colocada — a imagem "cresce" pra cima a partir da
            # base, nunca pra baixo. Nosso render tinha ancorado no canto
            # superior esquerdo (crescendo pra baixo), por isso uma casa
            # colocada rente ao chão no editor aparecia afundada no jogo: a
            # diferença de altura (tile_height*scale - tile_height do mapa)
            # inteira ficava abaixo da célula clicada. x fica igual ao do
            # Tiled também (alinhado à esquerda, sem centralizar).
            scale = tileset.get("scale", 1)
            rendered_height = tileset["tile_height"] * scale
            draw_x = x
            draw_y = y + self.tile_height - rendered_height
            if flags and local_id not in tileset["animations"]:
                # Tile espelhado/girado no editor: gera a variante uma vez
                # aqui (cacheada por tileset+id+flags), em vez de nunca.
                # Tiles ANIMADOS ficam de fora de propósito — a variante
                # teria de ser gerada por quadro de animação, e nenhum mapa
                # do projeto usa as duas coisas juntas hoje.
                image = self._oriented_image(tileset, local_id, flags)
                tiles.append((draw_x, draw_y, image, image.get_width(), image.get_height()))
                continue
            if local_id in tileset["animations"]:
                # (x, y, tileset, local_id, largura, altura) — o tamanho vem
                # do primeiro quadro da animação, que é sempre igual aos
                # outros dentro do mesmo tileset.
                first_frame = tileset["animation_frames"][local_id][0][0]
                animated_tiles.append(
                    (draw_x, draw_y, tileset, local_id,
                     first_frame.get_width(), first_frame.get_height())
                )
            else:
                image = self._tile_image(tileset, local_id)
                # Guarda o tamanho REAL da imagem junto com a posição: as
                # casas da vila são 128x128 num grid de 32x32 (35 tiles
                # assim na vila, 15 na Fase 1) e o culling comparava contra
                # self.tile_height (32). Um tile de 128px cujo topo saísse
                # pela borda de cima da câmera era descartado enquanto ainda
                # cobria ~100px dentro da tela — casas e árvores piscando na
                # borda superior.
                tiles.append(
                    (draw_x, draw_y, image, image.get_width(), image.get_height())
                )

    def _oriented_image(self, tileset, local_id, flags):
        """Aplica os bits de espelhamento/rotação do Tiled a um tile.

        O bit "diagonal" do Tiled é uma reflexão na diagonal principal
        (transposição), não uma rotação — a combinação dele com os bits
        horizontal/vertical é que produz as rotações de 90/270 graus. A
        ordem aqui (transpõe primeiro, espelha depois) é a mesma que o
        próprio Tiled documenta."""
        cache = self._oriented_cache
        key = (id(tileset), local_id, flags)
        image = cache.get(key)
        if image is not None:
            return image
        image = self._tile_image(tileset, local_id)
        if flags & FLIPPED_DIAGONALLY:
            image = pygame.transform.rotate(pygame.transform.flip(image, True, False), 90)
        if flags & FLIPPED_HORIZONTALLY:
            image = pygame.transform.flip(image, True, False)
        if flags & FLIPPED_VERTICALLY:
            image = pygame.transform.flip(image, False, True)
        cache[key] = image
        return image

    def _is_collision_layer(self, layer):
        """Reconhece a propriedade colisao=true ou nomes convencionais."""
        properties = self._properties(layer)
        value = properties.get("colisao", properties.get("collision", "false"))
        if str(value).casefold() in ("1", "true", "sim", "yes"):
            return True
        return _normalise(layer.get("name", "")) in ("colisao", "collision")

    def _is_foreground_layer(self, layer):
        """Reconhece a propriedade frente=true ou o nome "Frente" (pedido
        do Raul: uma camada que desenha por cima da Lia, ver
        Game._draw_world_foreground em game.py — chamado depois de
        player.draw())."""
        properties = self._properties(layer)
        value = properties.get("frente", properties.get("foreground", "false"))
        if str(value).casefold() in ("1", "true", "sim", "yes"):
            return True
        return _normalise(layer.get("name", "")) in ("frente", "foreground")

    @classmethod
    def _tile_values(cls, layer):
        data = layer.find("data")
        if data is None:
            return []

        encoding = data.get("encoding", "")
        if encoding == "csv":
            return [
                int(value.strip())
                for value in (data.text or "").split(",")
                if value.strip()
            ]
        if encoding == "base64":
            return cls._decode_base64_tiles(
                data.text or "",
                data.get("compression", ""),
            )
        if not encoding:
            return [int(tile.get("gid", 0)) for tile in data.findall("tile")]
        raise ValueError(f"Codificação de camada não suportada: {encoding}.")

    @staticmethod
    def _decode_base64_tiles(encoded_data, compression):
        """Lê o formato Base64 usado pelo Tiled, com ou sem compressão."""
        raw_data = base64.b64decode(encoded_data)
        decompressors = {
            "": lambda data: data,
            "zlib": zlib.decompress,
            "gzip": gzip.decompress,
        }
        try:
            raw_data = decompressors[compression](raw_data)
        except KeyError as error:
            raise ValueError(
                f"Compressão de camada não suportada: {compression}."
            ) from error
        except (gzip.BadGzipFile, zlib.error) as error:
            raise ValueError("Não foi possível descompactar a camada do Tiled.") from error

        if len(raw_data) % 4:
            raise ValueError("Dados de camada inválidos: tamanho não múltiplo de 4.")
        return list(struct.unpack(f"<{len(raw_data) // 4}I", raw_data))

    def _read_object_group(self, group):
        group_name = _normalise(group.get("name", "objetos"))
        self.object_groups[group_name] = [
            self._object_from_node(node)
            for node in group.findall("object")
        ]

    def _object_from_node(self, node):
        return {
            "name": node.get("name", ""),
            "type": node.get("type") or node.get("class", ""),
            "x": round(float(node.get("x", 0))),
            "y": round(float(node.get("y", 0))),
            "width": round(float(node.get("width", self.tile_width))),
            "height": round(float(node.get("height", self.tile_height))),
            "properties": self._properties(node),
        }

    def _tileset_for_gid(self, gid):
        """Localiza o tileset e o id local (dentro do tileset) de um gid."""
        for tileset in reversed(self.tilesets):
            if tileset["first_gid"] <= gid <= tileset["last_gid"]:
                return tileset, gid - tileset["first_gid"]
        return None, None

    @staticmethod
    def _tile_image(tileset, local_id):
        source = pygame.Rect(
            (local_id % tileset["columns"]) * tileset["tile_width"],
            (local_id // tileset["columns"]) * tileset["tile_height"],
            tileset["tile_width"],
            tileset["tile_height"],
        )
        image = tileset["image"].subsurface(source)
        scale = tileset.get("scale", 1)
        if scale != 1:
            # subsurface() não pode ser redimensionada in-place (ela
            # compartilha pixels com o atlas todo) — transform.scale() cria
            # uma cópia nova já do tamanho ampliado.
            image = pygame.transform.scale(
                image,
                (round(tileset["tile_width"] * scale), round(tileset["tile_height"] * scale)),
            )
        return image


    def objects(self, *group_names):
        result = []
        for name in group_names:
            result.extend(self.object_groups.get(_normalise(name), ()))
        return result

    def entities(self, entity_type):
        wanted = _normalise(entity_type)
        return [
            item
            for item in self.objects("Entidades")
            if _normalise(item["type"]) == wanted
        ]

    def entity(self, entity_type):
        entities = self.entities(entity_type)
        return entities[0] if entities else None

    def draw(self, surface, camera_x, camera_y):
        """Desenha os tiles normais (tudo que NÃO é a camada "Frente" — ver
        draw_foreground) só dos chunks que cruzam a área visível, em vez de
        checar tile por tile do mapa inteiro a cada quadro (ver
        _build_chunks)."""
        self._draw_chunks(surface, camera_x, camera_y, self._tile_chunks, self._animated_chunks)

    def draw_foreground(self, surface, camera_x, camera_y):
        """Só a camada "Frente" (pedido do Raul, Fase 1) — Game.draw chama
        isso DEPOIS de desenhar a Lia, pra ela ficar atrás desse cenário
        (ex.: uma bancada/moldura de porta em primeiro plano). Mesmo
        recorte por chunks do draw() normal, só que na lista separada
        (ver __init__/_read_tile_layer)."""
        self._draw_chunks(
            surface, camera_x, camera_y, self._foreground_tile_chunks, self._foreground_animated_chunks
        )

    def _draw_chunks(self, surface, camera_x, camera_y, tile_chunks, animated_chunks):
        right = camera_x + surface.get_width()
        bottom = camera_y + surface.get_height()
        chunk_w = self.CHUNK_TILES * self.tile_width
        chunk_h = self.CHUNK_TILES * self.tile_height
        # camera_x/camera_y chegam como float (suavização da câmera em
        # game.py) — int() antes do range(), que só aceita inteiros.
        first_col = int(camera_x // chunk_w) - 1
        last_col = int(right // chunk_w) + 1
        first_row = int(camera_y // chunk_h) - 1
        last_row = int(bottom // chunk_h) + 1
        # O laço interno roda ~1400 vezes por quadro numa fase grande: a
        # closure `visible()` que existia aqui aparecia como a 4ª linha mais
        # cara do jogo no cProfile (412.770 chamadas em 300 quadros). O teste
        # agora é inline e usa a LARGURA/ALTURA REAL do tile (ver
        # _read_tile_layer), não o tamanho do grid do mapa.
        blit = surface.blit
        current = self._current_frames
        for chunk_row in range(first_row, last_row + 1):
            for chunk_col in range(first_col, last_col + 1):
                key = (chunk_col, chunk_row)
                for x, y, image, width, height in tile_chunks.get(key, ()):
                    if x + width < camera_x or x > right:
                        continue
                    if y + height < camera_y or y > bottom:
                        continue
                    blit(image, (x - camera_x, y - camera_y))
                for x, y, tileset, local_id, width, height in animated_chunks.get(key, ()):
                    if x + width < camera_x or x > right:
                        continue
                    if y + height < camera_y or y > bottom:
                        continue
                    blit(current[(id(tileset), local_id)], (x - camera_x, y - camera_y))
