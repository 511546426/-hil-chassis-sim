"""MuJoCo 执行器查找与写入。"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np

from .model import ARM_LIMITS


@dataclass
class PhysicsSnapshot:
    qpos: np.ndarray
    qvel: np.ndarray


def actuator_id_for_joint(model, joint_name: str) -> int:
    """按关节名查找对应执行器（XML 中 actuator 可无 name）。"""
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if jid < 0:
        return -1
    for aid in range(model.nu):
        if model.actuator_trnid[aid, 0] == jid:
            return aid
    return -1


def _clamp_joint(name: str, value: float) -> float:
    lo, hi = ARM_LIMITS[name]
    return max(lo, min(hi, value))


def set_arm_position_ctrl(model, data, shoulder: float, elbow: float, wrist: float) -> None:
    for joint_name, value in (
        ('arm_shoulder', _clamp_joint('arm_shoulder', shoulder)),
        ('arm_elbow', _clamp_joint('arm_elbow', elbow)),
        ('arm_wrist', _clamp_joint('arm_wrist', wrist)),
    ):
        aid = actuator_id_for_joint(model, joint_name)
        if aid >= 0:
            data.ctrl[aid] = value


def zero_arm_actuator_ctrl(model, data) -> None:
    for joint_name in ('arm_shoulder', 'arm_elbow', 'arm_wrist'):
        aid = actuator_id_for_joint(model, joint_name)
        if aid >= 0:
            data.ctrl[aid] = 0.0


def capture_physics_snapshot(data) -> PhysicsSnapshot:
    return PhysicsSnapshot(qpos=data.qpos.copy(), qvel=data.qvel.copy())


def restore_physics_snapshot(data, snapshot: PhysicsSnapshot) -> None:
    data.qpos[:] = snapshot.qpos
    data.qvel[:] = snapshot.qvel


def apply_arm_display_pose(
    model,
    data,
    shoulder: float,
    elbow: float,
    wrist: float,
) -> None:
    """设置机械臂关节角并刷新运动学（用于显示/运动学锁定）。"""
    for joint_name, value in (
        ('arm_shoulder', _clamp_joint('arm_shoulder', shoulder)),
        ('arm_elbow', _clamp_joint('arm_elbow', elbow)),
        ('arm_wrist', _clamp_joint('arm_wrist', wrist)),
    ):
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
        if jid < 0:
            continue
        data.qpos[model.jnt_qposadr[jid]] = value
        data.qvel[model.jnt_dofadr[jid]] = 0.0
    mujoco.mj_forward(model, data)


def pin_arm_kinematics(
    model,
    data,
    shoulder: float,
    elbow: float,
    wrist: float,
) -> None:
    """每帧锁定机械臂姿态，避免重力/integration 干扰底盘动力学。"""
    apply_arm_display_pose(model, data, shoulder, elbow, wrist)
