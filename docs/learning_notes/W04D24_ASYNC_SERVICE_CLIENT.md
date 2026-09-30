# W04D24 — C++ 异步 Service Client

日期：2026-09-30  
状态：PASS

## 今日目标

将 Day23 的 CLI Service 调用改写为 C++ Client，调用仿真的 `/sim/reset_episode`，理解 `async_send_request()`、Future、超时和业务结果判断。

## Client 实现

文件：`ros2_ws/src/learning_tools_cpp/src/reset_client_node.cpp`

核心流程：

1. 创建 `rclcpp::Client<embodied_msgs::srv::ResetEpisode>`。
2. 使用 `wait_for_service(2s)`，避免 Server 不存在时无限等待。
3. 构造 Request，填写 `base_x/base_y/base_yaw`。
4. 调用 `async_send_request(request)`，得到表示未来 Response 的 Future。
5. 使用 `spin_until_future_complete(..., 3s)` 等待 Future 完成。
6. `future.get()` 取得 Response，先检查通信结果，再检查 `response->success`。

Service 接口为：

```text
float64 base_x 0.0
float64 base_y 0.0
float64 base_yaw 0.0
---
bool success
string message
```

## “异步”与当前等待方式

`async_send_request()` 是异步 API：发送请求后立即返回 Future，不存在直接阻塞式的 `call()`。但是本实现随后调用 `spin_until_future_complete()`，因此 `reset()` 函数会等待 Future 完成后才返回。它适合一次性命令行式 Client，同时保留了 ROS 2 的异步请求接口。

完全回调式的写法可以把回调传给 `async_send_request(request, callback)`，然后让节点持续 `rclcpp::spin(node)`；Response 到达时由回调处理，主线程不需要在 `reset()` 中等待。

## 失败路径

- `wait_for_service()` 超时：Server 未启动，记录错误并返回失败。
- `spin_until_future_complete()` 非 `SUCCESS`：请求超时或通信失败。
- Response 的 `success == false`：通信成功，但服务端业务处理失败，使用 `message` 输出原因。

因此，“收到 Response”和“Reset 业务成功”是两个不同判断层次。

## 构建与运行

`learning_tools_cpp/CMakeLists.txt` 新增 `reset_client_node`，并链接 `rclcpp` 与 `embodied_msgs` 类型支持；`package.xml` 已经包含 `embodied_msgs` 依赖，无需重复修改。

构建：

```bash
cd /home/changwei/changwei/project/ros2_ws
colcon build --packages-select learning_tools_cpp --symlink-install
source install/setup.bash
ros2 pkg executables learning_tools_cpp
```

启动仿真后运行：

```bash
ros2 run learning_tools_cpp reset_client_node
```

成功时输出 Reset 成功消息；停止仿真后再次运行，应得到 Service 不可用错误并以非零状态退出。ROS 2 Lyrical 下 Future 需要保持为非 `const` 对象，才能调用 `future.get()`。

## Day24 算法：判断平衡二叉树

`test/day24.cpp` 使用后序递归同时计算高度和判断平衡性。空树高度为 `0`；子树不平衡时返回哨兵 `-1`，父节点立即向上传播，避免重复计算。

- 时间复杂度：`O(n)`，每个节点最多访问一次。
- 空间复杂度：`O(h)`，递归栈深度为树高。

## 验证记录

```bash
g++ -std=c++17 -Wall -Wextra -pedantic -fsyntax-only test/day24.cpp
```

算法语法检查通过；ROS2 包构建通过，且 `reset_client_node` 已出现在 `ros2 pkg executables` 中并成功完成实际 Reset 调用。
