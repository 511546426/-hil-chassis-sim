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


def _default_python() -> str:
    if env_py := os.environ.get('CHASSIS_PYTHON'):
        return env_py
    home = os.path.expanduser('~')
    return os.path.join(home, 'miniconda3', 'envs', 'embodied', 'bin', 'python')


def _find_project_root() -> str:
    """定位项目根目录（含 scripts/env.sh 或 environment.yml）。"""
    if env_root := os.environ.get('CHASSIS_DEMO_ROOT'):
        root = os.path.abspath(env_root)
        if os.path.isfile(os.path.join(root, 'scripts', 'env.sh')):
            return root

    share = get_package_share_directory('chassis_simulation')
    for depth in (5, 4, 6):
        root = os.path.abspath(os.path.join(share, *(['..'] * depth)))
        if os.path.isfile(os.path.join(root, 'scripts', 'env.sh')):
            return root

    src_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
    )
    if os.path.isfile(os.path.join(src_root, 'scripts', 'env.sh')):
        return src_root

    raise RuntimeError(
        '未找到项目根目录（需要包含 scripts/env.sh）。\n'
        '可设置环境变量 CHASSIS_DEMO_ROOT=/path/to/project'
    )


def _setup_simulation_node(context, *args, **kwargs):
    project_root = _find_project_root()
    default_python = _default_python()

    python_exe = LaunchConfiguration('python_exe').perform(context)
    if not python_exe or python_exe == default_python:
        python_exe = default_python

    if not os.path.isfile(python_exe):
        raise RuntimeError(
            f'未找到 Python: {python_exe}\n'
            '请先创建统一环境: conda env create -f environment.yml\n'
            '或: source scripts/env.sh'
        )

    prefix = get_package_prefix('chassis_simulation')
    install_script = os.path.join(prefix, 'lib', 'chassis_simulation', 'simulation_node')
    ws_setup = os.path.join(project_root, 'ros2_ws', 'install', 'setup.bash')

    return [
        ExecuteProcess(
            cmd=[
                python_exe,
                install_script,
                '--ros-args',
                '-r', '__node:=simulation_node',
            ],
            name='simulation_node',
            output='screen',
            emulate_tty=True,
            additional_env={'SIMULATION_LOG_ONLY': '1'},
        ),
        LogInfo(msg=''),
        LogInfo(msg='=' * 60),
        LogInfo(msg='simulation_node 已在本终端启动（curses + 3D 窗口）'),
        LogInfo(msg=''),
        LogInfo(msg='请【另开一个终端】运行 controller_node 发送控制指令：'),
        LogInfo(msg=''),
        LogInfo(msg='  source scripts/env.sh   # 项目根目录下'),
        LogInfo(msg='  ros2 run chassis_controller controller_node'),
        LogInfo(msg=''),
        LogInfo(msg='在 controller 终端: 底盘 wsad  臂 ik肩 jl左右 uo腕  g夹爪  q退出（无需回车）'),
        LogInfo(msg='在本终端按 Q 退出 simulation_node'),
        LogInfo(msg='=' * 60),
        LogInfo(msg=''),
    ]


def generate_launch_description():
    try:
        default_python = _default_python()
    except RuntimeError:
        default_python = ''

    return LaunchDescription([
        DeclareLaunchArgument(
            'python_exe',
            default_value=default_python,
            description='embodied conda 环境中的 Python 解释器路径',
        ),
        OpaqueFunction(function=_setup_simulation_node),
    ])
