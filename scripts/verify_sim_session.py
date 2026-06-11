#!/usr/bin/env python3
"""P3-M0：SimSession 100 步 smoke — 验证 headless 步进可运行。"""

from __future__ import annotations

import sys

from embodied_gym import SimSession


def main() -> int:
    session = SimSession()
    state = session.read_state()
    print(f'init: x={state.base_x:+.3f} y={state.base_y:+.3f} yaw={state.base_yaw:+.3f}')

    for step in range(100):
        state = session.step_velocity_command(target_linear_x=0.5, target_steering_angle=0.0)

    print(
        f'after 100 steps @ vx=0.5: x={state.base_x:+.3f} y={state.base_y:+.3f} '
        f'vx={state.base_vx:+.3f}'
    )
    if state.base_x <= 0.1:
        print('FAIL: expected base_x to increase while driving forward')
        return 1
    print('PASS: SimSession 100-step forward motion')
    return 0


if __name__ == '__main__':
    sys.exit(main())
