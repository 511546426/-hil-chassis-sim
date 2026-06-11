#!/usr/bin/env python3
"""P3-M1：NavEnv reset/step smoke test。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

from embodied_gym.envs.nav_env import NavEnv


def main() -> int:
    root = Path(os.environ.get('CHASSIS_DEMO_ROOT', Path(__file__).resolve().parents[1]))
    task = root / 'configs/tasks/nav_point.yaml'
    env = NavEnv(task, seed=0)
    obs, info = env.reset()
    assert obs.shape == (8,), obs.shape
    assert np.isfinite(obs).all()
    print(f'reset goal=({info["goal_x"]:.2f}, {info["goal_y"]:.2f}) dist={info["goal_distance"]:.3f}')

    total_reward = 0.0
    for _ in range(50):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        if terminated or truncated:
            break

    print(f'goal=({info.get("goal_x", "?")}, {info.get("goal_y", "?")}) '
          f'dist={info.get("goal_distance", 0):.3f} reward_sum={total_reward:.3f}')
    print('PASS: NavEnv smoke')
    return 0


if __name__ == '__main__':
    sys.exit(main())
