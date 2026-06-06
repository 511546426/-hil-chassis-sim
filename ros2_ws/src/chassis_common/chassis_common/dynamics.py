"""底盘速度动力学：加减速度限制与急停。"""

import math


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
    """将 current 向 target 推进一个时间步，受加减速度约束。

    accel / decel 取正数幅值 (m/s² 或 rad/s²)。
    emergency=True 时目标视为 0，并使用 emergency_decel 减速。
    """
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


class VelocityTracker:
    """追踪目标速度，输出受动力学约束的实际速度。"""

    def __init__(
        self,
        max_linear_accel: float = 0.5,
        max_linear_decel: float = 1.0,
        max_angular_accel: float = 2.0,
        max_angular_decel: float = 4.0,
        emergency_linear_decel: float = 3.0,
        emergency_angular_decel: float = 6.0,
    ):
        self.max_linear_accel = max_linear_accel
        self.max_linear_decel = max_linear_decel
        self.max_angular_accel = max_angular_accel
        self.max_angular_decel = max_angular_decel
        self.emergency_linear_decel = emergency_linear_decel
        self.emergency_angular_decel = emergency_angular_decel

        self.vx_actual = 0.0
        self.omega_actual = 0.0

        self.target_vx = 0.0
        self.target_omega = 0.0
        self.emergency_brake = False

    def set_target(self, vx: float, omega: float, emergency_brake: bool = False) -> None:
        self.target_vx = vx
        self.target_omega = omega
        self.emergency_brake = emergency_brake

    def step(self, dt: float) -> tuple[float, float]:
        """推进一个时间步，返回 (vx_actual, omega_actual)。"""
        emergency = self.emergency_brake
        target_vx = 0.0 if emergency else self.target_vx
        target_omega = 0.0 if emergency else self.target_omega

        self.vx_actual = ramp_toward(
            self.vx_actual,
            target_vx,
            self.max_linear_accel,
            self.max_linear_decel,
            dt,
            emergency=emergency,
            emergency_decel=self.emergency_linear_decel,
        )
        self.omega_actual = ramp_toward(
            self.omega_actual,
            target_omega,
            self.max_angular_accel,
            self.max_angular_decel,
            dt,
            emergency=emergency,
            emergency_decel=self.emergency_angular_decel,
        )

        # 已停稳则自动解除急停
        if emergency and abs(self.vx_actual) < 1e-4 and abs(self.omega_actual) < 1e-4:
            self.emergency_brake = False

        return self.vx_actual, self.omega_actual
