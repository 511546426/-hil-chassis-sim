"""LLM-backed task planner: natural language -> task_id -> EmbodiedTaskPlan."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from embodied_msgs.msg import EmbodiedTaskPlan

from embodied_planner.llm_schema import LlmTaskClassification
from embodied_planner.plan_builder import plan_from_template
from embodied_planner.planner_config import LlmPlannerConfig, load_llm_config
from embodied_planner.templates import load_task_templates


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fence = re.search(r'```(?:json)?\s*(.*?)\s*```', stripped, re.DOTALL | re.IGNORECASE)
    if fence:
        stripped = fence.group(1).strip()
    return json.loads(stripped)


def build_system_prompt() -> str:
    lines = [
        'You are a task classifier for a mobile manipulator.',
        'Map user instructions to exactly ONE task_id from the whitelist.',
        'You do NOT control the robot. Output JSON only, no markdown.',
        '',
        'Whitelist:',
    ]
    for tpl in load_task_templates().values():
        lines.append(f'- {tpl.id}: {tpl.description}')
    lines += [
        '',
        'Output schema:',
        '{"task_id":"<id|unknown>","confidence":0.0,"reason":"..."}',
        '',
        'Examples:',
        '- "推红箱" -> {"task_id":"push_red_box","confidence":0.95,"reason":"push"}',
        '- "go to the red box" -> {"task_id":"nav_to_box_red","confidence":0.9,"reason":"nav"}',
        '- "dance" -> {"task_id":"unknown","confidence":0.0,"reason":"unsupported"}',
    ]
    return '\n'.join(lines)


class LlmPlanner:
    def __init__(self, config: LlmPlannerConfig | None = None) -> None:
        self.config = config or load_llm_config()
        self._templates = load_task_templates()

    def _call_openai_compat(self, user_text: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                'openai package required for LLM planner; pip install openai'
            ) from exc

        if not self.config.api_key:
            raise RuntimeError(
                f'API key missing; set env {self.config.api_key_env}'
            )

        client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout_sec,
        )
        kwargs: dict[str, Any] = {
            'model': self.config.model,
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
            'messages': [
                {'role': 'system', 'content': build_system_prompt()},
                {'role': 'user', 'content': user_text},
            ],
        }
        try:
            kwargs['response_format'] = {'type': 'json_object'}
            resp = client.chat.completions.create(**kwargs)
        except Exception:
            kwargs.pop('response_format', None)
            resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or '{}'

    def _call_ollama(self, user_text: str) -> str:
        payload = {
            'model': self.config.model,
            'stream': False,
            'format': 'json',
            'messages': [
                {'role': 'system', 'content': build_system_prompt()},
                {'role': 'user', 'content': user_text},
            ],
            'options': {'temperature': self.config.temperature},
        }
        req = urllib.request.Request(
            f'{self.config.ollama_host.rstrip("/")}/api/chat',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_sec) as resp:
                body = json.loads(resp.read().decode('utf-8'))
        except urllib.error.URLError as exc:
            raise RuntimeError(f'Ollama request failed: {exc}') from exc
        return body.get('message', {}).get('content', '{}')

    def classify(self, text: str) -> LlmTaskClassification:
        if self.config.provider == 'ollama':
            raw = self._call_ollama(text)
        elif self.config.provider == 'openai':
            raw = self._call_openai_compat(text)
        else:
            raise ValueError(f'unsupported LLM provider: {self.config.provider}')
        data = _extract_json(raw)
        return LlmTaskClassification.model_validate(data)

    def plan(self, text: str) -> EmbodiedTaskPlan:
        classification = self.classify(text)
        task_id = classification.validated_task_id(
            min_confidence=self.config.min_confidence
        )
        template = self._templates.get(task_id)
        if template is None:
            raise ValueError(f'template missing for task_id={task_id}')
        return plan_from_template(template, source='llm', raw_text=text)
