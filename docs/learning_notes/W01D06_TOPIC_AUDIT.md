# W01D06 — 项目 Topic 审计

日期：2026-07-19
状态：PASS

## 今日目标

从单个 Topic 的发布与订阅练习，进一步理解整个项目的 ROS Graph。审计主要业务 Topic 的消息类型、发布者、订阅者、频率、用途和过期风险，并区分静态代码关系与当前运行时关系。

## 概念

### 静态关系与运行时关系

源码中的 `create_publisher` 和 `create_subscription` 表示节点具备相应通信能力，但只有节点实际启动后，它才会出现在 ROS Graph 中。

因此，本次审计使用两种证据：

- 静态代码审计：找出项目中可能存在的发布者和订阅者；
- ROS 2 CLI：确认当前运行模式下实际存在的节点和连接关系。

### Topic 频率

本项目仿真步长和主要控制定时器周期为 20 ms，理论频率为：

```text
1000 ms / 20 ms = 50 Hz
```

理论值不能代替实测值。实际频率需要使用 `ros2 topic hz` 检查，不能根据日志行数判断。Day05 的日志即使节流为约 1 Hz，也不会改变 Topic 和订阅回调的约 50 Hz 运行频率。

### 消息过期

消息格式正确不代表消息仍然有效。如果订阅者处理速度不足，队列中的旧控制命令或旧状态可能已经不能反映系统当前情况。

队列深度为 10 只表示缓存容量，不表示旧消息在业务上一定安全。控制系统通常更关心最新状态和最新命令。

## 本次运行路径

本次使用遥控模式，避免同时启动自动 Agent：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
./scripts/hil_demo.sh --teleop
```

主要数据流：

```text
controller_node
      │
      │ /control_cmd
      ▼
simulation_node
      │
      ├── /chassis_state ──► controller_node / topic_logger_node
      ├── /arm_state ──────► controller_node
      └── /world_state ────► agent_node（自动控制模式）
