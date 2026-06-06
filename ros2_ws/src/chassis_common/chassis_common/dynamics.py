"""小汽车动力学：线速度 + 转向角跟踪，加减速度约束。"""

import math

from .kinematics import steering_to_omega
from .model import MAX_STEER_ANGLE, WHEELBASE


def ramp_toward(
    current: float,
    target: float,
    accel: float,
    decel: float,
    dt: float,
    *,
    emergency: bool = False,
    emergency_decel: float | None = None,
) -> float:
    if emergency:
        target = 0.0
        decel = emergency_decel if emergency_decel is not None else decel * 3.0

    delta = target - current
    if abs(delta) < 1e-9:
        return target

    max_change = (accel if delta > 0 else decel) * dt
    if abs(delta) <= max_change:
        return target
    return current + math.copysign(max_change, delta)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class CarTracker:
    """小汽车速度跟踪器：目标 (vx, steer) → 实际 (vx, omega)。"""

    def __init__(
        self,
        max_linear_accel: float = 0.5,
        max_linear_decel: float = 1.0,
        max_steer_rate: float = 1.2,
        max_angular_accel: float = 2.5,
        max_angular_decel: float = 4.0,
        emergency_linear_decel: float = 3.0,
        emergency_angular_decel: float = 6.0,
        wheelbase: float = WHEELBASE,
        max_steer_angle: float = MAX_STEER_ANGLE,
        pivot_speed_threshold: float = 0.08,
        max_pivot_omega: float = 1.5,
    ):
        self.max_linear_accel = max_linear_accel
        self.max_linear_decel = max_linear_decel
        self.max_steer_rate = max_steer_rate
        self.max_angular_accel = max_angular_accel
        self.max_angular_decel = max_angular_decel
        self.emergency_linear_decel = emergency_linear_decel
        self.emergency_angular_decel = emergency_angular_decel
        self.wheelbase = wheelbase
        self.max_steer_angle = max_steer_angle
        self.pivot_speed_threshold = pivot_speed_threshold
        self.max_pivot_omega = max_pivot_omega

        self.vx_actual = 0.0
        self.steer_actual = 0.0
        self.omega_actual = 0.0

        self.target_vx = 0.0
        self.target_steer = 0.0
        self.emergency_brake = False

    def set_target(
        self,
        vx: float,
        steer: float,
        emergency_brake: bool = False,
    ) -> None:
        self.target_vx = vx
        self.target_steer = _clamp(steer, -self.max_steer_angle, self.max_steer_angle)
        self.emergency_brake = emergency_brake

    def _desired_omega(self, vx: float, steer: float) -> float:
        return steering_to_omega(
            vx,
            steer,
            self.wheelbase,
            pivot_speed_threshold=self.pivot_speed_threshold,
            max_pivot_omega=self.max_pivot_omega,
            max_steer_angle=self.max_steer_angle,
        )

    def step(self, dt: float) -> tuple[float, float]:
        """返回 (vx_actual, omega_actual)。"""
        emergency = self.emergency_brake
        target_vx = 0.0 if emergency else self.target_vx
        target_steer = 0.0 if emergency else self.target_steer

        self.vx_actual = ramp_toward(
            self.vx_actual,
            target_vx,
            self.max_linear_accel,
            self.max_linear_decel,
            dt,
            emergency=emergency,
            emergency_decel=self.emergency_linear_decel,
        )
        self.steer_actual = ramp_toward(
            self.steer_actual,
            target_steer,
            self.max_steer_rate,
            self.max_steer_rate,
            dt,
            emergency=emergency,
            emergency_decel=self.max_steer_rate * 3.0,
        )

        omega_target = self._desired_omega(self.vx_actual, self.steer_actual)
        self.omega_actual = ramp_toward(
            self.omega_actual,
            omega_target,
            self.max_angular_accel,
            self.max_angular_decel,
            dt,
            emergency=emergency,
            emergency_decel=self.emergency_angular_decel,
        )

        if emergency and abs(self.vx_actual) < 1e-4 and abs(self.omega_actual) < 1e-4:
            self.emergency_brake = False
            self.steer_actual = 0.0

        return self.vx_actual, self.omega_actual


class EmbodiedTracker(CarTracker):
    """移动操作臂：底盘 CarTracker + 机械臂关节跟踪。"""

    def __init__(self, max_joint_rate: float = 1.5, **kwargs):
        super().__init__(**kwargs)
        self.max_joint_rate = max_joint_rate

        from .model import DEFAULT_ELBOW, DEFAULT_SHOULDER, DEFAULT_WRIST

        self.shoulder_actual = DEFAULT_SHOULDER
        self.elbow_actual = DEFAULT_ELBOW
        self.wrist_actual = DEFAULT_WRIST
        self.gripper_actual = 0.0

        self.target_shoulder = DEFAULT_SHOULDER
        self.target_elbow = DEFAULT_ELBOW
        self.target_wrist = DEFAULT_WRIST
        self.target_gripper = 0.0

    def set_arm_target(
        self,
        shoulder: float,
        elbow: float,
        wrist: float,
        gripper: float,
    ) -> None:
        self.target_shoulder = shoulder
        self.target_elbow = elbow
        self.target_wrist = wrist
        self.target_gripper = max(0.0, min(1.0, gripper))

    def set_embodied_target(
        self,
        vx: float,
        steer: float,
        shoulder: float,
        elbow: float,
        wrist: float,
        gripper: float,
        emergency_brake: bool = False,
    ) -> None:
        self.set_target(vx, steer, emergency_brake)
        self.set_arm_target(shoulder, elbow, wrist, gripper)

    def step(self, dt: float) -> tuple[float, float, dict[str, float], float]:
        vx, omega = super().step(dt)

        self.shoulder_actual = ramp_toward(
            self.shoulder_actual, self.target_shoulder,
            self.max_joint_rate, self.max_joint_rate, dt,
        )
        self.elbow_actual = ramp_toward(
            self.elbow_actual, self.target_elbow,
            self.max_joint_rate, self.max_joint_rate, dt,
        )
        self.wrist_actual = ramp_toward(
            self.wrist_actual, self.target_wrist,
            self.max_joint_rate, self.max_joint_rate, dt,
        )
        self.gripper_actual = ramp_toward(
            self.gripper_actual, self.target_gripper,
            2.0, 2.0, dt,
        )

        arm = {
            'arm_shoulder': self.shoulder_actual,
            'arm_elbow': self.elbow_actual,
            'arm_wrist': self.wrist_actual,
        }
        return vx, omega, arm, self.gripper_actual


VelocityTracker = CarTracker
