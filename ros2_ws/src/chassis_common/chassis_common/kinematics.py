"""运动学：转向角 → 角速度，底盘位姿积分。"""

import math

import mujoco
import numpy as np

from .state_reader import read_base_pose


def steering_to_omega(
    vx: float,
    steer_angle: float,
    wheelbase: float,
    *,
    pivot_speed_threshold: float = 0.08,
    max_pivot_omega: float = 1.5,
    max_steer_angle: float = 0.52,
) -> float:
    if abs(steer_angle) < 1e-6:
        return 0.0
    if abs(vx) < pivot_speed_threshold:
        if abs(max_steer_angle) < 1e-6:
            return 0.0
        return max_pivot_omega * (steer_angle / max_steer_angle)
    return vx * math.tan(steer_angle) / wheelbase


def apply_velocity_command(model, data, vx_cmd: float, omega_cmd: float) -> None:
    """将车体坐标系线速度/角速度写入 MuJoCo 底盘速度执行器。"""
    _, _, yaw = read_base_pose(model, data)
    data.ctrl[0] = vx_cmd * np.cos(yaw)
    data.ctrl[1] = vx_cmd * np.sin(yaw)
    data.ctrl[2] = omega_cmd


def set_base_pose(model, data, x: float, y: float, yaw: float) -> None:
    """直接设置底盘位姿并清零底盘速度。"""
    for jname, val in (
        ('slide_x', x),
        ('slide_y', y),
        ('hinge_z', yaw),
    ):
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid < 0:
            continue
        data.qpos[model.jnt_qposadr[jid]] = val
        data.qvel[model.jnt_dofadr[jid]] = 0.0


def advance_base_pose(
    x: float,
    y: float,
    yaw: float,
    vx: float,
    omega: float,
    dt: float,
) -> tuple[float, float, float]:
    """车体坐标系速度 → 世界系位姿增量（运动学，无侧滑）。"""
    return (
        x + vx * math.cos(yaw) * dt,
        y + vx * math.sin(yaw) * dt,
        yaw + omega * dt,
    )
