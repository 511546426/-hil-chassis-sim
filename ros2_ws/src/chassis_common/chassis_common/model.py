"""差速底盘 MuJoCo 模型定义。"""

TIMESTEP = 0.02

CHASSIS_XML = f"""
<mujoco model="chassis">
    <option timestep="{TIMESTEP}"/>

    <worldbody>
        <light diffuse="0.5 0.5 0.5" pos="0 0 3" dir="0 0 -1"/>
        <geom type="plane" size="5 5 0.1" rgba="0.9 0.9 0.9 1"/>

        <body name="chassis" pos="0 0 0.15">
            <joint name="slide_x" type="slide" axis="1 0 0"/>
            <joint name="slide_y" type="slide" axis="0 1 0"/>
            <joint name="hinge_z" type="hinge" axis="0 0 1"/>
            <geom type="box" size="0.3 0.2 0.1" rgba="0.2 0.5 0.8 1"/>
        </body>
    </worldbody>

    <actuator>
        <velocity joint="slide_x" kv="100" ctrllimited="true" ctrlrange="-2 2"/>
        <velocity joint="slide_y" kv="100" ctrllimited="true" ctrlrange="-2 2"/>
        <velocity joint="hinge_z" kv="50"  ctrllimited="true" ctrlrange="-3 3"/>
    </actuator>
</mujoco>
"""


def load_model():
    """从 XML 字符串加载 MuJoCo 模型。"""
    import mujoco

    return mujoco.MjModel.from_xml_string(CHASSIS_XML)
