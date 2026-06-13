"""Template-based task planner backend (C2-1a)."""

from __future__ import annotations

from embodied_msgs.msg import EmbodiedTaskPlan

from embodied_planner.plan_builder import plan_from_template
from embodied_planner.templates import match_template


class TemplatePlanner:
    def plan(self, text: str) -> EmbodiedTaskPlan:
        template = match_template(text)
        if template is None:
            raise ValueError(f'unknown task: {text!r}')
        return plan_from_template(template, source='template', raw_text=text)
