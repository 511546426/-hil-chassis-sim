#!/usr/bin/env python3
"""P3-M1：评估导航 PPO 策略成功率。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from stable_baselines3 import PPO

from embodied_gym.envs.nav_env import NavEnv


def _project_root() -> Path:
    return Path(os.environ.get('CHASSIS_DEMO_ROOT', Path(__file__).resolve().parents[1]))


def parse_args() -> argparse.Namespace:
    root = _project_root()
    parser = argparse.ArgumentParser(description='Evaluate navigation PPO policy')
    parser.add_argument('model', type=Path, help='Path to .zip model (best_model or final_model)')
    parser.add_argument(
        '--task',
        type=Path,
        default=root / 'configs/tasks/nav_point.yaml',
    )
    parser.add_argument('--episodes', type=int, default=100)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--success-threshold', type=float, default=0.80)
    return parser.parse_args()


def resolve_model_path(path: Path) -> Path:
    if path.suffix == '.zip':
        return path
    candidate = path.with_suffix('.zip')
    if candidate.is_file():
        return candidate
    return path


def main() -> int:
    args = parse_args()
    os.environ.setdefault('CHASSIS_DEMO_ROOT', str(_project_root()))

    task_path = args.task if args.task.is_absolute() else _project_root() / args.task
    model_path = resolve_model_path(
        args.model if args.model.is_absolute() else _project_root() / args.model
    )
    if not model_path.is_file():
        print(f'ERROR: model not found: {model_path}', file=sys.stderr)
        return 1

    model = PPO.load(str(model_path))
    env = NavEnv(task_path, seed=args.seed)

    successes = 0
    total_steps = 0
    for ep in range(args.episodes):
        obs, info = env.reset(seed=args.seed + ep)
        done = False
        steps = 0
        ep_success = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, _reward, terminated, truncated, info = env.step(action)
            steps += 1
            done = terminated or truncated
            ep_success = bool(info.get('success', False))
        if ep_success:
            successes += 1
        total_steps += steps

    rate = successes / args.episodes
    avg_steps = total_steps / args.episodes
    print(f'Episodes: {args.episodes}')
    print(f'Success: {successes}/{args.episodes} ({rate * 100:.1f}%)')
    print(f'Avg steps: {avg_steps:.1f}')
    if rate >= args.success_threshold:
        print(f'PASS: success rate >= {args.success_threshold * 100:.0f}%')
        return 0
    print(f'FAIL: success rate < {args.success_threshold * 100:.0f}%')
    return 1


if __name__ == '__main__':
    sys.exit(main())
