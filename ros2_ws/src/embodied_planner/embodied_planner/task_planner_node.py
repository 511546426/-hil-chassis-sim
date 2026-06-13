#!/usr/bin/env python3
"""P3-C2：task_planner_node — 自然语言/关键词 → /task_plan。"""

from __future__ import annotations

import rclpy
from embodied_msgs.msg import EmbodiedTaskPlan
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


def make_planner(backend: str, *, llm_config: str = ''):
    if backend == 'template':
        from embodied_planner.template_planner import TemplatePlanner

        return TemplatePlanner()
    if backend == 'llm':
        from embodied_planner.llm_planner import LlmPlanner
        from embodied_planner.planner_config import load_llm_config

        cfg_path = llm_config or None
        return LlmPlanner(load_llm_config(cfg_path) if cfg_path else None)
    if backend == 'llm_mock':
        from embodied_planner.llm_mock_planner import LlmMockPlanner

        return LlmMockPlanner()
    raise ValueError(f'unsupported planner_backend: {backend}')


class TaskPlannerNode(Node):
    def __init__(self) -> None:
        super().__init__('task_planner_node')
        self.declare_parameter('planner_backend', 'template')
        self.declare_parameter('llm_config', '')

        backend = self.get_parameter('planner_backend').value
        llm_config = self.get_parameter('llm_config').value
        self._planner = make_planner(backend, llm_config=llm_config)

        latched = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
        )
        self._pub_plan = self.create_publisher(EmbodiedTaskPlan, '/task_plan', latched)
        self.create_subscription(String, '/task_request', self._on_task_request, 10)
        self.get_logger().info(f'task_planner_node ready (backend={backend})')

    def _on_task_request(self, msg: String) -> None:
        text = msg.data.strip()
        if not text:
            self.get_logger().warning('empty /task_request ignored')
            return
        try:
            plan = self._planner.plan(text)
        except ValueError as exc:
            self.get_logger().error(str(exc))
            return
        except RuntimeError as exc:
            self.get_logger().error(str(exc))
            return
        plan.header.stamp = self.get_clock().now().to_msg()
        self._pub_plan.publish(plan)
        self.get_logger().info(
            f'published plan source={plan.source} brain={plan.recommended_brain} '
            f'goals={len(plan.goals)} raw={plan.raw_text!r}'
        )


def main() -> None:
    rclpy.init()
    node = TaskPlannerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
