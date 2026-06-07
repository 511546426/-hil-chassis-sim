# 第二期实施指南：技能层 + 推红箱任务 FSM（Python 全栈参考）

> **C++ 开发者请优先阅读**：[PHASE2_CPP_IMPLEMENTATION_GUIDE.md](./PHASE2_CPP_IMPLEMENTATION_GUIDE.md)（v1.1 主路径，已跳过 P1b / EmbodiedGoal）。  
> 本文档适用于：全 Python 实现，或 **C++ 路径下查阅仿真侧 M4/M5（接触、虚拟推箱）规格**。

> **用途**：供开发者**亲手实现**第二期功能，熟悉 ROS 2 消息、Agent 分层、状态机与仿真交互。  
> **前提**：第一期已完成（`/world_state`、脚本 Agent 导航到红箱、`ARM_REACH`）。  
> **关联文档**：[BRAIN_ROADMAP.md](./BRAIN_ROADMAP.md) 第二节架构与 5.2 任务清单。

---

## 0. 学习目标与实施原则

### 0.1 你要练到什么

| 能力 | 对应模块 |
|------|----------|
| ROS 2 自定义消息编译与引用 | `EmbodiedGoal.msg` |
| 分层控制：FSM → Skill → Command | `chassis_agent/` |
| 状态机设计与可观测性（日志） | `task_fsm.py` |
| 从 `/world_state` 读观测做判据 | Agent 各状态 `tick()` |
| 仿真侧「虚拟交互」设计 | `state_reader` + `sim_step` |
| 增量编译、HIL 联调 | `colcon build` + `hil_demo.sh` |

### 0.2 实施原则（请严格遵守）

1. **按里程碑顺序做**：每完成一节先自测，再进入下一节；不要一次写完再跑。
2. **你先写，AI/他人只做 review**：每个里程碑末尾有「验收清单」，未通过不往下走。
3. **单文件改动尽量 ≤ 150 行**：便于理解 diff。
4. **每个状态切换必须打日志**：格式统一，方便 grep。
5. **第二期不做**（除非有余力）：DWA 避障、`/task_goal` 话题订阅、真实 MuJoCo 夹爪碰撞。

### 0.3 预估工作量

| 里程碑 | 内容 | 建议时间 |
|--------|------|----------|
| M0 | 环境与代码阅读 | 0.5 天 |
| M1 | `EmbodiedGoal.msg` | 0.5 天 |
| M2 | 技能层接口 + 单元逻辑 | 1–2 天 |
| M3 | FSM 骨架（假接触） | 1–2 天 |
| M4 | 接触检测 | 1 天 |
| M5 | 虚拟推箱（仿真） | 2–3 天 |
| M6 | 倒车 + 位移验收 | 1 天 |
| M7 | `hil_demo.sh --task` | 0.5 天 |
| M8 | 文档与验收记录 | 0.5 天 |
| **合计** | | **约 2–3 周**（业余节奏） |

---

## 1. 第一期现状（你需要知道的接口）

### 1.1 已有数据流

```
simulation_node (50 Hz)
  pub /world_state   (EmbodiedWorldState)
  pub /chassis_state (Odometry)
  pub /arm_state     (JointState)
  sub /control_cmd   (EmbodiedCommand)

agent_node (50 Hz)
  sub /world_state
  pub /control_cmd
```

### 1.2 第一期 Agent 行为（将被重构，但逻辑可复用）

当前 `agent_node.py` 等价于一个 **2 态 FSM**：

```
NAV  →  pure_pursuit 到 (box_red.x - 0.35, box_red.y)，臂 ARM_STOW
REACH →  vx=0, 臂 ARM_REACH, gripper=0
```

你需要把其**导航部分**迁入 `NavigateSkill`，**臂姿部分**迁入 `ManipulateSkill`，再用 **6 态 FSM** 编排完整推箱任务。

### 1.3 仿真物理约束（设计决策的基础）

