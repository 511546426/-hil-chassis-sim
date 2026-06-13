#!/usr/bin/env python3
"""P3-M5：Rule vs RL 批量对照 — 委托 hil_benchmark core 套件。"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from benchmark_lib import project_root


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description='Compare rule / rl / hybrid brains')
    parser.add_argument(
        '--policy',
        type=Path,
        default=root / 'runs/nav_ppo/full/nav_policy.onnx',
    )
    parser.add_argument('--episodes', type=int, default=3)
    parser.add_argument(
        '--output',
        type=Path,
        default=root / 'runs/reports/rule_vs_rl.md',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    os.environ.setdefault('CHASSIS_DEMO_ROOT', str(root))
    python = os.environ.get('CHASSIS_PYTHON', sys.executable)
    cmd = [
        python,
        str(root / 'scripts/hil_benchmark.py'),
        '--suite',
        'core',
        '--episodes',
        str(args.episodes),
        '--policy',
        str(args.policy),
        '--output',
        str(args.output),
    ]
    return subprocess.call(cmd, cwd=root)


if __name__ == '__main__':
    sys.exit(main())
