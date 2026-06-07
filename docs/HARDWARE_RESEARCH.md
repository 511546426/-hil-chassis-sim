# 硬件调研清单（第二期 M8 填写）

> **何时写**：第二期软件验收（推箱 ≥ 0.2 m）通过后。  
> **规格说明**：[PHASE2_CPP_IMPLEMENTATION_GUIDE.md §13.2](./PHASE2_CPP_IMPLEMENTATION_GUIDE.md#132-下一步硬件调研清单必做)

---

## A. 差速移动底盘

| 调研项 | 说明 | 结论 |
|--------|------|------|
| 候选平台 | 带 encoders、可接 ROS 2 的差速小车 / AGV 套件 | |
| 驱动接口 | `cmd_vel` 还是厂商自定义？与 `EmbodiedCommand` 如何映射？ | |
| 控制频率 | 是否 ≥ 50 Hz？延迟？ | |
| 驱动实现 | `ros2_control` / 厂商 SDK / 自写 `chassis_driver_cpp` | |

**选定方案（简述）**：

---

## B. 3DOF 机械臂 + 夹爪

| 调研项 | 说明 | 结论 |
|--------|------|------|
| 自由度 | ≥ 3 旋转关节 + 夹爪 | |
| 工作空间 | 能否覆盖 STOW / REACH / GRASP_READY？ | |
| 控制方式 | 位置 / 速度 / 力矩 | |
| 夹爪反馈 | 是否有开合状态（对标 `world.gripper`）？ | |

**选定方案（简述）**：

---

## C. 上位机

| 调研项 | 说明 | 结论 |
|--------|------|------|
| 算力平台 | Jetson Orin Nano / NX / x86 Mini PC | |
| 负载 | 仅 Agent + 驱动，或含感知？ | |
| OS / ROS | 与开发机 lyrical 是否一致？ | |
| 急停 | 硬件急停链路 | |

**选定方案（简述）**：

---

## D. `embodied_core` 第一个真机适配点

```
仿真：EmbodiedWorldState → WorldView → FSM → EmbodiedCommand → simulation_node
真机：Odometry + JointState + … → WorldView → FSM → EmbodiedCommand → chassis_driver_cpp
```

| 优先级 | 模块 | 工作内容 |
|--------|------|----------|
| 1 | WorldView 适配 | 真机传感器 → `embodied_core::WorldView` |
| 2 | `chassis_driver_cpp` | `EmbodiedCommand` → 电机 / 关节指令 |
| 3 | `embodied_core` | FSM / Skill **不改** |

**第一个真机里程碑（建议）**：

> 仅验证 `NavigateSkill`：车到标记点 ±0.3 m，臂保持 STOW。

**计划时间**：

---

## E. 仿真 vs 真机差异备忘

| 项目 | 仿真 | 真机 |
|------|------|------|
| 物体位姿 | `/world_state` 真值 | 感知 / 标定 |
| 推箱 | virtual attach | 摩擦 / 真抓 |
| 接触 | 距离 heuristic | 力 / 电流 / 视觉 |

**备注**：
