"""HIL 演示启动。

simulation_node 需要独占终端（curses 面板 + MuJoCo 3D 窗口），
controller_node 需要交互式 stdin，因此二者必须分终端运行。

本 launch 仅启动 simulation_node，并在启动后打印 controller 启动命令。
"""

import os

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration


def _find_project_root() -> str:
    """定位项目根目录（含 ros2_sim_venv/ 的目录）。"""
    if env_root := os.environ.get('CHASSIS_DEMO_ROOT'):
        root = os.path.abspath(env_root)
        if os.path.isfile(os.path.join(root, 'ros2_sim_venv', 'bin', 'python3')):
            return root

    # ros2 launch 从 install/ 加载本文件，需从包 share 目录向上回溯
    share = get_package_share_directory('chassis_simulation')
    for depth in (5, 4, 6):
        root = os.path.abspath(os.path.join(share, *(['..'] * depth)))
        if os.path.isfile(os.path.join(root, 'ros2_sim_venv', 'bin', 'python3')):
            return root

    # 直接运行源码树中的 launch 文件时
    src_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
    )
    if os.path.isfile(os.path.join(src_root, 'ros2_sim_venv', 'bin', 'python3')):
        return src_root

    raise RuntimeError(
        '未找到项目根目录（需要包含 ros2_sim_venv/bin/python3）。\n'
        '可设置环境变量 CHASSIS_DEMO_ROOT=/path/to/project'
    )


def _setup_simulation_node(context, *args, **kwargs):
    project_root = _find_project_root()
    default_venv = os.path.join(project_root, 'ros2_sim_venv', 'bin', 'python3')

    venv_python = LaunchConfiguration('venv_python').perform(context)
    if not venv_python or venv_python == default_venv:
        venv_python = default_venv

    if not os.path.isfile(venv_python):
        raise RuntimeError(
            f'未找到 venv Python: {venv_python}\n'
            f'请先创建虚拟环境: python3 -m venv --copies --system-site-packages '
            f'{os.path.join(project_root, "ros2_sim_venv")}'
        )

    prefix = get_package_prefix('chassis_simulation')
    install_script = os.path.join(prefix, 'lib', 'chassis_simulation', 'simulation_node')
    ws_setup = os.path.join(project_root, 'ros2_ws', 'install', 'setup.bash')

    return [
        ExecuteProcess(
            cmd=[
                venv_python,
                install_script,
                '--ros-args',
                '-r', '__node:=simulation_node',
            ],
            name='simulation_node',
            output='screen',
            emulate_tty=True,
            # launch 下 curses 会乱码，强制走 ROS 日志模式
            additional_env={'SIMULATION_LOG_ONLY': '1'},
        ),
        LogInfo(msg=''),
        LogInfo(msg='=' * 60),
        LogInfo(msg='simulation_node 已在本终端启动（curses + 3D 窗口）'),
        LogInfo(msg=''),
        LogInfo(msg='请【另开一个终端】运行 controller_node 发送控制指令：'),
        LogInfo(msg=''),
        LogInfo(msg='  source /opt/ros/lyrical/setup.bash'),
        LogInfo(msg=f'  source {ws_setup}'),
        LogInfo(msg='  ros2 run chassis_controller controller_node'),
        LogInfo(msg=''),
        LogInfo(msg='在 controller 终端输入 w/s/a/d + 回车控制，q + 回车退出'),
        LogInfo(msg='在本终端按 Q 退出 simulation_node'),
        LogInfo(msg='=' * 60),
        LogInfo(msg=''),
    ]


def generate_launch_description():
    # default_value 在 launch 解析阶段计算，此时 ament index 已可用
    try:
        default_venv = os.path.join(_find_project_root(), 'ros2_sim_venv', 'bin', 'python3')
    except RuntimeError:
        default_venv = ''

    return LaunchDescription([
        DeclareLaunchArgument(
            'venv_python',
            default_value=default_venv,
            description='ros2_sim_venv 中的 Python 解释器路径',
        ),
        OpaqueFunction(function=_setup_simulation_node),
    ])
