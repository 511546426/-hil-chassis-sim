# W03D18 — Topic、目标与控制频率硬编码审计

日期：2026-09-09
状态：PASS

## 今日目标

审计项目中的绝对 Topic 和 Service 名称、红箱任务与坐标、成功阈值以及控制频率，判断哪些内容适合 Parameter、Namespace 或 Remapping，并为 Day19 选择一个低风险参数化目标。本日只形成审计结论，不进行主项目改造。

## 审计方法

搜索 C++ 和 Python 源码中的绝对 ROS 名称：

```bash
rg -n \
  "['\"]/[^'\"]+['\"]" \
  ros2_ws/src \
  --glob '*.cpp' \
  --glob '*.hpp' \
  --glob '*.py'
```

搜索目标物体、坐标和任务名称：

```bash
rg -n \
  'box_red|red_box|target_object|target_x|target_y' \
  ros2_ws/src \
  --glob '*.cpp' \
  --glob '*.hpp' \
  --glob '*.py'
```

搜索任务阈值：

```bash
rg -n \
  'push_min|arrival|tolerance|distance|reach_dist|goal_dist' \
  ros2_ws/src \
  --glob '*.cpp' \
  --glob '*.hpp' \
  --glob '*.py'
```

搜索 Timer 和控制周期：

```bash
rg -n \
  'create_wall_timer|create_timer|milliseconds|control_hz|publish_hz|rate_hz|frequency|timestep|0\.02' \
  ros2_ws/src \
  --glob '*.cpp' \
  --glob '*.hpp' \
  --glob '*.py'
```

搜索本身不依赖 ROS 2 运行环境，因此在 base shell 中执行不影响结果。只有构建和运行 ROS 2 节点时才需要加载项目环境。

## 绝对 ROS 名称

### 控制与状态闭环

| 名称 | 主要 Publisher | 主要 Subscriber |
|---|---|---|
| `/control_cmd` | C++ Agent、Python Agent、Controller | Simulation、学习监控节点 |
| `/chassis_state` | Simulation | Controller、学习监控节点 |
| `/arm_state` | Simulation | Controller |
| `/world_state` | Simulation | C++ Agent、Python Agent |

当前主控制数据流为：

```text
Simulation
├── /chassis_state → Controller
├── /arm_state → Controller
└── /world_state → Agent

Agent / Controller
└── /control_cmd → Simulation
```

这些 Topic 都采用绝对名称，因此把单个节点放入 `/robot1` Namespace 不会自动得到 `/robot1/control_cmd` 或 `/robot1/world_state`。如果以后同时运行两套机器人，不同实例可能共享状态或向同一个控制 Topic 发布命令。

`/control_cmd` 还存在多个可能的 Publisher。若 C++ Agent、Python Agent 和手动 Controller 同时运行，Simulation 会收到多个控制源的消息。ROS 2 允许多个 Publisher，但业务层必须明确仲裁或保证启动互斥。

### 任务规划链路

| 名称 | Publisher | Subscriber |
|---|---|---|
| `/task_request` | 外部任务入口 | Planner |
| `/task_plan` | Planner | C++ Agent |

链路为：

```text
/task_request → Planner → /task_plan → Agent
```

全局任务 Topic 适合当前单实例演示。多实例部署时，应让 Planner 和 Agent 使用一致的 Namespace 或 Remapping，避免一条任务被错误实例接收。

### Service

| 名称 | 用途 |
|---|---|
| `/sim/set_virtual_grasp` | Agent 请求仿真启用或释放虚拟抓取 |
| `/sim/reset_episode` | 复位仿真世界状态 |
| `/agent/reset_episode` | 复位 Agent 或 Brain 状态 |

`/sim/reset_episode` 和 `/agent/reset_episode` 是两个不同 Service。后续 Service 专题需要确认 episode reset 的调用顺序和异常路径，避免仿真状态与 Agent 状态不同步。

## Namespace 风险结论

当前系统采用单实例全局 ROS Graph：

```text
/control_cmd
/world_state
/task_plan
/sim/*
/agent/*
```

多机器人改造不能只修改 Agent。Simulation、Controller、Planner 和 Agent 必须使用同一套相对名称、Namespace 与 Remapping 规则，否则完整通信链路会断开。因此 Day18 只记录风险，不进行零散改名。

## 红箱名称与坐标

MuJoCo 场景在 `chassis_common/model.py` 中定义：

```text
box_red position = (2.5, 0.0, 0.18)
box_blue position = (-2.0, 1.5, 0.14)
```

这些值属于仿真模型和场景初始状态，不应仅因为是常量就直接改成 ROS Parameter。

C++ 主路径通过 `/world_state` 获取物体位置，并由 `WorldView::box_red_xy()`、`distance_to_box_red()` 和 `NavigateSkill::compute_to_box_red()` 使用实时观测。Agent 并非始终假设红箱固定在初始坐标。

