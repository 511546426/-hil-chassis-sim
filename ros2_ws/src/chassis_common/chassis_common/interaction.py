"""M5：虚拟抓取 —— 将 freejoint 物体位姿绑定到 gripper。"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco

from .state_reader import read_gripper_position, read_object_poses


@dataclass
class VirtualGraspState:
    active: bool = False
    object_body: str = ''
    offset_x: float = 0.0
    offset_y: float = 0.0
    offset_z: float = 0.0
    hold_z: float = 0.0
    hold_quat: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)


def _freejoint_qpos_slice(model, body_name: str) -> slice | None:
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if bid < 0:
        return None
    jid = int(model.body_jntadr[bid])
    if jid < 0 or int(model.jnt_type[jid]) != int(mujoco.mjtJoint.mjJNT_FREE):
        return None
    adr = int(model.jnt_qposadr[jid])
    return slice(adr, adr + 7)


def _freejoint_qvel_slice(model, body_name: str) -> slice | None:
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if bid < 0:
        return None
    jid = int(model.body_jntadr[bid])
    if jid < 0 or int(model.jnt_type[jid]) != int(mujoco.mjtJoint.mjJNT_FREE):
        return None
    adr = int(model.jnt_dofadr[jid])
    return slice(adr, adr + 6)


def begin_virtual_grasp(
    model,
    data,
    object_body: str,
    *,
    gripper_body: str = 'gripper',
) -> VirtualGraspState:
    """记录 gripper→object 世界系偏移，开启 virtual attach。"""
    if _freejoint_qpos_slice(model, object_body) is None:
        raise ValueError(f'body {object_body!r} has no freejoint')

    poses = read_object_poses(model, data, body_names=(object_body,))
    if object_body not in poses:
        raise ValueError(f'object {object_body!r} not found in scene')

    gx, gy, gz = read_gripper_position(model, data)
    ox, oy, oz, ow, oqx, oqy, oqz = poses[object_body]

    return VirtualGraspState(
        active=True,
        object_body=object_body,
        offset_x=ox - gx,
        offset_y=oy - gy,
        offset_z=oz - gz,
        hold_z=oz,
        hold_quat=(ow, oqx, oqy, oqz),
    )


def apply_virtual_grasp(model, data, state: VirtualGraspState) -> None:
    """若 active，将 object freejoint 写回 gripper + offset。"""
    if not state.active or not state.object_body:
        return

    qpos_sl = _freejoint_qpos_slice(model, state.object_body)
    qvel_sl = _freejoint_qvel_slice(model, state.object_body)
    if qpos_sl is None:
        return

    gx, gy, gz = read_gripper_position(model, data)
    qpos = data.qpos[qpos_sl]
    qpos[0] = gx + state.offset_x
    qpos[1] = gy + state.offset_y
    qpos[2] = state.hold_z
    ow, oqx, oqy, oqz = state.hold_quat
    qpos[3] = ow
    qpos[4] = oqx
    qpos[5] = oqy
    qpos[6] = oqz

    if qvel_sl is not None:
        data.qvel[qvel_sl] = 0.0

    mujoco.mj_forward(model, data)


def end_virtual_grasp(state: VirtualGraspState) -> VirtualGraspState:
    """关闭 attach，保留物体在当前位置。"""
    return VirtualGraspState(active=False)
