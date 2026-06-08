#!/usr/bin/env python3
"""simulation_node —— 移动操作臂具身智能体 (MuJoCo + ROS 2)"""

import curses
import math
import os
import signal
import sys
import time

import mujoco
import mujoco.viewer
import numpy as np
import rclpy
from chassis_common import (
    ARENA_HALF,
    TIMESTEP,
    EmbodiedTracker,
    initialize_robot_pose,
    load_model,
    read_base_pose,
    read_base_velocity,
    read_object_poses,
    setup_follow_camera,
    step_embodied_kinematic,
)
from embodied_msgs.msg import EmbodiedCommand, EmbodiedWorldState
from geometry_msgs.msg import Pose
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import JointState

model = load_model()
data = mujoco.MjData(model)

_LOG_EVERY_STEPS = 50
_shutdown_requested = False
_ARM_JOINT_NAMES = ('arm_shoulder', 'arm_elbow', 'arm_wrist')


def _handle_shutdown(signum, frame) -> None:
    global _shutdown_requested
    _shutdown_requested = True


def _install_signal_handlers() -> None:
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)


def _interruptible_sleep(duration: float) -> bool:
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        if _shutdown_requested:
            return False
        time.sleep(min(0.01, deadline - time.monotonic()))
    return not _shutdown_requested


class SimulationNode(Node):
    def __init__(self):
        super().__init__('simulation_node')

        self.declare_parameter('max_linear_accel', 0.5)
        self.declare_parameter('max_linear_decel', 1.0)
        self.declare_parameter('max_steer_rate', 1.2)
        self.declare_parameter('max_joint_rate', 1.5)

        self.tracker = EmbodiedTracker(
            max_linear_accel=self.get_parameter('max_linear_accel').value,
            max_linear_decel=self.get_parameter('max_linear_decel').value,
            max_steer_rate=self.get_parameter('max_steer_rate').value,
            max_joint_rate=self.get_parameter('max_joint_rate').value,
        )

        self.sub = self.create_subscription(
            EmbodiedCommand, '/control_cmd', self.on_control_cmd, 10
        )
        self.pub_odom = self.create_publisher(Odometry, '/chassis_state', 10)
        self.pub_arm = self.create_publisher(JointState, '/arm_state', 10)
        self.pub_world = self.create_publisher(EmbodiedWorldState, '/world_state', 10)
        self.pub_timer = self.create_timer(TIMESTEP, self.publish_state)

        self._last_cmd_log = ''

    def on_control_cmd(self, msg: EmbodiedCommand) -> None:
        self.tracker.set_embodied_target(
            msg.target_linear_x,
            msg.target_steering_angle,
            msg.arm_shoulder,
            msg.arm_elbow,
            msg.arm_wrist,
            msg.gripper,
            msg.emergency_brake,
        )
        summary = (
            f'base[vx={msg.target_linear_x:+.2f} steer={math.degrees(msg.target_steering_angle):+.0f}°] '
            f'arm[{msg.arm_shoulder:+.2f},{msg.arm_elbow:+.2f},{msg.arm_wrist:+.2f}] '
            f'grip={msg.gripper:.1f}'
            f'{" BRAKE" if msg.emergency_brake else ""}'
        )
        if summary != self._last_cmd_log:
            self.get_logger().info(f'← cmd {summary}')
            self._last_cmd_log = summary

    def publish_state(self) -> None:
        t = self.tracker

        odom = Odometry()
        odom.header.stamp = self.get_clock().now().to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'robot_base'
        x, y, yaw = read_base_pose(model, data)
        odom.pose.pose.position.x = float(x)
        odom.pose.pose.position.y = float(y)
        odom.pose.pose.orientation.z = math.sin(yaw / 2.0)
        odom.pose.pose.orientation.w = math.cos(yaw / 2.0)
        odom.twist.twist.linear.x = float(t.vx_actual)
        odom.twist.twist.linear.y = float(t.steer_actual)
        odom.twist.twist.angular.z = float(t.omega_actual)
        self.pub_odom.publish(odom)

        js = JointState()
        js.header.stamp = odom.header.stamp
        js.name = list(_ARM_JOINT_NAMES)
        js.position = [
            float(t.shoulder_actual),
            float(t.elbow_actual),
            float(t.wrist_actual),
        ]
        self.pub_arm.publish(js)

        world = EmbodiedWorldState()
        world.header.stamp = odom.header.stamp
        world.header.frame_id = 'odom'
        world.base_x = float(x)
        world.base_y = float(y)
        world.base_yaw = float(yaw)
        world.base_vx = float(t.vx_actual)
        world.base_steer = float(t.steer_actual)
        world.arm_shoulder = float(t.shoulder_actual)
        world.arm_elbow = float(t.elbow_actual)
        world.arm_wrist = float(t.wrist_actual)
        world.gripper = float(t.gripper_actual)

        object_poses = read_object_poses(model, data)
        world.object_names = list(object_poses.keys())
        world.object_poses = []
        for name in world.object_names:
            ox, oy, oz, ow, oqx, oqy, oqz = object_poses[name]
            pose = Pose()
            pose.position.x = ox
            pose.position.y = oy
            pose.position.z = oz
            pose.orientation.w = ow
            pose.orientation.x = oqx
            pose.orientation.y = oqy
            pose.orientation.z = oqz
            world.object_poses.append(pose)

        world.gripper_touching_object = False
        world.touched_object_name = ''
        self.pub_world.publish(world)

    def log_status(self, step: int) -> None:
        x, y, yaw = read_base_pose(model, data)
        yaw_deg = np.degrees(yaw)
        t = self.tracker
        brake = ' BRAKE' if t.emergency_brake else ''
        blocked = ''
        bvx, bvy, _ = read_base_velocity(model, data)
        if abs(t.vx_actual) > 0.15 and np.hypot(bvx, bvy) < 0.05 and data.ncon > 0:
            blocked = f' [碰撞 ncon={data.ncon}]'
        self.get_logger().info(
            f'state t={step * TIMESTEP:5.1f}s '
            f'base[vx={t.vx_actual:+.2f} steer={math.degrees(t.steer_actual):+.0f}°]{brake} '
            f'arm[{t.shoulder_actual:+.2f},{t.elbow_actual:+.2f},{t.wrist_actual:+.2f}] '
            f'grip={t.gripper_actual:.2f} '
            f'x={x:+6.2f} y={y:+6.2f} yaw={yaw_deg:+5.1f}°{blocked}'
        )


