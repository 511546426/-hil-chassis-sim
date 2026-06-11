"""导航动作解码 — 对齐 NavObsSpec 的 max_vx / max_steer。"""

from __future__ import annotations

import numpy as np

from .observation import NavObsSpec, load_nav_obs_spec


def decode_nav_action(
    action: np.ndarray | list[float],
    *,
    spec: NavObsSpec | None = None,
) -> tuple[float, float]:
    """归一化动作 [-1, 1] → (target_linear_x, target_steering_angle)。"""
    spec = spec or load_nav_obs_spec()
    arr = np.asarray(action, dtype=np.float64).reshape(-1)
    if arr.shape[0] != spec.action_dim:
        raise ValueError(f'expected action dim {spec.action_dim}, got {arr.shape[0]}')
    clipped = np.clip(arr, -1.0, 1.0)
    vx = float(clipped[0]) * spec.max_vx
    steer = float(clipped[1]) * spec.max_steer
    return vx, steer
