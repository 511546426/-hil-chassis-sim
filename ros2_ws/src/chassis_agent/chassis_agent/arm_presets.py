"""机械臂姿态预设（与 BRAIN_ROADMAP 一致）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArmPreset:
    shoulder: float
    elbow: float
    wrist: float


ARM_STOW = ArmPreset(0.35, 0.0, 0.25)
ARM_REACH = ArmPreset(0.55, 0.4, 0.3)
ARM_GRASP_READY = ArmPreset(0.45, 0.6, 0.2)

PRESETS: dict[str, ArmPreset] = {
    'ARM_STOW': ARM_STOW,
    'ARM_REACH': ARM_REACH,
    'ARM_GRASP_READY': ARM_GRASP_READY,
}
