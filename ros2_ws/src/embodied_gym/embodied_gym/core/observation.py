"""导航观测编码 — 对齐 embodied_core/nav_obs_spec.hpp 与 configs/rl/nav_obs_spec.json。"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NavObsSpec:
    obs_dim: int
    action_dim: int
    arena_half: float
    goal_scale: float
    max_vx: float
    max_steer: float
    obs_index: dict[str, int]


def _project_root() -> Path:
    env_root = os.environ.get('CHASSIS_DEMO_ROOT')
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[5]


def load_nav_obs_spec(path: Path | None = None) -> NavObsSpec:
    spec_path = path or (_project_root() / 'configs' / 'rl' / 'nav_obs_spec.json')
    with spec_path.open(encoding='utf-8') as f:
        raw = json.load(f)
    return NavObsSpec(
        obs_dim=int(raw['obs_dim']),
        action_dim=int(raw['action_dim']),
        arena_half=float(raw['arena_half']),
        goal_scale=float(raw['goal_scale']),
        max_vx=float(raw['max_vx']),
        max_steer=float(raw['max_steer']),
        obs_index=dict(raw['obs_index']),
    )


def _normalize_angle(angle: float) -> float:
    while angle <= -math.pi:
        angle += 2.0 * math.pi
    while angle > math.pi:
        angle -= 2.0 * math.pi
    return angle


def _resolve_goal_xy(
    base_x: float,
    base_y: float,
    goal_kind: str,
    goal_x: float,
    goal_y: float,
    object_name: str,
    objects: dict[str, tuple[float, float, float]],
) -> tuple[float, float]:
    if goal_kind in ('object', 'push_red_box'):
        name = 'box_red' if goal_kind == 'push_red_box' else object_name
        if name in objects:
            return objects[name][0], objects[name][1]
    return goal_x, goal_y


def encode_nav_obs(
    *,
    base_x: float,
    base_y: float,
    base_yaw: float,
    base_vx: float,
    base_steer: float,
    goal_x: float,
    goal_y: float,
    goal_kind: str = 'point',
    object_name: str = 'box_red',
    standoff: float = 0.35,
    objects: dict[str, tuple[float, float, float]] | None = None,
    spec: NavObsSpec | None = None,
) -> list[float]:
    """编码归一化导航观测（与 C++ encode_nav_obs 语义一致）。"""
    spec = spec or load_nav_obs_spec()
    objects = objects or {}

    tx, ty = _resolve_goal_xy(
        base_x, base_y, goal_kind, goal_x, goal_y, object_name, objects
    )
    dx = tx - base_x
    dy = ty - base_y
    dist = math.hypot(dx, dy)
    if standoff > 0.0 and dist > standoff:
        scale = (dist - standoff) / dist
        tx = base_x + dx * scale
        ty = base_y + dy * scale
        dx = tx - base_x
        dy = ty - base_y
        dist = math.hypot(dx, dy)

    cos_yaw = math.cos(base_yaw)
    sin_yaw = math.sin(base_yaw)
    goal_dx = cos_yaw * dx + sin_yaw * dy
    goal_dy = -sin_yaw * dx + cos_yaw * dy

    idx = spec.obs_index
    obs = [0.0] * spec.obs_dim
    obs[idx['base_x']] = base_x / spec.arena_half
    obs[idx['base_y']] = base_y / spec.arena_half
    obs[idx['base_yaw']] = _normalize_angle(base_yaw) / math.pi
    obs[idx['goal_dx']] = goal_dx / spec.goal_scale
    obs[idx['goal_dy']] = goal_dy / spec.goal_scale
    obs[idx['dist_goal']] = dist / spec.goal_scale
    obs[idx['base_vx']] = base_vx / spec.max_vx
    obs[idx['base_steer_abs']] = abs(base_steer) / spec.max_steer
    return obs
