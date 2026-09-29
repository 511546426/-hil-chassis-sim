# W04D22 — Topic、Service 与 Action 选型

日期：2026-09-29
状态：PASS

## 今日目标

进入 W4 Service 专题，比较 Topic、Service 和 Action 的通信模型，使用 ROS 2 CLI 检查项目接口并调用 Reset Service，理解通信成功、业务成功以及服务可用性之间的区别，为后续异步 Service Client 实验建立选型基础。

## 三种通信机制

| 机制 | 通信模型 | 直接响应 | 进度反馈 | 取消 | 典型用途 |
|---|---|---|---|---|---|
| Topic | 发布/订阅 | 否 | 不适用 | 不适用 | 连续状态、控制指令、传感器数据 |
| Service | 一次请求/一次响应 | 是 | 否 | 否 | Reset、查询、短时间操作 |
| Action | Goal/Feedback/Result | 是 | 是 | 是 | 导航、操作臂任务、长时间任务 |

选择接口时不应只考虑“能否传输数据”，还要考虑通信频率、任务持续时间、调用者是否需要结果、是否需要进度，以及是否允许中途取消。

## ROS Graph 的运行时特性

加载 workspace overlay 后执行：

```bash
ros2 topic list
```

在没有项目节点运行时，只看到：

```text
/parameter_events
/rosout
```

此时查询：

```bash
ros2 topic info /control_cmd -v
```

会得到：

```text
Unknown topic '/control_cmd'
```

这不是构建或环境错误。ROS 2 没有永久注册 Topic 的中心服务器，Topic 和 Service 由当前正在运行的节点端点组成。`source install/setup.bash` 只让 CLI 能发现安装空间中的 Package，不会自动启动节点或创建 ROS Graph 端点。

启动 Agent 后，Graph 中才会出现 `/control_cmd`、`/world_state`、`/task_plan` 和 `/agent/reset_episode` 等端点。

## Topic 选型

### `/control_cmd`

Agent 或 Controller 以约 50 Hz 持续发布控制命令，Simulation 消费最新指令。Topic 适合该场景，因为：

- 数据持续产生；
- Publisher 不应为每帧命令等待 Response；
- 可能存在多个控制源；
- 低延迟比逐帧业务确认更重要。

如果每个控制帧都使用 Service，请求/响应等待会增加耦合和延迟，不适合实时控制流。

### `/world_state`

Simulation 持续发布机器人和物体状态，Agent 订阅最新世界观测。它属于广播式连续数据，同样适合 Topic。

### `/task_plan`

Planner 发布任务计划，Agent 订阅。该 Topic 使用 transient-local QoS，使较晚加入的订阅者也能获得最近一条计划。它仍然是发布/订阅关系，而不是同步请求。

## Service 接口定义

### `ResetEpisode.srv`

接口定义：

```text
float64 base_x 0.0
float64 base_y 0.0
float64 base_yaw 0.0
---
bool success
string message
```

Request 并非完全空请求，而是包含三个带默认值的初始位姿字段。调用时传入：

```bash
"{}"
```

表示使用接口声明的默认值，将 base 复位到 `(0.0, 0.0, 0.0)`。

### `SetVirtualGrasp.srv`

接口定义：

```text
bool enable
string object_name
---
bool success
string message
```

它表达一次性的启用或释放请求，并返回是否成功。操作应快速完成，不需要连续进度和取消，因此使用 Service 合理。

## Service 发现与检查

节点运行时列出项目 Service：

```bash
ros2 service list |
  rg 'sim|agent'
```

主要结果：

```text
/sim/reset_episode
/sim/set_virtual_grasp
/agent/reset_episode
```

查看类型：

```bash
ros2 service type /sim/reset_episode
ros2 service type /agent/reset_episode
ros2 service type /sim/set_virtual_grasp
```

查看接口：

```bash
ros2 interface show embodied_msgs/srv/ResetEpisode
ros2 interface show embodied_msgs/srv/SetVirtualGrasp
```

按类型查找 Service：

```bash
ros2 service find embodied_msgs/srv/ResetEpisode
```

`/sim/reset_episode` 和 `/agent/reset_episode` 名称及服务端不同，但复用了相同的 `ResetEpisode` 接口类型。这说明 Service 名称标识业务端点，`.srv` 类型定义 Request/Response 数据契约。

## Reset Service 调用

复位 Simulation：

```bash
ros2 service call \
  /sim/reset_episode \
  embodied_msgs/srv/ResetEpisode \
  "{}"
```

也可以传入指定初始位姿：