Python Agent 中的 `RED_BOX_X` 和 `RED_BOX_Y` 已作为 `target_x`、`target_y` Parameter 声明，并只在观测中找不到红箱时作为 fallback 使用。因此这两个坐标已有基本配置入口。

`box_red` 还贯穿以下业务概念：

```text
push_red_box
nav_to_box_red
PushRedBoxFSM
box_red_xy()
distance_to_box_red()
```

这属于当前“推红箱”任务的架构耦合，而不只是一个字符串常量。泛化到任意物体需要同时调整 TaskGoal、FSM、WorldView 和 Skill 接口，不适合作为 Day19 的低风险练习。

测试代码中的 `box_red` 是测试输入和断言，不能因为搜索命中就当作生产配置全部替换。

## 成功阈值

最小推动距离定义在 `PushRedBoxFSM::Config`：

```cpp
double push_min_dist{0.20};
```

FSM 在 BackUp 阶段使用：

```cpp
if (has_box_push_origin_ && moved >= config_.push_min_dist)
```

这说明核心库已经支持通过 Config 调整阈值。但 `chassis_agent_cpp` 目前只把 `standoff` 和 `arrive_dist` 从 ROS Parameter 传入 FSM，没有声明和传入 `push_min_dist`。

因此 `push_min_dist` 是当前最合适的低风险参数化目标：

- Core 已经存在配置字段；
- Agent 只缺 ROS Parameter 入口；
- 保持默认值 `0.20` 时现有行为不变；
- 可以清晰验证合法值和错误值；
- Day20 可以继续在 Launch 中暴露该参数。

## 控制频率

当前主要循环均采用 `0.02 s` 或 `20 ms`：

| 组件 | 当前配置 | 等效频率 |
|---|---:|---:|
| MuJoCo 模型 timestep | `0.02 s` | 50 Hz |
| Simulation 状态发布 Timer | `TIMESTEP` | 50 Hz |
| C++ Agent 命令 Timer | `20 ms` | 50 Hz |
| Controller 命令 Timer | `20 ms` | 50 Hz |
| Python Agent 命令 Timer | `0.02 s` | 50 Hz |

换算公式为：

```text
frequency_hz = 1 / period_sec
50 Hz = 1 / 0.02 s
```

当前各组件频率一致，但周期分散在多个文件。未来如果只修改一处，可能导致仿真步长、状态发布和命令发布频率不一致。

控制频率值得后续统一配置，但它会影响 Timer、仿真和完整闭环稳定性，风险高于 `push_min_dist`，不作为 Day19 的首个参数化目标。

## 配置机制选择

| 内容 | 建议机制 |
|---|---|
| 日志频率、任务阈值、fallback 坐标 | Parameter |
| 部署时替换 Topic 或 Service 连接 | Remapping |
| 多机器人和多实例隔离 | Namespace + 相对名称 |
| MuJoCo 场景几何与初始物体 | 模型或场景配置 |
| 当前任务专用 FSM 和 Skill | 后续架构泛化，不做简单字符串替换 |

不是所有常量都应该成为 Parameter。只有需要在部署、实验或任务之间调整，并且能定义清晰合法范围的配置，才适合暴露为运行参数。

## Day19 改造选择

选择 `push_min_dist` 作为下一个低风险改造项。

计划在 `chassis_agent_cpp` 中声明：

```cpp
declare_parameter("push_min_dist", 0.20);
```

并传入 FSM：

```cpp
cfg.fsm.push_min_dist =
    node.get_parameter("push_min_dist").as_double();
```

后续需要补充：

- 默认值验证；
- `push_min_dist > 0.0` 的范围校验；
- CLI 覆盖验证；
- 默认参数下 smoke test 回归。

## 今日结论

今天完成了绝对 ROS 名称、红箱任务耦合、任务阈值和控制频率的项目审计。当前全局 Topic 设计适合单实例演示，但多实例运行存在数据串扰风险；红箱名称是跨模块任务设计，不能通过替换一个常量完成泛化；控制周期虽然保持 50 Hz 一致，但存在多点重复定义。

`push_min_dist` 已在 Core Config 中具备配置能力，却没有暴露为 ROS Parameter，是最适合 Day19 完成的低风险参数化改造。

## 算法支线

完成 LeetCode 102“二叉树的层序遍历”，代码位于 `test/day18.cpp`。

算法使用队列进行广度优先遍历。每轮开始时保存当前队列长度 `level_size`，本轮只处理这些节点；处理过程中加入的左右孩子留到下一轮，从而保留层级信息。

设二叉树有 `n` 个节点、最大宽度为 `w`：

- 时间复杂度：O(n)；
- 队列空间复杂度：O(w)；
- 结果空间复杂度：O(n)。
