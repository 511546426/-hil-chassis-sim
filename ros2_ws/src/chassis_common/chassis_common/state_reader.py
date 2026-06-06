"""从 MuJoCo data 正确读取机器人状态。"""

import mujoco

from .actuators import set_arm_position_ctrl
from .model import DEFAULT_ELBOW, DEFAULT_SHOULDER, DEFAULT_WRIST


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
