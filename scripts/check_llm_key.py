#!/usr/bin/env python3
"""检查 LLM API Key 是否已接入（不打印完整 Key）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(os.environ.get('CHASSIS_DEMO_ROOT', Path(__file__).resolve().parents[1]))


def main() -> int:
    os.environ.setdefault('CHASSIS_DEMO_ROOT', str(_project_root()))

    try:
        from embodied_planner.planner_config import load_llm_config, resolve_api_key
    except ImportError:
        print('ERROR: embodied_planner not installed; run colcon build', file=sys.stderr)
        return 1

    cfg_path = _project_root() / 'configs/planner_llm.yaml'
    if not cfg_path.is_file():
        print(f'ERROR: missing {cfg_path}', file=sys.stderr)
        print('  cp configs/planner_llm.yaml.example configs/planner_llm.yaml', file=sys.stderr)
        return 1

    cfg = load_llm_config()
    key = resolve_api_key(cfg.api_key_env)

    print(f'provider: {cfg.provider}')
    print(f'model:    {cfg.model}')
    print(f'base_url: {cfg.base_url}')
    print(f'key_env:  {cfg.api_key_env}')

    if not key:
        print('KEY:      NOT SET')
        print()
        print('接入方式（任选其一）:')
        print('  1) cp configs/planner_llm.local.env.example configs/planner_llm.local.env')
        print('     编辑 DEEPSEEK_API_KEY=sk-...  然后 source scripts/env.sh')
        print('  2) export DEEPSEEK_API_KEY=sk-...')
        print('  3) 在 ~/.claude/settings.json 配置 ANTHROPIC_AUTH_TOKEN（Claude Code DeepSeek）')
        return 1

    masked = key[:7] + '...' + key[-4:] if len(key) > 12 else '***'
    print(f'KEY:      OK ({masked})')

    if cfg.provider != 'ollama':
        try:
            from embodied_planner.llm_planner import LlmPlanner

            result = LlmPlanner(cfg).classify('推红箱')
            print(f'test:     OK -> {result.task_id} ({result.confidence:.2f})')
        except Exception as exc:
            print(f'test:     FAIL -> {exc}', file=sys.stderr)
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
