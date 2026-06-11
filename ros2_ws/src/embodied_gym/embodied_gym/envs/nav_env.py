"""随机点 / 物体导航 Gymnasium 环境（P3-M1）。"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from embodied_gym.core.action import decode_nav_action
from embodied_gym.core.observation import effective_goal_xy, encode_nav_obs, load_nav_obs_spec
from embodied_gym.core.sim_session import SimSession
from embodied_gym.core.task_spec import TaskSpec, load_task_spec, sample_base_pose, sample_goal
from embodied_gym.rewards.nav_reward import NavRewardEngine


class NavEnv(gym.Env):
    """Headless 导航环境：SimSession + NavObsSpec + TaskSpec。"""

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

        self.obs_spec = load_nav_obs_spec()
        self.session = SimSession()
        self.reward_engine = NavRewardEngine(self.task.reward)
        self._rng = random.Random(seed)

        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.obs_spec.obs_dim,),
            dtype=np.float32,
        )
        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(self.obs_spec.action_dim,),
            dtype=np.float32,
        )

        self._goal_kind = 'point'
        self._goal_x = 0.0
        self._goal_y = 0.0
        self._goal_object = self.task.goal.object_name
        self._step_count = 0
        self._prev_dist = 0.0

    @property
    def goal_distance(self) -> float:
        state = self.session.read_state()
        _tx, _ty, dist = effective_goal_xy(
            base_x=state.base_x,
            base_y=state.base_y,
            goal_x=self._goal_x,
            goal_y=self._goal_y,
            goal_kind=self._goal_kind,
            object_name=self._goal_object,
            standoff=self.task.goal.standoff,
            objects=self.session.object_poses(),
        )
        return dist

    def _build_obs(self) -> np.ndarray:
        state = self.session.read_state()
        obs = encode_nav_obs(
            base_x=state.base_x,
            base_y=state.base_y,
            base_yaw=state.base_yaw,
            base_vx=state.base_vx,
            base_steer=state.base_steer,
            goal_x=self._goal_x,
            goal_y=self._goal_y,
            goal_kind=self._goal_kind,
            object_name=self._goal_object,
            standoff=self.task.goal.standoff,
            objects=self.session.object_poses(),
            spec=self.obs_spec,
        )
        return np.asarray(obs, dtype=np.float32)

    def _is_out_of_bounds(self) -> bool:
        state = self.session.read_state()
        half = self.task.limits.arena_half
        return (
            abs(state.base_x) > half
            or abs(state.base_y) > half
        )

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        if seed is not None:
            self._rng.seed(seed)
        super().reset(seed=seed)

        base_x, base_y, base_yaw = sample_base_pose(self.task, self._rng)
        self._goal_kind, self._goal_x, self._goal_y, self._goal_object = sample_goal(
            self.task, self._rng
        )
        self.session.reset_episode(base_x=base_x, base_y=base_y, base_yaw=base_yaw)
        self._step_count = 0
        self._prev_dist = self.goal_distance

        info = {
            'goal_kind': self._goal_kind,
            'goal_x': self._goal_x,
            'goal_y': self._goal_y,
            'goal_distance': self._prev_dist,
        }
        return self._build_obs(), info

    def step(
        self, action: np.ndarray
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        vx, steer = decode_nav_action(action, spec=self.obs_spec)
        self.session.step_velocity_command(vx, steer)
        self._step_count += 1

        curr_dist = self.goal_distance
        success = curr_dist < self.task.success.distance_lt
        out_of_bounds = self._is_out_of_bounds()
        reward_breakdown = self.reward_engine.step_reward(
            prev_dist=self._prev_dist,
            curr_dist=curr_dist,
            success=success,
            out_of_bounds=out_of_bounds,
        )
        self._prev_dist = curr_dist

        terminated = success or out_of_bounds
        truncated = self._step_count >= self.task.max_steps and not terminated

        info = {
            'goal_distance': curr_dist,
            'success': success,
            'out_of_bounds': out_of_bounds,
            'reward_breakdown': reward_breakdown,
        }
        return self._build_obs(), float(reward_breakdown.total), terminated, truncated, info

    def close(self) -> None:
        return