当前 `sim_step.step_embodied_kinematic()` 的策略：

- **底盘**：运动学积分（非 MuJoCo 力驱动）
- **机械臂**：每帧 `pin_arm_kinematics` 锁定关节角
- **红箱/蓝箱**：仍走 `mj_step` 自由刚体

夹爪 geom 在 `model.py` 中设置了 `contype="0" conaffinity="0"`，**不与箱子发生物理碰撞**。

因此第二期 **不能指望「真实摩擦推箱」**，必须采用 **虚拟附着（virtual attach）**：

> 当 FSM 判定「已抓取」后，仿真在每步把 `box_red` 位姿绑定到 gripper/底盘的相对偏移，倒车时箱子随动。

这是刻意的设计选择，避免在第一期已稳定的 kinematic 栈上重新踩物理坑。

---

## 2. 第二期目标架构

### 2.1 分层图

```
┌─────────────────────────────────────────┐
│  TaskFSM (push_red_box)                  │
│  状态：IDLE → NAV → REACH → GRASP →     │
│        BACK_UP → DONE                    │
└──────────────────┬──────────────────────┘
                   │ 每 tick 输出「当前技能意图」
┌──────────────────▼──────────────────────┐
│  SkillExecutor                           │
│  组合 NavigateSkill + ManipulateSkill    │
│  → 完整 EmbodiedCommand                  │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  simulation_node + EmbodiedTracker       │
│  (+ virtual attach 在 sim_step)          │
└─────────────────────────────────────────┘
```

### 2.2 包与文件规划（完成后目录）

```
ros2_ws/src/
├── embodied_msgs/msg/
│   ├── EmbodiedCommand.msg      # 已有
│   ├── EmbodiedWorldState.msg   # 已有
│   └── EmbodiedGoal.msg         # M1 新增（先定义，M3 可不接话题）
│
├── chassis_common/chassis_common/
│   ├── state_reader.py          # M4 扩展：gripper 位姿、接触检测
│   ├── sim_step.py              # M5 扩展：virtual attach
│   └── interaction.py           # M5 新增：VirtualGrasp 状态（建议）
│
├── chassis_agent/chassis_agent/
│   ├── agent_node.py            # M3 重构：只保留 ROS 壳 + 调 FSM
│   ├── navigation.py            # 已有，M2 可能加 reverse 函数
│   ├── arm_presets.py           # 已有
│   ├── skill_executor.py        # M2 新增
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── navigate_skill.py    # M2 新增
│   │   └── manipulate_skill.py  # M2 新增
│   └── tasks/
│       ├── __init__.py
│       └── push_red_box_fsm.py  # M3 新增
│
scripts/
└── hil_demo.sh                  # M7 增加 --task push_red_box
```

### 2.3 频率与职责

| 组件 | 频率 | 职责 |
|------|------|------|
| `simulation_node` | 50 Hz | 物理步进、发布 `/world_state`、执行 virtual attach |
| `agent_node` | 50 Hz | 读最新 world，`fsm.tick()` → `SkillExecutor` → publish |
| FSM | 50 Hz（在 agent 定时器内） | 离散状态转移 |
| Skill | 50 Hz | 连续控制量（vx, steer, 关节目标） |

第二期 **FSM 与 Skill 同频**即可；不必强行做 1–5 Hz 大脑层（那是第三期 LLM/规划的事）。

---

## 3. 消息设计

### 3.1 `EmbodiedGoal.msg`（M1）

在 `ros2_ws/src/embodied_msgs/msg/EmbodiedGoal.msg` 新建：

```msg
# 语义任务目标（低频；第二期可在代码内构造，不必发布到话题）

std_msgs/Header header

uint8 NAVIGATE=0
uint8 MANIPULATE=1
uint8 IDLE=2
uint8 type

float64 target_x
float64 target_y
float64 target_yaw    # -999 表示不约束朝向

uint8 ARM_STOW=0
uint8 ARM_REACH=1
uint8 ARM_GRASP_READY=2
uint8 arm_preset

uint8 GRIPPER_HOLD=0
uint8 GRIPPER_OPEN=1
uint8 GRIPPER_CLOSE=2
uint8 gripper_action
```

