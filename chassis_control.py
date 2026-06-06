"""移动操作臂具身智能体 —— 单机 MuJoCo 仿真"""

import math
import sys
import time
from pathlib import Path

import curses
import glfw
import mujoco
import mujoco.viewer
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / 'ros2_ws' / 'src' / 'chassis_common'))
from chassis_common import (  # noqa: E402
    MAX_STEER_ANGLE,
    TIMESTEP,
    EmbodiedTracker,
    apply_embodied_actuators,
    initialize_robot_pose,
    load_model,
    read_base_pose,
    render_arm_for_display,
    restore_physics_snapshot,
    setup_follow_camera,
)

STEER_STEP = 0.08
ARM_STEP = 0.12

model = load_model()
data = mujoco.MjData(model)


def apply_key(t: EmbodiedTracker, cmd, keycode):
    if keycode in (ord('w'), glfw.KEY_W):
        t.set_target(1.0, t.target_steer)
    elif keycode in (ord('s'), glfw.KEY_S):
        t.set_target(-1.0, t.target_steer)
    elif keycode in (ord('a'), glfw.KEY_A):
        t.set_target(t.target_vx, min(t.target_steer + STEER_STEP, MAX_STEER_ANGLE))
    elif keycode in (ord('d'), glfw.KEY_D):
        t.set_target(t.target_vx, max(t.target_steer - STEER_STEP, -MAX_STEER_ANGLE))
    elif keycode in (ord('c'), glfw.KEY_C):
        t.set_target(t.target_vx, 0.0)
    elif keycode in (ord('i'), glfw.KEY_I):
        t.set_arm_target(t.target_shoulder + ARM_STEP, t.target_elbow, t.target_wrist, t.target_gripper)
    elif keycode in (ord('k'), glfw.KEY_K):
        t.set_arm_target(t.target_shoulder - ARM_STEP, t.target_elbow, t.target_wrist, t.target_gripper)
    elif keycode in (ord('j'), glfw.KEY_J):
        t.set_arm_target(t.target_shoulder, t.target_elbow + ARM_STEP, t.target_wrist, t.target_gripper)
    elif keycode in (ord('l'), glfw.KEY_L):
        t.set_arm_target(t.target_shoulder, t.target_elbow - ARM_STEP, t.target_wrist, t.target_gripper)
    elif keycode in (ord('u'), glfw.KEY_U):
        t.set_arm_target(t.target_shoulder, t.target_elbow, t.target_wrist + ARM_STEP, t.target_gripper)
    elif keycode in (ord('o'), glfw.KEY_O):
        t.set_arm_target(t.target_shoulder, t.target_elbow, t.target_wrist - ARM_STEP, t.target_gripper)
    elif keycode in (ord('g'), glfw.KEY_G):
        g = 0.0 if t.target_gripper > 0.5 else 1.0
        t.set_arm_target(t.target_shoulder, t.target_elbow, t.target_wrist, g)
    elif keycode in (ord(' '), glfw.KEY_SPACE):
        t.set_embodied_target(0, 0, t.target_shoulder, t.target_elbow, t.target_wrist, t.target_gripper)
    elif keycode in (ord('b'), glfw.KEY_B):
        t.set_embodied_target(0, 0, -0.3, -0.8, 0, 0, emergency_brake=True)
    elif keycode in (ord('q'), glfw.KEY_Q):
        cmd['running'] = False


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    tracker = EmbodiedTracker()
    cmd = {'running': True}
    step = 0

    def on_key(k):
        apply_key(tracker, cmd, k)

    initialize_robot_pose(model, data)
    with mujoco.viewer.launch_passive(model, data, key_callback=on_key) as viewer:
        setup_follow_camera(viewer, model, distance=7.0, elevation=-35.0)
        while cmd['running'] and viewer.is_running():
            k = stdscr.getch()
            if k != -1:
                apply_key(tracker, cmd, k)

            vx, omega, arm, grip = tracker.step(TIMESTEP)
            apply_embodied_actuators(model, data, vx=vx, omega=omega,
                                     shoulder=arm['arm_shoulder'], elbow=arm['arm_elbow'],
                                     wrist=arm['arm_wrist'], gripper=grip)
            mujoco.mj_step(model, data)
            arm_snapshot = render_arm_for_display(
                model, data,
                shoulder=arm['arm_shoulder'],
                elbow=arm['arm_elbow'],
                wrist=arm['arm_wrist'],
            )

            if step % 5 == 0:
                x, y, yaw = read_base_pose(model, data)
                yaw = np.degrees(yaw)
                t = tracker
                stdscr.erase()
                stdscr.addstr(0, 0, f'具身仿真 {step * TIMESTEP:5.1f}s')
                stdscr.addstr(1, 0, f'base vx={t.vx_actual:+.2f} steer={math.degrees(t.steer_actual):+.0f}°')
                stdscr.addstr(2, 0, f'arm S={arm["arm_shoulder"]:+.2f} E={arm["arm_elbow"]:+.2f} W={arm["arm_wrist"]:+.2f} G={t.gripper_actual:.2f}')
                stdscr.addstr(3, 0, f'x={x:+6.2f} y={y:+6.2f} yaw={yaw:+5.1f}°')
                stdscr.addstr(4, 0, '底盘:WSAD  臂:IK肩升降 JL肘左右 UO腕  G夹爪  空格停 Q退')
                stdscr.refresh()
            viewer.sync()
            restore_physics_snapshot(data, arm_snapshot)
            step += 1
            time.sleep(TIMESTEP)


if __name__ == '__main__':
    curses.wrapper(main)
    print('\n仿真结束')
