"""SimSession — headless MuJoCo 步进，复用 chassis_common（与 HIL 同源物理）。"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco

from chassis_common import (
    EmbodiedTracker,
    VirtualGraspState,
    initialize_robot_pose,
    load_model,
    read_base_pose,
    read_object_poses,
    step_embodied_kinematic,
)
from chassis_common.kinematics import steering_to_omega


@dataclass
class SimState:
    base_x: float
    base_y: float
    base_yaw: float
    base_vx: float
    base_steer: float
    gripper: float


class SimSession:
    """无 ROS 的仿真会话：model/data/tracker 生命周期与 simulation_node 步进一致。"""

    def __init__(
        self,
        *,
        max_linear_accel: float = 0.5,
        max_linear_decel: float = 1.0,
        max_steer_rate: float = 1.2,
        max_joint_rate: float = 1.5,
    ) -> None:
        self.model = load_model()
        self.data = mujoco.MjData(self.model)
        self.dt = float(self.model.opt.timestep)
        self.tracker = EmbodiedTracker(
            max_linear_accel=max_linear_accel,
            max_linear_decel=max_linear_decel,
            max_steer_rate=max_steer_rate,
            max_joint_rate=max_joint_rate,
        )
        self.virtual_grasp = VirtualGraspState()
        self.reset()

    def reset(self) -> SimState:
        return self.reset_episode()

    def reset_episode(
        self,
        *,
        base_x: float = 0.0,
        base_y: float = 0.0,
        base_yaw: float = 0.0,
    ) -> SimState:
        initialize_robot_pose(self.model, self.data)
        for jname, val in (
            ('slide_x', base_x),
            ('slide_y', base_y),
            ('hinge_z', base_yaw),
        ):
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                self.data.qpos[self.model.jnt_qposadr[jid]] = val
        self.data.qvel[:] = 0.0
        mujoco.mj_forward(self.model, self.data)

        self.tracker = EmbodiedTracker(
            max_linear_accel=self.tracker.max_linear_accel,
            max_linear_decel=self.tracker.max_linear_decel,
            max_steer_rate=self.tracker.max_steer_rate,
            max_joint_rate=self.tracker.max_joint_rate,
        )
        self.virtual_grasp = VirtualGraspState()
        return self.read_state()

    def object_poses(self) -> dict[str, tuple[float, float, float]]:
        poses = read_object_poses(self.model, self.data)
        return {name: (float(x), float(y), float(z)) for name, (x, y, z, *_rest) in poses.items()}

    def step(
        self,
        *,
        target_linear_x: float = 0.0,
        target_steering_angle: float = 0.0,
        arm_shoulder: float | None = None,
        arm_elbow: float | None = None,
        arm_wrist: float | None = None,
        gripper: float | None = None,
        emergency_brake: bool = False,
    ) -> SimState:
        t = self.tracker
        if arm_shoulder is not None:
            t.set_embodied_target(
                target_linear_x,
                target_steering_angle,
                arm_shoulder,
                arm_elbow if arm_elbow is not None else t.elbow_actual,
                arm_wrist if arm_wrist is not None else t.wrist_actual,
                gripper if gripper is not None else t.gripper_actual,
                emergency_brake,
            )
        else:
            t.set_embodied_target(
                target_linear_x,
                target_steering_angle,
                t.shoulder_actual,
                t.elbow_actual,
                t.wrist_actual,
                gripper if gripper is not None else t.gripper_actual,
                emergency_brake,
            )

        vx, omega, arm, _grip = t.step(self.dt)
        step_embodied_kinematic(
            self.model,
            self.data,
            t,
            self.dt,
            arm,
            vx,
            omega,
            self.virtual_grasp,
        )
        return self.read_state()

    def step_velocity_command(
        self,
        target_linear_x: float,
        target_steering_angle: float,
    ) -> SimState:
        """仅底盘速度指令（导航 RL 用）。"""
        return self.step(
            target_linear_x=target_linear_x,
            target_steering_angle=target_steering_angle,
        )

    def read_state(self) -> SimState:
        x, y, yaw = read_base_pose(self.model, self.data)
        t = self.tracker
        return SimState(
            base_x=float(x),
            base_y=float(y),
            base_yaw=float(yaw),
            base_vx=float(t.vx_actual),
            base_steer=float(t.steer_actual),
            gripper=float(t.gripper_actual),
        )

    @staticmethod
    def steering_to_omega(steer: float) -> float:
        return steering_to_omega(steer)
