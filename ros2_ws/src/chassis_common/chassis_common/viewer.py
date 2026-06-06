"""MuJoCo 被动 viewer 相机配置。"""

import mujoco


def setup_follow_camera(
    viewer,
    model,
    *,
    body_name: str = 'robot_base',
    distance: float = 6.0,
    elevation: float = -40.0,
    azimuth: float = 135.0,
) -> None:
    """配置相机跟踪底盘，走出初始视野后仍保持可见。"""
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if body_id < 0:
        raise ValueError(f'未找到 body: {body_name}')

    viewer.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
    viewer.cam.trackbodyid = body_id
    viewer.cam.fixedcamid = -1
    viewer.cam.distance = distance
    viewer.cam.elevation = elevation
    viewer.cam.azimuth = azimuth
