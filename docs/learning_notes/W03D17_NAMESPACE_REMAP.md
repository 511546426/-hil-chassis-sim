# W03D17 — Namespace、相对名称与 Remapping

日期：2026-08-29
状态：PASS

## 今日目标

学习 ROS 2 名称解析、Namespace 和 Remapping，使用同一个 `topic_logger_node` 可执行程序启动两个相互隔离的节点实例，并将 CLI 验证结果固化为双节点 Launch 文件。

## ROS 2 完整名称

ROS 2 节点和 Topic 在 Graph 中都有完整名称。节点的完整名称由 Namespace 和节点基础名称组成：

```text
Namespace: /robot1
Node name: state_monitor
Full name: /robot1/state_monitor
```

通过 CLI 设置：

```bash
ros2 run learning_tools_cpp topic_logger_node \
  --ros-args \
  -r __ns:=/robot1 \
  -r __node:=state_monitor
```

其中：

| 规则 | 作用 |
|---|---|
| `__ns` | 设置节点 Namespace |
| `__node` | 重映射节点名称 |

两个节点可以使用相同的基础名称，只要它们的完整名称不同：

```text
/robot1/state_monitor
/robot2/state_monitor
```

## 绝对名称与相对名称

以 `/` 开头的是绝对名称：

```text
/chassis_state
```

绝对名称已经包含从根开始的完整路径，不会自动加入节点 Namespace。因此位于 `/robot1` 下的节点使用 `/chassis_state` 时，最终仍然连接全局 Topic：

```text
/chassis_state
```

不以 `/` 开头的是相对名称：

```text
chassis_state
```

相对名称会在节点 Namespace 下解析：

```text
chassis_state + /robot1 → /robot1/chassis_state
chassis_state + /robot2 → /robot2/chassis_state
```

本次先用 `topic_name` 参数传入相对名称，再通过 `ros2 node info` 检查最终订阅。这证明源码或参数中保存的原始字符串，不一定等于 ROS Graph 中解析后的完整名称。

## CLI 双节点隔离

robot1 节点：

```bash
ros2 run learning_tools_cpp topic_logger_node \
  --ros-args \
  -r __ns:=/robot1 \
  -r __node:=state_monitor \
  -p topic_name:=chassis_state \
  -p log_every_n:=2
```

robot2 节点：

```bash
ros2 run learning_tools_cpp topic_logger_node \
  --ros-args \
  -r __ns:=/robot2 \
  -r __node:=state_monitor \
  -p topic_name:=chassis_state \
  -p log_every_n:=3
```

通过以下命令检查：

```bash
ros2 node list
ros2 node info /robot1/state_monitor
ros2 node info /robot2/state_monitor
```

两个节点分别订阅：

```text
/robot1/chassis_state
/robot2/chassis_state
```

向两个 Topic 发布不同数值后，robot1 只收到 `1.0`，robot2 只收到 `2.0`，消息没有串扰。两个节点的 `log_every_n` 参数也相互独立。

## Remapping 验证

Remapping 在启动时替换 ROS 名称，不要求修改节点业务源码。最初使用相对规则：

```bash
-r chassis_state:=odom
```

测试时改用完整名称，消除当前环境中相对名称展开和匹配的歧义：

```bash
ros2 run learning_tools_cpp topic_logger_node \
  --ros-args \
  -r __ns:=/robot1 \
  -p topic_name:=chassis_state \
  -r /robot1/chassis_state:=/robot1/odom \
  -p log_every_n:=1
```

通过：

```bash
ros2 node info /robot1/topic_logger_node
```

确认最终订阅为：

```text
/robot1/odom
```

再向该 Topic 发布：

```bash
ros2 topic pub \
  --rate 2 \
  /robot1/odom \
  nav_msgs/msg/Odometry \
  "{twist: {twist: {linear: {x: 3.0}}}}"
```

节点成功打印 `3.000`，完整名称 Remapping 验证通过。

