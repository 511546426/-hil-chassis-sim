# W03D20 — 在 Launch 中暴露 ROS Parameter

日期：2026-09-16
状态：PASS

## 今日目标

在 Day19 已完成 `push_min_dist` 节点参数化的基础上，为 `chassis_agent_cpp` 增加标准 ROS 2 Launch 入口。通过 Launch argument 配置推箱成功距离，并把配置以明确的浮点类型传给 Agent，使用户无需修改 C++ 源码或手写完整的 `ros2 run --ros-args` 命令。

## 配置分层

本次配置经过三个层次：

```text
命令行 Launch argument
  → LaunchConfiguration
  → Node parameters
  → Agent ROS Parameter
  → PushRedBoxFSM::Config
```

各层职责不同：

| 层次 | 职责 |
|---|---|
| C++ 节点 | 定义参数名称、类型、默认值、校验和实际行为 |
| Launch 文件 | 组织节点启动，并为本次部署提供参数值 |
| 命令行 | 临时覆盖 Launch 默认配置 |

Launch 不是把全部配置从 C++ 搬走。C++ 仍保留安全默认值，因此直接执行 `ros2 run` 时节点也能工作；Launch 为部署提供更清晰、可复现的配置入口。

## 为什么创建独立 Agent Launch

现有 `chassis_simulation/hil_demo.launch.py` 只启动 Simulation，并不创建 C++ Agent。把 `push_min_dist` 加到该文件中无法自动传给 Agent。

因此新增：

```text
ros2_ws/src/chassis_agent_cpp/launch/agent.launch.py
```

该 Launch 专门负责启动：

```text
chassis_agent_cpp/agent_node
```

## 声明 Launch argument

Launch 文件声明：

```python
DeclareLaunchArgument(
    "push_min_dist",
    default_value="0.20",
    description=(
        "Minimum box displacement required for the push task "
        "to succeed, in meters"
    ),
)
```

这使用户可以查看默认值，也可以在命令行覆盖：

```bash
ros2 launch chassis_agent_cpp \
  agent.launch.py \
  push_min_dist:=0.10
```

## `LaunchConfiguration` 的延迟求值

参数值通过：

```python
push_min_dist = LaunchConfiguration("push_min_dist")
```

取得。`LaunchConfiguration` 不是普通 Python 字符串或浮点数，而是 Launch 执行阶段才会解析的替换对象。因此不能在生成 LaunchDescription 时直接写：

```python
float(push_min_dist)
```

它应继续作为 substitution 传给支持延迟求值的 Launch API。

## 明确参数类型

Launch argument 的原始输入来自命令行字符串。为了保证传给节点的是浮点参数，使用：

```python
ParameterValue(
    push_min_dist,
    value_type=float,
)
```

完整节点参数为：

```python
parameters=[
    {
        "brain": "rule",
        "push_min_dist": ParameterValue(
            push_min_dist,
            value_type=float,
        ),
    }
]
```

这样可以避免 `push_min_dist` 被当成字符串传入已经声明为 double 的 ROS Parameter。

## 安装 Launch 文件

仅在源码中创建 Launch 文件还不够，ROS 2 CLI 通常从 Package 安装空间寻找资源。

在 `chassis_agent_cpp/CMakeLists.txt` 中增加：

```cmake
install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)
```

构建后，文件安装到：

```text
install/chassis_agent_cpp/share/chassis_agent_cpp/launch/agent.launch.py
```

## Package 运行依赖

在 `package.xml` 中增加：

```xml
<exec_depend>launch</exec_depend>
<exec_depend>launch_ros</exec_depend>
```

其中：

- `launch` 提供 Launch 核心动作和 substitutions；
- `launch_ros` 提供 ROS 节点启动和 ROS Parameter 转换支持。

依赖即使已经由系统或其他 Package 间接安装，也应该由实际使用它的 Package 明确声明。

## 构建结果

执行：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
cd ros2_ws