```

## CLI 审计命令

查看运行中的节点及节点接口：

```bash
ros2 node list
ros2 node info /controller_node
ros2 node info /simulation_node
```

查看 Topic 和消息类型：

```bash
ros2 topic list -t
```

查看主要 Topic 的发布者、订阅者和 QoS：

```bash
ros2 topic info /control_cmd -v
ros2 topic info /chassis_state -v
ros2 topic info /arm_state -v
ros2 topic info /world_state -v
```

抽样查看消息内容：

```bash
ros2 topic echo /control_cmd --once
ros2 topic echo /chassis_state --once
ros2 topic echo /arm_state --once
ros2 topic echo /world_state --once
```

测量实际发布频率：

```bash
ros2 topic hz /control_cmd
ros2 topic hz /chassis_state
ros2 topic hz /arm_state
ros2 topic hz /world_state
```

## Topic 接口表

| Topic | 消息类型 | 可能的发布者 | 可能的订阅者 | 发布方式 | 用途 |
|---|---|---|---|---|---|
| `/control_cmd` | `embodied_msgs/msg/EmbodiedCommand` | `controller_node`、C++/Python `agent_node` | `simulation_node`、`cmd_monitor_node` | 周期发布，约 50 Hz | 底盘、机械臂和夹爪目标命令 |
| `/chassis_state` | `nav_msgs/msg/Odometry` | `simulation_node` | `controller_node`、`topic_logger_node` | 周期发布，约 50 Hz | 底盘位姿和速度状态 |
| `/arm_state` | `sensor_msgs/msg/JointState` | `simulation_node` | `controller_node` | 周期发布，约 50 Hz | 机械臂关节状态 |
| `/world_state` | `embodied_msgs/msg/EmbodiedWorldState` | `simulation_node` | C++/Python `agent_node` | 周期发布，约 50 Hz | 机器人及环境物体状态 |
| `/task_request` | `std_msgs/msg/String` | REPL 或任务发送脚本 | `task_planner_node` | 事件驱动 | 输入自然语言任务 |
| `/task_plan` | `embodied_msgs/msg/EmbodiedTaskPlan` | `task_planner_node` | C++ `agent_node` | 事件驱动 | 传递结构化任务计划 |

表中的“可能”表示静态代码中存在对应接口；具体运行模式下的实际连接关系以 `ros2 topic info -v` 为准。

`/task_plan` 使用 `transient_local` durability 和深度 1，使后启动的订阅者也能收到最近一条任务计划。该行为方便节点重启，但也需要确认缓存的计划是否仍然有效。

## 系统 Topic 与非 Topic 接口

运行时还会看到 ROS 2 系统 Topic，例如：

```text
/rosout
/parameter_events
```

它们不属于本项目的核心业务数据流，应与业务 Topic 分开记录。

以下接口是 Service，不应混入 Topic 审计表：

```text
/sim/reset_episode
/sim/set_virtual_grasp
/agent/reset_episode
```

## 过期风险审计

| Topic | 是否强调最新值 | 主要过期风险 |
|---|---|---|
| `/control_cmd` | 是 | 仿真继续执行旧速度、旧转向或旧机械臂目标 |
| `/chassis_state` | 是 | 控制器使用旧位姿和速度状态 |
| `/arm_state` | 是 | 控制或显示逻辑使用旧关节姿态 |
| `/world_state` | 是 | Agent 根据旧机器人或物体位置作出错误决策 |
| `/task_request` | 是 | 已失效的任务可能被重复处理 |
| `/task_plan` | 是 | 新启动的 Agent 可能执行缓存但已经失效的计划 |

## 多发布者风险

ROS 2 允许多个 Publisher 向同一个 Topic 发布，但这不代表业务上一定安全。

`/control_cmd` 可能由遥控 Controller、C++ Agent 或 Python Agent 发布。如果多个控制节点同时运行，`simulation_node` 会交替收到不同来源的命令，可能导致：

- 机器人运动抖动；
- 遥控命令被自动控制命令覆盖；
- 急停状态被后续命令覆盖；
- 控制行为难以复现和排查。

因此，启动系统时应明确唯一的控制来源。遥控实验中不同时启动自动 Agent。

## 验收结果

- 能使用 `ros2 node list/info` 查看节点及其接口；
- 能使用 `ros2 topic list -t` 区分 Topic 名称和消息类型；
- 能使用 `ros2 topic info -v` 确认运行时发布者、订阅者和 QoS；
- 能使用 `ros2 topic echo --once` 抽样检查消息；
- 能使用 `ros2 topic hz` 测量真实频率；
- 能区分业务 Topic、系统 Topic 和 Service；
- 能说明高频状态的过期风险；
- 能说明 `/control_cmd` 的多发布者控制权风险。

验收结论：PASS。

## 今日结论

- Topic 审计不能只记录名称，还要记录类型、方向、频率、用途和风险；
- 源码表示可能的通信关系，ROS Graph 表示当前实际运行关系；
- 日志频率、回调频率和 Topic 发布频率是不同概念；
- 高频控制和状态消息通常要求尽快处理最新值；
- ROS 2 的多发布者能力需要配合明确的业务控制权设计。

## 算法支线

完成 LeetCode 59“螺旋矩阵 II”，使用四个边界逐圈生成 `n × n` 矩阵。

每一圈依次执行：

```text
左 → 右：填写 top，随后 top++
上 → 下：填写 right，随后 right--
右 → 左：填写 bottom，随后 bottom--
下 → 上：填写 left，随后 left++
```

关键认识：

- `matrix[row][column]` 中，前者是行，后者是列；
- 每走完一个方向，只收缩与该边对应的一个边界；
- 填写下边和左边前重新检查边界，避免窄矩阵或中心位置被重复填写；
- 奇数阶矩阵的中心元素会在最后一圈正确填写。

- 时间复杂度：O(n²)
- 额外空间复杂度：O(1)，不计算返回矩阵
- 代码文件：`test/day06.cpp`
