"""Roteiros determinísticos dos inimigos com estados específicos."""

import hashlib
import json
import random
from types import SimpleNamespace

import pygame

import enemy


CASES = {
    "DarkWraith/attack_damage_respawn": ("DarkWraith", 1900, 743),
    "Librarian/attack_pattern": ("Librarian", 1400, 731),
    "Specimen/attack_pattern": ("Specimen", 1800, 700),
    "SlimeKing/attack_pattern_and_summons": ("SlimeKing", 1500, 739),
}

_ACTOR_FIELDS = (
    "x", "y", "anchor_x", "anchor_y", "direction", "speed", "health",
    "state", "state_timer", "death_frame", "animation", "attack_cooldown",
    "attack_index", "lunge_start_x", "half_range", "blade_shots_fired",
    "cocoon_hits", "tomes", "blades", "spores", "pending_spawns",
)


def _clean(value):
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, dict):
        return {key: _clean(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    return value


def _actor_state(actor):
    state = {
        name: _clean(getattr(actor, name))
        for name in _ACTOR_FIELDS
        if hasattr(actor, name)
    }
    state["rect"] = list(actor.rect)
    state["alive"] = actor.alive
    if hasattr(actor, "melee_vulnerable"):
        state["melee_vulnerable"] = actor.melee_vulnerable
    hazards = getattr(actor, "active_hazards", None)
    state["hazards"] = [list(rect) for rect in hazards()] if hazards else []
    parryable = getattr(actor, "parryable_hazards", None)
    state["parryable"] = [list(rect) for rect, _cancel in parryable()] if parryable else []
    return state


def _make_actor(class_name):
    rect = pygame.Rect(-120, 260, 620, 30)
    return getattr(enemy, class_name)(SimpleNamespace(rect=rect))


def _drain_slime_spawns(actor, summons):
    pending = getattr(actor, "pending_spawns", None)
    if not pending:
        return 0
    half = 150 // 2
    for x, y in pending:
        zone = SimpleNamespace(rect=pygame.Rect(x - half, y, 150, 32))
        summons.append(enemy.SmallSlime(zone))
    count = len(pending)
    pending.clear()
    return count


def record_special_scenario(case_name):
    class_name, ticks, seed = CASES[case_name]
    random.seed(seed)
    actor = _make_actor(class_name)
    if hasattr(actor, "wake_up"):
        actor.wake_up()

    trace = hashlib.sha256()
    transitions = []
    actions = []
    summon_events = []
    summons = []
    previous_state = actor.state

    for tick in range(ticks):
        if class_name == "DarkWraith" and tick in (450, 500):
            damage = 1 if tick == 450 else 99
            actions.append([tick, "take_hit", damage, actor.take_hit(damage)])
        if class_name == "SlimeKing" and tick == 600:
            actions.append([tick, "kill_first_summon", summons[0].take_hit(100)])

        actor.update()
        for summon in summons:
            summon.update()
        spawned = _drain_slime_spawns(actor, summons)
        if spawned:
            summon_events.append([tick, "spawned", spawned, len(summons)])

        if actor.state != previous_state:
            transitions.append([tick, previous_state, actor.state, actor.state_timer])
            previous_state = actor.state

        state = {
            "actor": _actor_state(actor),
            "summons": [_actor_state(summon) for summon in summons],
        }
        trace.update(json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    return {
        "ticks": ticks,
        "seed": seed,
        "trace_sha256": trace.hexdigest(),
        "transitions": transitions,
        "actions": actions,
        "summon_events": summon_events,
        "final": state,
    }