colcon build \
  --symlink-install \
  --packages-up-to chassis_agent_cpp
```

构建完成：

```text
Summary: 4 packages finished
```

`embodied_core` 仍有既有的测试代码忽略 `[[nodiscard]]` 返回值警告，但没有 Package 构建失败。

## Launch 静态检查

加载工作区 overlay 后执行：

```bash
source install/setup.bash

ros2 launch chassis_agent_cpp \
  agent.launch.py \
  --show-args
```

结果包含：

```text
'push_min_dist':
    Minimum box displacement required for the push task to succeed, in meters
    (default: '0.20')
```

这证明：

- Package 可以被找到；
- Launch 文件已正确安装；
- Python Launch 可以解析；
- `push_min_dist` argument 已声明；
- 默认值和说明可被用户查看。

## 默认值与覆盖值验证

默认启动：

```bash
ros2 launch chassis_agent_cpp agent.launch.py
```

Agent 使用：

```text
push_min_dist = 0.20 m
```

覆盖启动：

```bash
ros2 launch chassis_agent_cpp \
  agent.launch.py \
  push_min_dist:=0.10
```

Agent 日志显示实际值 `0.10 m`，并且通过：

```bash
ros2 param get /agent_node_cpp push_min_dist
```

能够读取到对应的 double 值。由此确认 Launch argument 已经传到节点 Parameter，而不只是被 Launch 接收。

## 错误路径验证

零值：

```bash
ros2 launch chassis_agent_cpp \
  agent.launch.py \
  push_min_dist:=0.0
```

负数：

```bash
ros2 launch chassis_agent_cpp \
  agent.launch.py \
  push_min_dist:=-0.2
```

两者都由 Day19 的节点校验拒绝：

```text
push_min_dist must be finite and greater than 0
```

错误类型：

```bash
ros2 launch chassis_agent_cpp \
  agent.launch.py \
  push_min_dist:=wrong
```

由于 Launch 使用 `ParameterValue(..., value_type=float)`，无法转换的字符串会在 Launch 求值或节点启动阶段失败。非法启动结束后没有残留 `/agent_node_cpp`。

## `--show-args` 与实际启动的区别

`--show-args` 只能证明 Launch 文件可以被找到和解析，并展示声明的 argument。它不会创建节点，也不能证明参数已进入 FSM。

完整验收仍需：

```text
--show-args
  → 实际启动
  → 检查 Agent 日志
  → ros2 param get
  → 验证错误路径
```

## 当前实现边界

Day20 没有修改 `scripts/hil_demo.sh`。该脚本仍直接执行 `ros2 run chassis_agent_cpp agent_node`，使用节点默认值。

本日先建立标准 ROS 2 Launch 入口，集中学习：

```text
DeclareLaunchArgument
→ LaunchConfiguration
→ ParameterValue
→ Node parameters
→ CMake 安装
```

后续可以再决定是否让一键脚本接受 `--push-min-dist`，或让它复用新的 Launch 入口。

## 今日结论

今天完成了从 ROS Parameter 到 Launch 部署配置的闭环。C++ 节点负责定义和验证 `push_min_dist`，Launch 文件负责为一次启动提供配置，命令行则可以临时覆盖 Launch 默认值。

这种分层使同一个已编译可执行程序能够用于不同实验配置，同时保留安全默认值和明确错误提示。

## 算法支线

完成 LeetCode 101“对称二叉树”，代码位于 `test/day20.cpp`。

算法通过辅助函数同时比较两个镜像位置的节点：

```text
左子树的左孩子 ↔ 右子树的右孩子
左子树的右孩子 ↔ 右子树的左孩子
```

两个节点都为空时对称；只有一个为空或节点值不同时不对称；其余情况继续递归比较外侧和内侧节点。

设树有 `n` 个节点、树高为 `h`：

- 时间复杂度：O(n)；
- 递归调用栈：O(h)；
- 平衡树为 O(log n)；
- 退化树最坏为 O(n)。
