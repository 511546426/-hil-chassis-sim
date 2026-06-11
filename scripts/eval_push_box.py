#!/usr/bin/env python3
"""P3-M4：Headless 分层推箱评估（RL 导航 + Rule 操作）。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from stable_baselines3 import PPO

from embodied_gym.envs.push_box_env import PushBoxEnv


def _project_root() -> Path:
    return Path(os.environ.get('CHASSIS_DEMO_ROOT', Path(__file__).resolve().parents[1]))


def parse_args() -> argparse.Namespace:
    root = _project_root()
    parser = argparse.ArgumentParser(description='Evaluate hybrid push-box policy')
    parser.add_argument('model', type=Path, help='SB3 .zip model for navigation phase')
    parser.add_argument(
        '--task',
        type=Path,
        default=root / 'configs/tasks/push_box.yaml',
    )
    parser.add_argument('--episodes', type=int, default=5)
    parser.add_argument('--push-min-dist', type=float, default=0.20)
    return parser.parse_args()


def resolve_model(path: Path) -> Path:
    if path.suffix == '.zip':
        return path
    candidate = path.with_suffix('.zip')
    return candidate if candidate.is_file() else path


def main() -> int:
    args = parse_args()
    os.environ.setdefault('CHASSIS_DEMO_ROOT', str(_project_root()))

    model_path = resolve_model(
        args.model if args.model.is_absolute() else _project_root() / args.model
    )
    task_path = args.task if args.task.is_absolute() else _project_root() / args.task
    if not model_path.is_file():
        print(f'ERROR: model not found: {model_path}', file=sys.stderr)
        return 1

    model = PPO.load(str(model_path))
    env = PushBoxEnv(task_path)

    successes = 0
    for ep in range(args.episodes):
        obs, info = env.reset(seed=ep)
        done = False
        ep_success = False
        box_dist = 0.0
        steps = 0
        while not done:
            if env.phase.value == 'nav':
                action, _ = model.predict(obs, deterministic=True)
            else:
                action = env.action_space.sample() * 0.0
            obs, _reward, terminated, truncated, info = env.step(action)
            steps += 1
            done = terminated or truncated
            box_dist = float(info.get('box_push_dist', 0.0))
            ep_success = bool(info.get('success', False))
        print(
            f'ep {ep + 1}: steps={steps} box_push={box_dist:.3f} '
            f'phase={info.get("manipulate_phase", "N/A")} success={ep_success}'
        )
        if ep_success and box_dist >= args.push_min_dist:
            successes += 1

    rate = successes / args.episodes
    print(f'Push success: {successes}/{args.episodes} ({rate * 100:.1f}%)')
    if rate >= 0.8:
        print('PASS: push-box success rate >= 80%')
        return 0
    print('FAIL: push-box success rate < 80%')
    return 1


if __name__ == '__main__':
    sys.exit(main())
