"""Leitor simples de mapas TMX criados no Tiled.

O projeto usa somente o formato XML/CSV do Tiled, portanto não depende de
bibliotecas adicionais como pytmx.  As camadas de tiles são desenhadas pelo
jogo e as camadas de objetos fornecem colisões e itens interativos.
"""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
import unicodedata

import pygame


FLIPPED_GID_MASK = 0x1FFFFFFF


def _normalise(value):
    """Compara nomes de camadas sem se importar com maiúsculas ou acentos."""
    text = unicodedata.normalize("NFD", str(value).casefold())
    return "".join(
        char for char in text
        if char.isalnum()
    )


class TiledMap:
    """Mapa TMX ortogonal com tilesets externos ``.tsx`` e objetos retangulares."""

    def __init__(self, path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Mapa do Tiled não encontrado: {self.path}")

        root = ET.parse(self.path).getroot()
        if root.get("orientation", "orthogonal") != "orthogonal":
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
        self.object_groups = {}
        self._read_layers(root)

    @staticmethod
    def _properties(element):
        properties = {}
        for node in element.findall("./properties/property"):
            name = node.get("name", "")
            value = node.get("value", node.text or "")
            properties[name] = value
        return properties

    def _load_tilesets(self, root):
        tilesets = []
        for entry in root.findall("tileset"):
            first_gid = int(entry.get("firstgid", 1))
            source = entry.get("source")
            tileset_root = ET.parse(self.path.parent / source).getroot() if source else entry
            base_dir = (self.path.parent / source).parent if source else self.path.parent
            image = tileset_root.find("image")
            if image is None:
                continue
            image_path = base_dir / image.get("source", "")
            surface = pygame.image.load(image_path).convert_alpha()
            columns = int(tileset_root.get("columns", 1))
            tile_width = int(tileset_root.get("tilewidth", self.tile_width))
            tile_height = int(tileset_root.get("tileheight", self.tile_height))
            tile_count = int(tileset_root.get("tilecount", 0))
            tilesets.append({
                "first_gid": first_gid,
                "last_gid": first_gid + tile_count - 1,
                "image": surface,
                "columns": columns,
                "tile_width": tile_width,
                "tile_height": tile_height,
            })
        return tilesets

    def _read_layers(self, root):
        for layer in root.findall("layer"):
            self._read_tile_layer(layer)
        for group in root.findall("objectgroup"):
            self._read_object_group(group)

    def _read_tile_layer(self, layer):
        data = layer.find("data")
        if data is None:
            return
        encoding = data.get("encoding", "")
        if encoding == "csv":
            values = [int(value.strip()) for value in (data.text or "").split(",") if value.strip()]
        elif not encoding:
            values = [int(tile.get("gid", 0)) for tile in data.findall("tile")]
        else:
            raise ValueError(
                "No Tiled, salve a camada em CSV (Camada > Formato de dados da camada)."
            )

        layer_width = int(layer.get("width", self.width))
        for index, gid in enumerate(values):
            gid &= FLIPPED_GID_MASK
            if gid == 0:
                continue
            image = self._image_for_gid(gid)
            if image is None:
                continue
            column, row = index % layer_width, index // layer_width
            self.tiles.append((column * self.tile_width, row * self.tile_height, image))

    def _read_object_group(self, group):
        group_name = _normalise(group.get("name", "objetos"))
        objects = []
        for node in group.findall("object"):
            object_type = node.get("type") or node.get("class", "")
            objects.append({
                "name": node.get("name", ""),
                "type": object_type,
                "x": round(float(node.get("x", 0))),
                "y": round(float(node.get("y", 0))),
                "width": round(float(node.get("width", self.tile_width))),
                "height": round(float(node.get("height", self.tile_height))),
                "properties": self._properties(node),
            })
        self.object_groups[group_name] = objects

    def _image_for_gid(self, gid):
        for tileset in reversed(self.tilesets):
            if tileset["first_gid"] <= gid <= tileset["last_gid"]:
                tile_id = gid - tileset["first_gid"]
                source = pygame.Rect(
                    (tile_id % tileset["columns"]) * tileset["tile_width"],
                    (tile_id // tileset["columns"]) * tileset["tile_height"],
                    tileset["tile_width"], tileset["tile_height"],
                )
                return tileset["image"].subsurface(source)
        return None

    def objects(self, *group_names):
        result = []
        for name in group_names:
            result.extend(self.object_groups.get(_normalise(name), ()))
        return result

    def entities(self, entity_type):
        wanted = _normalise(entity_type)
        return [
            item for item in self.objects("Entidades")
            if _normalise(item["type"]) == wanted
        ]

    def entity(self, entity_type):
        entities = self.entities(entity_type)
        return entities[0] if entities else None

    def draw(self, surface, camera_x, camera_y):
        """Desenha apenas os tiles que cruzam a tela atual."""
        right = camera_x + surface.get_width()
        bottom = camera_y + surface.get_height()
        for x, y, image in self.tiles:
            if x + self.tile_width < camera_x or x > right:
                continue
            if y + self.tile_height < camera_y or y > bottom:
                continue
            surface.blit(image, (x - camera_x, y - camera_y))
