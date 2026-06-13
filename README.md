# 具身智能仿真平台

移动操作臂（Mobile Manipulator）MuJoCo 仿真 + ROS 2 HIL 架构。  
**身体**：移动底盘 + 3-DOF 机械臂 + 夹爪  
**环境**：可推动/可抓取的物体（红箱、蓝箱、重箱）

> 包名仍保留 `chassis_*` 历史命名，实质为具身智能体仿真栈。

## 架构

```
controller_node (遥控/未来agent)     simulation_node (身体仿真)
  pub /control_cmd  (EmbodiedCommand) ──►  sub
  sub /chassis_state (Odometry)         ◄──  pub
  sub /arm_state     (JointState)       ◄──  pub
```

## 环境准备

本项目使用 **单一 conda 环境 `embodied`**（Python 3.14，仿真 + ROS + RL）。

```bash
cd ~/changwei/project
conda env create -f environment.yml    # 首次创建
source scripts/env.sh                  # 每次开终端
```

验证：

```bash
python --version                       # 3.14.x
python -c "import rclpy, mujoco, gymnasium"
ros2 --help
```

> 旧版 `ros2_sim_venv` 已弃用，可手动删除：`rm -rf ros2_sim_venv`

## 编译

首次使用或全量编译时：

```bash
source scripts/env.sh
cd ros2_ws
colcon build --symlink-install
```

## 运行

**一键启动（推荐）：**
```bash
source scripts/env.sh
./scripts/hil_demo.sh
```

默认启动 **C++ Agent 自动推红箱**（导航 → 伸臂 → 夹爪 → 倒车 ≥ 0.2 m）。脚本会按需自动编译，后台运行 `simulation_node`（MuJoCo 3D 窗口），日志写入临时目录；Ctrl+C 退出后自动清理。

```bash
./scripts/hil_demo.sh --teleop    # 键盘遥控（开发调试用）
./scripts/hil_demo.sh --help
```

**Planner + brain=auto（自然语言任务，一键）：**
```bash
./scripts/hil_demo_planner.sh --interactive          # 推荐：本终端 REPL 发任务
./scripts/hil_demo_planner.sh --task "推红箱"        # 发一条后 tail 日志
PLANNER_BACKEND=llm_mock ./scripts/hil_demo_planner.sh --interactive
```

REPL 命令：`推红箱` / `去红箱` 直接发送，`reset` 复位，`quit` 退出。

Headless 快速验收（无 3D 窗口）：

```bash
./scripts/m5_smoke_test.sh
```

**手动分终端启动：**
```bash
# 两个终端均先执行
source scripts/env.sh

# 终端 1
ros2 launch chassis_simulation hil_demo.launch.py

# 终端 2
ros2 run chassis_controller controller_node
```

### 按键（即时，无需回车）

| 区域 | 按键 | 功能 |
|------|------|------|
| 底盘 | w/s | 前进/后退 |
| 底盘 | a/d | 转向角 ±（可连按微调） |
| 底盘 | c | 回正 |
| 底盘 | 空格/b | 停车/急停 |
| 机械臂 | i/k | 肩俯仰（抬起/放下） |
| 机械臂 | j/l | 肘偏航（前臂左右摆） |
| 机械臂 | u/o | 腕俯仰（末端屈伸） |
| 机械臂 | g | 切换夹爪开/合 |
| 通用 | q | 退出 |

### 建议任务（具身练习）

1. 移动到底盘红箱 `(2, 0.5)` 附近
2. `i/j/u` 调整机械臂伸向箱子
3. `g` 闭合夹爪，倒车 `s` 尝试拖动
4. 绕过绿色柱子到达蓝箱

## 下一步：接入「大脑」

详见 [docs/BRAIN_ROADMAP.md](docs/BRAIN_ROADMAP.md)
