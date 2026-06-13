"""TaskSpec YAML 加载 — 训练与评估共用。"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class GoalSpec:
    type: str = 'point'
    x: float = 0.0
    y: float = 0.0
    object_name: str = 'box_red'
    standoff: float = 0.0
    random: dict[str, list[float]] = field(default_factory=dict)


@dataclass(frozen=True)
class SuccessSpec:
    distance_lt: float = 0.30
    push_min_dist: float = 0.20


@dataclass(frozen=True)
class ResetSpec:
    base_x: float = 0.0
    base_y: float = 0.0
    base_yaw: float = 0.0
    randomize: dict[str, list[float]] = field(default_factory=dict)


@dataclass(frozen=True)
class RewardSpec:
    progress: float = 1.0
    time: float = -0.01
    collision: float = -5.0
    success: float = 10.0
    push_success: float = 20.0
    out_of_bounds: float = -5.0


@dataclass(frozen=True)
class LimitsSpec:
    arena_half: float = 15.0


@dataclass(frozen=True)
class TaskSpec:
    name: str
    max_steps: int
    dt: float
    goal: GoalSpec
    success: SuccessSpec
    reset: ResetSpec
    reward: RewardSpec
    limits: LimitsSpec


def _project_root() -> Path:
    env_root = os.environ.get('CHASSIS_DEMO_ROOT')
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[5]


def load_task_spec(path: str | Path) -> TaskSpec:
    spec_path = Path(path)
    if not spec_path.is_absolute():
        spec_path = _project_root() / spec_path

    if spec_path.is_file():
        with spec_path.open(encoding='utf-8') as f:
            raw = yaml.safe_load(f) or {}
        task_id = raw.get('task_id')
        if task_id:
            return load_task_spec_by_id(str(task_id))
        return _task_spec_from_dict(raw, name=spec_path.stem)

    task_id = str(path)
    try:
        registry = load_task_registry()
    except Exception:
        registry = {}
    if task_id in registry:
        return load_task_spec_by_id(task_id)

    raise FileNotFoundError(f'task spec not found: {path}')


def load_task_registry():
    from chassis_common.task_registry import load_task_registry as _load

    return _load()


def load_task_spec_by_id(task_id: str) -> TaskSpec:
    from chassis_common.task_registry import get_task_entry, gym_spec_dict

    entry = get_task_entry(task_id)
    return _task_spec_from_dict(gym_spec_dict(entry), name=entry.id)


def _task_spec_from_dict(raw: dict, *, name: str) -> TaskSpec:
    goal_raw = raw.get('goal', {})
    reset_raw = raw.get('reset', {})
    base_raw = reset_raw.get('base', {})
    reward_raw = raw.get('reward', {})
    limits_raw = raw.get('limits', {})

    return TaskSpec(
        name=str(raw.get('name', name)),
        max_steps=int(raw.get('max_steps', 500)),
        dt=float(raw.get('dt', 0.02)),
        goal=GoalSpec(
            type=str(goal_raw.get('type', 'point')),
            x=float(goal_raw.get('x', 0.0)),
            y=float(goal_raw.get('y', 0.0)),
            object_name=str(goal_raw.get('object_name', 'box_red')),
            standoff=float(goal_raw.get('standoff', 0.0)),
            random=dict(goal_raw.get('random', {})),
        ),
        success=SuccessSpec(
            distance_lt=float(raw.get('success', {}).get('distance_lt', 0.30)),
            push_min_dist=float(raw.get('success', {}).get('push_min_dist', 0.20)),
        ),
        reset=ResetSpec(
            base_x=float(base_raw.get('x', 0.0)),
            base_y=float(base_raw.get('y', 0.0)),
            base_yaw=float(base_raw.get('yaw', 0.0)),
            randomize=dict(reset_raw.get('randomize', {})),
        ),
        reward=RewardSpec(
            progress=float(reward_raw.get('progress', 1.0)),
            time=float(reward_raw.get('time', -0.01)),
            collision=float(reward_raw.get('collision', -5.0)),
            success=float(reward_raw.get('success', 10.0)),
            push_success=float(reward_raw.get('push_success', 20.0)),
            out_of_bounds=float(reward_raw.get('out_of_bounds', -5.0)),
        ),
        limits=LimitsSpec(
            arena_half=float(limits_raw.get('arena_half', 15.0)),
        ),
    )


def sample_uniform(rng: random.Random, bounds: list[float]) -> float:
    if len(bounds) != 2:
        raise ValueError(f'expected [low, high], got {bounds}')
    lo, hi = float(bounds[0]), float(bounds[1])
    return rng.uniform(lo, hi)


def sample_goal(task: TaskSpec, rng: random.Random) -> tuple[str, float, float, str]:
    goal = task.goal
    if goal.type == 'point' and goal.random:
        gx = sample_uniform(rng, goal.random.get('x', [goal.x, goal.x]))
        gy = sample_uniform(rng, goal.random.get('y', [goal.y, goal.y]))
        return 'point', gx, gy, goal.object_name
    if goal.type == 'object':
        return 'object', goal.x, goal.y, goal.object_name
    if goal.type == 'push_red_box':
        return 'push_red_box', goal.x, goal.y, 'box_red'
    return 'point', goal.x, goal.y, goal.object_name


def sample_base_pose(task: TaskSpec, rng: random.Random) -> tuple[float, float, float]:
    reset = task.reset
    x = reset.base_x
    y = reset.base_y
    yaw = reset.base_yaw
    rand = reset.randomize
    if 'base_x' in rand:
        x = sample_uniform(rng, rand['base_x'])
    if 'base_y' in rand:
        y = sample_uniform(rng, rand['base_y'])
    if 'base_yaw' in rand:
        yaw = sample_uniform(rng, rand['base_yaw'])
    return x, y, yaw
