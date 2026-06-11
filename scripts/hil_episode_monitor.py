#!/usr/bin/env python3
"""P3-M5：HIL episode 监控 — 支持导航 / 推箱两种判定。"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass

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


@dataclass
class EpisodeMetrics:
    steps: int = 0
    success: bool = False
    nav_dist: float | None = None
    box_push_dist: float = 0.0
    stuck_steps: int = 0


class HilEpisodeMonitor(Node):
    def __init__(
        self,
        *,
        mode: str,
        standoff: float,
        arrive_dist: float,
        push_min_dist: float,
        max_steps: int,
        object_name: str = 'box_red',
    ) -> None:
        super().__init__('hil_episode_monitor')
        self.mode = mode
        self.standoff = standoff
        self.arrive_dist = arrive_dist
        self.push_min_dist = push_min_dist
        self.max_steps = max_steps
        self.object_name = object_name
        self.metrics = EpisodeMetrics()
        self._box_x0: float | None = None
        self._box_y0: float | None = None
        self._done = False

        self.create_subscription(
            EmbodiedWorldState,
            '/world_state',
            self._on_world_state,
            10,
        )
        self.create_timer(0.02, self._on_tick)

    @property
    def done(self) -> bool:
        return self._done

    def _lookup_object_xy(self, msg: EmbodiedWorldState) -> tuple[float, float] | None:
        for name, pose in zip(msg.object_names, msg.object_poses):
            if name == self.object_name:
                return float(pose.position.x), float(pose.position.y)
        return None

    def _on_world_state(self, msg: EmbodiedWorldState) -> None:
        if self._done:
            return

        if abs(float(msg.base_vx)) > 0.15:
            self.metrics.stuck_steps = 0
        elif abs(float(msg.base_vx)) < 0.05:
            self.metrics.stuck_steps += 1

        box = self._lookup_object_xy(msg)
        if box is None:
            return

        if self.mode == 'push':
            if self._box_x0 is None:
                self._box_x0, self._box_y0 = box
                return
            self.metrics.box_push_dist = math.hypot(
                box[0] - self._box_x0, box[1] - self._box_y0
            )
            if self.metrics.box_push_dist >= self.push_min_dist:
                self._done = True
                self.metrics.success = True
            return

        dist = effective_goal_distance(
            base_x=float(msg.base_x),
            base_y=float(msg.base_y),
            goal_x=box[0],
            goal_y=box[1],
            standoff=self.standoff,
        )
        self.metrics.nav_dist = dist
        if dist < self.arrive_dist:
            self._done = True
            self.metrics.success = True

    def _on_tick(self) -> None:
        if self._done:
            return
        self.metrics.steps += 1
        if self.metrics.steps >= self.max_steps:
            self._done = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Monitor one HIL episode')
    parser.add_argument('--mode', choices=('nav', 'push'), default='push')
    parser.add_argument('--standoff', type=float, default=0.35)
    parser.add_argument('--arrive-dist', type=float, default=0.30)
    parser.add_argument('--push-min-dist', type=float, default=0.20)
    parser.add_argument('--max-steps', type=int, default=1500)
    parser.add_argument('--timeout-sec', type=float, default=45.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rclpy.init()
    node = HilEpisodeMonitor(
        mode=args.mode,
        standoff=args.standoff,
        arrive_dist=args.arrive_dist,
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
        metrics = node.metrics
        node.destroy_node()
        rclpy.shutdown()

    dist_text = f'{metrics.nav_dist:.3f}' if metrics.nav_dist is not None else 'N/A'
    print(
        f'steps={metrics.steps} success={metrics.success} '
        f'nav_dist={dist_text} box_push={metrics.box_push_dist:.3f} '
        f'stuck_steps={metrics.stuck_steps}'
    )
    return 0 if metrics.success else 1


if __name__ == '__main__':
    sys.exit(main())