**CMakeLists.txt** 在 `rosidl_generate_interfaces` 中加入 `"msg/EmbodiedGoal.msg"`（依赖不变）。

**package.xml** 无需额外依赖（已有 `std_msgs`）。

编译：

```bash
cd ros2_ws
colcon build --packages-select embodied_msgs
source install/setup.bash
ros2 interface show embodied_msgs/msg/EmbodiedGoal
```

### 3.2 第二期如何使用 EmbodiedGoal

**推荐（简单）**：只在 Python 里用 dataclass 镜像字段，**不发布 `/task_goal` 话题**。

```python
# chassis_agent/tasks/goal.py — 可选，你自己建
@dataclass
class TaskGoal:
    type: int
    target_x: float
    target_y: float
    arm_preset: int
    gripper_action: int
```

FSM 内部构造 `TaskGoal`，交给 `SkillExecutor.apply(goal, world)`。

**进阶（可选）**：增加 `task_goal_node` 或 launch 参数 —— 留到第二期验收后再做。

---

## 4. 技能层详细设计（M2）

### 4.1 公共数据结构

建议在 `chassis_agent/skills/types.py`（自建）定义：

```python
@dataclass
class SkillOutput:
    target_linear_x: float = 0.0
    target_steering_angle: float = 0.0
    arm_shoulder: float = 0.35
    arm_elbow: float = 0.0
    arm_wrist: float = 0.25
    gripper: float = 0.0
    emergency_brake: bool = False
```

### 4.2 `NavigateSkill`

**文件**：`chassis_agent/skills/navigate_skill.py`

**职责**：给定世界坐标目标点，输出 `vx` + `steer`。

**接口（你来实现）**：

```python
class NavigateSkill:
    def __init__(
        self,
        *,
        max_vx: float = 1.0,
        max_vx_reverse: float = 0.35,
        arrive_dist: float = 0.3,
        standoff: float = 0.35,
    ): ...

    def compute(
        self,
        world: EmbodiedWorldState,
        target_x: float,
        target_y: float,
        *,
        reverse: bool = False,
    ) -> SkillOutput:
        """reverse=True 时沿 base_yaw+π 方向后退。"""
```

**实现要点**：

1. **前进**：直接调用现有 `pure_pursuit(x, y, yaw, tx, ty, arrive_dist=...)`。
2. **standoff**：导航到红箱时，目标点 = `(box_x - standoff, box_y)`，与第一期 `_goal_xy` 一致。
3. **reverse（M6 再做）**：
   - 目标点取「当前位置沿 `yaw + π` 方向 back_dist 米处」；
   - 或 simpler：`target_linear_x = -max_vx_reverse`，`target_steering_angle = 0`（先直线倒车）；
   - `arrived` 判据：累计倒车距离 > 0.5 m **或** 超时 8 s。
4. **stuck 检测**：复用第一期 `_stuck_at_box` 逻辑，放在 FSM 的 `NAV_TO_RED` 态而非 Skill 内（职责更清晰）。

### 4.3 `ManipulateSkill`

**文件**：`chassis_agent/skills/manipulate_skill.py`

**职责**：根据 `arm_preset` 与 `gripper_action` 输出关节目标。

**接口**：

```python
class ManipulateSkill:
    PRESET_STOW = 0
    PRESET_REACH = 1
    PRESET_GRASP_READY = 2

    GRIPPER_OPEN = 1
    GRIPPER_CLOSE = 2
    GRIPPER_HOLD = 0

    def compute(
        self,
        world: EmbodiedWorldState,
        *,
        arm_preset: int,
        gripper_action: int,
    ) -> SkillOutput:
        ...
```