def _use_curses() -> bool:
    if os.environ.get('SIMULATION_LOG_ONLY', '').lower() in ('1', 'true', 'yes'):
        return False
    return sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('TERM', '') not in ('', 'dumb')


def _run_loop(node: SimulationNode, stdscr=None) -> None:
    global _shutdown_requested
    _shutdown_requested = False
    _install_signal_handlers()

    use_panel = stdscr is not None
    running = True
    step = 0
    t = node.tracker

    if use_panel:
        curses.curs_set(0)
        stdscr.nodelay(True)

    node.get_logger().info('simulation_node 已启动 —— 移动操作臂具身智能体')
    node.get_logger().info('场景含可推动物体 (红箱、蓝箱)')
    initialize_robot_pose(model, data)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        setup_follow_camera(viewer, model, distance=8.5, elevation=-30.0)
        node.get_logger().info(f'3D 场地 {ARENA_HALF * 2:.0f}×{ARENA_HALF * 2:.0f} m，相机跟踪 robot_base')

        while running and not _shutdown_requested and viewer.is_running() and rclpy.ok():
            if use_panel and stdscr.getch() == ord('q'):
                running = False

            rclpy.spin_once(node, timeout_sec=0.0)

            vx, omega, arm, grip = t.step(TIMESTEP)
            step_embodied_kinematic(model, data, t, TIMESTEP, arm, vx, omega)

            if use_panel and step % 5 == 0:
                x, y, yaw_deg = read_base_pose(model, data)
                yaw_deg = np.degrees(yaw_deg)
                stdscr.erase()
                stdscr.addstr(0, 0, f'具身仿真 | {step * TIMESTEP:5.1f}s')
                stdscr.addstr(1, 0, f'base vx={t.vx_actual:+.2f} steer={math.degrees(t.steer_actual):+.0f}°')
                stdscr.addstr(2, 0, f'arm  S={arm["arm_shoulder"]:+.2f} E={arm["arm_elbow"]:+.2f} W={arm["arm_wrist"]:+.2f} G={t.gripper_actual:.2f}')
                stdscr.addstr(3, 0, f'x={x:+6.2f} y={y:+6.2f} yaw={yaw_deg:+5.1f}°  Q:退出')
                stdscr.refresh()

            if step > 0 and step % _LOG_EVERY_STEPS == 0:
                node.log_status(step)

            viewer.sync()
            step += 1
            if not _interruptible_sleep(TIMESTEP):
                break

    node.get_logger().info('simulation_node 已退出')


def _run_curses(stdscr) -> None:
    rclpy.init()
    node = SimulationNode()
    try:
        _run_loop(node, stdscr)
    finally:
        node.destroy_node()
        rclpy.shutdown()


def _run_log_only() -> None:
    rclpy.init()
    node = SimulationNode()
    try:
        _run_loop(node, stdscr=None)
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main() -> None:
    try:
        if _use_curses():
            curses.wrapper(_run_curses)
        else:
            _run_log_only()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
