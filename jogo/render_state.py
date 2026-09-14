"""Dados da sessão consumidos pela renderização de Level."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorldDrawState:
    collected: set
    lever_on: bool
    sequence_progress: int
    sequence_solved: bool
    microscope_collected: set
    microscope_assembled: bool
    artifact_image: object
    artifacts_collected: set
    tools_collected: set
    energy_box_state: dict
    lab_microscope_sprites: dict
    lab_microscope_collected: set
    lab_microscope_assembled: bool