**实现要点**：

1. 从 `arm_presets.py` 取 `ARM_STOW / ARM_REACH / ARM_GRASP_READY`。
2. `gripper`：`OPEN→0.0`，`CLOSE→1.0`，`HOLD→保持当前 world.gripper`（或上次指令）。
3. 底盘输出全 0（操作态不移动）。
4. **臂到位判据**（供 FSM 使用）：

```python
def arm_at_preset(world: EmbodiedWorldState, preset: ArmPreset, tol: float = 0.08) -> bool:
    return (
        abs(world.arm_shoulder - preset.shoulder) < tol
        and abs(world.arm_elbow - preset.elbow) < tol
        and abs(world.arm_wrist - preset.wrist) < tol
    )
```

5. **夹爪到位判据**：`|world.gripper - target| < 0.05`。

### 4.4 `SkillExecutor`

**文件**：`chassis_agent/skill_executor.py`

**职责**：根据 FSM 给的「当前意图」调用 Skill，合并为一条 `EmbodiedCommand`。

**接口**：

```python
class SkillExecutor:
    def __init__(self): ...

    def step(
        self,
        world: EmbodiedWorldState,
        *,
        mode: str,  # 'navigate' | 'manipulate'
        nav_target: tuple[float, float] | None = None,
        nav_reverse: bool = False,
        arm_preset: int = ManipulateSkill.PRESET_STOW,
        gripper_action: int = ManipulateSkill.GRIPPER_HOLD,
    ) -> EmbodiedCommand:
        ...
```

**M2 验收**：写一个不依赖 ROS 的小脚本或 `python -c` 调用，传入 mock `EmbodiedWorldState` 字段，打印输出是否合理。

---

## 5. FSM 详细设计（M3–M6）

### 5.1 状态定义

**文件**：`chassis_agent/tasks/push_red_box_fsm.py`

```python
class PushRedBoxPhase(IntEnum):
    IDLE = 0
    NAV_TO_RED = 1
    REACH_ARM = 2
    CLOSE_GRIPPER = 3
    BACK_UP = 4
    DONE = 5
    FAILED = 6   # 建议加，便于超时处理
```

### 5.2 状态转移图

```
                    ┌─────────┐
                    │  IDLE   │
                    └────┬────┘
                         │ world 首帧有效
                         ▼
                 ┌───────────────┐
                 │  NAV_TO_RED   │◄── NavigateSkill, ARM_STOW, gripper open
                 └───────┬───────┘
           arrived/stuck│
                         ▼
                 ┌───────────────┐
                 │  REACH_ARM    │◄── 停车, ARM_REACH
                 └───────┬───────┘
                  arm_at│
                         ▼
                 ┌───────────────┐
                 │ CLOSE_GRIPPER │◄── ARM_REACH/GRASP_READY, gripper close
                 └───────┬───────┘
        gripper closed  │ + contact (M4)
                         ▼
                 ┌───────────────┐
                 │   BACK_UP     │◄── reverse nav, 通知 sim virtual attach
                 └───────┬───────┘
           box moved    │ > 0.2m
                         ▼
                 ┌───────────────┐
                 │    DONE       │
                 └───────────────┘
```

### 5.3 各状态进入/退出条件（实现规格）

| 状态 | 进入动作（日志） | 每 tick 输出 | 退出条件 | 超时 |
|------|------------------|--------------|----------|------|
| `IDLE` | — | 零速 STOW | 收到 `world != None` | — |
| `NAV_TO_RED` | `FSM NAV_TO_RED enter` | Navigate → box standoff | `pure_pursuit.arrived` 或 `_stuck_at_box` | 60 s → FAILED |
| `REACH_ARM` | `FSM REACH_ARM enter` | Manipulate REACH | `arm_at_preset(REACH)` | 10 s → 仍进 GRASP* |
| `CLOSE_GRIPPER` | `FSM CLOSE_GRIPPER enter` | gripper=1.0 | `gripper>0.95` 且 `world.gripper_touching_object` | 8 s → FAILED |
| `BACK_UP` | `FSM BACK_UP enter` + **通知 sim 附着** | reverse vx | 见 §5.4 | 15 s → DONE 或 FAILED |
| `DONE` | `FSM DONE` + 打印 box 位移 | 全零 STOW | — | — |

