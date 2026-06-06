"""差速底盘运动学：车体速度 -> 世界坐标系关节速度。"""

import numpy as np


def apply_velocity_command(data, vx_cmd: float, omega_cmd: float) -> None:
    """将车体坐标系线速度/角速度写入 MuJoCo 控制量。"""
    yaw = data.qpos[2]
    data.ctrl[0] = vx_cmd * np.cos(yaw)
    data.ctrl[1] = vx_cmd * np.sin(yaw)
    data.ctrl[2] = omega_cmd
