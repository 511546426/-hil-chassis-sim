# W02D10 — 使用 Launch 编排多个节点

日期：2026-07-23
状态：PASS

## 今日目标

理解 ROS 2 Launch 的用途和 Python Launch 文件的基本结构，并在 `learning_tools_cpp` 中使用一条命令同时启动 `topic_logger_node` 与 `cmd_monitor_node`。

## Launch 的职责

Launch 是 ROS 2 的启动编排机制。节点负责订阅、发布和业务逻辑；Launch 负责选择并启动节点，同时传入名称、参数、命名空间和 remapping 等运行配置。

```text
C++ 源代码
  → CMake + colcon 编译和安装
  → Launch 启动并配置一个或多个节点
```

不使用 Launch 时，需要分别执行：

```bash
ros2 run learning_tools_cpp topic_logger_node
ros2 run learning_tools_cpp cmd_monitor_node
```

使用 Launch 后只需：

```bash
ros2 launch learning_tools_cpp learning_bringup.launch.py
```

本日编排关系：

```text
learning_bringup.launch.py
├── topic_logger_node ──订阅──> /chassis_state
└── cmd_monitor_node   ──订阅──> /control_cmd
```

## Python Launch 格式

实现文件：`ros2_ws/src/learning_tools_cpp/launch/learning_bringup.launch.py`。

```python
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="learning_tools_cpp",
                executable="topic_logger_node",
                name="topic_logger_node",
                output="screen",
            ),
            Node(
                package="learning_tools_cpp",
                executable="cmd_monitor_node",
                name="cmd_monitor_node",
                output="screen",
            ),
        ]
    )
```

`generate_launch_description` 是约定入口，返回的 `LaunchDescription` 包含需要执行的启动动作。

`Node` 中各名称的含义：

| 参数 | 含义 |
|---|---|
| `package` | 可执行程序所属的 ROS 2 Package |
| `executable` | 构建并安装后的可执行程序名 |
| `name` | 节点进入 ROS graph 后的运行时名称 |
| `output="screen"` | 将节点日志输出到当前终端 |

Package、可执行程序和节点名可以相同，但属于不同层次，不能混为一个概念。

## 安装与依赖配置

Launch 文件位于源码目录还不够，`ros2 launch` 从 Package 的安装结果中查找它。因此在 `CMakeLists.txt` 中添加：

```cmake
install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)
```

构建后文件被安装到：

```text
install/learning_tools_cpp/share/learning_tools_cpp/launch/
```

由于 Python Launch 使用 `launch` 和 `launch_ros`，在 `package.xml` 中声明运行依赖：

```xml
<exec_depend>launch</exec_depend>
<exec_depend>launch_ros</exec_depend>
```

这再次体现 DAY09 的分工：`package.xml` 声明依赖，`CMakeLists.txt` 描述如何安装资源。

## 构建与运行

```bash
source /opt/ros/lyrical/setup.bash
cd /home/changwei/changwei/project/ros2_ws
colcon build --packages-up-to learning_tools_cpp
source install/setup.bash
ros2 launch learning_tools_cpp learning_bringup.launch.py
```

`--packages-up-to learning_tools_cpp` 会构建目标包，以及当前 workspace 中目标包依赖的包。

在另一个已 source 的终端验证：

```bash
ros2 node list
ros2 node info /topic_logger_node
ros2 node info /cmd_monitor_node
ros2 topic info /chassis_state -v
ros2 topic info /control_cmd -v
```

预期至少能看到：

```text
/topic_logger_node
/cmd_monitor_node
```

两个节点都是订阅者。节点成功启动但没有消息日志，通常表示对应 Topic 没有发布者或没有新消息，不等同于 Launch 失败。排错时先用 `ros2 node list` 确认节点，再用 `ros2 topic info -v` 检查端点。

在 Launch 终端按 `Ctrl+C`，Launch 会统一停止它管理的节点。

## 验收结果

- 能解释 Launch 是启动编排，而不是节点业务逻辑；
- 能区分 Package、Executable 和运行时 Node Name；
- 能读懂 Python Launch 的固定入口和节点动作；
- 知道 Launch 文件必须经过安装才能被 `ros2 launch` 查找；
- 已补充 `launch`、`launch_ros` 运行依赖和 CMake 安装规则；
- 能用一条 Launch 命令同时启动两个监控节点；
- 能区分“节点未启动”和“节点已启动但 Topic 没有数据”。

验收结论：PASS。

## 今日结论

Launch 把多个独立节点组织成一个可重复启动和停止的系统入口。今天完成的是最小固定配置；后续可以在此基础上继续加入 Launch Argument、条件启动、参数和 remapping。

## 算法支线

完成 LeetCode 232“用栈实现队列”。使用输入栈接收新元素，使用输出栈提供队首元素。只有执行 `pop` 或 `peek`、且输出栈为空时，才把输入栈中的全部元素转移到输出栈。

必须等输出栈为空后再转移，否则新加入的元素可能越过尚未出队的旧元素，破坏先进先出顺序。这种延迟到需要队首时才转移的方式是惰性转移。

- `push`：O(1)；
- `pop`、`peek`：单次最坏 O(n)，均摊 O(1)；
- `empty`：O(1)；
- 额外空间复杂度：O(n)；
- 代码文件：`test/day10.cpp`。
