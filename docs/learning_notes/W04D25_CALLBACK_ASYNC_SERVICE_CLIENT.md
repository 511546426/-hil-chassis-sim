# W04D25 — 回调式异步 Service Client

日期：2026-09-30  
状态：PASS

## 今日目标

完成 Day25 二叉树所有路径算法，并将 Day24 的 Future 等待式 Service Client 改为回调式异步 Client，理解 Executor、Response 回调和请求超时处理。

## 算法：二叉树的所有路径

文件：`test/day25.cpp`

使用递归从根节点向下遍历，并维护当前路径字符串：

1. 当前节点为空时返回；
2. 将当前节点值追加到路径；
3. 到达叶子节点时，把完整路径加入结果数组；
4. 否则递归访问左、右子树。

路径字符串按值传递，因此每层递归都会得到独立副本，不需要显式回溯。

复杂度：时间 `O(n)`；额外空间为递归栈 `O(h)`，不计算返回结果占用的空间。

## ROS2：回调式异步 Service Client

文件：`ros2_ws/src/learning_tools_cpp/src/reset_client_node.cpp`

调用目标：

```text
/sim/reset_episode
embodied_msgs/srv/ResetEpisode
```

发送请求的核心代码：

```cpp
client_->async_send_request(
    request,
    [this](rclcpp::Client<ResetEpisode>::SharedFuture future) {
      const auto response = future.get();
      // 处理 response
    });
```

`async_send_request()` 发送请求后立即返回，Response 到达时由 ROS2 Executor 自动调用回调。主函数使用：

```cpp
rclcpp::spin(node);
```

来持续处理 Service Response 和定时器事件。

## Future 等待式与回调式的区别

Day24 的方式是：

```text
async_send_request() → Future → spin_until_future_complete() → future.get()
```

API 虽然是异步的，但调用函数会主动等待 Future 完成。

Day25 的方式是：

```text
async_send_request(request, callback) → rclcpp::spin() → 自动执行 callback
```

发送请求后不在当前函数中等待，适合长期运行节点和多个并发请求。Future 表示未来的结果，回调表示结果到达后的处理逻辑。

## 超时与结果处理

回调式请求不会自动提供业务超时，因此实现了一个 3 秒的一次性定时器：

- Response 正常到达：取消定时器并处理结果；
- 3 秒内没有 Response：输出超时错误并退出；
- Response 到达但 `success == false`：输出服务端业务失败信息；
- Response 到达且 `success == true`：输出 Reset 成功信息。

这里仍然区分两层结果：通信是否收到 Response，以及 Service 业务是否成功。

## 构建与运行

```bash
cd /home/changwei/changwei/project/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --packages-select learning_tools_cpp --symlink-install
source install/setup.bash
```

检查可执行文件：

```bash
ros2 pkg executables learning_tools_cpp
```

启动仿真服务端：

```bash
ros2 launch chassis_simulation hil_demo.launch.py
```

另开终端运行 Client：

```bash
source install/setup.bash
ros2 run learning_tools_cpp reset_client_node
```

## 验证结果

```bash
g++ -std=c++17 -Wall -Wextra -pedantic -fsyntax-only test/day25.cpp
```

算法语法检查通过；`learning_tools_cpp` 构建通过；`reset_client_node` 已成功安装并可由 `ros2 run` 启动。工作区的修改包含 Day25 算法、回调式 Client 和本学习笔记。
