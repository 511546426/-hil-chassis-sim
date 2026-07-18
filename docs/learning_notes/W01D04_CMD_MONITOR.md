# W01D04 — 订阅并监控控制命令

日期：2026-07-18
状态：PASS

## 今日目标

在 `learning_tools_cpp` 中独立编写 C++ 节点 `cmd_monitor_node`，订阅项目的 `/control_cmd` Topic，并输出关键控制字段。

## 概念

`/control_cmd` 使用 `embodied_msgs/msg/EmbodiedCommand` 消息，适合通过 Topic 传输，因为控制命令是连续发布的数据流，不需要请求方等待单次响应。

本次验证的通信链路：

```text
controller_node → /control_cmd → cmd_monitor_node
                              ↘ simulation_node
```

仓库中有两个节点可以发布 `/control_cmd`：

- `chassis_controller/controller_node`：键盘遥控；
- `chassis_agent_cpp/agent_node`：自动控制。

本次使用 `controller_node` 完成验证，避免两个发布者同时控制仿真。

## 今日手写

- 文件：`ros2_ws/src/learning_tools_cpp/src/cmd_monitor_node.cpp`
- 节点名：`cmd_monitor_node`
- Topic：`/control_cmd`
- 消息类型：`embodied_msgs::msg::EmbodiedCommand`
- 队列深度：10
- 输出字段：
  - `target_linear_x`
  - `target_steering_angle`
  - `emergency_brake`

同时更新：

- `ros2_ws/src/learning_tools_cpp/CMakeLists.txt`
- `ros2_ws/src/learning_tools_cpp/package.xml`

## 构建命令

```bash
cd /home/changwei/changwei/project/ros2_ws
source /opt/ros/lyrical/setup.bash
source install/setup.bash
colcon build --symlink-install --packages-select learning_tools_cpp
```

构建结果：PASS，`learning_tools_cpp` 成功生成并安装 `cmd_monitor_node`。

## 运行命令

终端 1，启动仿真和键盘遥控：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
./scripts/hil_demo.sh --teleop
```

终端 2，启动监控节点：

```bash
cd /home/changwei/changwei/project/ros2_ws
source /opt/ros/lyrical/setup.bash
source install/setup.bash
ros2 run learning_tools_cpp cmd_monitor_node
```

检查 Topic 连接关系：

```bash
ros2 topic info /control_cmd -v
```

## 验收结果

监控节点能够持续接收消息并打印：

```text
linear_x=0.000, steering_angle=0.000, emergency_brake=false
```

键盘操作验证结果：

- `w` / `s` 能改变 `target_linear_x`；
- `a` / `d` 能改变 `target_steering_angle`；
- `b` 能将 `emergency_brake` 置为 `true`；
- 空格能让速度与转向角归零。

验收结论：PASS。

## 遇到的问题与修正

1. 订阅成员变量最初写成 `subscription`，实际声明为 `subscription_`，统一名称后修复。
2. `std::bind` 的占位符需要使用 `std::placeholders::_1`。
3. `emergency_brake` 最初拼写错误，并错误使用 `%f` 输出；修正字段名后，通过三元表达式以 `%s` 输出 `true` / `false`。
4. 当前 ROS 2 Lyrical 环境不识别 `ament_target_dependencies`，因此在 CMake 中使用 `target_link_libraries` 链接 `rclcpp` 和 `embodied_msgs` 的 C++ typesupport。

## 今日结论

- 能独立创建一个 ROS 2 C++ 订阅节点；
- 理解自定义消息头文件、回调签名和订阅对象生命周期；
- 知道新增节点时需要同步修改 CMake 和 `package.xml`；
- 能通过键盘遥控发布真实消息并验证订阅结果；
- 高频 Topic 会导致日志刷屏，下一步 D5 使用 `RCLCPP_INFO_THROTTLE` 学习日志节流。

## 算法支线

完成“双指针：有序数组的平方”：比较数组两端元素的平方，将较大值从结果数组末尾向前写入。

- 时间复杂度：O(n)
- 额外空间复杂度：O(n)
- 关键注意点：不能直接覆盖仍需读取的原数组元素，应使用独立结果数组。
