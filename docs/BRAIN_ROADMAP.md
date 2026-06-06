# 具身智能「大脑」接入路线图

本文档描述在现有 HIL 仿真栈上接入「大脑」的整体计划。后续开发按本文档分阶段执行。

**相关仓库**：[-hil-chassis-sim](https://github.com/511546426/-hil-chassis-sim.git)

---

## 1. 现状与目标

### 1.1 当前架构（身体层已就绪）

```
controller_node (键盘遥控)     simulation_node (MuJoCo 身体)
  pub /control_cmd  (EmbodiedCommand) ──►  sub
  sub /chassis_state (Odometry)         ◄──  pub
  sub /arm_state     (JointState)       ◄──  pub
```

| 组件 | 状态 | 说明 |
|------|------|------|
| `simulation_node` | ✅ | MuJoCo 50 Hz 物理仿真，场景含红箱/蓝箱/柱子 |
| `EmbodiedCommand` | ✅ | 底盘 vx + 转向角 + 3 关节角 + 夹爪 + 急停 |
| `EmbodiedTracker` | ✅ | 加速度/关节限速平滑，大脑可低频输出目标 |
| `controller_node` | ✅ | 键盘遥控，50 Hz 发布指令 |
| 物体位姿观测 | ❌ | 红箱/蓝箱位置未发布到 ROS |
| 任务/目标接口 | ❌ | 无结构化任务消息 |
| Episode / Reward | ❌ | 无重置与奖励，RL 无法落地 |
| 多控制源仲裁 | ❌ | `/control_cmd` 仅支持单一发布者 |

### 1.2 总体目标

在 **不推翻现有 HIL 架构** 的前提下，新增「大脑」层，实现：

1. **感知闭环**：发布世界状态（物体位姿、接触等）
2. **决策闭环**：`agent_node` 替代或并存于键盘遥控
3. **任务闭环**：支持导航、伸臂、夹爪、推/抓等具身任务
4. **可扩展**：为规则/BT、RL、LLM 规划预留统一接口

### 1.3 设计原则

- **分层控制**：大脑慢（1–5 Hz）→ 技能中（10–20 Hz）→ 身体快（50 Hz）
- **语义动作优先**：大脑输出目标位姿/臂姿预设，不直接端到端输出 7 维关节角
- **训练与 HIL 分离**：RL 在 headless Gym 中训练，策略部署到 `agent_node`
- **最小可行增量**：每期交付可运行、可演示的里程碑

---

## 2. 目标架构

### 2.1 分层架构图

```
┌─────────────────────────────────────────────────────────────┐
│  大脑层 (Brain)                                              │
│  - 任务规划：LLM / 规则 / 行为树 / 用户指令                    │
│  - 输出：EmbodiedGoal（语义目标，低频）                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  技能层 (Skill Executor)                                       │
│  - 导航：Pure Pursuit / DWA → vx + steer                       │
│  - 操作：臂姿预设状态机 → shoulder/elbow/wrist + gripper        │
│  - 输出：EmbodiedCommand（中频，经 Tracker 平滑到 50 Hz）        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  身体层 (Body) — 已实现                                        │
│  simulation_node + EmbodiedTracker + MuJoCo                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
agent_node / brain_node
  sub  /chassis_state      (Odometry)
  sub  /arm_state          (JointState)
  sub  /world_state        (EmbodiedWorldState)  ← 新增
  sub  /task_goal          (EmbodiedGoal)        ← 新增，可选
  pub  /control_cmd        (EmbodiedCommand)

simulation_node
  pub  /world_state        ← 新增
  （其余保持不变）
```

### 2.3 控制模式切换

| 模式 | 发布者 | 启动方式 |
|------|--------|----------|
| 遥控 | `controller_node` | `./scripts/hil_demo.sh`（默认） |
| Agent | `agent_node` | `./scripts/hil_demo.sh --agent` |
| 联调 | 二者互斥，同时只启一个 | launch 参数控制 |

---

## 3. 消息与接口设计

### 3.1 新增：`EmbodiedWorldState.msg`

仿真节点发布的完整观测（供大脑订阅）。

```msg
# 时间戳
std_msgs/Header header

# 底盘（与 /chassis_state 冗余，便于单话题订阅）
float64 base_x
float64 base_y
float64 base_yaw
float64 base_vx
float64 base_steer

# 机械臂
float64 arm_shoulder
float64 arm_elbow
float64 arm_wrist
float64 gripper          # 0=张开, 1=闭合

# 可动物体（按场景中 body 名）
geometry_msgs/Pose[] object_poses
string[]             object_names

# 接触/任务相关
bool gripper_touching_object
string touched_object_name   # 空串表示无接触
```

**实现要点**：在 `chassis_common/state_reader.py` 增加 `read_object_pose()`，从 MuJoCo `box_red`、`box_blue` 等 freejoint body 读取位姿。

### 3.2 新增：`EmbodiedGoal.msg`

大脑/上层下发的语义目标（低频，非 50 Hz 连续控制）。

```msg
# 任务类型
uint8 NAVIGATE=0
uint8 MANIPULATE=1
uint8 IDLE=2
uint8 type

# 导航目标（世界坐标，米）
float64 target_x
float64 target_y
float64 target_yaw     # 可选，-999 表示不约束

# 臂姿预设
uint8 ARM_STOW=0
uint8 ARM_REACH=1
uint8 ARM_GRASP_READY=2
uint8 arm_preset

# 夹爪
uint8 GRIPPER_HOLD=0
uint8 GRIPPER_OPEN=1
uint8 GRIPPER_CLOSE=2
uint8 gripper_action
```

**预设臂姿参考值**（在 `chassis_common` 中集中定义）：

| 预设 | shoulder | elbow | wrist | 用途 |
|------|----------|-------|-------|------|
| `ARM_STOW` | 0.35 | 0.0 | 0.25 | 默认/移动 |
| `ARM_REACH` | 0.55 | 0.4 | 0.3 | 伸向物体 |
| `ARM_GRASP_READY` | 0.45 | 0.6 | 0.2 | 抓取准备 |

### 3.3 保留：`EmbodiedCommand.msg`

技能层 → 身体的低层指令，**保持不变**。字段：

- `target_linear_x`, `target_steering_angle`, `emergency_brake`
- `arm_shoulder`, `arm_elbow`, `arm_wrist`, `gripper`

---

## 4. 方案选型结论

| 方案 | 描述 | 结论 |
|------|------|------|
| A. ROS agent 直连 | `agent_node` 订阅状态、发布 `EmbodiedCommand` | ✅ 第一期采用，验证闭环 |
| B. 分层大脑 | 大脑出 `EmbodiedGoal`，技能层出 `EmbodiedCommand` | ✅ 中长期主架构 |
| C. Gym + RL 训练 | headless 环境训练，策略部署到 agent | ✅ 第三期可选 |
| 端到端关节 RL/LLM | 大脑直接输出 7 维关节角 | ❌ 暂不采用，样本效率低、难调试 |

---

## 5. 分阶段实施计划

### 第一期：感知 + 脚本 Agent（预计 1–2 周）

**目标**：自动导航到红箱附近并切换到伸臂姿态，全程无需键盘。

#### 任务清单

- [ ] **P1-1** `state_reader.py`：实现 `read_object_poses(model, data) -> dict[str, pose]`
- [ ] **P1-2** `embodied_msgs`：新增 `EmbodiedWorldState.msg`，编译通过
- [ ] **P1-3** `simulation_node`：50 Hz 发布 `/world_state`
- [ ] **P1-4** 新建包 `chassis_agent`（Python）：
  - [ ] `agent_node`：订阅 `/world_state`
  - [ ] 实现 Pure Pursuit 或简单 P 控制：`base → (2.5, 0.0)`
  - [ ] 到位判据：距目标 < 0.3 m → 切换 `ARM_REACH` 预设
  - [ ] 发布 `/control_cmd`
- [ ] **P1-5** `hil_demo.sh`：增加 `--agent` 模式，启动 `agent_node` 替代 `controller_node`
- [ ] **P1-6** 文档与验收：录制或文字记录一次完整自动运行日志

#### 验收标准

1. `./scripts/hil_demo.sh --agent` 一键启动
2. 机器人自主移动到红箱 `(2.5, 0)` 附近（误差 < 0.5 m）
3. 到位后机械臂自动切换到 `ARM_REACH` 姿态
4. `/world_state` 中 `box_red` 位姿与仿真一致

#### 关键文件（计划新增/修改）

```
ros2_ws/src/embodied_msgs/msg/EmbodiedWorldState.msg   # 新增
ros2_ws/src/chassis_common/chassis_common/state_reader.py  # 扩展
ros2_ws/src/chassis_simulation/.../simulation_node.py      # 发布 world_state
ros2_ws/src/chassis_agent/                                 # 新包
  chassis_agent/agent_node.py
  chassis_agent/navigation.py      # Pure Pursuit
  chassis_agent/arm_presets.py     # 臂姿预设表
scripts/hil_demo.sh                                        # --agent
```

---

### 第二期：技能层 + 行为树任务（预计 2–4 周）

**目标**：完成 README 建议任务——导航 → 伸臂 → 夹爪 → 倒车推箱。

#### 任务清单

- [ ] **P2-1** `embodied_msgs`：新增 `EmbodiedGoal.msg`
- [ ] **P2-2** 技能模块拆分：
  - [ ] `NavigateSkill`：`EmbodiedGoal` → 底盘 `vx/steer`
  - [ ] `ManipulateSkill`：`arm_preset` + `gripper_action` → 关节目标
  - [ ] `SkillExecutor`：组合技能，输出 `EmbodiedCommand`
- [ ] **P2-3** 行为树或有限状态机（FSM）：
  ```
  IDLE → NAV_TO_RED → REACH_ARM → CLOSE_GRIPPER → BACK_UP → DONE
  ```
- [ ] **P2-4** 接触检测：利用 MuJoCo `data.contact` 或 gripper-object 距离 < 阈值，更新 `gripper_touching_object`
- [ ] **P2-5** 简单避障（可选）：DWA 或势场法绕开 `pillar_1/2`
- [ ] **P2-6** `hil_demo.sh --task push_red_box` 一键跑完整任务

#### 验收标准

1. 自动完成：移动到红箱 → 伸臂 → 闭合夹爪 → 倒车拖动箱子位移 > 0.2 m
2. 状态机可日志追踪（当前阶段、切换原因）
3. 遥控与 Agent 可通过参数切换，互不干扰

---

### 第三期：扩展大脑（按需，2 周+）

根据兴趣 **三选一或组合**：

#### 选项 C1：强化学习（导航）

- [ ] **P3-C1-1** `embodied_gym/`：Gymnasium 环境，headless MuJoCo
  - 观测：base pose + 目标相对坐标 + 障碍物距离
  - 动作：`vx ∈ [-1,1]`, `steer ∈ [-0.52, 0.52]`（连续 2 维）
  - 奖励：靠近目标 + 碰撞惩罚 + 时间惩罚
- [ ] **P3-C1-2** 迁移 `cartpole_train.py` 模式：`PPO` / `SAC` 训练脚本
- [ ] **P3-C1-3** 策略导出（ONNX 或 torch）→ `agent_node` 加载推理
- [ ] **P3-C1-4** 先只做导航，臂姿用离散预设（不动关节 RL）

**验收**：训练策略在 HIL 中自主导航到目标，成功率 > 80%（10 次试验）。

#### 选项 C2：LLM 任务规划

- [ ] **P3-C2-1** `task_planner_node`：自然语言 → `EmbodiedGoal` 序列（JSON）
- [ ] **P3-C2-2** 预定义任务模板：「去红箱」「抓蓝箱」「回原点」
- [ ] **P3-C2-3** CLI 或简单 Web 输入任务描述

**验收**：输入「把红箱推到左边」→ 输出可执行 goal 序列并跑通（允许简化语义）。

#### 选项 C3：多任务与课程学习

- [ ] **P3-C3-1** 任务注册表：红箱、蓝箱、绕柱、回巢
- [ ] **P3-C3-2** Episode reset 服务：`/reset_simulation`
- [ ] **P3-C3-3** 指标面板：成功率、耗时、碰撞次数

---

## 6. 包结构规划（完成后）

```
ros2_ws/src/
├── embodied_msgs/          # 消息：EmbodiedCommand, EmbodiedWorldState, EmbodiedGoal
├── chassis_common/         # 模型、动力学、状态读取、臂姿预设
├── chassis_simulation/     # simulation_node（身体）
├── chassis_controller/     # controller_node（键盘遥控）
├── chassis_agent/          # agent_node, 技能, 导航, BT/FSM  ← 新建
└── embodied_gym/           # Gym 环境（第三期，可选）        ← 新建

scripts/
├── hil_demo.sh             # --teleop | --agent | --task <name>
└── train_nav_rl.py         # 第三期 RL 训练入口（可选）

docs/
└── BRAIN_ROADMAP.md        # 本文档
```

---

## 7. 技术风险与对策

| 风险 | 对策 |
|------|------|
| 臂姿预设不够准，抓不到箱子 | 第二期加入「对准」微调：根据物体相对角度小幅调整 elbow |
| 推箱时底盘打滑或箱子飞 | 降低倒车速度上限；检查箱子质量与摩擦参数 |
| RL 训练不稳定 | 先 2 维导航；奖励塑形；用特权信息（物体真实位姿）训练 |
| LLM 输出不可执行 | 限制 JSON schema；只映射到预定义 `EmbodiedGoal` 枚举 |
| 遥控与 Agent 同时发指令 | launch 互斥；或增加 `control_arbiter` 节点（后期） |
| 仿真与训练环境不一致 | `chassis_common` 作为唯一模型/动力学来源，Gym 与 ROS 共用 |

---

## 8. 依赖与环境

与现有项目一致，无额外硬性依赖（第一期）：

```bash
source /opt/ros/lyrical/setup.bash
source ros2_sim_venv/bin/activate
cd ros2_ws && colcon build --symlink-install
```

第三期 RL 额外依赖（按需加入 `requirements.txt`）：

```
gymnasium>=0.29
stable-baselines3>=2.0
```

第三期 LLM 额外依赖：按选定 API（OpenAI / 本地模型）单独配置，**不写入仓库密钥**。

---

## 9. 执行顺序速查

```
第一期  →  /world_state + agent_node 导航到红箱 + 伸臂
第二期  →  EmbodiedGoal + 技能层 + 推箱任务 FSM
第三期  →  RL 或 LLM 或 多任务（按需）
```

**当前进度**：第一期尚未开始。完成每期后，在本文件对应章节勾选任务清单，并更新「当前进度」行。

---

## 10. 参考：建议练习任务（来自 README）

1. 移动到底盘红箱 `(2.5, 0)` 附近
2. `ARM_REACH` 调整机械臂伸向箱子
3. 闭合夹爪，倒车尝试拖动
4. 绕过绿色柱子到达蓝箱 `(-2.0, 1.5)`

以上任务序列作为 **第二期 FSM 的默认任务链**。