\* REACH 超时可放宽：第二期允许「臂未完全到位也尝试夹」，但日志须警告。

### 5.4 BACK_UP 完成判据

在 FSM 内记录：

```python
self._box_x0, self._box_y0  # 进入 BACK_UP 时 box_red 位置
self._back_start_x, self._back_start_y  # 进入 BACK_UP 时 base 位置
```

**成功条件（满足任一）**：

1. `hypot(box_x - box_x0, box_y - box_y0) >= 0.20`（主验收）
2. 倒车距离 `hypot(base_x - back_start_x, ... ) >= 0.6` 且 box 位移 > 0.10（备选）

### 5.5 FSM 类接口

```python
class PushRedBoxFSM:
    def __init__(self, logger): ...

    @property
    def phase(self) -> PushRedBoxPhase: ...

    def tick(
        self,
        world: EmbodiedWorldState,
        executor: SkillExecutor,
    ) -> EmbodiedCommand:
        """推进状态机，返回本帧控制指令。"""

    def _transition(self, new_phase: PushRedBoxPhase, reason: str) -> None:
        """统一打日志：FSM <old> -> <new>: <reason>"""
```

### 5.6 `agent_node.py` 重构规格

重构后 `agent_node` **不应包含**导航/臂姿细节，只做：

```python
def _publish_cmd(self):
    if self._world is None:
        return  # 或发零指令
    cmd = self._fsm.tick(self._world, self._executor)
    self._pub.publish(cmd)
```

参数可通过 ROS parameter 暴露：

- `task`（string，默认 `push_red_box`）
- `box_standoff`、`arrive_dist`、`push_min_dist`（0.2）

---

## 6. 接触检测设计（M4）

### 6.1 为何不用 MuJoCo contact（第二期）

夹爪无碰撞体；强行开启会与 kinematic 臂、第一期稳定性冲突。**第二期统一用几何距离 heuristic。**

### 6.2 gripper 世界坐标估算

在 `state_reader.py` 新增（你来实现）：

```python
def read_gripper_position(model, data) -> tuple[float, float, float]:
    """返回 gripper body 的 x,y,z（data.xpos）。"""
```

MuJoCo body 名：`'gripper'`（见 `model.py`）。

### 6.3 接触判据函数

```python
GRIP_CONTACT_DIST = 0.22   # 可调：略大于几何距离
GRIP_CONTACT_Z_TOL = 0.15

def detect_gripper_contact(
    model,
    data,
    *,
    object_names: tuple[str, ...] = ('box_red', 'box_blue'),
) -> tuple[bool, str]:
    """
    返回 (touching, object_name)。
    条件：水平距离 < GRIP_CONTACT_DIST 且 |dz| < GRIP_CONTACT_Z_TOL
    """
```

### 6.4 写入 `/world_state`

在 `simulation_node.publish_state()` 中：

```python
touching, name = detect_gripper_contact(model, data)
world.gripper_touching_object = touching
world.touched_object_name = name if touching else ''
```

### 6.5 M4 验收

1. 遥控模式：开车到红箱旁，键盘 `g` 闭合夹爪，**不一定需要**碰到箱子。
2. `ros2 topic echo /world_state --field gripper_touching_object`：臂伸向箱附近时应为 `true`。
3. 远离箱子时为 `false`。

---

## 7. 虚拟推箱设计（M5）

### 7.1 概念

FSM 进入 `BACK_UP` 时，仿真认为「`box_red` 已被抓住」，每步在 `mj_step` **之后**把箱子位姿更新为：

