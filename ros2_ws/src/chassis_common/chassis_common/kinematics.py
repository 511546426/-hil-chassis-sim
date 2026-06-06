"""运动学：转向角 → 角速度，车体速度 → 世界坐标系关节速度。"""

import math

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
