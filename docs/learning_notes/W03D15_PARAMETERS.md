# W03D15 — ROS 2 Parameter 基础

日期：2026-08-29
状态：PASS

## 今日目标

学习 ROS 2 Parameter 的声明、默认值、命令行覆盖和查询方式，将 `topic_logger_node` 中写死的订阅 Topic 与日志频率改为节点参数，并通过正常值、非法值和测试消息验证参数确实影响节点行为。

## Parameter 解决什么问题

Parameter 是属于某个节点的配置值，适合表达 Topic 名称、日志频率、阈值和开关等运行配置。它与 Topic 的职责不同：

| 机制 | 主要用途 |
|---|---|
| Parameter | 配置某个节点的行为 |
| Topic | 在节点之间持续传输业务数据 |

修改前，`topic_logger_node` 把 `/chassis_state` 写死在源码中，并为每条消息输出日志。更换 Topic 或降低日志频率都需要修改源码和重新编译，不利于复用和部署。

## 参数设计

本次为节点增加两个参数：

| 参数 | 类型 | 默认值 | 用途 |
|---|---|---|---|
| `topic_name` | string | `/chassis_state` | 指定订阅的 Odometry Topic |
| `log_every_n` | integer | `50` | 每收到 N 条消息输出一次日志 |

节点在构造时声明并读取参数：

```cpp
topic_name_ = declare_parameter<std::string>(
    "topic_name", "/chassis_state");
log_every_n_ = declare_parameter<int>("log_every_n", 50);
```

`declare_parameter()` 既向节点声明参数，也返回本次启动实际使用的值。启动时没有覆盖则使用默认值；通过 ROS 参数传入时则使用覆盖值。

## 参数校验

Topic 名称不能为空，日志间隔必须大于零：

```cpp
if (topic_name_.empty()) {
  throw std::invalid_argument("topic_name must not be empty");
}
if (log_every_n_ <= 0) {
  throw std::invalid_argument("log_every_n must be greater than 0");
}
```

校验应在创建订阅之前完成，使节点遇到错误配置时立即拒绝启动，并提供明确原因。否则 `log_every_n=0` 会使取模运算无效，空 Topic 名也无法表达有效订阅目标。

## 参数驱动的订阅与日志

创建订阅时使用 `topic_name_`：

```cpp
sub_ = create_subscription<Odometry>(
    topic_name_, 10, callback);
```

回调累计收到的消息数量，只在计数能够被 `log_every_n_` 整除时输出：

```cpp
++message_count_;
if (message_count_ % log_every_n_ != 0) {
  return;
}
```

启动日志同时显示实际配置，便于运行时确认：

```text
listening on <topic>, logging every <n> messages
```

## 构建验证

在标准 ROS 2 工作区执行：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
cd ros2_ws

colcon build \
  --symlink-install \
  --packages-select learning_tools_cpp
```

结果：

```text
Finished <<< learning_tools_cpp [30.0s]
Summary: 1 package finished [30.2s]
```

单包构建通过。构建后重新加载 overlay：

```bash
source install/setup.bash
```

## CLI 覆盖与参数查询

使用命令行覆盖默认参数：

```bash
ros2 run learning_tools_cpp topic_logger_node \
  --ros-args \
  -p topic_name:=/chassis_state \
  -p log_every_n:=10
```

在另一个已加载项目环境和 workspace overlay 的终端中查询：

```bash
ros2 param list /topic_logger_node
ros2 param get /topic_logger_node topic_name
ros2 param get /topic_logger_node log_every_n
```

验证结果：节点能够列出两个参数，读取到的 `topic_name` 为 `/chassis_state`，`log_every_n` 为命令行覆盖后的 `10`。这说明修改运行配置不再需要修改源码或重新构建。

## 非法值验证

使用零作为日志间隔：

```bash
ros2 run learning_tools_cpp topic_logger_node \
  --ros-args -p log_every_n:=0
```

节点拒绝启动，并指出：

```text
log_every_n must be greater than 0
```

使用空 Topic 名：

```bash
ros2 run learning_tools_cpp topic_logger_node \
  --ros-args -p topic_name:=""
```

节点拒绝启动，并指出：

```text
topic_name must not be empty
```

正常路径和错误路径均已验证。

## Topic 与日志节流验证

为避免依赖完整仿真，节点订阅测试 Topic，并设置每三条消息记录一次：

```bash
ros2 run learning_tools_cpp topic_logger_node \
  --ros-args \
  -p topic_name:=/test_chassis_state \
  -p log_every_n:=3
```

使用 ROS 2 CLI 以 2 Hz 发布 Odometry：

```bash
ros2 topic pub \
  --rate 2 \
  /test_chassis_state \
  nav_msgs/msg/Odometry \
  "{twist: {twist: {linear: {x: 1.25}}}}"
```

节点能够订阅 `/test_chassis_state`，并大约每收到三条消息输出一次 `linear.x = 1.250`。分别使用 `log_every_n=1`、`3` 和 `10` 后，日志输出间隔随参数变化，证明参数不仅能被查询，也实际控制了程序行为。

Topic 连接可以通过以下命令检查：

```bash
ros2 topic info /test_chassis_state -v
ros2 topic hz /test_chassis_state
```

## 当前实现的边界

当前代码只在节点构造时读取一次参数，并把值保存到成员变量中。参数声明、参数服务器中的值发生变化、程序内部成员变量随之更新是不同的事情。

今天尚未注册运行时参数更新回调，因此不能假定：

```bash
ros2 param set /topic_logger_node log_every_n 5
```

一定会同步改变 `log_every_n_` 和实际日志行为。动态参数修改将在 Day16 专门验证和实现。

## 今日结论

今天将 `topic_logger_node` 从硬编码节点改为基础参数化节点，完成了参数声明、默认值、CLI 覆盖、查询、非法值校验和行为验证。Parameter 让同一份可执行程序能够适应不同 Topic 与日志频率，同时保留可直接启动的安全默认值。

需要记住：参数能被声明和查询，不代表程序已经支持动态更新；运行时修改必须由节点明确处理并同步到实际使用的状态。

## 算法支线

完成 LeetCode 144“二叉树的前序遍历”，代码位于 `test/day15.cpp`。

前序遍历顺序为：

```text
当前节点 → 左子树 → 右子树
```

递归函数遇到空节点时返回；遇到非空节点时先记录当前值，再递归处理左右子树。调用栈会保存父节点的执行位置，因此左子树完成后能够自动返回并继续右子树。

设树中有 `n` 个节点、树高为 `h`：

- 时间复杂度：O(n)；
- 结果数组空间：O(n)；
- 递归调用栈：O(h)，最坏为 O(n)。
