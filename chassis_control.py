"""差速底盘仿真 —— curses 终端控制 + MuJoCo 3D 窗口

架构：curses(终端键盘+面板) + MuJoCo viewer(3D渲染)
内置加减速度动力学，与 ROS 2 simulation_node 行为一致。
"""

import sys
import time
from pathlib import Path

import curses
import glfw
import mujoco
import mujoco.viewer
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / 'ros2_ws' / 'src' / 'chassis_common'))
from chassis_common import TIMESTEP, VelocityTracker, apply_velocity_command, load_model  # noqa: E402

model = load_model()
data = mujoco.MjData(model)


def apply_key(tracker: VelocityTracker, cmd, keycode):
    """统一处理终端 / 3D 窗口按键。"""
    if keycode in (ord('w'), glfw.KEY_W):
        tracker.set_target(1.0, tracker.target_omega)
    elif keycode in (ord('s'), glfw.KEY_S):
        tracker.set_target(-1.0, tracker.target_omega)
    elif keycode in (ord('a'), glfw.KEY_A):
        tracker.set_target(tracker.target_vx, 2.0)
    elif keycode in (ord('d'), glfw.KEY_D):
        tracker.set_target(tracker.target_vx, -2.0)
    elif keycode in (ord(' '), glfw.KEY_SPACE):
        tracker.set_target(0.0, 0.0)
    elif keycode in (ord('b'), glfw.KEY_B):
        tracker.set_target(0.0, 0.0, emergency_brake=True)
    elif keycode in (ord('q'), glfw.KEY_Q):
        cmd['running'] = False


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)

    tracker = VelocityTracker()
    cmd = {'running': True}
    step = 0

    def on_viewer_key(keycode):
        apply_key(tracker, cmd, keycode)

    with mujoco.viewer.launch_passive(model, data, key_callback=on_viewer_key) as viewer:
        viewer.cam.distance = 5.0
        viewer.cam.elevation = -30

        while cmd['running'] and viewer.is_running():
            key = stdscr.getch()
            if key != -1:
                apply_key(tracker, cmd, key)

            vx, omega = tracker.step(TIMESTEP)
            apply_velocity_command(data, vx, omega)
            mujoco.mj_step(model, data)

            if step % 5 == 0:
                x, y, yaw_deg = data.qpos[0], data.qpos[1], np.degrees(data.qpos[2])
                vx_w, vy_w, omega_w = data.qvel[0], data.qvel[1], data.qvel[2]
                brake = ' BRAKE' if tracker.emergency_brake else ''

                stdscr.erase()
                stdscr.addstr(0, 0, f'底盘仿真 {step * TIMESTEP:5.1f}s')
                stdscr.addstr(
                    1, 0,
                    f'tgt[vx={tracker.target_vx:+5.2f} w={tracker.target_omega:+5.2f}]{brake}',
                )
                stdscr.addstr(
                    2, 0,
                    f'act[vx={tracker.vx_actual:+5.2f} w={tracker.omega_actual:+5.2f}]  '
                    f'x={x:+7.3f} y={y:+7.3f} yaw={yaw_deg:+7.1f}°',
                )
                stdscr.addstr(
                    3, 0,
                    'W/S/A/D:移动 空格:停车  B:急停  Q:退出',
                )
                stdscr.refresh()

            viewer.sync()
            step += 1
            time.sleep(TIMESTEP)


if __name__ == '__main__':
    curses.wrapper(main)
    print('\n仿真结束')