```
box_pos = gripper_pos + R(yaw) @ attach_offset_body
```

其中 `attach_offset_body` 为进入附着时记录的 gripper→box 向量（在 base 或 gripper 坐标系下）。

### 7.2 建议新增 `interaction.py`

**文件**：`chassis_common/chassis_common/interaction.py`

```python
@dataclass
class VirtualGraspState:
    active: bool = False
    object_body: str = ''
    offset_x: float = 0.0   # gripper 坐标系下偏移
    offset_y: float = 0.0
    offset_z: float = 0.0

def begin_virtual_grasp(
    model, data, object_body: str, gripper_body: str = 'gripper'
) -> VirtualGraspState: ...

def apply_virtual_grasp(model, data, state: VirtualGraspState) -> None:
    """若 active，写 box freejoint qpos。"""
```

**实现提示**：

1. `box_red` 使用 `freejoint`，qpos 为 7 维：xyz + quat(wxyz)。
2. 附着时记录 offset = box_pos - gripper_pos（世界系），每步用当前 gripper 位姿 + offset 写回。
3. 只旋转 yaw 时，简化版可 **只更新 box 的 x,y**，z 和 quat 保持不变（足够验收 0.2 m 位移）。

### 7.3 与 simulation_node 的衔接

**方案 A（推荐）**：仿真节点订阅一个 **私有标志话题** —— 过重。

**方案 B（推荐）**：在 `EmbodiedCommand` 中 **不新增字段**；仿真根据 world 状态推断：

- `gripper > 0.95` 且 `gripper_touching_object` 且 `|base_vx| < 0.05` 持续 0.5 s → 自动 `begin_virtual_grasp`

**方案 C（最清晰，建议你用）**：在 `simulation_node` 增加 **参数字** + **服务**：

```python
# 服务类型可用 std_srvs/SetBool 或自建 Trigger
# /sim/set_virtual_grasp  data: true/false
```

FSM 进入 `BACK_UP` 时，agent 调用 service 开启附着；`DONE` 时关闭。

为练习 ROS service，**推荐方案 C**。若嫌麻烦，先用方案 B。

### 7.4 修改 `sim_step.py`

在 `step_embodied_kinematic()` 末尾增加可选参数：

```python
def step_embodied_kinematic(..., virtual_grasp: VirtualGraspState | None = None):
    ...
    mujoco.mj_step(model, data)
    ...
    if virtual_grasp and virtual_grasp.active:
        apply_virtual_grasp(model, data, virtual_grasp)
```

### 7.5 M5 验收

1. 遥控：到箱旁、伸臂、闭合，手动发倒车（或临时写测试脚本），观察箱子是否随动。
2. 箱子不应穿透地面或飞到天上。
3. 解除附着后箱子留在当前位置。

---

## 8. 倒车导航（M6）

在 `navigation.py` 增加：

```python
def reverse_drive(
    yaw: float,
    *,
    max_vx_reverse: float = 0.35,
) -> NavigationCommand:
    return NavigationCommand(-max_vx_reverse, 0.0, False)
```

`BACK_UP` 态使用 `nav_reverse=True` 或专用 `reverse_drive`。

**注意**：倒车时 `EmbodiedTracker` 仍平滑 vx；负向加速度用 `max_linear_decel` 限制，避免瞬移。

**与 virtual attach 联调**：必须 **先 attach 再倒车**，否则 box 不动，验收失败。

---

## 9. 启动脚本（M7）

修改 `scripts/hil_demo.sh`：

```bash
# 新增变量
TASK=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task)
      TASK="$2"; AGENT_MODE=1; shift 2 ;;
    ...
  esac
done

# agent 启动时传参
if [[ "$TASK" == "push_red_box" ]]; then
  ros2 run chassis_agent agent_node --ros-args -p task:=push_red_box
fi
```

