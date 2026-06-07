# 模块测试参考（navigation / FSM / Skill）

> 主流程见 [SKILL.md](./SKILL.md)。Agent 读 diff 后按本文件补用例。

## 白名单路径

| 路径 | 测试文件 | 优先级 |
|------|----------|--------|
| `include/embodied_core/world_view.hpp` | `test/test_world_view.cpp` | ✅ 已有 |
| `navigation.hpp` / `navigation.cpp` | `test/test_navigation.cpp` | 高 |
| `navigate_skill.*` | `test/test_navigate_skill.cpp` | 高 |
| `manipulate_skill.*` | `test/test_manipulate_skill.cpp` | 中 |
| `skill_executor.*` | `test/test_skill_executor.cpp` | 中 |
| `push_red_box_fsm.*` | `test/test_push_red_box_fsm.cpp` | 中（见下） |

**不在 UT skill 范围**：`chassis_simulation/`、`chassis_common/`（MuJoCo）、`chassis_agent_cpp` 节点 spin → 用 `./scripts/hil_demo.sh` 冒烟。

---

## pure_pursuit / navigation

对照 Python：`ros2_ws/src/chassis_agent/chassis_agent/navigation.py`

| 用例 | 输入要点 | 期望 |
|------|----------|------|
| `already_at_goal` | dist < arrive_dist | vx=0, arrived=true |
| `drive_forward` | 目标在前方 2m | vx>0, \|steer\| 小 |
| `large_heading_error` | yaw 与目标差 >45° | vx 降低（若实现 k_slow） |
| `python_parity` | 与 Python 同组 x,y,yaw,tx,ty | vx/steer 近似（EXPECT_NEAR） |

常量：`arrive_dist=0.3`, `look_ahead=0.8`, `max_vx=1.0`, `wheelbase=0.32`

---

## NavigateSkill

| 用例 | 说明 |
|------|------|
| `compute_to_box_red_with_box` | objects 含 box_red，目标点在 standoff 前 |
| `compute_to_box_red_fallback` | 无 box，fallback (2.15, 0) 或参数化 fallback |
| `reverse_negative_vx` | reverse=true → vx < 0（M6 后） |

构造 `WorldView` 用 `make_world_with` 辅助函数（与 `test_world_view.cpp` 一致）。

---

## ManipulateSkill

| 用例 | 说明 |
|------|------|
| `preset_stow_reach` | 输出关节角等于 kArmStow / kArmReach |
| `gripper_open_close` | Open→0, Close→1 |
| `arm_at_preset_within_tol` | 实际角接近预设 → true |
| `arm_at_preset_outside_tol` | 差 > tol → false |

---

## PushRedBoxFSM（不要一次测全链）

FSM 用 **固定 WorldView 序列 + 多帧 tick**，不测 ROS。

| 用例 | 做法 |
|------|------|
| `idle_to_nav` | 首帧有效 world → phase NavToRed |
| `nav_to_reach_arrived` | mock Executor 或真实 Executor + 到达 dist |
| `reach_to_close_arm_ready` | arm_at_preset 满足后转移 |
| `close_to_back_gripper_contact` | gripper≈1 且 gripper_touching_object |
| `back_to_done_box_moved` | 记录 box 初值，更新 world 中 box 位置 |

若未抽象 Fake Executor，M3 可先测 **转移条件**（extract 为 free function）再测完整 FSM。

---

## Python 仿真（可选 pytest，非本 skill 默认）

| 函数 | 测法 |
|------|------|
| `detect_gripper_contact` | mock gripper/box 坐标，不测 MuJoCo |

触发语：用户明确说「Python 仿真单测」时再启用。
