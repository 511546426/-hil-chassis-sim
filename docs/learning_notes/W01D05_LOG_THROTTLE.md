# W01D05 — 高频 Topic 日志节流

日期：2026-07-19
状态：PASS

## 今日目标

给 `cmd_monitor_node` 的高频日志增加节流，观察 `/control_cmd` 在约 50 Hz 发布时，不节流与节流后的日志输出差异，并确认日志节流不会降低 Topic 的发布或订阅回调频率。

## 概念

`/control_cmd` 是持续发布的控制命令 Topic。若订阅回调每收到一条消息都调用 `RCLCPP_INFO`，50 Hz 的 Topic 每秒可能输出约 50 条日志，造成终端刷屏、关键信息被淹没，并增加日志格式化和终端 I/O 开销。

日志节流的目标是：

```text
/control_cmd（约 50 Hz）→ cmdCallback（持续执行）→ 日志（最多约 1 Hz）
```

节流只限制日志的输出频率，不限制消息的发布频率，也不会主动跳过订阅回调。

本次使用的宏为：

```cpp
RCLCPP_INFO_THROTTLE(
    get_logger(),
    *get_clock(),
    1000,
    "linear_x=%.3f, steering_angle=%.3f, emergency_brake=%s",
    msg->target_linear_x,
    msg->target_steering_angle,
    msg->emergency_brake ? "true" : "false");
```

参数含义：

- `get_logger()`：获取当前节点的日志记录器；
- `*get_clock()`：提供判断节流间隔所需的节点时钟；
- `1000`：节流周期，单位为毫秒；
- 后续参数：日志格式字符串和需要输出的字段。

正确的宏名是 `RCLCPP_INFO_THROTTLE`，不是 `RCLCPP_INFO_THROTTLED`。

## 今日手写

- 文件：`ros2_ws/src/learning_tools_cpp/src/cmd_monitor_node.cpp`
- 节点名：`cmd_monitor_node`
- Topic：`/control_cmd`
- 消息类型：`embodied_msgs::msg::EmbodiedCommand`
- 节流周期：1000 ms
- 输出字段：
  - `target_linear_x`
  - `target_steering_angle`
  - `emergency_brake`

将普通日志：

```cpp
RCLCPP_INFO(get_logger(), ...);
```

改为节流日志：

```cpp
RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 1000, ...);
```

## 构建命令

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
cd ros2_ws
colcon build --symlink-install --packages-select learning_tools_cpp
source install/setup.bash
```

## 运行命令

终端 1，启动仿真和键盘遥控：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
./scripts/hil_demo.sh --teleop
```

终端 2，启动监控节点：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
cd ros2_ws
source install/setup.bash
ros2 run learning_tools_cpp cmd_monitor_node
```

终端 3，检查 Topic 的实际发布频率：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
ros2 topic hz /control_cmd
```

检查 Topic 的发布者和订阅者：

```bash
ros2 topic info /control_cmd -v
```

## 验收结果

运行观察结果符合预期：

- `/control_cmd` 能够持续发布控制消息；
- `cmd_monitor_node` 能够正常接收消息；
- 键盘操作能够改变速度、转向角和急停字段；
- 设置 1000 ms 节流周期后，日志约每秒输出一次；
- 日志输出频率下降，但 Topic 仍保持原有发布和订阅行为。

真实消息频率应使用 `ros2 topic hz /control_cmd` 检查，不能根据节流后的日志行数判断。

验收结论：运行现象 PASS。

## 遇到的问题与修正

1. `RCLCPP_INFO` 不接受 Clock 和节流周期参数，需要改用专门的节流宏。
2. 节流宏的正确名称是 `RCLCPP_INFO_THROTTLE`，末尾没有字母 `D`。
3. `1000` 的单位是毫秒，表示同一个日志调用点最多约每秒输出一次。
4. 日志节流和消息节流是两个概念：回调仍会持续执行，只是日志不会在每次回调时输出。
5. 将误写的 `RCLCPP_INFO_THROTTLED` 修正为 `RCLCPP_INFO_THROTTLE` 后，源码与运行验证保持一致。

## 今日结论

- 理解高频 Topic 每次回调都打印日志带来的问题；
- 能使用 `RCLCPP_INFO_THROTTLE` 控制日志输出频率；
- 理解节流宏中 Logger、Clock 和时间间隔参数的含义；
- 知道日志节流不会降低订阅回调频率；
- 能使用 `ros2 topic hz` 检查 Topic 的真实频率；
- 能区分普通日志宏与节流日志宏的参数形式。

## 算法支线

完成 LeetCode 209“长度最小的子数组”，使用滑动窗口寻找元素和大于等于 `target` 的最短连续子数组。

核心思路：

- `right` 向右移动，将新元素加入窗口；
- 当窗口和大于等于 `target` 时，更新最短长度；
- 使用 `while` 连续向右移动 `left`，尽可能缩小当前窗口；
- 若不存在满足条件的连续子数组，则返回 0。

关键认识：内层使用 `while` 而不是 `if`，因为窗口满足条件后可能需要连续收缩多次，才能得到当前右边界下的最短长度。

- 时间复杂度：O(n)
- 额外空间复杂度：O(1)
- 适用条件：本题数组元素均为正数，窗口和会随左右边界移动呈现可利用的单调变化。
- 代码文件：`test/day05.cpp`
