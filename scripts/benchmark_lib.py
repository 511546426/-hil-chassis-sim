"""P3-C3-3：HIL 批量评估共享库 — 指标、复位、报告。"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    return Path(os.environ.get('CHASSIS_DEMO_ROOT', Path(__file__).resolve().parents[1]))


@dataclass
class EpisodeResult:
    success: bool
    steps: int
    elapsed_sec: float = 0.0
    nav_dist: float | None = None
    box_push: float = 0.0
    stuck_steps: int = 0
    collision: bool = False

    @classmethod
    def from_monitor_line(cls, line: str, *, elapsed_sec: float = 0.0) -> EpisodeResult:
        fields: dict[str, str] = {}
        for token in line.strip().split():
            if '=' in token:
                key, val = token.split('=', 1)
                fields[key] = val
        nav_raw = fields.get('nav_dist', 'N/A')
        nav_dist = None if nav_raw in ('N/A', 'None', '') else float(nav_raw)
        stuck = int(fields.get('stuck_steps', '0'))
        success = fields.get('success', 'False') == 'True'
        collision_raw = fields.get('collision', 'False')
        collision = collision_raw == 'True'
        if not collision and not success and stuck >= 100:
            collision = True
        return cls(
            success=success,
            steps=int(fields.get('steps', '0')),
            elapsed_sec=float(fields.get('elapsed_sec', elapsed_sec)),
            nav_dist=nav_dist,
            box_push=float(fields.get('box_push', '0')),
            stuck_steps=stuck,
            collision=collision,
        )


@dataclass
class ScenarioReport:
    name: str
    mode: str
    brain: str
    task: str = ''
    task_text: str = ''
    planner_backend: str = ''
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
    def avg_elapsed_sec(self) -> float:
        if not self.episodes:
            return 0.0
        return sum(ep.elapsed_sec for ep in self.episodes) / len(self.episodes)

    @property
    def avg_box_push(self) -> float:
        pushes = [ep.box_push for ep in self.episodes if ep.box_push > 0.0]
        if not pushes:
            return 0.0
        return sum(pushes) / len(pushes)

    @property
    def collision_rate(self) -> float:
        if not self.episodes:
            return 0.0
        return sum(1 for ep in self.episodes if ep.collision) / len(self.episodes)


@dataclass
class BenchmarkSuite:
    name: str
    description: str
    episodes: int
    policy: Path
    scenarios: list[ScenarioReport]


def resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = root / path
    if candidate.exists():
        return candidate
    return path


@dataclass
class ScenarioSpec:
    name: str
    mode: str
    brain: str
    task: str = ''
    task_text: str = ''
    planner_backend: str = ''
    standoff: float = 0.35
    arrive_dist: float = 0.30
    push_min_dist: float = 0.20
    max_steps: int = 0
    timeout_sec: float = 0.0

    def ros_task(self) -> str:
        if self.task:
            return self.task
        return 'push_red_box' if self.mode == 'push' else 'nav_to_box_red'

    def monitor_max_steps(self) -> int:
        if self.max_steps > 0:
            return self.max_steps
        return 500 if self.mode == 'nav' else 1500

    def monitor_timeout(self) -> float:
        if self.timeout_sec > 0.0:
            return self.timeout_sec
        return 15.0 if self.mode == 'nav' else 45.0


def load_benchmark_config(path: Path) -> dict[str, Any]:
    with path.open(encoding='utf-8') as fh:
        return yaml.safe_load(fh)


def resolve_scenario_spec(raw: dict[str, Any]) -> ScenarioSpec:
    """Resolve benchmark scenario from registry task_id with optional overrides."""
    from chassis_common.task_registry import load_task_registry

    task_id = str(raw.get('task_id', raw.get('task', '')))
    registry = load_task_registry()
    entry = registry.get(task_id)

    if entry is not None:
        task_text = str(raw.get('task_text', ''))
        if not task_text and raw.get('planner_backend'):
            task_text = entry.default_task_text
        return ScenarioSpec(
            name=str(raw['name']),
            mode=str(raw.get('mode', entry.monitor.mode)),
            brain=str(raw.get('brain', entry.recommended_brain)),
            task=entry.id,
            task_text=task_text,
            planner_backend=str(raw.get('planner_backend', '')),
            standoff=float(raw.get('standoff', entry.monitor.standoff)),
            arrive_dist=float(raw.get('arrive_dist', entry.monitor.arrive_dist)),
            push_min_dist=float(raw.get('push_min_dist', entry.monitor.push_min_dist)),
            max_steps=int(raw.get('max_steps', entry.monitor.max_steps)),
            timeout_sec=float(raw.get('timeout_sec', entry.monitor.timeout_sec)),
        )

    return ScenarioSpec(
        name=str(raw['name']),
        mode=str(raw.get('mode', 'push')),
        brain=str(raw.get('brain', 'rule')),
        task=str(raw.get('task', '')),
        task_text=str(raw.get('task_text', '')),
        planner_backend=str(raw.get('planner_backend', '')),
        standoff=float(raw.get('standoff', 0.35)),
        arrive_dist=float(raw.get('arrive_dist', 0.30)),
        push_min_dist=float(raw.get('push_min_dist', 0.20)),
        max_steps=int(raw.get('max_steps', 0)),
        timeout_sec=float(raw.get('timeout_sec', 0.0)),
    )


def load_suite(
    config_path: Path,
    suite_name: str,
    *,
    episodes_override: int | None = None,
    policy_override: Path | None = None,
    scenario_filter: set[str] | None = None,
) -> BenchmarkSuite:
    root = project_root()
    cfg = load_benchmark_config(config_path)
    default_policy = resolve_path(
        root, policy_override or cfg.get('default_policy', 'runs/nav_ppo/full/nav_policy.onnx')
    )
    default_episodes = int(cfg.get('default_episodes', 3))
    suites = cfg.get('suites', {})
    if suite_name not in suites:
        raise KeyError(f'unknown suite {suite_name!r}; available: {", ".join(suites)}')

    entry = suites[suite_name]
    episodes = episodes_override or int(entry.get('episodes', default_episodes))
    policy = resolve_path(root, entry.get('policy', default_policy))

    scenarios: list[ScenarioReport] = []
    for raw in entry.get('scenarios', []):
        name = str(raw['name'])
        if scenario_filter and name not in scenario_filter:
            continue
        spec = resolve_scenario_spec(raw)
        scenarios.append(
            ScenarioReport(
                name=spec.name,
                mode=spec.mode,
                brain=spec.brain,
                task=spec.task,
                task_text=spec.task_text,
                planner_backend=spec.planner_backend,
            )
        )

    if not scenarios:
        raise ValueError(f'suite {suite_name!r} has no scenarios after filter')

    return BenchmarkSuite(
        name=suite_name,
        description=str(entry.get('description', '')),
        episodes=episodes,
        policy=policy,
        scenarios=scenarios,
    )


def scenario_specs_from_suite(suite: BenchmarkSuite, cfg_path: Path) -> list[ScenarioSpec]:
    cfg = load_benchmark_config(cfg_path)
    entry = cfg['suites'][suite.name]
    specs: list[ScenarioSpec] = []
    names = {sc.name for sc in suite.scenarios}
    for raw in entry.get('scenarios', []):
        if raw['name'] not in names:
            continue
        specs.append(resolve_scenario_spec(raw))
    return specs


def ros2_shell(env_sh: Path, setup_bash: Path, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            'bash',
            '-lc',
            f'source "{env_sh}" && source "{setup_bash}" && timeout 15 {command}',
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def wait_for_service(
    env_sh: Path,
    setup_bash: Path,
    service: str,
    *,
    timeout_sec: float = 30.0,
) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        proc = ros2_shell(env_sh, setup_bash, 'ros2 service list')
        if service in proc.stdout:
            return True
        time.sleep(0.5)
    return False


def reset_sim_subprocess(env_sh: Path, setup_bash: Path) -> bool:
    proc = ros2_shell(
        env_sh,
        setup_bash,
        'ros2 service call /sim/reset_episode embodied_msgs/srv/ResetEpisode "{}"',
    )
    return proc.returncode == 0 and 'success=True' in proc.stdout


def reset_episode_subprocess(env_sh: Path, setup_bash: Path) -> bool:
    for service in ('/sim/reset_episode', '/agent/reset_episode'):
        proc = ros2_shell(
            env_sh,
            setup_bash,
            f'ros2 service call {service} embodied_msgs/srv/ResetEpisode "{{}}"',
        )
        if proc.returncode != 0 or 'success=True' not in proc.stdout:
            return False
    return True


def send_task_subprocess(root: Path, python: str, text: str) -> None:
    subprocess.run(
        [python, str(root / 'scripts/send_task.py'), text, '--wait-sec', '0.5'],
        cwd=root,
        env={**os.environ, 'CHASSIS_DEMO_ROOT': str(root)},
        check=False,
    )


def write_markdown_report(
    path: Path,
    *,
    suite: BenchmarkSuite,
    wall_sec: float,
    config_path: Path,
) -> None:
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        f'# HIL Benchmark — {suite.name} (P3-C3-3)',
        '',
        f'- Generated: {now}',
        f'- Config: `{config_path.relative_to(project_root())}`',
        f'- Description: {suite.description}',
        f'- Episodes per scenario: {suite.episodes}',
        f'- Policy: `{suite.policy}`',
        f'- Total wall time: {wall_sec:.1f}s',
        '',
        '## Summary',
        '',
        '| Scenario | Brain | Mode | Success | Avg Steps | Avg Time [s] | Collisions | Avg Push [m] |',
        '|----------|-------|------|---------|-----------|--------------|------------|--------------|',
    ]
    for sc in suite.scenarios:
        lines.append(
            f'| `{sc.name}` | {sc.brain} | {sc.mode} | '
            f'{sc.success_rate * 100:.0f}% | {sc.avg_steps:.1f} | '
            f'{sc.avg_elapsed_sec:.2f} | {sc.collision_rate * 100:.0f}% | '
            f'{sc.avg_box_push:.3f} |'
        )

    lines.extend(['', '## Episodes', ''])
    for sc in suite.scenarios:
        meta = sc.name
        if sc.planner_backend:
            meta += f' (planner={sc.planner_backend})'
        if sc.task_text:
            meta += f' text={sc.task_text!r}'
        lines.append(f'### {meta}')
        lines.append('')
        for idx, ep in enumerate(sc.episodes, start=1):
            nav = 'N/A' if ep.nav_dist is None else f'{ep.nav_dist:.3f}'
            lines.append(
                f'- ep {idx}: success={ep.success} steps={ep.steps} '
                f'elapsed={ep.elapsed_sec:.2f}s nav_dist={nav} '
                f'box_push={ep.box_push:.3f} stuck={ep.stuck_steps} '
                f'collision={ep.collision}'
            )
        lines.append('')

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
