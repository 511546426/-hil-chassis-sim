"""机械臂控制。"""

from .actuators import (
    PhysicsSnapshot,
    apply_arm_display_pose,
    capture_physics_snapshot,
    zero_arm_actuator_ctrl,
)
from .kinematics import apply_velocity_command
from .model import DEFAULT_ELBOW, DEFAULT_SHOULDER, DEFAULT_WRIST


def apply_embodied_actuators(
    model,
    data,
    *,
    vx: float,
    omega: float,
    shoulder: float,
    elbow: float,
    wrist: float,
    gripper: float,
) -> None:
    """写入底盘速度指令；机械臂执行器保持关闭，避免与显示用运动学冲突。"""
    del shoulder, elbow, wrist, gripper
    apply_velocity_command(model, data, vx, omega)
    zero_arm_actuator_ctrl(model, data)


def render_arm_for_display(
    model,
    data,
    *,
    shoulder: float,
    elbow: float,
    wrist: float,
) -> PhysicsSnapshot:
    """保存物理状态 → 应用机械臂显示姿态。调用方在 viewer.sync 后须 restore_physics_snapshot。"""
    snapshot = capture_physics_snapshot(data)
    apply_arm_display_pose(model, data, shoulder, elbow, wrist)
    return snapshot


def default_arm_pose() -> tuple[float, float, float]:
    return DEFAULT_SHOULDER, DEFAULT_ELBOW, DEFAULT_WRIST