`agent_node` 读取 `task` 参数，实例化 `PushRedBoxFSM`。

用法：

```bash
./scripts/hil_demo.sh --task push_red_box --build
```

---

## 10. 分步实施里程碑（手把手顺序）

### M0：阅读与跑通第一期（0.5 天）

**任务**：

1. 画出你理解的 topic 图（纸笔即可）。
2. 跑 `./scripts/hil_demo.sh --agent`， tail 日志，确认 NAV → REACH。
3. 阅读并注释（加你自己的注释）：
   - `agent_node.py`
   - `navigation.py`
   - `simulation_node.publish_state()`
   - `sim_step.py`

**验收**：能口头说明「为什么停车后 base 不会 drift」。

---

### M1：EmbodiedGoal 消息（0.5 天）

**任务**：

1. 新建 `EmbodiedGoal.msg`。
2. 改 `CMakeLists.txt`，编译通过。
3. `ros2 interface show` 确认。

**验收**：编译零错误；**暂不写 Python 引用**也可。

---

### M2：技能层（1–2 天）

**任务**：

1. 建 `skills/types.py`、`navigate_skill.py`、`manipulate_skill.py`、`skill_executor.py`。
2. 从旧 `agent_node` **复制**逻辑进 Skill，不要重写算法。
3. 暂时保留旧 `agent_node` 不动，写 `if __name__ == '__main__'` 本地测试 ManipulateSkill。

**验收**：

- Navigate 到 (2.15, 0) 输出 vx>0。
- Manipulate REACH 输出 shoulder≈0.55。
- SkillExecutor 输出可构造为 `EmbodiedCommand`。

---

### M3：FSM 骨架，假接触（1–2 天）

**任务**：

1. 实现 `PushRedBoxFSM`，**CLOSE_GRIPPER 态暂用** `gripper>0.95` **即跳转**，不检查 contact。
2. `BACK_UP` 态先 **vx=0 占位**。
3. 重构 `agent_node` 使用 FSM + Executor。
4. 统一日志：`FSM NAV_TO_RED -> REACH_ARM: arrived dist=0.28`。

**验收**：

- `./scripts/hil_demo.sh --agent` 仍能看到 NAV → 伸臂。
- 日志能 grep 到全部状态名。

---

### M4：接触检测（1 天）

**任务**：

1. 实现 `read_gripper_position`、`detect_gripper_contact`。
2. 接入 `simulation_node`。
3. FSM `CLOSE_GRIPPER` 改为必须 `world.gripper_touching_object`。

**验收**：伸臂到箱旁后，`/world_state` 接触为 true；FSM 能进入 BACK_UP。

---

### M5：虚拟推箱（2–3 天）

**任务**：

1. 实现 `interaction.py` + 修改 `sim_step.py`。
2. simulation 侧实现 attach（service 或自动判据）。
3. agent 在 BACK_UP enter 时触发 attach。

**验收**：遥控模式下倒车能带动红箱。

---

### M6：倒车与完整任务（1 天）

**任务**：

1. 实现 `reverse_drive` / `nav_reverse`。
2. FSM 完整跑通 IDLE → DONE。
3. 记录 box 初始与最终位移。

**验收**（第二期终验）：

- 自动：移动 → 伸臂 → 夹爪 → 倒车，**红箱位移 ≥ 0.2 m**。
- 全程无键盘。
- 日志含每次 `FSM * -> *: reason`。

---

### M7：启动脚本（0.5 天）

**任务**：`--task push_red_box` 一键启动。

**验收**：新终端同事只跑一条命令能复现。

---

### M8：验收记录（0.5 天）

在 `docs/` 自建 `PHASE2_ACCEPTANCE.md`（可选），粘贴：

- 命令
- 关键日志片段
- box 位移数值
- 遇到的问题与解决

并更新 `BRAIN_ROADMAP.md` 第二期 checklist。

---

## 11. 调参表（建议初值）

