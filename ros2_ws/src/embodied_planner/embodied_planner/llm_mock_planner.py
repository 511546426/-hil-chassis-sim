"""Deterministic LLM mock for offline tests and HIL without API keys."""

from __future__ import annotations

from embodied_msgs.msg import EmbodiedTaskPlan

from embodied_planner.llm_schema import LlmTaskClassification
from embodied_planner.plan_builder import plan_from_template
from embodied_planner.templates import load_task_templates, match_template


class LlmMockPlanner:
    """Template match first, then lightweight keyword heuristics."""

    def __init__(self) -> None:
        self._templates = load_task_templates()

    def classify(self, text: str) -> LlmTaskClassification:
        tpl = match_template(text)
        if tpl is not None:
            return LlmTaskClassification(
                task_id=tpl.id,
                confidence=0.99,
                reason='mock template match',
            )
        lowered = text.lower()
        if 'push' in lowered or '推' in text:
            return LlmTaskClassification(
                task_id='push_red_box',
                confidence=0.8,
                reason='mock keyword push',
            )
        if 'box' in lowered or '红箱' in text or 'red box' in lowered:
            return LlmTaskClassification(
                task_id='nav_to_box_red',
                confidence=0.8,
                reason='mock keyword nav box',
            )
        if 'point' in lowered or '坐标' in text:
            return LlmTaskClassification(
                task_id='nav_to_point',
                confidence=0.75,
                reason='mock keyword nav point',
            )
        return LlmTaskClassification(
            task_id='unknown',
            confidence=0.0,
            reason='mock unknown',
        )

    def plan(self, text: str) -> EmbodiedTaskPlan:
        classification = self.classify(text)
        task_id = classification.validated_task_id(min_confidence=0.5)
        template = self._templates[task_id]
        return plan_from_template(template, source='llm_mock', raw_text=text)
