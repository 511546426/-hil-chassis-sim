# W03D21 — 参数表与 W3 周验收

日期：2026-09-17
状态：PASS（目标物体泛化延期）

## 今日目标

整理项目中已经声明的 ROS Parameter 和 Launch argument，记录类型、默认值、合法范围、动态修改能力及 Launch 暴露情况，并复核 Parameter、Namespace、Remapping 和 Launch 的职责边界，完成第三周学习验收。

## 审计方法

搜索 C++ Parameter：

```bash
rg -n \
  'declare_parameter|get_parameter' \
  ros2_ws/src \
  --glob '*.cpp' \
  --glob '*.hpp'
```

搜索 Python Parameter：

```bash
rg -n \
  'declare_parameter|get_parameter' \
  ros2_ws/src \
  --glob '*.py'
```

搜索 Launch 配置：

```bash
rg -n \
  'DeclareLaunchArgument|LaunchConfiguration|ParameterValue|parameters=' \
  ros2_ws/src \
  --glob '*.py'
```

必须区分：

- `declare_parameter()` 声明节点拥有的 ROS Parameter；
- `DeclareLaunchArgument` 声明 Launch 的启动输入；
- `LaunchConfiguration` 延迟读取 Launch argument；
- `Node(parameters=...)` 才会把 Launch 配置传给节点参数；
- 普通 C++ 或 Python 常量不会自动出现在 ROS 参数系统中。

## `topic_logger_node` 参数表

| 参数 | 类型 | 默认值 | 合法范围 | 启动覆盖 | 动态修改 | Launch 暴露 |
|---|---|---|---|---|---|---|
| `topic_name` | string | `/chassis_state` | 非空 | 是 | 否，明确拒绝 | 否 |
| `log_every_n` | integer | `50` | `> 0` 且在 `int` 范围内 | 是 | 是 | 否 |

`topic_name` 在创建 Subscription 时使用。运行期间只修改字符串不能让已有 Subscription 自动连接新 Topic，因此参数回调明确拒绝动态修改。

`log_every_n` 只影响回调中的计数判断，可以在参数回调校验后安全更新。动态修改后日志频率立即变化。

验证命令：

```bash
ros2 param get /topic_logger_node topic_name
ros2 param get /topic_logger_node log_every_n
ros2 param set /topic_logger_node log_every_n 2
ros2 param set /topic_logger_node topic_name /another_state
```

结果：`log_every_n` 修改成功，`topic_name` 的运行时修改被拒绝。

## `agent_node_cpp` 参数表

| 参数 | 类型 | 默认值 | 当前校验或约束 | 启动覆盖 | 动态修改 | Agent Launch 暴露 |
|---|---|---|---|---|---|---|
| `brain` | string | `rule` | `rule`、`rl`、`hybrid`、`auto` | 是 | 否 | 固定传入 `rule` |
| `policy` | string | 空字符串 | `rl`、`hybrid` 时必须非空 | 是 | 否 | 否 |
| `task` | string | `nav_to_box_red` | 当前主要支持红箱导航或推箱任务 | 是 | 否 | 否 |
| `standoff` | double | `0.35` | 尚无显式范围校验 | 是 | 否 | 否 |
| `arrive_dist` | double | `0.30` | 尚无显式范围校验 | 是 | 否 | 否 |
| `push_min_dist` | double | `0.20` | 有限且 `> 0` | 是 | 否 | 是 |
| `listen_task_plan` | bool | `true` | bool | 是 | 否 | 否 |
| `auto_push_brain` | string | `rule` | 用于 auto 模式选择推箱 Brain | 是 | 否 | 否 |

这些参数都在节点构造阶段读取，没有注册运行时更新回调，因此表中记录为启动时配置。

`agent.launch.py` 当前只把 `push_min_dist` 声明为可覆盖的 Launch argument，并固定传入 `brain=rule`。执行：

```bash
ros2 launch chassis_agent_cpp \
  agent.launch.py \
  --show-args
```

可以看到：

```text
push_min_dist
default: 0.20
```

使用 `push_min_dist:=0.15` 启动后，节点参数和启动日志均显示 `0.15`，证明 Launch argument 已传入实际 ROS Parameter。

## `simulation_node` 参数表

| 参数 | 类型 | 默认值 | 当前校验 | 启动覆盖 | 动态修改 | Launch 暴露 |
|---|---|---:|---|---|---|---|
| `max_linear_accel` | double | `0.5` | 未显式校验 | 是 | 否 | 否 |
| `max_linear_decel` | double | `1.0` | 未显式校验 | 是 | 否 | 否 |
| `max_steer_rate` | double | `1.2` | 未显式校验 | 是 | 否 | 否 |
| `max_joint_rate` | double | `1.5` | 未显式校验 | 是 | 否 | 否 |

Simulation 在构造函数中读取这些参数，并用它们创建 `EmbodiedTracker`。没有动态参数回调，因此运行时修改参数服务器中的值不能保证 Tracker 配置同步改变。

`chassis_simulation/hil_demo.launch.py` 声明的 `python_exe` 是 Launch argument，不是 Simulation ROS Parameter。

## Python `agent_node` 参数表

| 参数 | 类型 | 默认值 | 用途 | 动态修改 |
|---|---|---:|---|---|
| `target_x` | double | `2.5` | 找不到红箱观测时的 fallback X | 否 |
| `target_y` | double | `0.0` | 找不到红箱观测时的 fallback Y | 否 |
| `arrive_dist` | double | `0.3` | 导航到达阈值 | 否 |

