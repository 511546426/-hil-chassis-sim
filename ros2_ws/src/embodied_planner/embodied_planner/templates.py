"""P3-C2：任务模板加载与关键词匹配（C3-1：委托 registry）。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from chassis_common.task_registry import (
    PlannerGoalSpec,
    TaskRegistryEntry,
    load_task_registry,
    match_task_entry,
)


@dataclass(frozen=True)
class GoalTemplate:
    kind: str
    x: float = 0.0
    y: float = 0.0
    object_name: str = 'box_red'
    standoff: float = 0.35

    def to_msg_fields(self) -> dict:
        return PlannerGoalSpec(
            kind=self.kind,
            x=self.x,
            y=self.y,
            object_name=self.object_name,
            standoff=self.standoff,
        ).to_msg_fields()


@dataclass(frozen=True)
class TaskTemplate:
    id: str
    description: str
    recommended_brain: str
    goals: tuple[GoalTemplate, ...]
    aliases: tuple[str, ...] = field(default_factory=tuple)


def _entry_to_template(entry: TaskRegistryEntry) -> TaskTemplate:
    return TaskTemplate(
        id=entry.id,
        description=entry.description,
        recommended_brain=entry.recommended_brain,
        goals=tuple(
            GoalTemplate(
                kind=goal.kind,
                x=goal.x,
                y=goal.y,
                object_name=goal.object_name,
                standoff=goal.standoff,
            )
            for goal in entry.planner_goals
        ),
        aliases=entry.aliases,
    )


def load_task_templates(
    path: str | Path | None = None,
) -> dict[str, TaskTemplate]:
    del path  # registry is the single source of truth (P3-C3-1)
    return {task_id: _entry_to_template(entry) for task_id, entry in load_task_registry().items()}


def match_template(
    text: str,
    templates: dict[str, TaskTemplate] | None = None,
) -> TaskTemplate | None:
    if templates is not None:
        query = re.sub(r'\s+', ' ', text.strip().lower())
        if not query:
            return None
        for template in templates.values():
            if template.id.lower() == query:
                return template
            for alias in template.aliases:
                norm = re.sub(r'\s+', ' ', alias.strip().lower())
                if norm == query or norm in query or query in norm:
                    return template
        return None

    entry = match_task_entry(text)
    return _entry_to_template(entry) if entry else None


def get_template_by_id(task_id: str) -> TaskTemplate:
    from chassis_common.task_registry import get_task_entry

    return _entry_to_template(get_task_entry(task_id))