| 参数 | 值 | 说明 |
|------|-----|------|
| `standoff` | 0.35 m | 停在箱前距离 |
| `arrive_dist` | 0.30 m | Pure Pursuit 到达半径 |
| `GRIP_CONTACT_DIST` | 0.22 m | 接触水平距离 |
| `GRIP_CONTACT_Z_TOL` | 0.15 m | 接触高度差 |
| `max_vx_reverse` | 0.35 m/s | 倒车速度上限 |
| `push_min_dist` | 0.20 m | 验收推箱位移 |
| `arm_tol` | 0.08 rad | 臂到位 |
| `gripper_closed` | 0.95 | 夹爪闭合阈值 |
| NAV 超时 | 60 s | |
| GRASP 超时 | 8 s | |

调参方法：每次只改一个，记录结果。

---

## 12. 调试命令速查

```bash
# 环境
source /opt/ros/lyrical/setup.bash
source /home/changwei/changwei/project/ros2_ws/install/setup.bash

# 编译
cd /home/changwei/changwei/project/ros2_ws
colcon build --packages-select embodied_msgs chassis_common chassis_agent chassis_simulation

# 只看 box 名与位姿
ros2 topic echo /world_state --field object_names
ros2 topic echo /world_state --field object_poses

# 接触
ros2 topic echo /world_state --field gripper_touching_object

# 杀残留
pkill -f simulation_node; pkill -f agent_node
```

---

## 13. 常见坑

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 编译找不到 EmbodiedGoal | 未 rebuild / 未 source | `colcon build` + `source install/setup.bash` |
| 到了箱旁但不进 BACK_UP | 接触距离阈值太小 | 增大 `GRIP_CONTACT_DIST` |
| 夹爪闭合但 contact false | gripper body 位置与视觉不一致 | 打印 `read_gripper_position` 与 box 距离 |
| 倒车箱子不动 | 未 virtual attach | 检查 service / attach 逻辑 |
| 箱子飞走 | attach 每步重复累加 offset | 固定 world 系 offset 或 gripper 系 offset |
| FSM 卡 NAV | stuck 未触发 | 对照第一期 `_stuck_at_box` |
| 改 Python 不生效 | 未 symlink 或未重装 | `colcon build --symlink-install` |

---

## 14. 第二期验收标准（与 ROADMAP 对齐）

1. `./scripts/hil_demo.sh --task push_red_box` 一键启动。
2. 自动完成：移动到红箱 → 伸臂 → 闭合夹爪 → 倒车，**红箱位移 > 0.2 m**。
3. FSM 阶段可日志追踪（含切换原因）。
4. 遥控与 Agent 仍互斥（launch 只启一个控制源）。
5. **你本人**能讲解：FSM 每态做什么、virtual attach 为何必要、接触检测公式。

---

## 15. 与 AI 协作的建议姿势

每个里程碑完成后，可以这样请求 review：

```
我完成了 M4，改动文件：
- state_reader.py (+detect_gripper_contact)
- simulation_node.py (+publish contact)

现象：/world_state 在距离 0.3m 时为 false，0.18m 时为 true。
请 review 接口设计是否合理，不要直接改我代码。
```

避免：「推箱不行，帮我修」—— 应先贴日志、贴位移、贴你已查过的假设。

---

## 16. 完成后可选进阶（非第二期必须）

- 把 `arm_presets` 迁入 `chassis_common`，与 ROADMAP 表一致。
- 发布 `/task_goal`（EmbodiedGoal）+ 简单 `task_loader_node`。
- 根据 box 相对角度微调 `elbow`（ROADMAP 风险对策）。
- 真实 MuJoCo 夹爪碰撞（第三期或专项实验）。

---

**文档版本**：v1.0（对应第一期 commit `46cc7fb` 之后）  
**维护**：完成各里程碑后可在本文档对应节追加「实际采用参数」与踩坑记录。