这三个值只在节点构造时读取。正常情况下节点优先使用 `/world_state` 中的实时红箱位置，`target_x` 和 `target_y` 是 fallback，而不是持续假设红箱位于固定坐标。

## `task_planner_node` 参数表

| 参数 | 类型 | 默认值 | 合法值或约束 | 动态修改 |
|---|---|---|---|---|
| `planner_backend` | string | `template` | `template`、`llm`、`llm_mock` | 否 |
| `llm_config` | string | 空字符串 | 可选 LLM 配置文件路径 | 否 |

Planner 在构造阶段根据 `planner_backend` 创建具体实现。未知 backend 会抛出明确错误。`llm_config` 仅在 `llm` backend 下使用。

## Launch argument 表

| Package / Launch | Argument | 默认值 | 是否为节点 Parameter |
|---|---|---|---|
| `chassis_agent_cpp/agent.launch.py` | `push_min_dist` | `0.20` | 是，传给 Agent |
| `chassis_simulation/hil_demo.launch.py` | `python_exe` | embodied Python 路径 | 否，用于选择进程解释器 |
| `learning_tools_cpp/learning_bringup.launch.py` | `enable_topic_logger` | `true` | 否，用作启动条件 |
| `learning_tools_cpp/learning_bringup.launch.py` | `enable_cmd_monitor` | `true` | 否，用作启动条件 |

`namespaced_monitors.launch.py` 为两个节点传入固定参数值，但当前没有声明可从命令行覆盖的 Launch argument。

## Namespace 周验收

执行：

```bash
ros2 launch learning_tools_cpp \
  namespaced_monitors.launch.py
```

ROS Graph 中出现：

```text
/robot1/state_monitor
/robot2/state_monitor
```

两个节点分别订阅：

```text
/robot1/chassis_state
/robot2/chassis_state
```

它们使用相同基础节点名和相对 Topic 名，但 Namespace 不同，因此完整节点名、Topic 和参数服务相互隔离。

## 配置机制选择

| 需求 | 推荐机制 |
|---|---|
| 修改阈值、日志频率和运行配置 | Parameter |
| 一次启动多个节点并传入配置 | Launch |
| 为相同节点创建多个隔离实例 | Namespace |
| 在部署阶段替换 Topic 或 Service 名称 | Remapping |
| 保存一组可复用节点参数 | YAML 参数文件 |

Parameter 与 Remapping 都可能影响节点连接，但语义不同。Parameter 是节点主动提供的业务配置；Remapping 是 ROS Graph 层的通用名称替换。

Namespace 只自动作用于相对名称。以 `/` 开头的绝对 Topic 不会因为节点进入 `/robot1` 而变成 `/robot1/topic`。

## W3 已完成内容

- 为学习节点声明 `topic_name` 和 `log_every_n`；
- 使用 CLI 查询和覆盖 Parameter；
- 为 `log_every_n` 实现运行时动态更新；
- 对非法参数给出明确错误；
- 明确拒绝不安全的动态 Topic 修改；
- 使用 Namespace 启动两个隔离的监控节点；
- 验证相对名称、绝对名称和 Remapping；
- 审计项目绝对 Topic、红箱耦合和控制频率；
- 将 `push_min_dist` 暴露为 Agent Parameter；
- 通过 Launch argument 配置 `push_min_dist`；
- 整理项目参数表和配置机制边界。

## 延期项：目标物体泛化

第三周原计划包含通过同一个 Launch 选择 `box_red` 或 `box_blue`。当前尚未真正实现这一目标。

原因是红箱不仅是一个参数默认值，还存在于：

```text
PushRedBoxFSM
push_red_box
box_red_xy()
distance_to_box_red()
NavigateSkill::compute_to_box_red()
```

只新增 `target_object=box_blue` 并不能让上述逻辑自动处理蓝箱。真正泛化需要调整 TaskGoal、WorldView、Skill 和 FSM 的接口与测试，因此记录为后续任务泛化专题，而不是在 Day21 制造一个没有实际效果的参数。

W3 结论：

```text
Parameter、Namespace、Remapping 与 Launch：PASS
任意目标物体切换：DEFERRED
```

## 今日结论

第三周完成了从单一参数声明到部署配置体系的学习闭环。节点负责定义参数和校验，Launch 负责组织启动和传值，Namespace 负责多实例隔离，Remapping 负责部署时替换通信名称。

参数能被 `ros2 param get` 读取不代表程序支持动态更新；Launch argument 能被 `--show-args` 显示也不代表节点已经实际使用。完整验收必须继续检查节点日志、ROS Parameter 值、ROS Graph 连接和错误路径。

## 算法支线

完成 LeetCode 104“二叉树的最大深度”，代码位于 `test/day21.cpp`。

递归定义为：空节点深度为 0；非空节点的最大深度等于左右子树最大深度中的较大值加 1。

```text
maxDepth(node)
  = max(maxDepth(node.left), maxDepth(node.right)) + 1
```

设树有 `n` 个节点、树高为 `h`：

- 时间复杂度：O(n)；
- 递归调用栈：O(h)；
- 平衡树为 O(log n)；
- 退化树最坏为 O(n)。
