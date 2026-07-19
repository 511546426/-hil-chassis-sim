# W01D07 — ROS Graph 与第一周复盘

日期：2026-07-19
状态：PASS

## 今日目标

基于 Day06 的 Topic 审计结果，绘制遥控、自动控制和 Planner 三条数据流，闭卷口述一次完整控制闭环，并复盘第一周学习的 Node、Topic、CLI、订阅节点和日志节流知识。

系统级节点图和接口说明已整理至：`docs/ROS_GRAPH.md`。

## 三条核心数据流

### 遥控路径

```text
键盘 → controller_node → /control_cmd → simulation_node
                         simulation_node
                           ├── /chassis_state → controller_node
                           └── /arm_state ────→ controller_node
```

### 自动控制闭环

```text
simulation_node → /world_state → agent_node
simulation_node ← /control_cmd ← agent_node
```

### Planner 路径

```text
任务输入 → /task_request → task_planner_node
         → /task_plan    → agent_node
         → /control_cmd  → simulation_node
```

关键分工：Planner 决定“做什么”，Agent 决定“如何控制”，Simulation 执行动作并产生新的世界状态。

## 第一周 CLI 复盘

```bash
ros2 node list
ros2 node info /simulation_node
ros2 topic list -t
ros2 topic info /control_cmd -v
ros2 topic echo /world_state --once
ros2 topic hz /world_state
```

- `node list/info` 用于检查节点和节点接口；
- `topic list/info` 用于检查 Topic 类型、端点和 QoS；
- `topic echo --once` 用于抽样查看消息；
- `topic hz` 用于测量真实频率。

## 第一周代码复盘

### `topic_logger_node`

- 订阅 `/chassis_state`；
- 消息类型为 `nav_msgs/msg/Odometry`；
- 输出底盘线速度。

### `cmd_monitor_node`

- 订阅 `/control_cmd`；
- 消息类型为 `embodied_msgs/msg/EmbodiedCommand`；
- 输出速度、转向角和急停字段；
- 使用 `RCLCPP_INFO_THROTTLE` 避免高频日志刷屏。

## 风险复盘

- `/control_cmd` 存在 Controller、C++ Agent 和 Python Agent 等潜在发布者；
- ROS 2 允许多发布者，但项目没有控制仲裁器；
- 运行时应只选择一个有效控制来源；
- 高频控制和状态数据积压后可能过期；
- 日志频率不能代替 Topic 频率，真实频率应使用 `ros2 topic hz` 测量。

## 验收结果

- 能区分节点、Topic 和 Service；
- 能说明每个主要节点的职责；
- 能画出遥控控制路径；
- 能画出 Agent 的状态反馈闭环；
- 能画出 Planner 到 Agent 的任务链路；
- 能区分高频控制数据、状态数据和事件驱动的任务数据；
- 能解释 `/control_cmd` 的多发布者风险；
- 能使用 CLI 检查节点、Topic、消息内容和频率。

验收结论：PASS。

## 今日结论

第一周已经从“认识单个 ROS 2 节点”推进到“理解系统级数据闭环”。后续学习新接口时，应继续从职责、数据方向、消息类型、时效性和错误路径五个角度分析，而不是只记 API 写法。

## 算法支线

完成 LeetCode 242“有效的字母异位词”。题目约束字符串只包含小写英文字母，因此使用长度固定为 26 的数组记录字符频次。

核心步骤：

1. 两个字符串长度不同，直接返回 `false`；
2. 遍历第一个字符串，通过 `character - 'a'` 映射下标并增加计数；
3. 遍历第二个字符串，对相同位置减少计数；
4. 所有计数均为 0 时，两个字符串互为字母异位词。

关键认识：固定数组可以实现键范围已知的小型哈希表，数组下标是字符键，数组元素是字符出现次数。

- 时间复杂度：O(n)
- 额外空间复杂度：O(1)
- 代码文件：`test/day07.cpp`
