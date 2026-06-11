#!/usr/bin/env python3
"""P3-M5：Rule vs RL 批量对照评估，输出 Markdown 报告。"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import rclpy
from embodied_msgs.srv import ResetEpisode
from rclpy.node import Node


def _project_root() -> Path:
    return Path(os.environ.get('CHASSIS_DEMO_ROOT', Path(__file__).resolve().parents[1]))


@dataclass
class EpisodeResult:
    success: bool
    steps: int
    nav_dist: float | None = None
    box_push: float = 0.0
    stuck_steps: int = 0


@dataclass
class BrainReport:
    name: str
    task: str
    mode: str
    episodes: list[EpisodeResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if not self.episodes:
            return 0.0
        return sum(1 for ep in self.episodes if ep.success) / len(self.episodes)

    @property
    def avg_steps(self) -> float:
        if not self.episodes:
            return 0.0
        return sum(ep.steps for ep in self.episodes) / len(self.episodes)

    @property
    def avg_box_push(self) -> float:
        pushes = [ep.box_push for ep in self.episodes if ep.box_push > 0.0]
        if not pushes:
            return 0.0
        return sum(pushes) / len(pushes)


def parse_episode_output(text: str) -> EpisodeResult:
    fields: dict[str, str] = {}
    for token in text.strip().split():
        if '=' in token:
            key, val = token.split('=', 1)
            fields[key] = val
    nav_raw = fields.get('nav_dist', 'N/A')
    nav_dist = None if nav_raw == 'N/A' else float(nav_raw)
    return EpisodeResult(
        success=fields.get('success', 'False') == 'True',
        steps=int(fields.get('steps', '0')),
        nav_dist=nav_dist,
        box_push=float(fields.get('box_push', '0')),
        stuck_steps=int(fields.get('stuck_steps', '0')),
    )


class ResetClient(Node):
    def __init__(self) -> None:
        super().__init__('compare_rule_rl_reset')
        self.sim_client = self.create_client(ResetEpisode, '/sim/reset_episode')
        self.agent_client = self.create_client(ResetEpisode, '/agent/reset_episode')

    def wait_sim_ready(self, timeout_sec: float = 30.0) -> bool:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if self.sim_client.wait_for_service(timeout_sec=0.5):
                return True
        return False

    def wait_agent_ready(self, timeout_sec: float = 10.0) -> bool:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if self.agent_client.wait_for_service(timeout_sec=0.5):
                return True
        return False

    def reset_episode(self) -> bool:
        req = ResetEpisode.Request()
        for client in (self.sim_client, self.agent_client):
            future = client.call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
            if not future.done() or future.result() is None:
                return False
            if not future.result().success:
                return False
        return True


def run_python_hybrid_eval(
    *,
    model: Path,
    episodes: int,
    python: str,
) -> BrainReport:
    root = _project_root()
    cmd = [
        python,
        str(root / 'scripts/eval_push_box.py'),
        str(model),
        '--episodes',
        str(episodes),
    ]
    proc = subprocess.run(
        cmd,
        cwd=root,
        env={**os.environ, 'CHASSIS_DEMO_ROOT': str(root)},
        capture_output=True,
        text=True,
        check=False,
    )
    report = BrainReport(name='hybrid_py', task='push_box', mode='push')
    for line in proc.stdout.splitlines():
        if not line.startswith('ep '):
            continue
        parts = dict(
            item.split('=', 1)
            for item in line.split()[2:]
            if '=' in item
        )
        report.episodes.append(
            EpisodeResult(
                success=parts.get('success', 'False') == 'True',
                steps=int(parts.get('steps', '0')),
                box_push=float(parts.get('box_push', '0')),
            )
        )
    if proc.returncode != 0 and not report.episodes:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
    return report


def write_markdown(
    path: Path,
    *,
    reports: list[BrainReport],
    episodes: int,
    policy: Path,
) -> None:
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        '# Rule vs RL Comparison (P3-M5)',
        '',
        f'- Generated: {now}',
        f'- Episodes per brain: {episodes}',
        f'- Policy: `{policy}`',
        '',
        '## Summary',
        '',
        '| Brain | Task | Success | Avg Steps | Avg Box Push [m] |',
        '|-------|------|---------|-----------|------------------|',
    ]
    for rep in reports:
        lines.append(
            f'| `{rep.name}` | {rep.task} | '
            f'{rep.success_rate * 100:.1f}% | {rep.avg_steps:.1f} | {rep.avg_box_push:.3f} |'
        )
    lines.extend(['', '## Episodes', ''])
    for rep in reports:
        lines.append(f'### {rep.name} ({rep.task})')
        lines.append('')
        for idx, ep in enumerate(rep.episodes, start=1):
            nav = 'N/A' if ep.nav_dist is None else f'{ep.nav_dist:.3f}'
            lines.append(
                f'- ep {idx}: success={ep.success} steps={ep.steps} '
                f'nav_dist={nav} box_push={ep.box_push:.3f}'
            )
        lines.append('')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def parse_args() -> argparse.Namespace:
    root = _project_root()
    parser = argparse.ArgumentParser(description='Compare rule / rl / hybrid brains')
    parser.add_argument(
        '--policy',
        type=Path,
        default=root / 'runs/nav_ppo/full/nav_policy.onnx',
    )
    parser.add_argument('--episodes', type=int, default=3)
    parser.add_argument(
        '--output',
        type=Path,
        default=root / 'runs/reports/rule_vs_rl.md',
    )
    parser.add_argument(
        '--python-only',
        action='store_true',
        help='Skip HIL; run headless Python hybrid eval only',
    )
    parser.add_argument('--skip-python', action='store_true')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = _project_root()
    os.environ.setdefault('CHASSIS_DEMO_ROOT', str(root))
    python = os.environ.get('CHASSIS_PYTHON', sys.executable)
    policy = args.policy if args.policy.is_absolute() else root / args.policy
    reports: list[BrainReport] = []

    if not args.skip_python:
        model_zip = root / 'runs/nav_ppo/full/best_model'
        reports.append(
            run_python_hybrid_eval(
                model=model_zip,
                episodes=args.episodes,
                python=python,
            )
        )

    if args.python_only:
        write_markdown(args.output, reports=reports, episodes=args.episodes, policy=policy)
        print(f'Report written: {args.output}')
        return 0

    ws = root / 'ros2_ws'
    monitor = root / 'scripts/hil_episode_monitor.py'
    sim_node = (
        ws / 'install/chassis_simulation/lib/chassis_simulation/simulation_node'
    )
    setup_bash = ws / 'install/setup.bash'
    env_sh = root / 'scripts/env.sh'

    if not sim_node.is_file():
        print('HIL nodes not built; run colcon build first or use --python-only', file=sys.stderr)
        return 1
    if not setup_bash.is_file():
        print(f'missing {setup_bash}; colcon build first', file=sys.stderr)
        return 1

    sim_proc: subprocess.Popen | None = None
    agent_proc: subprocess.Popen | None = None
    log_dir = Path(os.environ.get('TMPDIR', '/tmp')) / f'compare_rule_rl_{os.getpid()}'

    def stop_agent() -> None:
        nonlocal agent_proc
        if agent_proc and agent_proc.poll() is None:
            agent_proc.terminate()
            try:
                agent_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                agent_proc.kill()
        agent_proc = None

    def stop_sim() -> None:
        nonlocal sim_proc
        stop_agent()
        if sim_proc and sim_proc.poll() is None:
            sim_proc.terminate()
            try:
                sim_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                sim_proc.kill()
        sim_proc = None

    brain_specs = [
        ('rule', 'push_red_box', 'push', []),
        (
            'hybrid',
            'push_red_box',
            'push',
            [
                f'-p brain:=hybrid',
                f'-p policy:={policy}',
                '-p task:=push_red_box',
            ],
        ),
        (
            'rl',
            'nav_to_box_red',
            'nav',
            [
                f'-p brain:=rl',
                f'-p policy:={policy}',
                '-p task:=nav_to_box_red',
            ],
        ),
    ]

    env = os.environ.copy()
    env['SIMULATION_HEADLESS'] = '1'
    env['SIMULATION_LOG_ONLY'] = '1'
    log_dir.mkdir(parents=True, exist_ok=True)

    try:
        sim_proc = subprocess.Popen(
            [python, str(sim_node)],
            cwd=root,
            env=env,
            stdout=(log_dir / 'sim.log').open('w'),
            stderr=subprocess.STDOUT,
        )
        time.sleep(2.0)
        if sim_proc.poll() is not None:
            print('simulation_node failed to start', file=sys.stderr)
            return 1

        rclpy.init()
        reset_client = ResetClient()
        if not reset_client.wait_sim_ready():
            print('sim reset service not ready', file=sys.stderr)
            return 1

        for brain_name, task, mode, extra_args in brain_specs:
            stop_agent()
            agent_cmd = (
                f'source "{env_sh}" && source "{setup_bash}" && '
                f'ros2 run chassis_agent_cpp agent_node --ros-args '
                f'{" ".join(extra_args)} '
                f'-p standoff:=0.35 -p arrive_dist:=0.30'
            )
            agent_proc = subprocess.Popen(
                ['bash', '-lc', agent_cmd],
                cwd=root,
                env=env,
                stdout=(log_dir / f'agent_{brain_name}.log').open('w'),
                stderr=subprocess.STDOUT,
            )
            time.sleep(2.0)
            if agent_proc.poll() is not None:
                print(f'agent_node ({brain_name}) failed to start', file=sys.stderr)
                return 1
            if not reset_client.wait_agent_ready():
                print(f'agent reset service not ready ({brain_name})', file=sys.stderr)
                return 1
            if not reset_client.reset_episode():
                print(f'initial reset failed ({brain_name})', file=sys.stderr)
                return 1
            time.sleep(0.3)

            rep = BrainReport(name=brain_name, task=task, mode=mode)
            max_steps = 500 if mode == 'nav' else 1500
            timeout = 15.0 if mode == 'nav' else 45.0
            for _ep in range(args.episodes):
                if not reset_client.reset_episode():
                    print('reset_episode failed', file=sys.stderr)
                    return 1
                time.sleep(0.3)
                proc = subprocess.run(
                    [
                        python,
                        str(monitor),
                        '--mode',
                        mode,
                        '--max-steps',
                        str(max_steps),
                        '--timeout-sec',
                        str(timeout),
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                line = proc.stdout.strip().splitlines()[-1] if proc.stdout else ''
                rep.episodes.append(parse_episode_output(line))
            reports.append(rep)

        reset_client.destroy_node()
        rclpy.shutdown()
    finally:
        stop_sim()

    write_markdown(args.output, reports=reports, episodes=args.episodes, policy=policy)
    print(f'Report written: {args.output}')
    for rep in reports:
        print(
            f'{rep.name}: success={rep.success_rate * 100:.1f}% '
            f'avg_steps={rep.avg_steps:.1f}'
        )
    return 0


if __name__ == '__main__':
    sys.exit(main())
