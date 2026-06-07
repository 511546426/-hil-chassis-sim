#!/usr/bin/env python3
"""agent_node —— 脚本 Agent：导航到红箱并切换伸臂姿态。"""

from __future__ import annotations

import math

import rclpy
from embodied_msgs.msg import EmbodiedCommand, EmbodiedWorldState
from rclpy.node import Node

from .arm_presets import ARM_REACH, ARM_STOW
from .navigation import pure_pursuit

RED_BOX_X = 2.5
RED_BOX_Y = 0.0
ARRIVE_DIST = 0.3


class AgentNode(Node):
    def __init__(self) -> None:
        super().__init__('agent_node')

        self.declare_parameter('target_x', RED_BOX_X)
        self.declare_parameter('target_y', RED_BOX_Y)
        self.declare_parameter('arrive_dist', ARRIVE_DIST)

        self._fallback_x = float(self.get_parameter('target_x').value)
        self._fallback_y = float(self.get_parameter('target_y').value)
        self._arrive_dist = float(self.get_parameter('arrive_dist').value)

        self._world: EmbodiedWorldState | None = None
        self._nav_done = False
        self._logged_arrival = False

        self.create_subscription(
            EmbodiedWorldState, '/world_state', self._on_world_state, 10
        )
        self._pub = self.create_publisher(EmbodiedCommand, '/control_cmd', 10)
        self.create_timer(0.02, self._publish_cmd)
        self._last_cmd_log = ''

        self.get_logger().info(
            f'agent_node 已启动 —— 目标红箱附近 (fallback {self._fallback_x:.1f}, {self._fallback_y:.1f})'
        )

    def _on_world_state(self, msg: EmbodiedWorldState) -> None:
        self._world = msg

    @staticmethod
    def _box_red_xy(world: EmbodiedWorldState) -> tuple[float, float] | None:
        for name, pose in zip(world.object_names, world.object_poses):
            if name == 'box_red':
                return pose.position.x, pose.position.y
        return None

    def _goal_xy(self, world: EmbodiedWorldState) -> tuple[float, float]:
        box = self._box_red_xy(world)
        if box is None:
            return self._fallback_x - 0.35, self._fallback_y
        return box[0] - 0.35, box[1]

    def _distance_to_box(self, world: EmbodiedWorldState) -> float | None:
        box = self._box_red_xy(world)
        if box is None:
            return None
        return math.hypot(box[0] - world.base_x, box[1] - world.base_y)

    def _stuck_at_box(self, world: EmbodiedWorldState, cmd_vx: float) -> bool:
        box_dist = self._distance_to_box(world)
        if box_dist is None:
            return False
        if box_dist <= 0.52 and cmd_vx > 0.05:
            return True
        return (
            cmd_vx > 0.15
            and abs(world.base_vx) < 0.05
            and box_dist < 0.75
        )

    def _publish_cmd(self) -> None:
        cmd = EmbodiedCommand()
        cmd.emergency_brake = False
        cmd.gripper = 0.0

        if self._world is None:
            preset = ARM_STOW
            cmd.target_linear_x = 0.0
            cmd.target_steering_angle = 0.0
        elif self._nav_done:
            preset = ARM_REACH
            cmd.target_linear_x = 0.0
            cmd.target_steering_angle = 0.0
            if not self._logged_arrival:
                w = self._world
                box_dist = self._distance_to_box(w)
                dist_str = f'{box_dist:.2f} m' if box_dist is not None else 'n/a'
                self.get_logger().info(
                    f'已到达红箱附近 (距红箱 {dist_str})，切换 ARM_REACH'
                )
                self._logged_arrival = True
        else:
            preset = ARM_STOW
            w = self._world
            goal_x, goal_y = self._goal_xy(w)
            nav = pure_pursuit(
                w.base_x,
                w.base_y,
                w.base_yaw,
                goal_x,
                goal_y,
                arrive_dist=self._arrive_dist,
            )
            cmd.target_linear_x = nav.target_linear_x
            cmd.target_steering_angle = nav.target_steering_angle
            if nav.arrived or self._stuck_at_box(w, nav.target_linear_x):
                self._nav_done = True

        cmd.arm_shoulder = preset.shoulder
        cmd.arm_elbow = preset.elbow
        cmd.arm_wrist = preset.wrist
        self._pub.publish(cmd)

        summary = (
            f'phase={"REACH" if self._nav_done else "NAV"} '
            f'base[vx={cmd.target_linear_x:+.2f} steer={math.degrees(cmd.target_steering_angle):+.0f}°] '
            f'arm[{cmd.arm_shoulder:+.2f},{cmd.arm_elbow:+.2f},{cmd.arm_wrist:+.2f}]'
        )
        if summary != self._last_cmd_log:
            self.get_logger().info(f'→ cmd {summary}')
            self._last_cmd_log = summary


def main() -> None:
    rclpy.init()
    node = AgentNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
