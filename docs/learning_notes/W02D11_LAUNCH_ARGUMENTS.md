# W02D11 — Launch Argument 与条件启动

日期：2026-07-22
状态：PASS

## 今日目标

在 DAY10 的双节点 Launch 基础上增加启动参数，使一份 Launch 文件可以选择启动 `topic_logger_node` 和 `cmd_monitor_node`，不再为了切换节点组合反复修改源码。

## 核心概念

Launch Argument 是传给 Launch 文件的启动配置，适合控制节点是否启动、namespace、参数文件和 remapping 等编排行为。

今天使用的完整链路：

```text
DeclareLaunchArgument
  → 声明参数名、默认值和说明
LaunchConfiguration
  → 在 Launch 执行时读取最终参数值
IfCondition
  → 根据参数决定是否执行 Node 动作
命令行 name:=value
  → 覆盖默认值
```

Launch Argument 与 Node Parameter 不同：前者由 Launch 系统读取并控制启动编排，后者由节点读取并控制节点内部行为。Launch Argument 可以进一步传递为 Node Parameter，但两者不是同一个概念。

## 实现内容

修改文件：

```text
ros2_ws/src/learning_tools_cpp/launch/learning_bringup.launch.py
```

新增导入：

```python
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
```

运行时配置：

```python
enable_topic_logger = LaunchConfiguration("enable_topic_logger")
enable_cmd_monitor = LaunchConfiguration("enable_cmd_monitor")
```

两个参数默认值均为 `"true"`。节点通过下面的条件决定是否启动：

```python
condition=IfCondition(enable_topic_logger)
condition=IfCondition(enable_cmd_monitor)
```

`LaunchConfiguration` 不是函数执行时立即取得的普通布尔值，而是延迟到 Launch 真正运行时解析，这样命令行才能覆盖默认值。

## 实际排错

第一次修改后出现：

```text
NameError: name 'DeclareLaunchArgument' is not defined
```

检查源码发现四个问题：

1. 误导入了与 ROS 2 无关的 `asyncio.Condition`；
2. 使用 `DeclareLaunchArgument` 前没有从 `launch.actions` 导入；
3. 使用 `IfCondition` 和 `LaunchConfiguration` 前没有导入；
4. 参数声明被写在 `generate_launch_description()` 外，也没有放入 `LaunchDescription` 动作列表。

修正后重新构建并 source，执行：

```bash
ros2 launch learning_tools_cpp learning_bringup.launch.py --show-args
```

成功显示：

```text
enable_topic_logger  (default: 'true')
enable_cmd_monitor   (default: 'true')
```

这说明 ROS 2 已从安装后的 Launch 文件中正确读取两个参数。

## 构建与验证

```bash
conda deactivate
source /opt/ros/lyrical/setup.bash
cd /home/changwei/changwei/project/ros2_ws
colcon build --packages-select learning_tools_cpp
source install/setup.bash
```

默认启动两个节点：

```bash
ros2 launch learning_tools_cpp learning_bringup.launch.py
```

只启动 Topic Logger：

```bash
ros2 launch learning_tools_cpp learning_bringup.launch.py \
  enable_cmd_monitor:=false
```

只启动 Command Monitor：

```bash
ros2 launch learning_tools_cpp learning_bringup.launch.py \
  enable_topic_logger:=false
```

另一个已 source 的终端可以通过 `ros2 node list` 验证被关闭的节点没有进入 ROS graph。

## 验收结果

- 能声明并读取 Launch Argument；
- 能使用 `IfCondition` 控制节点启动；
- 能从命令行覆盖默认值；
- 能区分 Launch Argument 与 Node Parameter；
- 能使用 `--show-args` 检查可用参数；
- 能根据 traceback 定位缺失导入和错误代码位置；
- 两个参数已被安装后的 Launch 正确识别。

验收结论：PASS。

## 今日结论

DAY10 解决了“用一条命令启动多个节点”，DAY11 进一步解决了“用同一份 Launch 选择启动组合”。编写 Launch 时，声明、读取和使用参数缺一不可，而且所有启动动作都必须放入返回的 `LaunchDescription`。

## 算法支线

完成 LeetCode 225“用队列实现栈”。使用一个队列，每次 `push` 新元素后，将此前的全部旧元素依次从队首取出并重新加入队尾，使最新元素移动到队首。

正确的不变量是：每次 `push` 结束后，队列从队首到队尾按照元素从新到旧排列。

```text
push(1) → [1]
push(2) → [2, 1]
push(3) → [3, 2, 1]
```

因此队首始终相当于栈顶，`pop` 和 `top` 可以直接操作队首。旋转次数必须等于加入新元素之前的队列长度。

- `push`：O(n)；
- `pop`、`top`、`empty`：O(1)；
- 额外空间复杂度：O(n)；
- 代码文件：`test/day11.cpp`。
