# 第二期 C++ 实施指南：产品路径（embodied_core + chassis_agent_cpp）

> **主读者**：熟悉 C++、Python 处于了解阶段的开发者。  
> **策略**：**C++ 写大脑与技能**；**Python 仅保留 MuJoCo 仿真身体**（接触、虚拟推箱）。  
> **前提**：第一期 Python Agent 已完成，作为行为对照与算法参考。  
> **关联**：[BRAIN_ROADMAP.md](./BRAIN_ROADMAP.md)、[PHASE2_CLASS_DIAGRAM.md](./PHASE2_CLASS_DIAGRAM.md)（类/函数职责）、Python 参考版 [PHASE2_IMPLEMENTATION_GUIDE.md](./PHASE2_IMPLEMENTATION_GUIDE.md)

**修订说明（v1.1）**：

- ❌ **跳过 P1b**：不在 C++ 里单独复现第一期；`pure_pursuit` 在 **M2** 写 `NavigateSkill` 时一并移植。
- ❌ **跳过 M1 `EmbodiedGoal.msg`**：第二期 FSM 用 C++ enum；语义目标消息留 **第三期**。
- ✅ **M2 末尾**：留 **0.5 天 ROS 冒烟**（仅导航，不跑完整 FSM）。
- ✅ **M8**：验收 + **真机硬件调研清单**。

---

## 0. 语言分工（必读）

| 层级 | 语言 | 包 | 第二期你要写吗 |
|------|------|-----|----------------|
| 算法 + FSM（无 ROS） | **C++** | `embodied_core` | ✅ 主战场 |
| Agent ROS 节点 | **C++** | `chassis_agent_cpp` | ✅ 主战场 |
| 键盘遥控 | C++ | `chassis_controller` | ❌ 只读参考 |
| MuJoCo 仿真 | Python | `chassis_simulation` | ⚠️ M4/M5 小改 |
| 模型 / 步进 | Python | `chassis_common` | ⚠️ M4/M5 小改 |
| 第一期 Agent（遗留） | Python | `chassis_agent` | ❌ 不扩展 |
| 消息 | `.msg` / `.srv` | `embodied_msgs` | ⚠️ 仅 M5 新增 `SetVirtualGrasp.srv` |

