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
        self.tile_collisions = []
        self.object_groups = {}
        self.elapsed_ms = 0.0
        self._read_layers(root)

    def update(self, dt_ms):
        """Avança o relógio das animações de tile (ex.: água) em milissegundos."""
        self.elapsed_ms += dt_ms

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
        return {
            "first_gid": first_gid,
            "last_gid": first_gid + int(tileset_root.get("tilecount", 0)) - 1,
            "image": pygame.image.load(image_path).convert_alpha(),
            "columns": int(tileset_root.get("columns", 1)),
            "tile_width": int(tileset_root.get("tilewidth", self.tile_width)),
            "tile_height": int(tileset_root.get("tileheight", self.tile_height)),
            "animations": self._load_animations(tileset_root),
        }

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
        for layer in root.findall("layer"):
            self._read_tile_layer(layer)
        for group in root.findall("objectgroup"):
            self._read_object_group(group)

    def _read_tile_layer(self, layer):
        values = self._tile_values(layer)
        layer_width = int(layer.get("width", self.width))
        layer_x = int(layer.get("x", 0))
        layer_y = int(layer.get("y", 0))
        creates_collision = self._is_collision_layer(layer)
        for index, raw_gid in enumerate(values):
            gid = raw_gid & FLIPPED_GID_MASK
            if not gid:
                continue
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
            if local_id in tileset["animations"]:
                self.animated_tiles.append((x, y, tileset, local_id))
            else:
                self.tiles.append((x, y, self._tile_image(tileset, local_id)))

    def _is_collision_layer(self, layer):
        """Reconhece a propriedade colisao=true ou nomes convencionais."""
        properties = self._properties(layer)
        value = properties.get("colisao", properties.get("collision", "false"))
        if str(value).casefold() in ("1", "true", "sim", "yes"):
            return True
        return _normalise(layer.get("name", "")) in ("colisao", "collision")

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
        return tileset["image"].subsurface(source)

    def _image_for_gid(self, gid):
        tileset, local_id = self._tileset_for_gid(gid)
        return self._tile_image(tileset, local_id) if tileset else None

    def _current_frame_image(self, tileset, local_id):
        """Resolve o quadro atual de um tile animado (ex.: água), a partir do
        relógio acumulado em self.elapsed_ms e das durações do Tiled."""
        frames = tileset["animations"][local_id]
        total_duration = sum(duration for _, duration in frames)
        if total_duration <= 0:
            return self._tile_image(tileset, local_id)
        elapsed = self.elapsed_ms % total_duration
        for frame_id, duration in frames:
            if elapsed < duration:
                return self._tile_image(tileset, frame_id)
            elapsed -= duration
        return self._tile_image(tileset, frames[-1][0])

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
        """Desenha apenas os tiles que cruzam a área visível."""
        right = camera_x + surface.get_width()
        bottom = camera_y + surface.get_height()

        def visible(x, y):
            if x + self.tile_width < camera_x or x > right:
                return False
            if y + self.tile_height < camera_y or y > bottom:
                return False
            return True

        for x, y, image in self.tiles:
            if visible(x, y):
                surface.blit(image, (x - camera_x, y - camera_y))
        for x, y, tileset, local_id in self.animated_tiles:
            if visible(x, y):
                image = self._current_frame_image(tileset, local_id)
                surface.blit(image, (x - camera_x, y - camera_y))