```bash
ros2 service call \
  /sim/reset_episode \
  embodied_msgs/srv/ResetEpisode \
  "{base_x: 1.0, base_y: 0.5, base_yaw: 0.0}"
```

复位 Agent：

```bash
ros2 service call \
  /agent/reset_episode \
  embodied_msgs/srv/ResetEpisode \
  "{}"
```

两个 Service 的职责不同：

| Service | 主要职责 |
|---|---|
| `/sim/reset_episode` | 复位机器人、物体、tracker 等仿真状态 |
| `/agent/reset_episode` | 复位 Brain、FSM、阶段和任务内部状态 |

Agent 当前忽略 Reset Request 中的 base 位姿字段，因为它只复位自身业务状态；Simulation 使用这些字段设置初始位姿。

## 通信成功与业务成功

Service 调用有两个层次：

1. Client 成功找到 Server、发送 Request 并收到 Response；
2. Response 中 `success` 为 `true`，表示业务操作成功。

收到 Response 不等于业务一定成功。服务端可以正常响应：

```text
success: false
message: "具体失败原因"
```

Client 必须同时处理通信错误、等待超时和业务失败字段。

## Service 不可用场景

停止 Agent 后，`/agent/reset_episode` 会从 ROS Graph 消失。继续执行调用时，CLI 会等待 Service 出现，直到用户中断。

这说明实际 Client 不能假设 Server 一定已经启动，也不能无限等待。Day24 的异步 Reset Client 需要使用：

```text
wait_for_service
```

并设置明确的等待周期或总超时，在 Service 不可用时输出可理解的错误并退出。

## 为什么完整推箱任务适合 Action

推红箱包含：

```text
导航
→ 伸臂
→ 闭合夹爪
→ 倒车
→ 判断物体位移
```

任务持续时间长，调用者还需要：

- 查看当前阶段；
- 获得距离、时间等 Feedback；
- 中途 Cancel；
- 设置超时；
- 获取结构化 Result。

如果使用 Service，Client 只能等待一个最终 Response，无法原生获得进度或取消。因此完整任务在 W5/W6 将设计为 Action。

## 项目接口选型表

| 业务接口 | 当前机制 | 结论 | 原因 |
|---|---|---|---|
| `/control_cmd` | Topic | 合理 | 高频连续控制，不逐帧等待响应 |
| `/world_state` | Topic | 合理 | 持续广播世界状态 |
| `/chassis_state` | Topic | 合理 | 连续底盘状态 |
| `/task_plan` | Topic | 基本合理 | Planner 发布计划，支持 late joiner |
| `/sim/reset_episode` | Service | 合理 | 一次请求/响应，快速复位仿真 |
| `/agent/reset_episode` | Service | 合理 | 快速复位 FSM 和 Brain |
| `/sim/set_virtual_grasp` | Service | 合理 | 一次性启用或释放操作 |
| 完整推红箱任务 | 内部 FSM，缺少外部长任务接口 | 后续改造 | 需要 Feedback、Cancel、Timeout 和 Result |

## Reset 一致性问题

只复位 Simulation 而不复位 Agent，可能出现：

- Simulation 已回到初始状态，Agent 仍处于 BackUp 或 Done；
- Agent 使用复位前的 FSM 阶段控制新世界；
- virtual grasp 或任务内部缓存与仿真不一致。

只复位 Agent 而不复位 Simulation，也可能让 Agent 把已经移动过的物体当成新 episode 的初始状态。

Day22 只记录这一问题。Day27/Day28 将通过连续 reset 和生命周期分析验证正确复位顺序及竞态。

## 今日结论

今天完成了 Topic、Service 与 Action 的项目化选型。通信机制没有绝对优劣，关键是业务语义：持续数据流使用 Topic，快速请求/响应使用 Service，长时间且需要反馈和取消的任务使用 Action。

ROS Graph 只反映当前运行端点；环境被 source 不代表节点已经运行。Service Client 也必须处理 Server 不可用、Response 业务失败和超时，而不能只写理想成功路径。

## 算法支线

完成 LeetCode 111“二叉树的最小深度”，代码位于 `test/day22.cpp`。

空节点深度为 0。只有左子树为空时，必须沿右子树寻找叶子；只有右子树为空时，必须沿左子树寻找叶子。只有左右子树都存在，才能取二者的较小深度。

设树有 `n` 个节点、树高为 `h`：

- 时间复杂度：O(n)；
- 递归调用栈：O(h)；
- 平衡树为 O(log n)；
- 退化树最坏为 O(n)。
