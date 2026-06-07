"""从 MuJoCo data 正确读取机器人状态。"""

from __future__ import annotations

import mujoco

from .actuators import set_arm_position_ctrl
from .model import DEFAULT_ELBOW, DEFAULT_SHOULDER, DEFAULT_WRIST, SCENE_OBJECT_BODIES

ObjectPose = tuple[float, float, float, float, float, float, float]


def _joint_qpos(model, data, name: str) -> float:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    if jid < 0:
        return 0.0
    return float(data.qpos[model.jnt_qposadr[jid]])


def _joint_qvel(model, data, name: str) -> float:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    if jid < 0:
        return 0.0
    return float(data.qvel[model.jnt_dofadr[jid]])


def read_base_pose(model, data) -> tuple[float, float, float]:
    return (
        _joint_qpos(model, data, 'slide_x'),
        _joint_qpos(model, data, 'slide_y'),
        _joint_qpos(model, data, 'hinge_z'),
    )


def read_base_velocity(model, data) -> tuple[float, float, float]:
    return (
        _joint_qvel(model, data, 'slide_x'),
        _joint_qvel(model, data, 'slide_y'),
        _joint_qvel(model, data, 'hinge_z'),
    )


def read_arm_joint_positions(model, data) -> tuple[float, float, float]:
    return (
        _joint_qpos(model, data, 'arm_shoulder'),
        _joint_qpos(model, data, 'arm_elbow'),
        _joint_qpos(model, data, 'arm_wrist'),
    )


def read_object_poses(
    model,
    data,
    body_names: tuple[str, ...] | None = None,
) -> dict[str, ObjectPose]:
    """读取 freejoint 物体位姿，返回 body 名 -> (x, y, z, qw, qx, qy, qz)。"""
    names = body_names if body_names is not None else SCENE_OBJECT_BODIES
    poses: dict[str, ObjectPose] = {}
    for name in names:
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        if bid < 0:
            continue
        pos = data.xpos[bid]
        quat = data.xquat[bid]
        poses[name] = (
            float(pos[0]),
            float(pos[1]),
            float(pos[2]),
            float(quat[0]),
            float(quat[1]),
            float(quat[2]),
            float(quat[3]),
        )
    return poses


def initialize_robot_pose(
    model,
    data,
    *,
    shoulder=DEFAULT_SHOULDER,
    elbow=DEFAULT_ELBOW,
    wrist=DEFAULT_WRIST,
) -> None:
    for jname, val in (
        ('slide_x', 0.0),
        ('slide_y', 0.0),
        ('hinge_z', 0.0),
        ('arm_shoulder', shoulder),
        ('arm_elbow', elbow),
        ('arm_wrist', wrist),
    ):
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            data.qpos[model.jnt_qposadr[jid]] = val

    data.qvel[:] = 0.0
    data.ctrl[:] = 0.0
    set_arm_position_ctrl(model, data, shoulder, elbow, wrist)
    mujoco.mj_forward(model, data)
