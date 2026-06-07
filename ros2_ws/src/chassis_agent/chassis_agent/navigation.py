"""导航控制：Pure Pursuit 与简单 P 控制。"""

from __future__ import annotations

import math
from dataclasses import dataclass


def normalize_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


@dataclass
class NavigationCommand:
    target_linear_x: float
    target_steering_angle: float
    arrived: bool


def approach_point(
    base_x: float,
    base_y: float,
    target_x: float,
    target_y: float,
    standoff: float,
) -> tuple[float, float]:
    """在目标点前留出 standoff 距离，避免顶到物体中心。"""
    dx = target_x - base_x
    dy = target_y - base_y
    dist = math.hypot(dx, dy)
    if dist < 1e-3:
        return target_x - standoff, target_y
    scale = max(0.0, dist - standoff) / dist
    return base_x + dx * scale, base_y + dy * scale


def pure_pursuit(
    x: float,
    y: float,
    yaw: float,
    target_x: float,
    target_y: float,
    *,
    look_ahead: float = 0.8,
    max_vx: float = 1.0,
    max_steer: float = 0.52,
    arrive_dist: float = 0.3,
    k_slow: float = 0.6,
) -> NavigationCommand:
    """Pure Pursuit 导航到目标点。"""
    dx = target_x - x
    dy = target_y - y
    dist = math.hypot(dx, dy)
    if dist < arrive_dist:
        return NavigationCommand(0.0, 0.0, True)

    target_heading = math.atan2(dy, dx)
    heading_err = normalize_angle(target_heading - yaw)

    if dist > look_ahead:
        lx = x + look_ahead * math.cos(target_heading)
        ly = y + look_ahead * math.sin(target_heading)
    else:
        lx, ly = target_x, target_y

    local_y = math.sin(-yaw) * (lx - x) + math.cos(-yaw) * (ly - y)
    curvature = 2.0 * local_y / max(look_ahead ** 2, 1e-6)
    steer = max(-max_steer, min(max_steer, math.atan(curvature * 0.32)))

    speed_factor = max(0.5, math.cos(heading_err))
    vx = max_vx * speed_factor
    if abs(heading_err) > math.radians(45):
        vx *= 0.5

    return NavigationCommand(vx, steer, False)
