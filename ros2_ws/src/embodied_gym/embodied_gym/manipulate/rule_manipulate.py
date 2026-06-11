"""规则操作控制器 — 对齐 PushRedBoxFSM 操作段（Reach → 夹爪 → 倒车）。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto

from chassis_common import (
    begin_virtual_grasp,
    detect_gripper_contact,
    end_virtual_grasp,
)
from chassis_common.model import DEFAULT_ELBOW, DEFAULT_SHOULDER, DEFAULT_WRIST

from embodied_gym.core.sim_session import SimSession


class ManipulatePhase(Enum):
    REACH_ARM = auto()
    CLOSE_GRIPPER = auto()
    BACK_UP = auto()
    DONE = auto()
    FAILED = auto()


ARM_REACH = (0.55, 0.4, 0.3)
ARM_STOW = (DEFAULT_SHOULDER, DEFAULT_ELBOW, DEFAULT_WRIST)


@dataclass
class ManipulateConfig:
    push_min_dist: float = 0.20
    max_vx_reverse: float = 0.35
    creep_vx_forward: float = 0.12
    arm_tol: float = 0.08
    gripper_tol: float = 0.05
    phase_timeout_reach: float = 15.0
    phase_timeout_gripper: float = 15.0
    phase_timeout_back_up: float = 15.0


@dataclass
class ManipulateStepResult:
    phase: ManipulatePhase
    box_push_dist: float
    done: bool
    success: bool


class RuleManipulateController:
    def __init__(self, config: ManipulateConfig | None = None) -> None:
        self.config = config or ManipulateConfig()
        self.phase = ManipulatePhase.REACH_ARM
        self.phase_time = 0.0
        self.box_x0 = 0.0
        self.box_y0 = 0.0
        self.has_box_origin = False

    def reset(self) -> None:
        self.phase = ManipulatePhase.REACH_ARM
        self.phase_time = 0.0
        self.has_box_origin = False

    def _arm_at(self, session: SimSession, target: tuple[float, float, float]) -> bool:
        t = session.tracker
        tol = self.config.arm_tol
        return (
            abs(t.shoulder_actual - target[0]) <= tol
            and abs(t.elbow_actual - target[1]) <= tol
            and abs(t.wrist_actual - target[2]) <= tol
        )

    def _box_xy(self, session: SimSession) -> tuple[float, float] | None:
        poses = session.object_poses()
        if 'box_red' not in poses:
            return None
        x, y, _z = poses['box_red']
        return x, y

    def box_push_distance(self, session: SimSession) -> float:
        if not self.has_box_origin:
            return 0.0
        box = self._box_xy(session)
        if box is None:
            return 0.0
        return math.hypot(box[0] - self.box_x0, box[1] - self.box_y0)

    def step(self, session: SimSession, dt: float) -> ManipulateStepResult:
        self.phase_time += dt
        cfg = self.config

        if self.phase == ManipulatePhase.REACH_ARM:
            session.step(
                target_linear_x=0.0,
                target_steering_angle=0.0,
                arm_shoulder=ARM_REACH[0],
                arm_elbow=ARM_REACH[1],
                arm_wrist=ARM_REACH[2],
                gripper=0.0,
            )
            if self._arm_at(session, ARM_REACH):
                self.phase = ManipulatePhase.CLOSE_GRIPPER
                self.phase_time = 0.0
            elif self.phase_time > cfg.phase_timeout_reach:
                self.phase = ManipulatePhase.FAILED

        elif self.phase == ManipulatePhase.CLOSE_GRIPPER:
            touching, _name = detect_gripper_contact(session.model, session.data)
            creep_vx = cfg.creep_vx_forward if not touching else 0.0
            session.step(
                target_linear_x=creep_vx,
                target_steering_angle=0.0,
                arm_shoulder=ARM_REACH[0],
                arm_elbow=ARM_REACH[1],
                arm_wrist=ARM_REACH[2],
                gripper=1.0,
            )
            touching, _name = detect_gripper_contact(session.model, session.data)
            gripper_closed = session.tracker.gripper_actual >= (1.0 - cfg.gripper_tol)
            if gripper_closed and touching:
                box = self._box_xy(session)
                if box is not None:
                    self.box_x0, self.box_y0 = box
                    self.has_box_origin = True
                session.virtual_grasp = begin_virtual_grasp(
                    session.model, session.data, 'box_red'
                )
                self.phase = ManipulatePhase.BACK_UP
                self.phase_time = 0.0
            elif self.phase_time > cfg.phase_timeout_gripper:
                self.phase = ManipulatePhase.FAILED

        elif self.phase == ManipulatePhase.BACK_UP:
            session.step(
                target_linear_x=-cfg.max_vx_reverse,
                target_steering_angle=0.0,
                arm_shoulder=ARM_REACH[0],
                arm_elbow=ARM_REACH[1],
                arm_wrist=ARM_REACH[2],
                gripper=1.0,
            )
            moved = self.box_push_distance(session)
            if self.has_box_origin and moved >= cfg.push_min_dist:
                self.phase = ManipulatePhase.DONE
                session.virtual_grasp = end_virtual_grasp(session.virtual_grasp)
            elif self.phase_time > cfg.phase_timeout_back_up:
                self.phase = ManipulatePhase.FAILED
                session.virtual_grasp = end_virtual_grasp(session.virtual_grasp)

        elif self.phase in (ManipulatePhase.DONE, ManipulatePhase.FAILED):
            session.step(
                target_linear_x=0.0,
                target_steering_angle=0.0,
                arm_shoulder=ARM_STOW[0],
                arm_elbow=ARM_STOW[1],
                arm_wrist=ARM_STOW[2],
                gripper=0.0,
            )

        moved = self.box_push_distance(session)
        success = self.phase == ManipulatePhase.DONE
        done = self.phase in (ManipulatePhase.DONE, ManipulatePhase.FAILED)
        return ManipulateStepResult(
            phase=self.phase,
            box_push_dist=moved,
            done=done,
            success=success,
        )
