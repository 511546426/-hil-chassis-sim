#!/usr/bin/env python3
"""simulation_node —— 模拟底盘 (MuJoCo + ROS 2)

角色: HIL 里的「模拟底盘」
  - sub  /control_cmd   ← 域控发来的 ChassisCommand (CAN 下行等价)
  - pub  /chassis_state ← 底盘位姿/速度反馈 (CAN 上行等价)
  - 内部: 加减速度动力学 + MuJoCo 物理引擎
"""

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
from chassis_common import TIMESTEP, VelocityTracker, apply_velocity_command, load_model
from chassis_msgs.msg import ChassisCommand
from nav_msgs.msg import Odometry
from rclpy.node import Node

model = load_model()
data = mujoco.MjData(model)

_LOG_EVERY_STEPS = 50
_shutdown_requested = False


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
        self.declare_parameter('max_angular_accel', 2.0)
        self.declare_parameter('max_angular_decel', 4.0)
        self.declare_parameter('emergency_linear_decel', 3.0)
        self.declare_parameter('emergency_angular_decel', 6.0)

        self.tracker = VelocityTracker(
            max_linear_accel=self.get_parameter('max_linear_accel').value,
            max_linear_decel=self.get_parameter('max_linear_decel').value,
            max_angular_accel=self.get_parameter('max_angular_accel').value,
            max_angular_decel=self.get_parameter('max_angular_decel').value,
            emergency_linear_decel=self.get_parameter('emergency_linear_decel').value,
            emergency_angular_decel=self.get_parameter('emergency_angular_decel').value,
        )

        self.sub = self.create_subscription(
            ChassisCommand, '/control_cmd', self.on_control_cmd, 10
        )
        self.pub = self.create_publisher(Odometry, '/chassis_state', 10)
        self.pub_timer = self.create_timer(TIMESTEP, self.publish_state)

        self._last_cmd_log = ''

    def on_control_cmd(self, msg: ChassisCommand) -> None:
        self.tracker.set_target(
            msg.target_linear_x,
            msg.target_angular_z,
            msg.emergency_brake,
        )
        summary = (
            f'tgt[vx={msg.target_linear_x:+.2f} w={msg.target_angular_z:+.2f}]'
            f'{" BRAKE" if msg.emergency_brake else ""}'
        )
        if summary != self._last_cmd_log:
            self.get_logger().info(f'← cmd {summary}')
            self._last_cmd_log = summary

    def publish_state(self) -> None:
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_link'

        x, y, yaw = data.qpos[0], data.qpos[1], data.qpos[2]
        msg.pose.pose.position.x = float(x)
        msg.pose.pose.position.y = float(y)
        msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
        msg.pose.pose.orientation.w = math.cos(yaw / 2.0)

        msg.twist.twist.linear.x = float(self.tracker.vx_actual)
        msg.twist.twist.angular.z = float(self.tracker.omega_actual)

        self.pub.publish(msg)

    def log_status(self, step: int) -> None:
        x, y, yaw_deg = data.qpos[0], data.qpos[1], np.degrees(data.qpos[2])
        vx, vy, omega = data.qvel[0], data.qvel[1], data.qvel[2]
        t = self.tracker
        brake = ' BRAKE' if t.emergency_brake else ''
        self.get_logger().info(
            f'state t={step * TIMESTEP:5.1f}s '
            f'tgt[vx={t.target_vx:+5.2f} w={t.target_omega:+5.2f}]{brake} '
            f'act[vx={t.vx_actual:+5.2f} w={t.omega_actual:+5.2f}] '
            f'x={x:+7.3f} y={y:+7.3f} yaw={yaw_deg:+7.1f}° '
            f'vx={vx:+5.2f} vy={vy:+5.2f} w={omega:+5.2f}'
        )


def _use_curses() -> bool:
    if os.environ.get('SIMULATION_LOG_ONLY', '').lower() in ('1', 'true', 'yes'):
        return False
    return (
        sys.stdin.isatty()
        and sys.stdout.isatty()
        and os.environ.get('TERM', '') not in ('', 'dumb')
    )


def _run_loop(node: SimulationNode, stdscr=None) -> None:
    global _shutdown_requested
    _shutdown_requested = False
    _install_signal_handlers()

    use_panel = stdscr is not None
    running = True
    step = 0

    if use_panel:
        curses.curs_set(0)
        stdscr.nodelay(True)

    node.get_logger().info('simulation_node 已启动（加减速度动力学已启用）')
    t = node.tracker
    node.get_logger().info(
        f'动力学参数: lin_accel={t.max_linear_accel} lin_decel={t.max_linear_decel} '
        f'ang_accel={t.max_angular_accel} ang_decel={t.max_angular_decel}'
    )
    if use_panel:
        node.get_logger().info('模式: curses 面板 + MuJoCo 3D（本终端按 Q 退出）')
    else:
        node.get_logger().info('模式: ROS 日志（ros2 launch 推荐）')

    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.distance = 5.0
        viewer.cam.elevation = -30

        while running and not _shutdown_requested and viewer.is_running() and rclpy.ok():
            if use_panel:
                key = stdscr.getch()
                if key == ord('q'):
                    running = False

            vx, omega = node.tracker.step(TIMESTEP)
            apply_velocity_command(data, vx, omega)
            mujoco.mj_step(model, data)
            rclpy.spin_once(node, timeout_sec=0.0)

            if use_panel and step % 5 == 0:
                x, y, yaw_deg = data.qpos[0], data.qpos[1], np.degrees(data.qpos[2])
                stdscr.erase()
                stdscr.addstr(0, 0, f'simulation_node | {step * TIMESTEP:5.1f}s')
                stdscr.addstr(
                    1, 0,
                    f'tgt[vx={t.target_vx:+5.2f} w={t.target_omega:+5.2f}]'
                    f'{" BRAKE" if t.emergency_brake else ""}',
                )
                stdscr.addstr(
                    2, 0,
                    f'act[vx={t.vx_actual:+5.2f} w={t.omega_actual:+5.2f}]',
                )
                stdscr.addstr(3, 0, f'x={x:+7.3f} y={y:+7.3f} yaw={yaw_deg:+7.1f}°')
                stdscr.addstr(4, 0, 'pub→/chassis_state  sub←/control_cmd  Q:退出')
                stdscr.refresh()

            if step > 0 and step % _LOG_EVERY_STEPS == 0:
                node.log_status(step)

            viewer.sync()
            step += 1
            if not _interruptible_sleep(TIMESTEP):
                break

    if _shutdown_requested:
        node.get_logger().info('收到退出信号 (Ctrl+C)，正在关闭...')
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
