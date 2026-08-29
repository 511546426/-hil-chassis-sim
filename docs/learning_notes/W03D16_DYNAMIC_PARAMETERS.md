# W03D16 — ROS 2 动态参数与配置导出

日期：2026-08-29
状态：PASS

## 今日目标

在 Day15 参数声明和启动时覆盖的基础上，学习运行期间查询、修改和导出 ROS 2 Parameter。为 `topic_logger_node` 增加参数更新回调，使 `log_every_n` 的动态修改能够立即影响日志行为，同时拒绝非法值和不安全的 Topic 动态切换。

## 启动时参数与动态参数

Day15 的实现只在构造函数中读取一次参数：

```cpp
log_every_n_ = declare_parameter<int>("log_every_n", 50);
```

这里涉及两个状态：

1. ROS 2 节点参数系统中保存的参数值；
2. 回调逻辑实际使用的 C++ 成员变量 `log_every_n_`。

如果没有参数更新回调，不能假定 `ros2 param set` 后成员变量和程序行为一定同步改变。动态参数支持需要节点验证新值，并主动把接受的值应用到运行状态。

## 参数查询命令

节点运行后，可以使用：

```bash
ros2 param list /topic_logger_node
ros2 param get /topic_logger_node log_every_n
ros2 param describe /topic_logger_node log_every_n
```

三条命令分别用于列出节点参数、读取当前值和查看参数描述。当前代码尚未设置详细的 `ParameterDescriptor`，因此 `describe` 显示的信息可能比较基础。

## 注册参数更新回调

节点使用 `add_on_set_parameters_callback()` 注册回调：

```cpp
parameter_callback_handle_ = add_on_set_parameters_callback(
    [this](const std::vector<rclcpp::Parameter>& parameters) {
      return onParametersChanged(parameters);
    });
```

回调注册返回的 Handle 被保存为节点成员：

```cpp
rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr
    parameter_callback_handle_;
```

保存 Handle 很重要。如果返回值只保存在临时变量中并随即销毁，注册的回调可能失效。

## 动态更新 `log_every_n`

参数回调执行以下检查：

1. 参数名称是否为 `log_every_n`；
2. 参数类型是否为 ROS 2 integer；
3. 参数值是否大于零；
4. 参数值是否能放入当前使用的 C++ `int`；
5. 全部检查通过后才更新成员变量。

类型检查：

```cpp
if (parameter.get_type() !=
    rclcpp::ParameterType::PARAMETER_INTEGER) {
  result.successful = false;
  result.reason = "log_every_n must be an integer";
  return result;
}
```

范围检查：

```cpp
const auto value = parameter.as_int();
if (value <= 0 || value > std::numeric_limits<int>::max()) {
  result.successful = false;
  result.reason = "log_every_n must be greater than 0";
  return result;
}
```

实现先把候选值保存在局部变量中，完成整批参数校验后才更新 `log_every_n_`。这样可以避免批量设置中后续参数失败时，前面的成员变量已经被部分修改。

## 为什么不动态修改 `topic_name`

本次明确拒绝运行时修改 `topic_name`：

```cpp
result.successful = false;
result.reason =
    "topic_name cannot be changed while the node is running";
```

订阅对象是在节点构造时根据 `topic_name_` 创建的。只改变字符串成员变量不会让已有 Subscription 自动转移到新 Topic。安全的动态切换至少需要：

```text
验证新 Topic 名称
  → 创建或替换 Subscription
  → 处理切换期间的回调和消息
  → 确认旧订阅释放
```

因此当前把 `topic_name` 定义为“启动时可配置、运行时不可修改”，比接受修改但保持旧订阅更清晰。

## 构建结果

执行：

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

动态参数代码在当前 ROS 2 Lyrical 环境中构建通过。

## 运行时验证

节点以测试 Topic 和初始间隔 `10` 启动：

```bash
ros2 run learning_tools_cpp topic_logger_node \
  --ros-args \
  -p topic_name:=/test_chassis_state \
  -p log_every_n:=10
```

使用 10 Hz Odometry 消息验证日志频率：

```bash
ros2 topic pub \
  --rate 10 \
  /test_chassis_state \
  nav_msgs/msg/Odometry \
  "{twist: {twist: {linear: {x: 1.25}}}}"
```

运行期间修改：

```bash
ros2 param set /topic_logger_node log_every_n 2
```

设置成功后，节点输出新值，日志由每 10 条输出一次立即变为每 2 条输出一次。这证明参数系统中的新值已经通过回调同步到实际成员变量和节点行为。

## 失败路径验证

零值和负数被拒绝：

```bash
ros2 param set /topic_logger_node log_every_n 0
ros2 param set /topic_logger_node log_every_n -5
```

错误类型被拒绝：

```bash
ros2 param set /topic_logger_node log_every_n wrong
```

动态切换 Topic 被拒绝：

```bash
ros2 param set \
  /topic_logger_node \
  topic_name \
  /another_topic
```

失败后再次执行 `ros2 param get`，参数仍保持之前的合法值。失败的参数事务没有覆盖节点当前配置。

## `ros2 param dump`

执行：

```bash
ros2 param dump /topic_logger_node
```

`dump` 将节点当前的 ROS 2 参数导出为 YAML，相当于为节点配置拍摄快照。典型结构为：

```yaml
/topic_logger_node:
  ros__parameters:
    log_every_n: 2
    topic_name: /test_chassis_state
```

保存到临时文件：

```bash
ros2 param dump /topic_logger_node \
  > /tmp/topic_logger_params.yaml
```

导出的 YAML 可以用于：

- 保存一次运行的实际配置；
- 对比不同运行之间的参数差异；
- 调试配置是否符合预期；
- 通过 `--params-file` 复现启动配置。

例如：

```bash
ros2 run learning_tools_cpp topic_logger_node \
  --ros-args \
  --params-file /tmp/topic_logger_params.yaml
```

`dump` 只保存 ROS 2 Parameter，不保存 Topic 消息、ROS Graph、FSM 状态或普通 C++ 成员变量。如果某个值没有声明为 Parameter，它也不会出现在导出结果中。

不同 ROS 2 发行版的 `dump` 文件选项可能不同，实际使用前应执行：

```bash
ros2 param dump -h
```

## 今日结论

今天完成了 `log_every_n` 的动态更新闭环：CLI 发起修改，节点回调校验参数，合法值同步到成员变量并立即改变日志频率，非法值则携带明确原因被拒绝。

Parameter 的核心不只是能够 `get` 和 `set`，而是节点需要定义哪些参数允许动态变化、合法范围是什么，以及变化后如何安全应用到运行资源。简单整数可以直接更新；Topic Subscription 等资源型配置则需要更完整的重建和并发设计。

## 算法支线

完成 LeetCode 145“二叉树的后序遍历”，代码位于 `test/day16.cpp`。

递归顺序为：

```text
左子树 → 右子树 → 当前节点
```

递归函数遇到空节点时返回；对非空节点先递归遍历左右子树，最后把当前节点值加入结果数组。

设树有 `n` 个节点、树高为 `h`：

- 时间复杂度：O(n)；
- 结果数组空间：O(n)；
- 递归调用栈：O(h)，最坏为 O(n)。