## 为什么启动日志一度具有误导性

当前节点启动日志打印的是参数原始值：

```cpp
topic_name_.c_str()
```

当参数值是 `chassis_state` 时，日志显示相对名称；发生 Remapping 后，它也不会显示最终的 `/robot1/odom`。因此诊断实际连接时，应优先使用：

```bash
ros2 node info <full_node_name>
ros2 topic info <full_topic_name> -v
```

后续可以把启动日志改为打印：

```cpp
sub_->get_topic_name()
```

这样可以直接看到 Subscription 解析和重映射后的最终 Topic。

## Parameter 与 Remapping 的区别

| 机制 | 含义 | 查看方式 |
|---|---|---|
| `topic_name` Parameter | 节点主动暴露的业务配置 | `ros2 param get` |
| Topic Remapping | ROS Graph 层的名称替换规则 | `ros2 node info`、`ros2 topic info` |

Parameter 必须由节点声明、读取和校验；Remapping 是 ROS 2 通用部署机制，不需要节点为每个名称专门实现参数。

对于 Topic，使用相对名称并通过 Namespace 和 Remapping 部署通常更容易复用。日志频率、阈值等行为配置则更适合 Parameter。

## 双节点 Launch

新增：

```text
ros2_ws/src/learning_tools_cpp/launch/namespaced_monitors.launch.py
```

Launch 启动两个 `topic_logger_node`：

| 完整节点名 | Topic 参数 | 最终 Topic | 日志间隔 |
|---|---|---|---:|
| `/robot1/state_monitor` | `chassis_state` | `/robot1/chassis_state` | 2 |
| `/robot2/state_monitor` | `chassis_state` | `/robot2/chassis_state` | 3 |

Launch 中有意使用相对 Topic 名：

```python
parameters=[
    {
        "topic_name": "chassis_state",
        "log_every_n": 2,
    }
]
```

如果改成 `/chassis_state`，两个 Namespace 下的节点都会订阅同一个全局 Topic，无法实现通信隔离。

## 构建与 Launch 验证

执行：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
cd ros2_ws

colcon build \
  --symlink-install \
  --packages-select learning_tools_cpp

source install/setup.bash
```

结果：

```text
Finished <<< learning_tools_cpp [0.17s]
Summary: 1 package finished [0.29s]
```

静态解析：

```bash
ros2 launch learning_tools_cpp \
  namespaced_monitors.launch.py \
  --show-args
```

输出：

```text
No arguments.
```

这表示 Launch 可以被找到和解析，且当前没有声明 Launch arguments。实际启动后，两个节点、两个 Subscription、不同消息和不同参数均完成验证。

自动环境首次执行静态检查时，ROS 2 无法写入 `~/.ros/log`，导致 Launch 加载报错。将 `ROS_LOG_DIR` 指向可写的 `/tmp` 后验证通过，说明问题来自执行环境的文件权限，而不是 Launch 语法。

## 今日结论

今天完成了 ROS 2 名称体系的最小闭环：相对名称通过 Namespace 解析为完整名称，Remapping 在部署阶段替换最终通信名称，Launch 则把多实例配置固定为可重复启动的入口。

诊断名称问题时，不能只看源码字符串或启动日志，必须在 ROS Graph 中检查节点的完整名称、Publisher 和 Subscriber 的最终 Topic。使用相对名称是实现多机器人、多实例隔离的重要基础。

## 算法支线

完成 LeetCode 94“二叉树的中序遍历”，代码位于 `test/day17.cpp`。

递归顺序为：

```text
左子树 → 当前节点 → 右子树
```

递归函数遇到空节点时返回；非空节点先遍历左子树，再记录当前节点，最后遍历右子树。

设树有 `n` 个节点、树高为 `h`：

- 时间复杂度：O(n)；
- 结果数组空间：O(n)；
- 递归调用栈：O(h)，最坏为 O(n)。
