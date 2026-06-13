#!/usr/bin/env python3
"""Quick test: DeepSeek / LLM task classification (no ROS)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(os.environ.get('CHASSIS_DEMO_ROOT', Path(__file__).resolve().parents[1]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Test LLM task classification')
    parser.add_argument('texts', nargs='*', default=[
        '帮我把红箱子推远一点',
        'go to the red box',
        '跳个舞',
    ])
    parser.add_argument('--backend', choices=('llm', 'llm_mock'), default='llm')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.environ.setdefault('CHASSIS_DEMO_ROOT', str(_project_root()))

    if args.backend == 'llm_mock':
        from embodied_planner.llm_mock_planner import LlmMockPlanner

        planner = LlmMockPlanner()
        classify = planner.classify
    else:
        from embodied_planner.llm_planner import LlmPlanner
        from embodied_planner.planner_config import load_llm_config, resolve_api_key

        cfg = load_llm_config()
        if not resolve_api_key(cfg.api_key_env):
            print(
                'ERROR: no API key. Set DEEPSEEK_API_KEY or configure ~/.claude/settings.json',
                file=sys.stderr,
            )
            return 1
        planner = LlmPlanner(cfg)
        classify = planner.classify

    failed = 0
    for text in args.texts:
        try:
            result = classify(text)
            print(f'OK  {text!r} -> {result.task_id} ({result.confidence:.2f}) {result.reason}')
        except Exception as exc:
            failed += 1
            print(f'FAIL {text!r} -> {exc}', file=sys.stderr)

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
