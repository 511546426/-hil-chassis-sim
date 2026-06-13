"""Load planner LLM config from yaml + environment."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import yaml


def _project_root() -> Path:
    env_root = os.environ.get('CHASSIS_DEMO_ROOT')
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[4]


def _claude_settings_token() -> str:
    """DeepSeek key configured for Claude Code lives in ~/.claude/settings.json."""
    settings_path = Path.home() / '.claude' / 'settings.json'
    if not settings_path.is_file():
        return ''
    try:
        with settings_path.open(encoding='utf-8') as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ''
    env_block = raw.get('env', {})
    if not isinstance(env_block, dict):
        return ''
    token = env_block.get('ANTHROPIC_AUTH_TOKEN') or env_block.get('DEEPSEEK_API_KEY')
    return str(token).strip() if token else ''


def _local_env_token() -> str:
    """Read DEEPSEEK_API_KEY from configs/planner_llm.local.env if present."""
    env_path = _project_root() / 'configs/planner_llm.local.env'
    if not env_path.is_file():
        return ''
    try:
        with env_path.open(encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('export '):
                    line = line[len('export ') :]
                if '=' not in line:
                    continue
                name, _, value = line.partition('=')
                name = name.strip()
                value = value.strip().strip('"').strip("'")
                if name in ('DEEPSEEK_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'OPENAI_API_KEY'):
                    if value:
                        return value
    except OSError:
        return ''
    return ''


def resolve_api_key(api_key_env: str) -> str:
    """Resolve API key from env vars, local env file, or Claude Code settings."""
    key = os.environ.get(api_key_env, '').strip()
    if key:
        return key
    if api_key_env == 'DEEPSEEK_API_KEY':
        for fallback_env in ('DEEPSEEK_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'OPENAI_API_KEY'):
            key = os.environ.get(fallback_env, '').strip()
            if key:
                return key
        key = _local_env_token()
        if key:
            return key
        return _claude_settings_token()
    if api_key_env == 'OPENAI_API_KEY':
        key = os.environ.get('OPENAI_API_KEY', '').strip()
        if key:
            return key
        return _local_env_token()
    return ''


@dataclass(frozen=True)
class LlmPlannerConfig:
    provider: str
    model: str
    base_url: str
    api_key: str
    api_key_env: str
    ollama_host: str
    timeout_sec: float
    min_confidence: float
    temperature: float
    max_tokens: int


def load_llm_config(path: str | Path | None = None) -> LlmPlannerConfig:
    cfg_path = Path(path) if path else _project_root() / 'configs/planner_llm.yaml'
    if not cfg_path.is_file():
        raise FileNotFoundError(
            f'missing {cfg_path}; copy configs/planner_llm.yaml.example'
        )
    with cfg_path.open(encoding='utf-8') as f:
        raw = yaml.safe_load(f) or {}

    openai_raw = raw.get('openai', {}) or {}
    ollama_raw = raw.get('ollama', {}) or {}
    api_key_env = str(openai_raw.get('api_key_env', 'OPENAI_API_KEY'))
    provider = str(raw.get('provider', 'openai'))

    return LlmPlannerConfig(
        provider=provider,
        model=str(raw.get('model', 'gpt-4o-mini')),
        base_url=str(openai_raw.get('base_url', 'https://api.openai.com/v1')),
        api_key=resolve_api_key(api_key_env),
        api_key_env=api_key_env,
        ollama_host=str(ollama_raw.get('host', 'http://127.0.0.1:11434')),
        timeout_sec=float(
            ollama_raw.get('timeout_sec', openai_raw.get('timeout_sec', 30))
        ),
        min_confidence=float(raw.get('min_confidence', 0.5)),
        temperature=float(raw.get('temperature', 0.0)),
        max_tokens=int(raw.get('max_tokens', 256)),
    )
