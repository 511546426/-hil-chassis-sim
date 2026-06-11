"""分层推箱环境：RL 导航 + Rule 操作（P3-M4）。"""

from __future__ import annotations

import math
from enum import Enum
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from embodied_gym.core.action import decode_nav_action
from embodied_gym.core.observation import encode_nav_obs, load_nav_obs_spec
from embodied_gym.core.task_spec import TaskSpec, load_task_spec
from embodied_gym.envs.nav_env import NavEnv
from embodied_gym.manipulate.rule_manipulate import ManipulatePhase, RuleManipulateController
from embodied_gym.rewards.nav_reward import NavRewardEngine


def stuck_at_box(
    *,
    center_dist: float,
    cmd_vx: float,
    base_vx: float,
) -> bool:
    """与 embodied_core::stuck_at_box 一致。"""
    if center_dist <= 0.52 and cmd_vx > 0.05:
        return True
    return cmd_vx > 0.15 and abs(base_vx) < 0.05 and center_dist < 0.75


class HybridPhase(str, Enum):
    NAV = 'nav'
    MANIPULATE = 'manipulate'


class PushBoxEnv(gym.Env):
    """Hybrid 推箱：导航段复用 NavEnv obs/action；操作段由 RuleManipulateController 驱动。"""

    metadata = {'render_modes': []}

    def __init__(
        self,
        task: str | Path | TaskSpec,
        *,
        seed: int | None = None,
    ) -> None:
        super().__init__()
        if isinstance(task, TaskSpec):
            self.task = task
        else:
            self.task = load_task_spec(task)

        self.nav_env = NavEnv(self.task, seed=seed)
        self.obs_spec = load_nav_obs_spec()
        self.reward_engine = NavRewardEngine(self.task.reward)
        self.manipulator = RuleManipulateController()
        self.phase = HybridPhase.NAV
        self._total_steps = 0
        self._prev_dist = 0.0
        self._last_nav_cmd_vx = 0.0

        self.observation_space = self.nav_env.observation_space
        self.action_space = self.nav_env.action_space

    @property
    def session(self):
        return self.nav_env.session

    def _center_dist_to_box(self) -> float | None:
        state = self.session.read_state()
        poses = self.session.object_poses()
        if 'box_red' not in poses:
            return None
        bx, by, _z = poses['box_red']
        return math.hypot(bx - state.base_x, by - state.base_y)

    def _ready_for_manipulate(self) -> bool:
        dist = self._center_dist_to_box()
        if dist is None:
            return False
        state = self.session.read_state()
        if stuck_at_box(
            center_dist=dist,
            cmd_vx=self._last_nav_cmd_vx,
            base_vx=state.base_vx,
        ):
            return True
        # 与 hybrid_nav_complete / PushRedBoxFSM::navigation_complete 一致
        return dist <= self.task.goal.standoff + self.task.success.distance_lt

    def _push_min_dist(self) -> float:
        return float(getattr(self.task.success, 'push_min_dist', 0.20))

    def _build_obs(self) -> np.ndarray:
        state = self.session.read_state()
        obs = encode_nav_obs(
            base_x=state.base_x,
            base_y=state.base_y,
            base_yaw=state.base_yaw,
            base_vx=state.base_vx,
            base_steer=state.base_steer,
            goal_x=0.0,
            goal_y=0.0,
            goal_kind='object',
            object_name='box_red',
            standoff=self.task.goal.standoff,
            objects=self.session.object_poses(),
            spec=self.obs_spec,
        )
        return np.asarray(obs, dtype=np.float32)

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        obs, info = self.nav_env.reset(seed=seed, options=options)
        self.phase = HybridPhase.NAV
        self.manipulator.reset()
        self._total_steps = 0
        self._prev_dist = info.get('goal_distance', 0.0)
        self._last_nav_cmd_vx = 0.0
        info['hybrid_phase'] = self.phase.value
        return obs, info

    def step(
        self, action: np.ndarray
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        self._total_steps += 1
        reward = 0.0
        info: dict[str, Any] = {'hybrid_phase': self.phase.value}

        if self.phase == HybridPhase.NAV:
            self._last_nav_cmd_vx, _steer = decode_nav_action(
                action, spec=self.obs_spec
            )
            obs, step_reward, terminated, truncated, nav_info = self.nav_env.step(action)
            reward += step_reward
            info.update(nav_info)
            if self._ready_for_manipulate():
                self.phase = HybridPhase.MANIPULATE
                info['hybrid_phase'] = self.phase.value
                info['nav_complete'] = True
                return obs, float(reward), False, truncated, info
            if terminated or truncated:
                return obs, float(reward), terminated, truncated, info
            return obs, float(reward), False, self._total_steps >= self.task.max_steps, info

        result = self.manipulator.step(self.session, self.task.dt)
        info['manipulate_phase'] = result.phase.name
        info['box_push_dist'] = result.box_push_dist
        reward += self.task.reward.time

        if result.success:
            reward += getattr(self.task.reward, 'push_success', 20.0)
        if result.done and not result.success:
            reward -= 5.0

        obs = self._build_obs()
        terminated = result.done
        truncated = self._total_steps >= self.task.max_steps and not terminated
        info['success'] = result.success and result.box_push_dist >= self._push_min_dist()
        return obs, float(reward), terminated, truncated, info

    def close(self) -> None:
        self.nav_env.close()
