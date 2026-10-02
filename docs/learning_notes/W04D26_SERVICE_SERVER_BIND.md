# W04D26 — Service Server 与 std::bind

日期：2026-10-02  
状态：PASS

## 今日目标

完成“左叶子之和”递归算法，阅读项目中已有的 ROS2 Service Server，并理解 `std::bind` 如何把成员函数注册为 ROS2 回调。

## 算法：左叶子之和

文件：`test/day26.cpp`

递归遍历二叉树，并通过 `is_left` 参数记录当前节点是否为父节点的左孩子：

```cpp
sumLeftLeaves(node->left, true);
sumLeftLeaves(node->right, false);
```

只有同时满足以下条件才累加：

```text
当前节点是左孩子
当前节点没有左右子节点
```

根节点从 `is_left = false` 开始，因为根节点没有父节点。空节点返回 `0`，最终结果为左右子树结果之和。

复杂度：时间 `O(n)`；递归栈空间 `O(h)`。

## ROS2 Service Server 阅读

从项目根目录搜索源码：

```bash
cd ~/changwei/project
rg -n "create_service|reset_episode" \
  ros2_ws/src/chassis_simulation \
  ros2_ws/src/learning_tools_cpp
```

仿真节点已经提供 `/sim/reset_episode`，因此本日重点是阅读和验证已有 Server，没有重复创建同名 Server，避免端点冲突。

检查 Service 类型和详细信息：

```bash
cd ~/changwei/project/ros2_ws
source install/setup.bash
ros2 service type /sim/reset_episode
ros2 service info /sim/reset_episode
ros2 interface show embodied_msgs/srv/ResetEpisode
```

调用 Server：

```bash
ros2 service call \
  /sim/reset_episode \
  embodied_msgs/srv/ResetEpisode \
  "{base_x: 1.0, base_y: 0.5, base_yaw: 0.0}"
```

Service Server 的职责是接收 Request、执行处理逻辑，并填写 Response 中的 `success` 和 `message`。

## std::bind 的用法

成员函数依赖对象实例，不能只传递函数地址。`std::bind` 可以把成员函数、当前对象和参数位置绑定成可调用对象：

```cpp
service_ = create_service<ResetEpisode>(
    "/learning/reset_episode",
    std::bind(
        &ServerNode::handle_reset,
        this,
        std::placeholders::_1,
        std::placeholders::_2));
```

假设回调声明为：

```cpp
void handle_reset(
    const std::shared_ptr<ResetEpisode::Request> request,
    std::shared_ptr<ResetEpisode::Response> response);
```

参数映射关系为：

```text
std::placeholders::_1 → request
std::placeholders::_2 → response
```

ROS2 收到请求后，效果等价于调用：

```cpp
this->handle_reset(request, response);
```

现代 C++ 也可以用 Lambda 实现同样的回调，通常可读性更好；`std::bind` 则是 ROS2 示例中常见的传统写法。

## 今日结论

- Service Client 负责发送请求；
- Service Server 负责处理请求并返回 Response；
- `create_service()` 注册服务端点；
- `std::bind` 将成员函数转换为 ROS2 可调用的回调对象；
- 现有仿真 Server 已能通过 CLI 验证，无需新增同名 Server。

## 验证

```bash
g++ -std=c++17 -Wall -Wextra -pedantic -fsyntax-only test/day26.cpp
git diff --check
```

算法语法检查通过，笔记中的 ROS2 CLI 路径已按项目根目录和 `ros2_ws` 工作空间分别说明。
