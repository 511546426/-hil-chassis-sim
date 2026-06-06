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

```bash
source /opt/ros/lyrical/setup.bash
python3 -m venv --copies --system-site-packages ros2_sim_venv
source ros2_sim_venv/bin/activate && pip install -r requirements.txt
```

## 编译

首次使用或全量编译时：

```bash
source /opt/ros/lyrical/setup.bash
export PATH="/home/changwei/changwei/project/ros2_sim_venv/bin:$PATH"
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
```

## 运行

**一键启动（推荐）：**
```bash
./scripts/hil_demo.sh
```

脚本会**按需自动编译**（首次运行、或改动了 `chassis_common` / `chassis_simulation` / `chassis_controller` 源码时），然后在当前终端启动 `controller_node`（键盘遥控），并在后台启动 `simulation_node`（弹出 3D 窗口）。日志写入临时文件，可用 `tail -f` 分终端查看；按 `q` 退出或 Ctrl+C 结束后，仿真停止且日志自动删除。

可选参数：

```bash
./scripts/hil_demo.sh --build      # 强制重新编译
./scripts/hil_demo.sh --no-build # 跳过编译检查（适合已确认 install 最新时）
```

**手动分终端启动：**
```bash
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

在 `controller_node` 之上新增 `agent_node`，用 RL/规划替换键盘：
- 观测：`/chassis_state` + `/arm_state` + 物体位姿
- 动作：`EmbodiedCommand`
- `cartpole_train.py` 可迁移为导航/操作 RL 训练脚本
