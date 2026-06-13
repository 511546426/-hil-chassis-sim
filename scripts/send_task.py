#!/usr/bin/env python3
"""P3-C2：发送任务请求或直发 TaskPlan。"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import rclpy
from embodied_msgs.msg import EmbodiedTaskPlan
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from embodied_planner.template_planner import TemplatePlanner


def _project_root() -> Path:
    return Path(os.environ.get('CHASSIS_DEMO_ROOT', Path(__file__).resolve().parents[1]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Send a task to the embodied planner/agent')
    parser.add_argument('text', help='Natural language or template alias, e.g. "推红箱"')
    parser.add_argument(
        '--direct',
        action='store_true',
        help='Publish /task_plan directly (skip /task_request + planner node)',
    )
    parser.add_argument(
        '--wait-sec',
        type=float,
        default=2.0,
        help='Seconds to wait after publish before exit',
    )
    return parser.parse_args()


class TaskSender(Node):
    def __init__(self) -> None:
        super().__init__('send_task')
        latched = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
        )
        self._pub_plan = self.create_publisher(EmbodiedTaskPlan, '/task_plan', latched)
        self._pub_request = self.create_publisher(String, '/task_request', 10)
        self._planner = TemplatePlanner()

    def send_direct(self, text: str) -> EmbodiedTaskPlan:
        plan = self._planner.plan(text)
        plan.header.stamp = self.get_clock().now().to_msg()
        self._pub_plan.publish(plan)
        return plan

    def send_request(self, text: str) -> None:
        msg = String()
        msg.data = text
        self._pub_request.publish(msg)


def main() -> int:
    args = parse_args()
    os.environ.setdefault('CHASSIS_DEMO_ROOT', str(_project_root()))

    rclpy.init()
    node = TaskSender()
    try:
        if args.direct:
            plan = node.send_direct(args.text)
            template = None
            try:
                from embodied_planner.templates import match_template

                template = match_template(args.text)
            except Exception:
                pass
            brain = template.recommended_brain if template else 'rule'
            print(
                f'Published /task_plan goals={len(plan.goals)} '
                f'recommended_brain={brain} raw={plan.raw_text!r}'
            )
        else:
            node.send_request(args.text)
            print(f'Published /task_request text={args.text!r}')
        time.sleep(args.wait_sec)
    except ValueError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
