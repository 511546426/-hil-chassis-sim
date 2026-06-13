#!/usr/bin/env python3
"""P3-C2-3：交互式任务 REPL — 循环发送 /task_request，可选 reset。"""

from __future__ import annotations

import argparse
import os
import readline  # noqa: F401 — enable line editing
import sys
import time
from pathlib import Path

import rclpy
from embodied_msgs.srv import ResetEpisode
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


def _project_root() -> Path:
    return Path(os.environ.get('CHASSIS_DEMO_ROOT', Path(__file__).resolve().parents[1]))


class TaskRepl(Node):
    def __init__(self) -> None:
        super().__init__('task_repl')
        self._pub = self.create_publisher(String, '/task_request', 10)
        self._sim_reset = self.create_client(ResetEpisode, '/sim/reset_episode')
        self._agent_reset = self.create_client(ResetEpisode, '/agent/reset_episode')

    def wait_ready(self, timeout_sec: float = 15.0) -> bool:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if self._pub.get_subscription_count() > 0:
                return True
            rclpy.spin_once(self, timeout_sec=0.1)
        return False

    def send(self, text: str) -> bool:
        msg = String()
        msg.data = text
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if self._pub.get_subscription_count() > 0:
                break
            rclpy.spin_once(self, timeout_sec=0.1)
        if self._pub.get_subscription_count() == 0:
            print('警告: task_planner_node 未订阅 /task_request', file=sys.stderr)
            return False
        self._pub.publish(msg)
        end = time.monotonic() + 0.5
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
        print(f'→ /task_request {text!r}')
        return True

    def reset_episode(self) -> bool:
        req = ResetEpisode.Request()
        for client, name in (
            (self._sim_reset, 'sim'),
            (self._agent_reset, 'agent'),
        ):
            if not client.wait_for_service(timeout_sec=5.0):
                print(f'reset 不可用: {name}', file=sys.stderr)
                return False
            future = client.call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
            if not future.done() or future.result() is None:
                print(f'reset 超时: {name}', file=sys.stderr)
                return False
            if not future.result().success:
                print(f'reset 失败: {name} — {future.result().message}', file=sys.stderr)
                return False
        print('→ episode reset (sim + agent)')
        return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Interactive task REPL for planner HIL')
    parser.add_argument(
        '--wait-ready-sec',
        type=float,
        default=15.0,
        help='Wait for task_planner_node subscription',
    )
    return parser.parse_args()


def print_help() -> None:
    print(
        '命令: 输入自然语言任务直接发送; reset 复位场景; help 帮助; quit 退出\n'
        '示例: 推红箱 | 帮我把红箱子推远一点 | please go to the red box'
    )


def main() -> int:
    args = parse_args()
    os.environ.setdefault('CHASSIS_DEMO_ROOT', str(_project_root()))

    rclpy.init()
    node = TaskRepl()
    try:
        print('Task REPL — 等待 task_planner_node…')
        if not node.wait_ready(timeout_sec=args.wait_ready_sec):
            print('ERROR: planner 未就绪', file=sys.stderr)
            return 1
        print_help()
        while rclpy.ok():
            try:
                line = input('task> ').strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            lower = line.lower()
            if lower in ('q', 'quit', 'exit'):
                break
            if lower == 'help':
                print_help()
                continue
            if lower == 'reset':
                node.reset_episode()
                continue
            node.send(line)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
