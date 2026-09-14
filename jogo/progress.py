"""Formato v1 de progresso, validado antes de alterar a sessão."""

import json
import math
from pathlib import Path
from tempfile import NamedTemporaryFile

from game_data import ITEM_DEFS, MAX_LIVES, STARTING_LIVES

SAVE_VERSION = 1


def _number(value, name, *, integer=False, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: número esperado")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value < minimum or (integer and int(value) != value):
        raise ValueError(f"{name}: valor inválido")
    return int(value) if integer else value


def decode_progress(data, valid_levels):
    """Devolve uma cópia normalizada; nunca modifica o dicionário recebido."""
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != SAVE_VERSION:
        raise ValueError("Versão de save incompatível")
    index = data.get("level")
    if type(index) not in (int, str) or index not in valid_levels:
        raise ValueError("Fase inválida")
    checkpoint = data.get("checkpoint")
    if not isinstance(checkpoint, (list, tuple)) or len(checkpoint) != 2:
        raise ValueError("Checkpoint inválido")
    checkpoint = tuple(_number(v, "checkpoint", minimum=-math.inf) for v in checkpoint)
    if any(abs(v) > 2**30 for v in checkpoint):
        raise ValueError("Checkpoint fora do intervalo suportado pelo SDL")
    inventory = data.get("inventory", {})
    if not isinstance(inventory, dict):
        raise ValueError("Inventário inválido")
    inventory = {k: _number(v, k, integer=True) for k, v in inventory.items() if k in ITEM_DEFS}
    collected = data.get("collected", [])
    if not isinstance(collected, list):
        raise ValueError("Coletas inválidas")
    collected = {_number(i, "coleta", integer=True) for i in collected}
    ranged = data.get("ranged_unlocked", False)
    if type(ranged) is not bool:
        raise ValueError("Habilidade inválida")
    return {
        "level": index,
        "checkpoint": checkpoint,
        "lives": min(MAX_LIVES, _number(data.get("lives", STARTING_LIVES), "vidas")),
        "shield": _number(data.get("shield", 0), "escudo", integer=True),
        "inventory": inventory,
        # Saves antigos eram escritos antes do desbloqueio ao concluir a escola.
        "ranged_unlocked": ranged or (type(index) is int and index >= 1),
        "collected": collected,
    }


def read_progress(path, valid_levels):
    return decode_progress(json.loads(path.read_text(encoding="utf-8")), valid_levels)


def write_progress(path, data):
    """Substitui o arquivo somente depois de concluir a nova gravação."""
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