**Python 第二期仅改仿真侧**（见 [§8](#8-python-仿真侧-m4m5)）：其余全部 C++。

---

## 1. 目标架构

```
┌──────────────────────────────────────────────────────────┐
│  chassis_agent_cpp::AgentNode          (C++, rclcpp)      │
│    sub /world_state  →  embodied_core::PushRedBoxFSM     │
│    pub /control_cmd  ←  SkillExecutor                     │
│    cli /sim/set_virtual_grasp  (M5)                        │
└────────────────────────────┬─────────────────────────────┘
                             │ ROS 2
┌────────────────────────────▼─────────────────────────────┐
│  simulation_node (Python)                                 │
│    pub /world_state  +  contact  +  virtual attach        │
└──────────────────────────────────────────────────────────┘
```

### 1.1 为何拆 `embodied_core`

- **可测试**：Pure Pursuit、FSM 不依赖 `rclcpp`，可 gtest 单测。
- **可上车**：真机直接链 `embodied_core`，换 ROS 节点或裸线程即可。
- **Python 第一期** 的 `navigation.py` / `agent_node.py` 是移植源，不是扩展目标。

### 1.2 真机衔接（第二期结束时应能讲清）

```
仿真：/world_state → WorldView → FSM → EmbodiedCommand → simulation_node
真机：驱动/估计   → WorldView → FSM → EmbodiedCommand → chassis_driver_cpp
                         ↑ 第一个真机适配点：只换 I/O，embodied_core 不动
```

详见 [§13 M8：下一步选硬件](#13-m8-验收--下一步选硬件)。

---

## 2. 包结构（完成后）

```
ros2_ws/src/
├── embodied_msgs/
│   └── srv/SetVirtualGrasp.srv           # M5 新增（非 EmbodiedGoal）
│
├── embodied_core/                        # M2 新建（C++ 库）
│   ├── include/embodied_core/
│   │   ├── arm_preset.hpp
│   │   ├── navigation.hpp               # pure_pursuit（M2 移植）
│   │   ├── world_view.hpp
│   │   ├── skill_output.hpp
│   │   ├── navigate_skill.hpp
│   │   ├── manipulate_skill.hpp
│   │   ├── skill_executor.hpp
│   │   └── push_red_box_fsm.hpp         # M3
│   └── src/ ...
│
├── chassis_agent_cpp/                    # M2 新建（C++ 节点）
│   └── src/agent_node.cpp
│
├── chassis_controller/                   # 已有，rclcpp 模板
├── chassis_simulation/                   # Python，M4/M5
├── chassis_common/                       # Python，M4/M5
└── chassis_agent/                        # Python 第一期，冻结
```

**第三期再增**：`EmbodiedGoal.msg`、`embodied_policy_cpp`、`chassis_driver_cpp`。

---

## 3. 里程碑总览

| 里程碑 | 内容 | 语言 | 建议时间 |
|--------|------|------|----------|
| **M0** | 读代码 + 跑通 Python `--agent` 对照 | — | 0.5 天 |
| **M2** | `embodied_core` 技能层 + `pure_pursuit` 移植 + **ROS 冒烟** | C++ | 2–3 天 |
| **M3** | `PushRedBoxFSM` 骨架（假接触） | C++ | 1–2 天 |
| **M4** | 接触检测 | Python | 1 天 |
| **M5** | 虚拟推箱 + `SetVirtualGrasp.srv` | Py + C++ client | 2–3 天 |
| **M6** | 倒车 + 完整推箱验收 | C++ | 1 天 |
| **M7** | `hil_demo.sh --task push_red_box` | bash | 0.5 天 |
| **M8** | 验收记录 + **硬件调研清单** | md | 0.5–1 天 |

**合计**：约 **1.5–2 周**（业余）。  
**不做**：P1b 对齐第一期、M1 `EmbodiedGoal.msg`、P2-5 避障（可选）。

---

## 4. M0：准备（0.5 天）

**任务**：

1. 跑 `./scripts/hil_demo.sh --agent`，确认第一期 NAV → REACH。
2. 精读并对照：
   - `chassis_agent/navigation.py`（`pure_pursuit` 移植源）
   - `chassis_controller/src/controller_node.cpp`（rclcpp 模板）
   - `simulation_node.publish_state()`（`/world_state` 字段）
3. 画 topic 图：`/world_state` → Agent → `/control_cmd` → 仿真。

**验收**：能说明 kinematic 底盘停车为何不 drift（`sim_step.py`）。

---

## 5. M2：技能层 + pure_pursuit 移植 + ROS 冒烟（2–3 天）

### 5.1 本里程碑目标

一次性建立 C++ 主栈，**不单独做 P1b**：

1. 新建 `embodied_core`、`chassis_agent_cpp`。
2. 移植 `pure_pursuit` → `navigation.cpp`。
3. 实现 `NavigateSkill`、`ManipulateSkill`、`SkillExecutor`。
4. **M2 末**：`agent_node` 仅 **导航到红箱 standoff 并停车**（`ARM_STOW`），验证 ROS 胶水。

### 5.2 `arm_preset.hpp`

```cpp
#pragma once
namespace embodied_core {

struct ArmPreset {
  double shoulder{};
  double elbow{};
  double wrist{};
};

inline constexpr ArmPreset kArmStow{0.35, 0.0, 0.25};
inline constexpr ArmPreset kArmReach{0.55, 0.4, 0.3};
inline constexpr ArmPreset kArmGraspReady{0.45, 0.6, 0.2};

}  // namespace embodied_core
```

### 5.3 `navigation.hpp` / `navigation.cpp`

```cpp
struct NavigationCommand {
  double target_linear_x{0.0};
  double target_steering_angle{0.0};
  bool arrived{false};
};

NavigationCommand pure_pursuit(
    double x, double y, double yaw,
    double target_x, double target_y,
    double arrive_dist = 0.3,
    double look_ahead = 0.8,
    double max_vx = 1.0,
    double max_steer = 0.52,
    double wheelbase = 0.32);
```

**移植源**：`chassis_agent/navigation.py`，逐行对照，数值应一致。

### 5.4 `world_view.hpp`

FSM 与技能层 **不依赖** `embodied_msgs`：

```cpp
struct WorldView {
  double base_x{}, base_y{}, base_yaw{};
  double base_vx{}, base_steer{};
  double arm_shoulder{}, arm_elbow{}, arm_wrist{};
  double gripper{};
  std::vector<ObjectPose> objects;
  bool gripper_touching_object{false};
  std::string touched_object_name;

  std::optional<std::pair<double, double>> box_red_xy() const;
  std::optional<double> distance_to_box_red() const;
};
```

`agent_node.cpp` 中实现 `WorldView from_msg(const EmbodiedWorldState &)`。

**stuck 辅助**（M3 FSM 也会用）：

```cpp
bool stuck_at_box(const WorldView &w, double cmd_vx) {
  auto dist = w.distance_to_box_red();
  if (!dist) return false;
  if (*dist <= 0.52 && cmd_vx > 0.05) return true;
  return cmd_vx > 0.15 && std::abs(w.base_vx) < 0.05 && *dist < 0.75;
}
```

### 5.5 `NavigateSkill`

```cpp
class NavigateSkill {
 public:
  explicit NavigateSkill(double standoff = 0.35, double arrive_dist = 0.3);

  SkillOutput compute(const WorldView &world,
                      double target_x, double target_y,
                      bool reverse = false) const;

  SkillOutput compute_to_box_red(const WorldView &world, bool reverse = false) const;
};
```

- 前进：内部调 `pure_pursuit`。
- `compute_to_box_red`：目标 = `(box_x - standoff, box_y)`，无 box 时用 fallback `(2.15, 0)`。
- `reverse`：M6 再完善；M2 可留空实现。

### 5.6 `ManipulateSkill` + `SkillExecutor`

与旧版 §6.3–6.4 相同：`Preset` / `GripperAction` enum，`arm_at_preset()` / `gripper_at()` 静态判据。

### 5.7 CMake 模板

**`embodied_core/CMakeLists.txt`**（M2 最小集）：

```cmake
add_library(embodied_core SHARED
  src/navigation.cpp
  src/world_view.cpp
  src/navigate_skill.cpp
  src/manipulate_skill.cpp
  src/skill_executor.cpp
)
target_include_directories(embodied_core PUBLIC include)
# ament_export_targets ...
```

**`chassis_agent_cpp/CMakeLists.txt`**：

```cmake
add_executable(agent_node src/agent_node.cpp)
ament_target_dependencies(agent_node rclcpp embodied_msgs)
target_link_libraries(agent_node embodied_core::embodied_core)
```

### 5.8 M2 末：ROS 冒烟（0.5 天，必做）

`agent_node` **临时**逻辑（不必上 FSM）：

```cpp
// 伪代码
if (!world) { publish zero; return; }
auto out = navigate_skill_.compute_to_box_red(world);
if (out 对应 arrived || stuck_at_box) { vx=0; steer=0; }
// 臂保持 kArmStow
publish EmbodiedCommand
```

```bash
colcon build --packages-select embodied_core chassis_agent_cpp
source install/setup.bash
# 终端1: simulation_node  终端2:
ros2 run chassis_agent_cpp agent_node
```

**M2 验收清单**：

- [ ] `pure_pursuit` gtest 或手工断言与 Python 同输入输出接近
- [ ] 机器人能导航到红箱前并停车（允许 ±0.1 m）
- [ ] 日志有 vx / steer
- [ ] **不要求** ARM_REACH（那是 M3 FSM 的事）

---

## 6. M3：PushRedBoxFSM（1–2 天）

### 6.1 状态与转移

```
IDLE → NAV_TO_RED → REACH_ARM → CLOSE_GRIPPER → BACK_UP → DONE
                                              ↘ FAILED（超时）
```

```cpp
enum class PushRedBoxPhase : uint8_t {
  Idle, NavToRed, ReachArm, CloseGripper, BackUp, Done, Failed
};

class PushRedBoxFSM {
 public:
  struct Config {
    double standoff{0.35};
    double arrive_dist{0.3};
    double push_min_dist{0.20};
    double max_vx_reverse{0.35};
  };

  SkillOutput tick(const WorldView &world, SkillExecutor &executor, double dt_sec);

  bool should_enable_virtual_grasp() const;   // M5
  bool should_disable_virtual_grasp() const;

 private:
  void transition(PushRedBoxPhase next, const char *reason);
};
```

**M3 阶段 `CLOSE_GRIPPER`**：仅用 `gripper > 0.95` 跳转，**暂不检查 contact**（M4 再接）。

**日志格式**：

```
FSM NavToRed -> ReachArm: arrived dist=0.28
FSM CloseGripper -> BackUp: gripper closed (contact pending M4)
```

**M3 验收**：

- [ ] 能 NAV → REACH_ARM（日志可见 FSM 切换）
- [ ] 假接触下能进入 BACK_UP 占位（vx=0 可先）

---

## 7. M4：接触检测（Python，1 天）

| 文件 | 改动 |
|------|------|
| `chassis_common/state_reader.py` | `read_gripper_position`、`detect_gripper_contact` |
| `chassis_simulation/simulation_node.py` | 填充 `gripper_touching_object` |

```python
GRIP_CONTACT_DIST = 0.22
GRIP_CONTACT_Z_TOL = 0.15
```

算法规格：[PHASE2_IMPLEMENTATION_GUIDE.md §6](./PHASE2_IMPLEMENTATION_GUIDE.md)。

C++ FSM `CLOSE_GRIPPER` 改为：`gripper > 0.95 && world.gripper_touching_object`。

**验收**：`ros2 topic echo /world_state --field gripper_touching_object` 在箱旁为 true。

---

## 8. Python 仿真侧 M4/M5

| 文件 | 改动 |
|------|------|
| `chassis_common/interaction.py` | **新建** `VirtualGraspState`、`apply_virtual_grasp` |
| `chassis_common/sim_step.py` | 步进末尾 attach |
| `chassis_simulation/simulation_node.py` | `SetVirtualGrasp` service server |

---

## 9. M5：Virtual Grasp Service（2–3 天）

### 9.1 `embodied_msgs/srv/SetVirtualGrasp.srv`

```
bool enable
string object_name
---
bool success
string message
```

**说明**：这是第二期 **唯一新增** 的 msg/srv 定义；**不要**在此里程碑加 `EmbodiedGoal.msg`。

### 9.2 C++ Agent

FSM 进入 `BackUp` → `enable=true, object_name="box_red"`；`Done`/`Failed` → `enable=false`。

### 9.3 M5 验收

遥控或 Agent：attach 后倒车，红箱随动，不飞天、不穿地。

---

## 10. M6：倒车 + 完整验收（1 天）

`NavigateSkill` 实现 `reverse=true`：`target_linear_x = -max_vx_reverse`（建议 0.35 m/s）。

**成功判据**（进入 BACK_UP 时记录 box 初值）：

- `hypot(box_x - box_x0, box_y - box_y0) >= 0.20 m`

---

## 11. M7：启动脚本（0.5 天）

```bash
./scripts/hil_demo.sh --agent-cpp          # C++ Agent
./scripts/hil_demo.sh --task push_red_box  # 完整任务
```

编译包列表加入 `embodied_core`、`chassis_agent_cpp`。

---

## 12. 编译与调试

```bash
source /opt/ros/lyrical/setup.bash
cd /home/changwei/changwei/project/ros2_ws

colcon build --packages-select embodied_msgs embodied_core chassis_agent_cpp \
  --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo

colcon build --packages-select chassis_common chassis_simulation --symlink-install

source install/setup.bash
ros2 interface show embodied_msgs/srv/SetVirtualGrasp   # M5 后
```

**单元测试（embodied_core gtest）**：

```bash
./scripts/run_embodied_core_tests.sh
```

Skill： [`.cursor/skills/cpp-unit-test/`](../.cursor/skills/cpp-unit-test/SKILL.md)（读 diff → 补 test → 出 Markdown 报告）。

---

## 13. M8：验收 + 下一步选硬件

### 13.1 第二期软件验收

1. `./scripts/hil_demo.sh --task push_red_box` 一键 C++ Agent。
2. 自动：导航 → 伸臂 → 夹爪 → 倒车，红箱位移 ≥ 0.2 m。
3. 日志可 `grep 'FSM .* -> .*'`。
4. 能口头解释：`embodied_core` vs `chassis_agent_cpp`、virtual attach 为何在 Python。

可选：在 `docs/PHASE2_ACCEPTANCE.md` 记录命令、日志片段、box 位移数值。

### 13.2 下一步：硬件调研清单（必做）

第二期软件验收通过后，填写下表（可新建 `docs/HARDWARE_RESEARCH.md`）：

#### A. 差速移动底盘

| 调研项 | 说明 | 你的结论（待填） |
|--------|------|------------------|
| 候选平台 | 带 encoders、可接 ROS 2 的差速小车 / AGV 套件 | |
| 驱动接口 | `cmd_vel` 还是厂商自定义？与 `EmbodiedCommand.target_linear_x/steer` 如何映射？ | |
| 控制频率 | 是否 ≥ 50 Hz？延迟大概多少？ | |
| 参考驱动包 | `ros2_control` / 厂商 SDK / 自写 `chassis_driver_cpp` | |

#### B. 3DOF 机械臂 + 夹爪

| 调研项 | 说明 | 你的结论（待填） |
|--------|------|------------------|
| 自由度 | 至少 3 旋转关节 + 1 夹爪 DOF | |
| 关节范围 | 能否覆盖 `kArmStow` / `kArmReach` / `kArmGraspReady` 工作空间？ | |
| 控制方式 | 位置控制 / 速度 / 力矩；与仿真 `EmbodiedCommand` 关节角字段如何对应？ | |
| 夹爪 | 开合反馈是否可用（对标 `world.gripper`）？ | |

#### C. 上位机

| 调研项 | 说明 | 你的结论（待填） |
|--------|------|------------------|
| 算力 | Jetson Orin Nano / Orin NX / x86 Mini PC | |
| 负载 | 仅 `chassis_agent_cpp` + 驱动，还是含相机 / SLAM？ | |
| OS | Ubuntu + ROS 2 版本是否与开发机一致（lyrical）？ | |
| 实时性 | 硬实时需求低可先普通 Linux；急停建议硬件链路 | |

#### D. `embodied_core` 第一个真机适配点

按优先级实施：

```
1. WorldView 适配层（chassis_agent_cpp 或 embodied_core/adapters/）
   - 真机：从 Odometry + JointState + 感知 拼 WorldView
   - 仿真：从 EmbodiedWorldState 拼 WorldView（已有）

2. 输出适配层 chassis_driver_cpp
   - 输入：EmbodiedCommand
   - 输出：底盘 motor cmd + 臂 trajectory / joint targets

3. embodied_core 本库：FSM / NavigateSkill / ManipulateSkill 不改
```

**建议第一个真机里程碑（第三期前）**：

> 真机 **只验证 NavigateSkill**：给定 WorldView，车能开到标记点 ±0.3 m；臂可先 manual / 固定 STOW。

#### E. 仿真与真机差异（提前想）

| 项目 | 仿真 | 真机 |
|------|------|------|
| 物体位姿 | `/world_state` 真值 | 需感知或标定 |
| 推箱 | virtual attach | 物理摩擦 / 真抓；可能需新 FSM 分支 |
| 接触 | 距离 heuristic | 力传感 / 电流 / 视觉 |

---

## 14. 第三期衔接

| 模块 | 语言 | 何时 |
|------|------|------|
| `EmbodiedGoal.msg` + `/task_goal` | `.msg` | 第三期 LLM/规划需要时 |
| `embodied_gym` | Python | RL 训练 |
| `embodied_policy_cpp` | C++ | 策略上车 |
| `chassis_driver_cpp` | C++ | 硬件调研完成后 |
| `task_planner_node` | Python/云端 | 可选 |

---

## 15. 调参表

| 参数 | 值 |
|------|-----|
| standoff | 0.35 m |
| arrive_dist | 0.30 m |
| GRIP_CONTACT_DIST | 0.22 m |
| push_min_dist | 0.20 m |
| max_vx_reverse | 0.35 m/s |
| arm_tol | 0.08 rad |
| gripper_closed | 0.95 |

---

## 16. 与 Python 参考指南的关系

| 主题 | 看哪份 |
|------|--------|
| FSM 状态图、接触/虚拟推箱公式 | [PHASE2_IMPLEMENTATION_GUIDE.md](./PHASE2_IMPLEMENTATION_GUIDE.md) |
| C++ 接口、里程碑、硬件清单 | **本文档** |
| `pure_pursuit` 参考实现 | `chassis_agent/navigation.py` |
| rclcpp 节点模板 | `chassis_controller/src/controller_node.cpp` |

---

**文档版本**：v1.1  
**维护**：完成各 M* 后追加实际参数与踩坑；硬件调研写入 `docs/HARDWARE_RESEARCH.md`。
