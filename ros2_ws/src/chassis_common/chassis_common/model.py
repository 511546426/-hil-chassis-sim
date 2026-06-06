"""移动操作臂（具身智能体）MuJoCo 模型 —— 稳定性优先。"""

TIMESTEP = 0.02
ARENA_HALF = 15.0
WHEELBASE = 0.32
MAX_STEER_ANGLE = 0.52

ARM_LIMITS = {
    'arm_shoulder': (-1.0, 1.0),   # 绕 Y 轴俯仰：抬起/放下
    'arm_elbow': (-1.2, 1.2),      # 绕 Z 轴偏航：前臂左右摆
    'arm_wrist': (-1.2, 1.2),      # 绕 Y 轴俯仰：腕部屈伸
}
GRIPPER_OPEN = 0.0
GRIPPER_CLOSED = 1.0
GRIPPER_FINGER_TRAVEL = 0.03

# 稳定初始姿态（手臂抬起，避免戳地）
DEFAULT_SHOULDER = 0.35
DEFAULT_ELBOW = 0.0
DEFAULT_WRIST = 0.25

ROBOT_XML = f"""
<mujoco model="mobile_manipulator">
    <option timestep="{TIMESTEP}" gravity="0 0 -9.81"/>

    <default>
        <joint damping="0.8" armature="0.05"/>
        <geom friction="0.8 0.1 0.001" condim="3"/>
    </default>

    <visual>
        <headlight diffuse="0.55 0.55 0.55" ambient="0.25 0.25 0.25"/>
        <rgba haze="0.12 0.18 0.28 1"/>
        <global azimuth="135" elevation="-25"/>
    </visual>

    <asset>
        <texture name="grid" type="2d" builtin="checker"
                 rgb1="0.88 0.92 0.96" rgb2="0.72 0.78 0.84" width="512" height="512"/>
        <material name="floor" texture="grid" texrepeat="15 15" reflectance="0.08"/>
        <material name="wall" rgba="0.55 0.60 0.68 0.35"/>
        <material name="base_mat" rgba="0.38 0.40 0.45 1"/>
        <material name="arm_mat" rgba="0.92 0.55 0.12 1"/>
        <material name="gripper_mat" rgba="0.25 0.25 0.28 1"/>
        <material name="pillar" rgba="0.30 0.62 0.42 1"/>
    </asset>

    <worldbody>
        <light pos="0 0 12" dir="0 0 -1" diffuse="0.75 0.75 0.75" castshadow="false"/>
        <light pos="-8 -6 10" dir="0.5 0.5 -1" diffuse="0.35 0.35 0.35" castshadow="false"/>

        <geom name="floor" type="plane" size="{ARENA_HALF} {ARENA_HALF} 0.1" material="floor"/>

        <geom name="wall_px" type="box" pos="{ARENA_HALF} 0 0.6" size="0.15 {ARENA_HALF} 0.6"
              material="wall" contype="0" conaffinity="0"/>
        <geom name="wall_nx" type="box" pos="{-ARENA_HALF} 0 0.6" size="0.15 {ARENA_HALF} 0.6"
              material="wall" contype="0" conaffinity="0"/>
        <geom name="wall_py" type="box" pos="0 {ARENA_HALF} 0.6" size="{ARENA_HALF} 0.15 0.6"
              material="wall" contype="0" conaffinity="0"/>
        <geom name="wall_ny" type="box" pos="0 {-ARENA_HALF} 0.6" size="{ARENA_HALF} 0.15 0.6"
              material="wall" contype="0" conaffinity="0"/>

        <geom name="pillar_1" type="cylinder" pos=" 5  3 0.5" size="0.25 0.5" material="pillar"/>
        <geom name="pillar_2" type="cylinder" pos="-4  6 0.5" size="0.25 0.5" material="pillar"/>

        <!-- 可推物体：单个 freejoint 红箱，远离出生点 -->
        <body name="box_red" pos="2.5 0.0 0.18">
            <freejoint/>
            <geom name="box_red_geom" type="box" size="0.14 0.14 0.14" mass="1.2" rgba="0.85 0.25 0.20 1"/>
        </body>
        <body name="box_blue" pos="-2.0 1.5 0.14">
            <freejoint/>
            <geom name="box_blue_geom" type="box" size="0.11 0.11 0.11" mass="0.8" rgba="0.25 0.45 0.85 1"/>
        </body>

        <!-- 移动操作臂 -->
        <body name="robot_base" pos="0 0 0.12">
            <joint name="slide_x" type="slide" axis="1 0 0"/>
            <joint name="slide_y" type="slide" axis="0 1 0"/>
            <joint name="hinge_z" type="hinge" axis="0 0 1"/>

            <geom name="base_collision" type="cylinder" size="0.20 0.08" material="base_mat"/>
            <geom name="mast" type="cylinder" pos="0 0 0.09" size="0.04 0.05"
                  rgba="0.30 0.32 0.36 1" contype="0" conaffinity="0"/>

            <body name="arm_shoulder_link" pos="0 0 0.14" gravcomp="1">
                <joint name="arm_shoulder" type="hinge" axis="0 1 0" range="-1.0 1.0"/>
                <geom name="link1" type="capsule" fromto="0 0 0 0.20 0 0" size="0.04"
                      material="arm_mat" contype="0" conaffinity="0"/>
                <geom name="link1_col" type="capsule" fromto="0 0 0 0.20 0 0" size="0.035"
                      contype="0" conaffinity="0"/>

                <body name="arm_elbow_link" pos="0.20 0 0" gravcomp="1">
                    <joint name="arm_elbow" type="hinge" axis="0 0 1" range="-1.2 1.2"/>
                    <geom name="link2" type="capsule" fromto="0 0 0 0.16 0 0" size="0.035"
                          material="arm_mat" contype="0" conaffinity="0"/>
                    <geom name="link2_col" type="capsule" fromto="0 0 0 0.16 0 0" size="0.03"
                          contype="0" conaffinity="0"/>

                    <body name="arm_wrist_link" pos="0.16 0 0" gravcomp="1">
                        <joint name="arm_wrist" type="hinge" axis="0 1 0" range="-1.2 1.2"/>
                        <geom name="link3" type="capsule" fromto="0 0 0 0.10 0 0" size="0.03"
                              material="arm_mat" contype="0" conaffinity="0"/>

                        <body name="gripper" pos="0.10 0 0" gravcomp="1">
                            <geom name="palm" type="box" size="0.02 0.04 0.02"
                                  material="gripper_mat" contype="0" conaffinity="0"/>
                            <geom name="finger_l" type="box" pos="0.02 0.035 0" size="0.015 0.01 0.025"
                                  material="gripper_mat" contype="0" conaffinity="0"/>
                            <geom name="finger_r" type="box" pos="0.02 -0.035 0" size="0.015 0.01 0.025"
                                  material="gripper_mat" contype="0" conaffinity="0"/>
                        </body>
                    </body>
                </body>
            </body>
        </body>
    </worldbody>

    <!-- 禁用底盘与机械臂自碰撞 -->
    <contact>
        <exclude body1="robot_base" body2="arm_shoulder_link"/>
        <exclude body1="robot_base" body2="arm_elbow_link"/>
        <exclude body1="robot_base" body2="arm_wrist_link"/>
        <exclude body1="robot_base" body2="gripper"/>
        <exclude body1="arm_shoulder_link" body2="arm_elbow_link"/>
        <exclude body1="arm_elbow_link" body2="arm_wrist_link"/>
        <exclude body1="arm_wrist_link" body2="gripper"/>
    </contact>

    <actuator>
        <velocity name="act_slide_x" joint="slide_x" kv="80" ctrllimited="true" ctrlrange="-2 2"/>
        <velocity name="act_slide_y" joint="slide_y" kv="80" ctrllimited="true" ctrlrange="-2 2"/>
        <velocity name="act_hinge_z" joint="hinge_z" kv="40" ctrllimited="true" ctrlrange="-3 3"/>
        <position name="act_arm_shoulder" joint="arm_shoulder" kp="20" kv="6" ctrlrange="-1.0 1.0"/>
        <position name="act_arm_elbow"    joint="arm_elbow"    kp="20" kv="6" ctrlrange="-1.2 1.2"/>
        <position name="act_arm_wrist"    joint="arm_wrist"    kp="15" kv="5" ctrlrange="-1.2 1.2"/>
    </actuator>
</mujoco>
"""

CHASSIS_XML = ROBOT_XML


def load_model():
    import mujoco
    return mujoco.MjModel.from_xml_string(ROBOT_XML)
