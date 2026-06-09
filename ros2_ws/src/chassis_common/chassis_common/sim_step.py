"""仿真步进：物体走 MuJoCo 物理，底盘/机械臂走运动学。"""

import mujoco

from .actuators import pin_arm_kinematics, zero_arm_actuator_ctrl
from .dynamics import EmbodiedTracker
from .interaction import VirtualGraspState, apply_virtual_grasp
from .kinematics import advance_base_pose, set_base_pose
from .state_reader import read_base_pose


def step_embodied_kinematic(
    model,
    data,
    tracker: EmbodiedTracker,
    dt: float,
    arm: dict[str, float],
    vx: float,
    omega: float,
    virtual_grasp: VirtualGraspState | None = None,
) -> None:
    """一步仿真：底盘运动学积分，机械臂锁定，物体仍由 MuJoCo 物理更新。"""
    x0, y0, yaw0 = read_base_pose(model, data)
    freeze_base = (
        abs(tracker.target_vx) < 0.02
        and abs(tracker.target_steer) < 0.02
    )

    pin_arm_kinematics(
        model,
        data,
        shoulder=arm['arm_shoulder'],
        elbow=arm['arm_elbow'],
        wrist=arm['arm_wrist'],
    )
    zero_arm_actuator_ctrl(model, data)
    data.ctrl[0:3] = 0.0

    mujoco.mj_step(model, data)

    if freeze_base:
        set_base_pose(model, data, x0, y0, yaw0)
    else:
        x1, y1, yaw1 = advance_base_pose(x0, y0, yaw0, vx, omega, dt)
        set_base_pose(model, data, x1, y1, yaw1)

    pin_arm_kinematics(
        model,
        data,
        shoulder=arm['arm_shoulder'],
        elbow=arm['arm_elbow'],
        wrist=arm['arm_wrist'],
    )

    if virtual_grasp is not None and virtual_grasp.active:
        apply_virtual_grasp(model, data, virtual_grasp)
