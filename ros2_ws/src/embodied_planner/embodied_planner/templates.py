"""P3-C2：任务模板加载与关键词匹配。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class GoalTemplate:
    kind: str
    x: float = 0.0
    y: float = 0.0
    object_name: str = 'box_red'
    standoff: float = 0.35

    def to_msg_fields(self) -> dict:
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
class TaskTemplate:
    id: str
    description: str
    recommended_brain: str
    goals: tuple[GoalTemplate, ...]
    aliases: tuple[str, ...] = field(default_factory=tuple)


def _project_root() -> Path:
    env_root = os.environ.get('CHASSIS_DEMO_ROOT')
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[4]


def _normalize(text: str) -> str:
    lowered = text.strip().lower()
    return re.sub(r'\s+', ' ', lowered)


def load_task_templates(
    path: str | Path | None = None,
) -> dict[str, TaskTemplate]:
    spec_path = Path(path) if path else _project_root() / 'configs/task_templates/index.yaml'
    with spec_path.open(encoding='utf-8') as f:
        raw = yaml.safe_load(f) or {}

    templates: dict[str, TaskTemplate] = {}
    for task_id, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        goals = tuple(
            GoalTemplate(
                kind=str(g.get('kind', 'PUSH_RED_BOX')),
                x=float(g.get('x', 0.0)),
                y=float(g.get('y', 0.0)),
                object_name=str(g.get('object_name', 'box_red')),
                standoff=float(g.get('standoff', 0.35)),
            )
            for g in entry.get('goals', [])
        )
        templates[task_id] = TaskTemplate(
            id=str(entry.get('id', task_id)),
            description=str(entry.get('description', task_id)),
            recommended_brain=str(entry.get('recommended_brain', 'rule')),
            goals=goals,
            aliases=tuple(str(a) for a in entry.get('aliases', [])),
        )
    return templates


def match_template(
    text: str,
    templates: dict[str, TaskTemplate] | None = None,
) -> TaskTemplate | None:
    catalog = templates if templates is not None else load_task_templates()
    query = _normalize(text)
    if not query:
        return None

    for template in catalog.values():
        if _normalize(template.id) == query:
            return template
        for alias in template.aliases:
            if _normalize(alias) == query:
                return template

    for template in catalog.values():
        for alias in template.aliases:
            if _normalize(alias) in query or query in _normalize(alias):
                return template
    return None
