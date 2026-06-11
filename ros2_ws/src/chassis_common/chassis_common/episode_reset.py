"""P3-M5：episode 复位 — simulation_node 与 SimSession 共用。"""

from __future__ import annotations

import mujoco

from .dynamics import EmbodiedTracker
from .interaction import VirtualGraspState, end_virtual_grasp
from .model import DEFAULT_ELBOW, DEFAULT_SHOULDER, DEFAULT_WRIST
from .state_reader import initialize_robot_pose


def reset_episode_state(
    model,
    data,
    *,
    base_x: float = 0.0,
    base_y: float = 0.0,
    base_yaw: float = 0.0,
    tracker: EmbodiedTracker | None = None,
    virtual_grasp: VirtualGraspState | None = None,
) -> tuple[EmbodiedTracker, VirtualGraspState]:
    """复位 MuJoCo 场景、tracker 与 virtual grasp（与 /sim/reset_episode 语义一致）。"""
    mujoco.mj_resetData(model, data)
    initialize_robot_pose(
        model,
        data,
        shoulder=DEFAULT_SHOULDER,
        elbow=DEFAULT_ELBOW,
        wrist=DEFAULT_WRIST,
    )
    for jname, val in (
        ('slide_x', base_x),
        ('slide_y', base_y),
        ('hinge_z', base_yaw),
    ):
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            data.qpos[model.jnt_qposadr[jid]] = val
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)

    if tracker is None:
        tracker = EmbodiedTracker()
    else:
        tracker = EmbodiedTracker(
            max_linear_accel=tracker.max_linear_accel,
            max_linear_decel=tracker.max_linear_decel,
            max_steer_rate=tracker.max_steer_rate,
            max_joint_rate=tracker.max_joint_rate,
        )

    if virtual_grasp is None:
        virtual_grasp = VirtualGraspState()
    else:
        virtual_grasp = end_virtual_grasp(virtual_grasp)

    return tracker, virtual_grasp
