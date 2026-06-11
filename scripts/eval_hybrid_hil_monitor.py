#!/usr/bin/env python3
"""P3-M4：HIL Hybrid 推箱 monitor — 检测 box_red 位移 ≥ push_min_dist。"""

from __future__ import annotations

import argparse
import math
import sys

import rclpy
from embodied_msgs.msg import EmbodiedWorldState
from rclpy.node import Node


class HybridPushMonitor(Node):
    def __init__(self, *, push_min_dist: float, max_steps: int) -> None:
        super().__init__('eval_hybrid_hil_monitor')
        self.push_min_dist = push_min_dist
        self.max_steps = max_steps
        self.steps = 0
        self.done = False
        self.success = False
        self.box_x0: float | None = None
        self.box_y0: float | None = None
        self.last_push_dist = 0.0
        self.last_phase = ''

        self.create_subscription(
            EmbodiedWorldState,
            '/world_state',
            self._on_world_state,
            10,
        )
        self.create_timer(0.02, self._on_tick)

    def _lookup_box(self, msg: EmbodiedWorldState) -> tuple[float, float] | None:
        for name, pose in zip(msg.object_names, msg.object_poses):
            if name == 'box_red':
                return float(pose.position.x), float(pose.position.y)
        return None

    def _on_world_state(self, msg: EmbodiedWorldState) -> None:
        if self.done:
            return
        box = self._lookup_box(msg)
        if box is None:
            return
        if self.box_x0 is None:
            self.box_x0, self.box_y0 = box
            return
        self.last_push_dist = math.hypot(box[0] - self.box_x0, box[1] - self.box_y0)
        if self.last_push_dist >= self.push_min_dist:
            self.done = True
            self.success = True

    def _on_tick(self) -> None:
        if self.done:
            return
        self.steps += 1
        if self.steps >= self.max_steps:
            self.done = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Monitor hybrid push-box in HIL')
    parser.add_argument('--push-min-dist', type=float, default=0.20)
    parser.add_argument('--max-steps', type=int, default=1500)
    parser.add_argument('--timeout-sec', type=float, default=45.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rclpy.init()
    node = HybridPushMonitor(
        push_min_dist=args.push_min_dist,
        max_steps=args.max_steps,
    )
    deadline = node.get_clock().now().nanoseconds + int(args.timeout_sec * 1e9)
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.05)
            if node.get_clock().now().nanoseconds > deadline:
                break
    finally:
        node.destroy_node()
        rclpy.shutdown()

    print(
        f'steps={node.steps} box_push={node.last_push_dist:.3f} success={node.success}'
    )
    if node.success:
        print('PASS: hybrid HIL push-box displacement >= push_min_dist')
        return 0
    print('FAIL: hybrid HIL push-box did not reach push_min_dist')
    return 1


if __name__ == '__main__':
    sys.exit(main())
