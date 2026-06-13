#!/usr/bin/env python3
"""P3-C3-3：HIL 批量评估 — 多场景 × N episode，输出 Markdown 报告。"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmark_lib import (
    EpisodeResult,
    ScenarioSpec,
    load_suite,
    project_root,
    reset_sim_subprocess,
    scenario_specs_from_suite,
    send_task_subprocess,
    wait_for_service,
    write_markdown_report,
)


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description='Run HIL benchmark suites')
    parser.add_argument(
        '--config',
        type=Path,
        default=root / 'configs/benchmark/default.yaml',
    )
    parser.add_argument(
        '--suite',
        default='core',
        help='Suite name in config (core | planner_auto | quick)',
    )
    parser.add_argument('--episodes', type=int, default=0, help='Override suite episodes')
    parser.add_argument(
        '--policy',
        type=Path,
        default=None,
        help='Override ONNX policy path',
    )
    parser.add_argument(
        '--scenarios',
        default='',
        help='Comma-separated scenario names to run (default: all in suite)',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Markdown report path (default: runs/reports/benchmark_<suite>_<ts>.md)',
    )
    parser.add_argument(
        '--list-suites',
        action='store_true',
        help='List available suites and exit',
    )
    return parser.parse_args()


def build_agent_args(spec: ScenarioSpec, policy: Path) -> list[str]:
    args = [
        f'-p brain:={spec.brain}',
        f'-p standoff:={spec.standoff}',
        f'-p arrive_dist:={spec.arrive_dist}',
    ]
    if spec.brain in ('rl', 'hybrid', 'auto'):
        args.append(f'-p policy:={policy}')
    if spec.task:
        args.append(f'-p task:={spec.task}')
    elif spec.brain in ('rl', 'hybrid'):
        args.append(f'-p task:={spec.ros_task()}')
    if spec.planner_backend:
        args.append('-p listen_task_plan:=true')
    else:
        args.append('-p listen_task_plan:=false')
    return args


def run_monitor(
    *,
    python: str,
    monitor: Path,
    spec: ScenarioSpec,
    root: Path,
) -> EpisodeResult:
    started = time.monotonic()
    proc = subprocess.run(
        [
            python,
            str(monitor),
            '--mode',
            spec.mode,
            '--standoff',
            str(spec.standoff),
            '--arrive-dist',
            str(spec.arrive_dist),
            '--push-min-dist',
            str(spec.push_min_dist),
            '--max-steps',
            str(spec.monitor_max_steps()),
            '--timeout-sec',
            str(spec.monitor_timeout()),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.monotonic() - started
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout else ''
    result = EpisodeResult.from_monitor_line(line, elapsed_sec=elapsed)
    if result.elapsed_sec <= 0.0:
        result.elapsed_sec = elapsed
    return result


def list_suites(config_path: Path) -> None:
    cfg = __import__('yaml').safe_load(config_path.read_text(encoding='utf-8'))
    print(f'Config: {config_path}')
    for name, entry in cfg.get('suites', {}).items():
        desc = entry.get('description', '')
        eps = entry.get('episodes', cfg.get('default_episodes', 3))
        n_sc = len(entry.get('scenarios', []))
        print(f'  {name}: {desc} ({n_sc} scenarios, {eps} ep/scenario)')


def main() -> int:
    args = parse_args()
    root = project_root()
    os.environ.setdefault('CHASSIS_DEMO_ROOT', str(root))

    if args.list_suites:
        list_suites(args.config)
        return 0

    scenario_filter = (
        {s.strip() for s in args.scenarios.split(',') if s.strip()}
        if args.scenarios
        else None
    )
    episodes_override = args.episodes if args.episodes > 0 else None
    suite = load_suite(
        args.config,
        args.suite,
        episodes_override=episodes_override,
        policy_override=args.policy,
        scenario_filter=scenario_filter,
    )
    specs = scenario_specs_from_suite(suite, args.config)
    spec_by_name = {spec.name: spec for spec in specs}

    if not suite.policy.is_file():
        print(f'Policy not found: {suite.policy}', file=sys.stderr)
        return 1

    ws = root / 'ros2_ws'
    sim_node = ws / 'install/chassis_simulation/lib/chassis_simulation/simulation_node'
    setup_bash = ws / 'install/setup.bash'
    env_sh = root / 'scripts/env.sh'
    monitor = root / 'scripts/hil_episode_monitor.py'
    python = os.environ.get('CHASSIS_PYTHON', sys.executable)

    if not sim_node.is_file() or not setup_bash.is_file():
        print('Build HIL packages first: colcon build', file=sys.stderr)
        return 1

    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    output = args.output or (root / f'runs/reports/benchmark_{suite.name}_{ts}.md')

    log_dir = Path(os.environ.get('TMPDIR', '/tmp')) / f'hil_benchmark_{os.getpid()}'
    log_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['SIMULATION_HEADLESS'] = '1'
    env['SIMULATION_LOG_ONLY'] = '1'

    sim_proc: subprocess.Popen | None = None
    planner_proc: subprocess.Popen | None = None
    agent_proc: subprocess.Popen | None = None
    log_files: list[object] = []
    wall_started = time.monotonic()

    def stop_agent() -> None:
        nonlocal agent_proc
        if agent_proc and agent_proc.poll() is None:
            agent_proc.terminate()
            try:
                agent_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                agent_proc.kill()
        agent_proc = None

    def stop_planner() -> None:
        nonlocal planner_proc
        stop_agent()
        if planner_proc and planner_proc.poll() is None:
            planner_proc.terminate()
            try:
                planner_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                planner_proc.kill()
        planner_proc = None

    def stop_all() -> None:
        nonlocal sim_proc
        stop_planner()
        if sim_proc and sim_proc.poll() is None:
            sim_proc.terminate()
            try:
                sim_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                sim_proc.kill()
        sim_proc = None

    def start_agent(spec: ScenarioSpec, *, log_suffix: str) -> bool:
        nonlocal agent_proc
        agent_args = build_agent_args(spec, suite.policy)
        agent_cmd = (
            f'source "{env_sh}" && source "{setup_bash}" && '
            f'ros2 run chassis_agent_cpp agent_node --ros-args '
            f'{" ".join(agent_args)}'
        )
        agent_log = (log_dir / f'agent_{log_suffix}.log').open('w')
        log_files.append(agent_log)
        agent_proc = subprocess.Popen(
            ['bash', '-lc', agent_cmd],
            cwd=root,
            env=env,
            stdout=agent_log,
            stderr=subprocess.STDOUT,
        )
        if not wait_for_service(env_sh, setup_bash, '/agent/reset_episode', timeout_sec=12.0):
            return False
        return agent_proc.poll() is None

    try:
        for scenario_report in suite.scenarios:
            spec = spec_by_name[scenario_report.name]

            for ep_idx in range(suite.episodes):
                stop_planner()
                stop_agent()
                if sim_proc and sim_proc.poll() is None:
                    sim_proc.terminate()
                    try:
                        sim_proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        sim_proc.kill()
                    sim_proc = None

                sim_log = (log_dir / f'sim_{spec.name}_ep{ep_idx + 1}.log').open('w')
                log_files.append(sim_log)
                sim_proc = subprocess.Popen(
                    [python, str(sim_node)],
                    cwd=root,
                    env=env,
                    stdout=sim_log,
                    stderr=subprocess.STDOUT,
                )
                time.sleep(2.0)
                if sim_proc.poll() is not None:
                    print('simulation_node failed to restart', file=sys.stderr)
                    return 1
                if not wait_for_service(env_sh, setup_bash, '/sim/reset_episode'):
                    print('sim reset service not ready', file=sys.stderr)
                    return 1

                if spec.planner_backend:
                    planner_cmd = (
                        f'source "{env_sh}" && source "{setup_bash}" && '
                        f'ros2 run embodied_planner task_planner_node --ros-args '
                        f'-p planner_backend:={spec.planner_backend}'
                    )
                    planner_log = (log_dir / f'planner_{spec.name}_ep{ep_idx + 1}.log').open('w')
                    log_files.append(planner_log)
                    planner_proc = subprocess.Popen(
                        ['bash', '-lc', planner_cmd],
                        cwd=root,
                        env=env,
                        stdout=planner_log,
                        stderr=subprocess.STDOUT,
                    )
                    time.sleep(1.5)

                suffix = f'{spec.name}_ep{ep_idx + 1}'
                if not start_agent(spec, log_suffix=suffix):
                    print(f'agent failed ({spec.name} ep {ep_idx + 1})', file=sys.stderr)
                    return 1

                if spec.planner_backend and spec.task_text:
                    send_task_subprocess(root, python, spec.task_text)
                    time.sleep(0.8)

                ep = run_monitor(
                    python=python,
                    monitor=monitor,
                    spec=spec,
                    root=root,
                )
                scenario_report.episodes.append(ep)
                print(
                    f'{spec.name}[{ep_idx + 1}]: success={ep.success} steps={ep.steps} '
                    f'elapsed={ep.elapsed_sec:.2f}s collision={ep.collision}'
                )

    finally:
        stop_all()
        for handle in log_files:
            try:
                handle.close()
            except Exception:
                pass

    wall_sec = time.monotonic() - wall_started
    write_markdown_report(
        output,
        suite=suite,
        wall_sec=wall_sec,
        config_path=args.config,
    )
    print(f'Report: {output}')
    for sc in suite.scenarios:
        print(
            f'{sc.name}: success={sc.success_rate * 100:.0f}% '
            f'avg_steps={sc.avg_steps:.1f} avg_time={sc.avg_elapsed_sec:.2f}s'
        )
    return 0


if __name__ == '__main__':
    sys.exit(main())
