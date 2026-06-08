# 具身智能「大脑」接入路线图

本文档描述在现有 HIL 仿真栈上接入「大脑」的整体计划。后续开发按本文档分阶段执行。

**相关仓库**：[-hil-chassis-sim](https://github.com/511546426/-hil-chassis-sim.git)

**实施文档**：

| 路径 | 适用 |
|------|------|
| [PHASE2_CPP_IMPLEMENTATION_GUIDE.md](./PHASE2_CPP_IMPLEMENTATION_GUIDE.md) | **推荐**：C++ 产品路径（`embodied_core` + `chassis_agent_cpp`） |
| [PHASE2_CLASS_DIAGRAM.md](./PHASE2_CLASS_DIAGRAM.md) | 第二期类图、FSM、各类/函数职责说明 |
| [PHASE2_IMPLEMENTATION_GUIDE.md](./PHASE2_IMPLEMENTATION_GUIDE.md) | Python 全栈参考 / 仿真侧 M4–M5 规格 |

---

## 0. 语言策略（产品路径）

本项目采用 **混合语言**，不是「全 Python」或「全 C++」：

| 层级 | 语言 | 说明 |
|------|------|------|
| 仿真身体（MuJoCo HIL） | **Python** | 迭代快、MuJoCo 生态成熟；**不上车** |
| 大脑 / 技能 / FSM | **C++** | 与真机、ROS 2 工业栈一致；**可复用到产品** |
| 遥控 | **C++** | 已有 `controller_node` |
| 消息 | **`.msg`** | C++/Python 共用 |
| RL 训练（第三期） | **Python** | Gym + SB3 |
| 策略推理 / 真机驱动（第三期+） | **C++** | ONNX、驱动 SDK |

**第一期**用 Python Agent 验证闭环；**第一期.b 起**新功能在 C++ 实现，Python Agent（`chassis_agent`）冻结为对照。

### 0.1 哪种语言更有优势？（按场景）

| 场景 | 更优 | 原因 |
|------|------|------|
| 产品 onboard、硬实时、长期维护 | **C++** | 性能、确定性、驱动与 Nav2/MoveIt 生态 |
| MuJoCo 仿真、快速试算法 | **Python** | API 简洁、改场景快 |
| ML 训练 | **Python** | PyTorch / SB3 |
| ML 上车推理 | **C++** | TensorRT / ONNX，延迟与部署 |
| 你当前背景（熟 C++、Python 了解） | **主写 C++** | 学习效率与产品方向一致 |

**结论**：不是二选一；**C++ 是产品主语言，Python 是仿真与训练的辅助语言**。

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
| 物体位姿观测 | ✅ | `/world_state` 含 `box_red` / `box_blue` |
| `EmbodiedWorldState` | ✅ | 50 Hz 发布 |
| Python 脚本 Agent | ✅ | `chassis_agent`：导航到红箱 + `ARM_REACH` |
| C++ 产品 Agent | ⏳ | `embodied_core` + `chassis_agent_cpp`（第二期 M2 起，**跳过 P1b**） |
| 任务/目标接口 | ⏳ | `EmbodiedGoal.msg`（**第三期**；第二期 FSM 用 C++ enum） |
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

### 2.2 数据流（C++ 产品路径）

```
chassis_agent_cpp (C++)          simulation_node (Python)
  sub  /world_state      ◄───  pub  /world_state
  pub  /control_cmd      ───►  sub  /control_cmd
  cli  /sim/set_virtual_grasp ─► srv (M5 虚拟推箱)

embodied_core (C++ 库，无 ROS)
  ← navigation, FSM, skills
```

可选扩展：`/task_goal` (EmbodiedGoal) ← 第三期 planner。

### 2.3 控制模式切换

| 模式 | 发布者 | 语言 | 启动方式 |
|------|--------|------|----------|
| 遥控 | `controller_node` | C++ | `./scripts/hil_demo.sh`（默认） |
| Agent（遗留对照） | `chassis_agent/agent_node` | Python | `./scripts/hil_demo.sh --agent` |
| **Agent（推荐）** | `chassis_agent_cpp/agent_node` | **C++** | `./scripts/hil_demo.sh --agent-cpp` |
| 推箱任务 | 同上 C++ Agent | C++ | `./scripts/hil_demo.sh --task push_red_box` |
| 联调 | 遥控与 Agent **互斥** | — | 同时只启一个控制源 |

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

**预设臂姿参考值**（在 `embodied_core/arm_preset.hpp` 集中定义；Python `arm_presets.py` 与之数值一致）：

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

### 第一期：感知 + 脚本 Agent（预计 1–2 周）— ✅ 已完成

**目标**：自动导航到红箱附近并切换到伸臂姿态，全程无需键盘。

#### 任务清单

- [x] **P1-1** `state_reader.py`：实现 `read_object_poses(model, data) -> dict[str, pose]`
- [x] **P1-2** `embodied_msgs`：新增 `EmbodiedWorldState.msg`，编译通过
- [x] **P1-3** `simulation_node`：50 Hz 发布 `/world_state`
- [x] **P1-4** 新建包 `chassis_agent`（Python）：
  - [x] `agent_node`：订阅 `/world_state`
  - [x] Pure Pursuit：`base → (box_red - standoff)`
  - [x] 到位 → `ARM_REACH`
  - [x] 发布 `/control_cmd`
- [x] **P1-5** `hil_demo.sh`：`--agent` 模式
- [ ] **P1-6** 文档与验收：录制或文字记录一次完整自动运行日志（可选）

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

### 第二期：技能层 + 推红箱 FSM（预计 1.5–2 周）

**目标**：完成 README 建议任务——导航 → 伸臂 → 夹爪 → 倒车推箱；结束时具备 **真机硬件调研路线**。

> **主文档（C++）**：[PHASE2_CPP_IMPLEMENTATION_GUIDE.md](./PHASE2_CPP_IMPLEMENTATION_GUIDE.md)（v1.1：跳过 P1b、跳过 EmbodiedGoal、含 M8 硬件清单）  
> **Python 仿真规格**：[PHASE2_IMPLEMENTATION_GUIDE.md §6–§8](./PHASE2_IMPLEMENTATION_GUIDE.md)

**执行策略**：

- ❌ 不做 **P1b**（不在 C++ 单独复现第一期）；`pure_pursuit` 在 **M2** 写 `NavigateSkill` 时移植。
- ❌ 第二期 **不定义** `EmbodiedGoal.msg`（第三期需要再加）。
- ✅ M2 末 **ROS 冒烟**（仅导航）；M8 **硬件调研清单**。

#### 语言分工

| 任务 | 语言 |
|------|------|
| M2–M3、M6–M7 技能 / FSM / Agent | **C++** |
| M4–M5 接触、虚拟推箱 | **Python**（仿真） |
| M5 `SetVirtualGrasp.srv` | `.srv` |

#### 任务清单

- [ ] **P2-M2** `embodied_core` + `chassis_agent_cpp`：`pure_pursuit`、`NavigateSkill`、`ManipulateSkill`、`SkillExecutor` + ROS 冒烟
- [ ] **P2-M3** `PushRedBoxFSM`（C++）：
  ```
  IDLE → NAV_TO_RED → REACH_ARM → CLOSE_GRIPPER → BACK_UP → DONE
  ```
- [ ] **P2-M4** 接触检测（Python `state_reader` + `simulation_node`）
- [ ] **P2-M5** `SetVirtualGrasp.srv` + 虚拟推箱（Python sim + C++ client）
- [ ] **P2-5** 简单避障（可选，**建议跳过**）
- [ ] **P2-M6** 倒车 + 推箱位移验收（≥ 0.2 m）
- [ ] **P2-M7** `hil_demo.sh --task push_red_box`（C++ Agent）
- [ ] **P2-M8** 验收记录 + [硬件调研清单](./HARDWARE_RESEARCH.md)

#### 验收标准

1. 自动完成：移动到红箱 → 伸臂 → 闭合夹爪 → 倒车拖动箱子位移 > 0.2 m
2. 状态机可日志追踪（当前阶段、切换原因）
3. 遥控与 Agent 可通过参数切换，互不干扰
4. 完成硬件调研表（底盘 / 臂 / 上位机 / `embodied_core` 真机适配点）

---

### ~~第一期.b~~（已取消）

> 原「C++ 对齐第一期」合并进 **第二期 M2**（`pure_pursuit` 移植 + ROS 冒烟），不再单独设里程碑。

### 第三期：扩展大脑（按需，2 周+）

根据兴趣 **三选一或组合**：

#### 选项 C1：强化学习（导航）

- [ ] **P3-C1-1** `embodied_gym/`：Gymnasium 环境，headless MuJoCo
  - 观测：base pose + 目标相对坐标 + 障碍物距离
  - 动作：`vx ∈ [-1,1]`, `steer ∈ [-0.52, 0.52]`（连续 2 维）
  - 奖励：靠近目标 + 碰撞惩罚 + 时间惩罚
- [ ] **P3-C1-2** 迁移 `cartpole_train.py` 模式：`PPO` / `SAC` 训练脚本
- [ ] **P3-C1-3** 策略导出 ONNX → **`embodied_policy_cpp`**（C++ 推理，非 Python agent）
- [ ] **P3-C1-4** 先只做导航，臂姿用离散预设（不动关节 RL）

**验收**：训练策略在 HIL 中自主导航到目标，成功率 > 80%（10 次试验）。

#### 选项 C2：LLM 任务规划

- [ ] **P3-C2-0** `embodied_msgs`：新增 `EmbodiedGoal.msg`（第三期需要时再定义）
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
├── embodied_msgs/          # .msg / .srv（第二期仅 SetVirtualGrasp.srv；EmbodiedGoal 第三期）
├── embodied_core/          # C++：导航、臂姿、FSM、技能（无 ROS）     ← 产品核心
├── chassis_agent_cpp/      # C++：agent_node                          ← 产品 ROS 入口
├── chassis_controller/     # C++：键盘遥控
├── chassis_simulation/     # Python：simulation_node（MuJoCo HIL）
├── chassis_common/         # Python：模型、sim_step、接触/虚拟推箱
├── chassis_agent/          # Python：第一期对照（冻结，不扩展）
├── embodied_gym/           # Python：第三期 RL 训练（可选）
└── embodied_policy_cpp/    # C++：第三期策略推理（可选）

scripts/
├── hil_demo.sh             # --agent-cpp | --task push_red_box | 默认遥控
└── train_nav_rl.py         # 第三期 RL 训练入口（可选）

docs/
├── BRAIN_ROADMAP.md
├── PHASE2_CPP_IMPLEMENTATION_GUIDE.md   # C++ 主路径（v1.1）
├── PHASE2_CLASS_DIAGRAM.md
├── PHASE2_IMPLEMENTATION_GUIDE.md       # Python 参考 / 仿真规格
└── HARDWARE_RESEARCH.md                 # M8 硬件调研（第二期完成后填写）

.cursor/skills/cpp-unit-test/              # C++ 单元测试 Agent skill
scripts/run_embodied_core_tests.sh         # 一键 gtest + Markdown 报告
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
source scripts/env.sh
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
第一期    ✅  Python Agent 验证闭环（已完成）
第二期  ⏳  M0→M2 embodied_core + 技能 + ROS 冒烟 → FSM 推箱 → M8 硬件调研
第三期       EmbodiedGoal（按需）+ RL/LLM + chassis_driver_cpp 真机
```

**当前进度**：第一期已完成。**下一步：第二期 M0 → M2**，见 [PHASE2_CPP_IMPLEMENTATION_GUIDE.md §4–§5](./PHASE2_CPP_IMPLEMENTATION_GUIDE.md)。

---

## 10. 参考：建议练习任务（来自 README）

1. 移动到底盘红箱 `(2.5, 0)` 附近
2. `ARM_REACH` 调整机械臂伸向箱子
3. 闭合夹爪，倒车尝试拖动
4. 绕过绿色柱子到达蓝箱 `(-2.0, 1.5)`

以上任务序列作为 **第二期 FSM 的默认任务链**。
