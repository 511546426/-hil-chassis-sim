#!/usr/bin/env python3
"""P3-M1：导航 PPO 训练入口。"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from embodied_gym.envs.nav_env import NavEnv


def _project_root() -> Path:
    return Path(os.environ.get('CHASSIS_DEMO_ROOT', Path(__file__).resolve().parents[1]))


def load_ppo_config(path: Path) -> dict:
    with path.open(encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_args() -> argparse.Namespace:
    root = _project_root()
    parser = argparse.ArgumentParser(description='Train navigation PPO policy (P3-M1)')
    parser.add_argument(
        '--task',
        type=Path,
        default=root / 'configs/tasks/nav_point.yaml',
        help='TaskSpec YAML path',
    )
    parser.add_argument(
        '--ppo-config',
        type=Path,
        default=root / 'configs/rl/ppo_nav.yaml',
        help='PPO hyperparameter YAML',
    )
    parser.add_argument('--timesteps', type=int, default=500_000)
    parser.add_argument('--n-envs', type=int, default=8)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument(
        '--run-dir',
        type=Path,
        default=None,
        help='Output directory (default: runs/nav_ppo/<timestamp>)',
    )
    parser.add_argument('--smoke', action='store_true', help='Quick 20k-step smoke run')
    parser.add_argument('--eval-freq', type=int, default=20_000)
    parser.add_argument('--checkpoint-freq', type=int, default=50_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.environ.setdefault('CHASSIS_DEMO_ROOT', str(_project_root()))

    task_path = args.task if args.task.is_absolute() else _project_root() / args.task
    ppo_path = args.ppo_config if args.ppo_config.is_absolute() else _project_root() / args.ppo_config
    if not task_path.is_file():
        print(f'ERROR: task file not found: {task_path}', file=sys.stderr)
        return 1
    if not ppo_path.is_file():
        print(f'ERROR: ppo config not found: {ppo_path}', file=sys.stderr)
        return 1

    timesteps = 20_000 if args.smoke else args.timesteps
    run_dir = args.run_dir
    if run_dir is None:
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        run_dir = _project_root() / 'runs' / 'nav_ppo' / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    ppo_cfg = load_ppo_config(ppo_path)
    net_arch = ppo_cfg.get('network', {}).get('net_arch', [128, 128])

    def env_fn():
        return NavEnv(task_path, seed=args.seed)

    vec_cls = SubprocVecEnv if args.n_envs > 1 else DummyVecEnv
    train_env = make_vec_env(env_fn, n_envs=args.n_envs, vec_env_cls=vec_cls, seed=args.seed)
    eval_env = DummyVecEnv([env_fn])

    model = PPO(
        ppo_cfg.get('policy', 'MlpPolicy'),
        train_env,
        device='cpu',
        learning_rate=float(ppo_cfg.get('learning_rate', 3e-4)),
        n_steps=int(ppo_cfg.get('n_steps', 2048)),
        batch_size=int(ppo_cfg.get('batch_size', 64)),
        n_epochs=int(ppo_cfg.get('n_epochs', 10)),
        gamma=float(ppo_cfg.get('gamma', 0.99)),
        gae_lambda=float(ppo_cfg.get('gae_lambda', 0.95)),
        clip_range=float(ppo_cfg.get('clip_range', 0.2)),
        ent_coef=float(ppo_cfg.get('ent_coef', 0.01)),
        vf_coef=float(ppo_cfg.get('vf_coef', 0.5)),
        max_grad_norm=float(ppo_cfg.get('max_grad_norm', 0.5)),
        policy_kwargs={'net_arch': net_arch},
        verbose=1,
        seed=args.seed,
        tensorboard_log=str(run_dir / 'tb'),
    )

    callbacks = [
        CheckpointCallback(
            save_freq=max(args.checkpoint_freq // args.n_envs, 1),
            save_path=str(run_dir / 'checkpoints'),
            name_prefix='nav_ppo',
        ),
        EvalCallback(
            eval_env,
            best_model_save_path=str(run_dir),
            log_path=str(run_dir / 'eval'),
            eval_freq=max(args.eval_freq // args.n_envs, 1),
            n_eval_episodes=10,
            deterministic=True,
        ),
    ]

    print(f'Task: {task_path}')
    print(f'Run dir: {run_dir}')
    print(f'Timesteps: {timesteps}  n_envs: {args.n_envs}')
    model.learn(total_timesteps=timesteps, callback=callbacks)
    final_path = run_dir / 'final_model'
    model.save(str(final_path))
    print(f'Saved: {final_path}.zip')
    return 0


if __name__ == '__main__':
    sys.exit(main())
