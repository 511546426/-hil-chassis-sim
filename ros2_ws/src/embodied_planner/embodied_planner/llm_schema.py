"""LLM planner JSON schema validation."""

from __future__ import annotations

from pydantic import BaseModel, Field

KNOWN_TASK_IDS = frozenset({
    'push_red_box',
    'nav_to_box_red',
    'nav_to_point',
    'unknown',
})


class LlmTaskClassification(BaseModel):
    task_id: str = Field(..., description='Whitelisted task template id')
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    reason: str = ''

    def validated_task_id(self, *, min_confidence: float = 0.5) -> str:
        tid = self.task_id.strip()
        if tid not in KNOWN_TASK_IDS:
            raise ValueError(f'invalid task_id from LLM: {tid!r}')
        if tid == 'unknown' or self.confidence < min_confidence:
            raise ValueError(
                f'LLM rejected: task_id={tid} confidence={self.confidence}'
            )
        return tid
