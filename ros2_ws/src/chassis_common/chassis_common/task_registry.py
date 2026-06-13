"""P3-C3-1：统一 TaskSpec 注册表 — planner / gym / benchmark 共用。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    env_root = os.environ.get('CHASSIS_DEMO_ROOT')
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[3]


DEFAULT_REGISTRY_PATH = project_root() / 'configs/tasks/registry.yaml'
LEGACY_TEMPLATE_PATH = project_root() / 'configs/task_templates/index.yaml'


@dataclass(frozen=True)
class MonitorSpec:
    mode: str
    standoff: float = 0.35
    arrive_dist: float = 0.30
    push_min_dist: float = 0.20
    max_steps: int = 1500
    timeout_sec: float = 45.0


@dataclass(frozen=True)
class PlannerGoalSpec:
    kind: str
    x: float = 0.0
    y: float = 0.0
    object_name: str = 'box_red'
    standoff: float = 0.35

    def to_msg_fields(self) -> dict[str, Any]:
        kind_map = {
            'POINT': 0,
            'OBJECT': 1,
            'PUSH_RED_BOX': 2,
        }
        return {
            'kind': kind_map[self.kind.upper()],
            'x': self.x,
            'y': self.y,
            'object_name': self.object_name,
            'standoff': self.standoff,
        }


@dataclass(frozen=True)
class TaskRegistryEntry:
    id: str
    description: str
    recommended_brain: str
    aliases: tuple[str, ...]
    monitor: MonitorSpec
    planner_goals: tuple[PlannerGoalSpec, ...]
    gym: dict[str, Any]

    @property
    def default_task_text(self) -> str:
        return self.aliases[0] if self.aliases else self.id


def _normalize(text: str) -> str:
    lowered = text.strip().lower()
    return re.sub(r'\s+', ' ', lowered)


def _parse_monitor(raw: dict[str, Any]) -> MonitorSpec:
    return MonitorSpec(
        mode=str(raw.get('mode', 'nav')),
        standoff=float(raw.get('standoff', 0.35)),
        arrive_dist=float(raw.get('arrive_dist', 0.30)),
        push_min_dist=float(raw.get('push_min_dist', 0.20)),
        max_steps=int(raw.get('max_steps', 1500)),
        timeout_sec=float(raw.get('timeout_sec', 45.0)),
    )


def _parse_planner_goals(raw: dict[str, Any]) -> tuple[PlannerGoalSpec, ...]:
    goals = raw.get('goals', [])
    return tuple(
        PlannerGoalSpec(
            kind=str(g.get('kind', 'PUSH_RED_BOX')),
            x=float(g.get('x', 0.0)),
            y=float(g.get('y', 0.0)),
            object_name=str(g.get('object_name', 'box_red')),
            standoff=float(g.get('standoff', 0.35)),
        )
        for g in goals
    )


def _parse_entry(task_id: str, raw: dict[str, Any]) -> TaskRegistryEntry:
    planner_raw = raw.get('planner', {})
    if not planner_raw.get('goals'):
        planner_raw = {'goals': raw.get('goals', [])}
    return TaskRegistryEntry(
        id=str(raw.get('id', task_id)),
        description=str(raw.get('description', task_id)),
        recommended_brain=str(raw.get('recommended_brain', 'rule')),
        aliases=tuple(str(a) for a in raw.get('aliases', [])),
        monitor=_parse_monitor(raw.get('monitor', {})),
        planner_goals=_parse_planner_goals(planner_raw),
        gym=dict(raw.get('gym', {})),
    )


def load_task_registry(path: str | Path | None = None) -> dict[str, TaskRegistryEntry]:
    registry_path = Path(path) if path else DEFAULT_REGISTRY_PATH
    if not registry_path.is_absolute():
        registry_path = project_root() / registry_path
    with registry_path.open(encoding='utf-8') as fh:
        raw = yaml.safe_load(fh) or {}

    tasks_raw = raw.get('tasks', raw)
    entries: dict[str, TaskRegistryEntry] = {}
    for task_id, entry in tasks_raw.items():
        if isinstance(entry, dict):
            entries[task_id] = _parse_entry(task_id, entry)
    return entries


def get_task_entry(task_id: str, registry: dict[str, TaskRegistryEntry] | None = None) -> TaskRegistryEntry:
    catalog = registry if registry is not None else load_task_registry()
    if task_id not in catalog:
        raise KeyError(f'unknown task_id: {task_id!r}')
    return catalog[task_id]


def match_task_entry(
    text: str,
    registry: dict[str, TaskRegistryEntry] | None = None,
) -> TaskRegistryEntry | None:
    catalog = registry if registry is not None else load_task_registry()
    query = _normalize(text)
    if not query:
        return None

    for entry in catalog.values():
        if _normalize(entry.id) == query:
            return entry
        for alias in entry.aliases:
            if _normalize(alias) == query:
                return entry

    for entry in catalog.values():
        for alias in entry.aliases:
            norm_alias = _normalize(alias)
            if norm_alias in query or query in norm_alias:
                return entry
    return None


def gym_spec_dict(entry: TaskRegistryEntry) -> dict[str, Any]:
    gym = dict(entry.gym)
    gym.setdefault('name', entry.id)
    return gym


def legacy_template_dict(entry: TaskRegistryEntry) -> dict[str, Any]:
    return {
        'id': entry.id,
        'description': entry.description,
        'recommended_brain': entry.recommended_brain,
        'aliases': list(entry.aliases),
        'goals': [
            {
                'kind': goal.kind,
                'x': goal.x,
                'y': goal.y,
                'object_name': goal.object_name,
                'standoff': goal.standoff,
            }
            for goal in entry.planner_goals
        ],
    }
