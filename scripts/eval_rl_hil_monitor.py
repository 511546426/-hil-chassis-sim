#!/usr/bin/env python3
"""P3-M3：HIL RL 导航评估 — 订阅 /world_state，检测是否到达 box_red。"""

from __future__ import annotations

import argparse
import math
import sys

import rclpy
from embodied_msgs.msg import EmbodiedWorldState
from rclpy.node import Node


def effective_goal_distance(
    *,
    base_x: float,
    base_y: float,
    goal_x: float,
    goal_y: float,
    standoff: float,
) -> float:
    dx = goal_x - base_x
    dy = goal_y - base_y
    dist = math.hypot(dx, dy)
    if standoff > 0.0 and dist > standoff:
        return dist - standoff
    return dist


class NavEvalMonitor(Node):
    def __init__(
        self,
        *,
        standoff: float,
        arrive_dist: float,
        max_steps: int,
        object_name: str,
    ) -> None:
        super().__init__('eval_rl_hil_monitor')
        self.standoff = standoff
        self.arrive_dist = arrive_dist
        self.max_steps = max_steps
        self.object_name = object_name
        self.steps = 0
        self.done = False
        self.success = False
        self.last_dist: float | None = None

        self.create_subscription(
            EmbodiedWorldState,
            '/world_state',
            self._on_world_state,
            10,
        )
        self.create_timer(0.02, self._on_tick)

    def _lookup_object_xy(self, msg: EmbodiedWorldState) -> tuple[float, float] | None:
        for name, pose in zip(msg.object_names, msg.object_poses):
            if name == self.object_name:
                return float(pose.position.x), float(pose.position.y)
        return None

    def _on_world_state(self, msg: EmbodiedWorldState) -> None:
        if self.done:
            return
        goal = self._lookup_object_xy(msg)
        if goal is None:
            return
        dist = effective_goal_distance(
            base_x=float(msg.base_x),
            base_y=float(msg.base_y),
            goal_x=goal[0],
            goal_y=goal[1],
            standoff=self.standoff,
        )
        self.last_dist = dist
        if dist < self.arrive_dist:
            self.done = True
            self.success = True

    def _on_tick(self) -> None:
        if self.done:
            return
        self.steps += 1
        if self.steps >= self.max_steps:
            self.done = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Monitor HIL RL navigation to box_red')
    parser.add_argument('--standoff', type=float, default=0.35)
    parser.add_argument('--arrive-dist', type=float, default=0.30)
    parser.add_argument('--max-steps', type=int, default=500)
    parser.add_argument('--object-name', default='box_red')
    parser.add_argument('--timeout-sec', type=float, default=15.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rclpy.init()
    node = NavEvalMonitor(
        standoff=args.standoff,
        arrive_dist=args.arrive_dist,
        max_steps=args.max_steps,
        object_name=args.object_name,
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

    dist_text = f'{node.last_dist:.3f}' if node.last_dist is not None else 'N/A'
    print(f'steps={node.steps} dist={dist_text} success={node.success}')
    if node.success:
        print('PASS: RL HIL navigation reached box_red')
        return 0
    print('FAIL: RL HIL navigation did not reach box_red in time')
    return 1


if __name__ == '__main__':
    sys.exit(main())
