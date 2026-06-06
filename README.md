# 差速底盘仿真 Demo

从 MuJoCo 单机仿真到 ROS 2 HIL（Hardware-in-the-Loop）的递进式学习项目。

## 项目结构

```
.
├── chassis_control.py          # 单机 MuJoCo 仿真（终端 + 3D）
├── cartpole_train.py           # 强化学习入门（独立练习）
├── ros2_sim_venv/              # ROS 2 + MuJoCo 专用虚拟环境
└── ros2_ws/src/
    ├── chassis_common/         # 共享底盘模型与运动学
    ├── chassis_controller/     # C++ 域控节点
    └── chassis_simulation/     # Python 模拟底盘节点 + launch
```

## 架构

```
controller_node (C++)              simulation_node (Python)
  pub /control_cmd  (ChassisCommand) ──►  sub
  sub /chassis_state (Odometry)      ◄──  pub
```

- `/control_cmd`：`chassis_msgs/ChassisCommand`
  - `target_linear_x` / `target_angular_z`：目标速度
  - `emergency_brake`：急停标志
- `/chassis_state`：位姿与**实际**速度反馈（`nav_msgs/Odometry`）
- 加减速度限制在 **simulation_node** 侧执行（可配置 ROS 参数）

## 环境准备

### 1. ROS 2

需要已安装 ROS 2 Lyrical：

```bash
source /opt/ros/lyrical/setup.bash
```

### 2. Python 虚拟环境（simulation_node 专用）

`ros2_sim_venv` 使用 `--system-site-packages`，以便在 venv 内访问系统 ROS 2 的 `rclpy`，同时独立安装 MuJoCo：

```bash
cd /home/changwei/changwei/project

# 首次创建或重建 venv（--copies 确保 entry point 使用 venv 内 Python）
python3 -m venv --copies --system-site-packages ros2_sim_venv
source ros2_sim_venv/bin/activate
source /opt/ros/lyrical/setup.bash
pip install -r requirements.txt
```

> **说明**：ROS 2 的 Python 绑定与系统 Python 版本绑定（当前为 3.14），
> 因此不能用 conda 的 Python 3.12 跑 `rclpy`。`ros2_sim_venv` 就是为解决这个问题而设的。

### 3. 单机脚本（可选 conda 环境）

`chassis_control.py` 和 `cartpole_train.py` 可在 conda `robot` 环境中运行：

```bash
conda activate robot
pip install -r requirements.txt
```

## 编译

```bash
source /opt/ros/lyrical/setup.bash
# 将 venv 的 Python 置于 PATH 前（不要 source activate，否则会干扰 colcon）
export PATH="$(pwd)/ros2_sim_venv/bin:$PATH"
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
```

## 运行

### 单机 MuJoCo 仿真

```bash
python chassis_control.py
```

按键：`W/S` 前进后退，`A/D` 左右转，空格停止，`Q` 退出。

### ROS 2 HIL 双终端启动（推荐）

`simulation_node` 占用终端显示 curses 面板 + 3D 窗口，`controller_node` 需要交互式键盘输入，**必须分两个终端运行**（`ros2 launch` 无法把 stdin 转给子进程）。

**终端 1 — 模拟底盘：**

```bash
source /opt/ros/lyrical/setup.bash
source ros2_ws/install/setup.bash
./scripts/hil_demo.sh
# 或: ros2 launch chassis_simulation hil_demo.launch.py
```

**终端 2 — 域控制器（另开终端）：**

```bash
source /opt/ros/lyrical/setup.bash
source ros2_ws/install/setup.bash
ros2 run chassis_controller controller_node
```

在**终端 2**：

| 按键 | 效果 |
|------|------|
| `w` + 回车 | 目标前进 1.0 m/s（逐渐加速） |
| `s` + 回车 | 目标后退 |
| `a` / `d` | 左转 / 右转 |
| `空格` + 回车 | 正常停车（按减速度平滑减速） |
| `b` + 回车 | 急停（更大减速度快速刹停） |
| `q` + 回车 | 退出 |

在**终端 1**按 `Q` 或 `Ctrl+C` 退出 simulation_node。

### 动力学参数（可选）

```bash
ros2 run chassis_simulation simulation_node --ros-args \
  -p max_linear_accel:=0.5 \
  -p max_linear_decel:=1.0 \
  -p emergency_linear_decel:=3.0
```

## 常见问题

**simulation_node 没有面板输出 / 出现 `^[OA` 乱码**：`ros2 launch` 会劫持终端，curses 面板无法正常工作。launch 已自动切换为 **ROS 日志模式**（约 1Hz 打印状态，收到指令时即时打印）。如需完整 curses 面板，请用 `./scripts/hil_demo.sh` 直接启动。

**OpenGL 0x502 警告**：MuJoCo 3D 窗口需要可用的 OpenGL 环境（显卡驱动 / DISPLAY）。3D 可能无法显示，但物理仿真和 ROS 话题通信不受影响。

**venv 路径错误**：若 `pip` 报「错误的解释器」，说明 venv 是从其他路径迁移来的，按上文步骤重建即可。
