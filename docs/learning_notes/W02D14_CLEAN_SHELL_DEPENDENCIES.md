# W02D14 — 干净终端构建与 Package 依赖

日期：2026-08-20
状态：PASS

## 今日目标

从干净终端重新完成项目环境加载、选择性构建、工作区 overlay 加载和 Launch 验证，并整理 `chassis_agent_cpp` 的工作区依赖关系。通过这次复现，确认项目不是依赖旧终端中残留的环境变量才能运行。

## 干净终端与环境加载

新开终端后，先进入项目并加载统一环境：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
```

使用以下命令检查环境：

```bash
echo "$ROS_DISTRO"
which ros2
which python
python --version
```

当前项目加载 ROS 2 Lyrical，并使用 `embodied` conda 环境中的 Python。`source` 只改变当前 shell 的环境，新开的终端不会继承之前终端加载的 ROS 2 工作区 overlay，因此每个新终端都要重新加载环境。

完整顺序为：

```text
新终端
  → source scripts/env.sh
  → 进入 ros2_ws
  → colcon build
  → source install/setup.bash
  → ros2 run / ros2 launch
```

## 工作区位置检查

构建前进入标准 ROS 2 工作区：

```bash
cd /home/changwei/changwei/project/ros2_ws
pwd
```

必须确认当前目录是 `ros2_ws`。`colcon` 会在执行命令的当前目录创建 `build/`、`install/` 和 `log/`；如果在项目根目录构建，就会把这些生成物放错位置。它们不会在构建结束后自动删除。

## Package 发现

执行：

```bash
colcon list
```

`colcon list` 从源码空间发现 Package，并显示名称、路径和构建类型。它只能证明 Package 的源码可以被发现，不能证明 Package 已成功构建、安装或运行。

本工作区同时包含：

- 使用 `ament_cmake` 的 C++ Package；
- 使用 `ament_python` 的 Python Package。

## 工作区依赖图

执行：

```bash
colcon graph --packages-up-to chassis_agent_cpp
```

再列出参与构建的 Package：

```bash
colcon list \
  --packages-up-to chassis_agent_cpp \
  --names-only
```

当前构建范围包含：

```text
embodied_msgs
embodied_core
embodied_policy_cpp
chassis_agent_cpp
```

结合各包的 `package.xml`，可以整理为：

```text
chassis_agent_cpp
├── embodied_msgs
├── embodied_core
└── embodied_policy_cpp
    └── embodied_core
```

此外，`chassis_agent_cpp` 还直接声明了 `rclcpp` 和 `geometry_msgs` 等系统 ROS 依赖；`embodied_msgs` 依赖 `geometry_msgs`、`std_msgs` 和 ROS interface 生成工具。

`colcon` 根据依赖拓扑决定构建顺序。自定义消息包需要先生成消息代码和 typesupport，业务包才能在编译时引用生成的 C++ 类型。

## 选择性构建

执行：

```bash
colcon build \
  --symlink-install \
  --packages-up-to chassis_agent_cpp
```

本次选择性构建完成。`--packages-up-to` 会选择目标 Package 及其工作区依赖，适合首次构建、依赖发生变化或希望验证完整依赖链的场景。

与之对比：

| 参数 | 构建范围 | 典型场景 |
|---|---|---|
| `--packages-select` | 只选择指定 Package | 依赖已构建后的快速增量构建 |
| `--packages-up-to` | 目标 Package 及其工作区依赖 | 首次构建或依赖发生变化 |

构建完成只能说明编译和安装阶段成功，不能据此推断自动测试或运行时闭环一定通过。

## 加载并验证 Overlay

构建后执行：

```bash
source install/setup.bash
```

随后检查关键 Package 的安装位置：

```bash
ros2 pkg prefix embodied_msgs
ros2 pkg prefix embodied_core
ros2 pkg prefix embodied_policy_cpp
ros2 pkg prefix chassis_agent_cpp
```

这些路径应指向当前 `ros2_ws/install`。如果构建后没有重新 source，当前终端可能找不到新 Package，或者继续使用旧 overlay 中的安装结果。

## 依赖声明审计

当前 ROS 2 Lyrical 的 `ros2 pkg` 支持：

```text
create  executables  list  prefix  xml
```

它不提供 `ros2 pkg dependencies` 子命令。执行该命令出现 `invalid choice` 是 CLI 版本差异，不是 conda 或 ROS 环境故障。

本次改用下面的命令查看安装后的 Package 清单：

```bash
ros2 pkg xml chassis_agent_cpp
```

筛选依赖字段：

```bash
ros2 pkg xml chassis_agent_cpp |
  rg 'depend|buildtool'
```

工具分工如下：

| 工具或文件 | 用途 |
|---|---|
| `colcon graph` | 查看工作区 Package 的构建拓扑 |
| `colcon list --packages-up-to` | 列出目标及其工作区依赖 |
| `ros2 pkg xml` | 查看安装后的 Package manifest |
| `package.xml` | 声明 Package 层面的构建、运行和测试依赖 |
| `CMakeLists.txt` | 查找依赖，并把依赖连接到具体 C++ target |

对于 C++ Package，依赖通常需要同时正确出现在 `package.xml` 和 `CMakeLists.txt` 中。只修改一处可能导致本机增量构建偶然通过，却在干净环境中失败。

## Launch 验证

加载 overlay 后检查 Launch 参数：

```bash
ros2 launch learning_tools_cpp learning_bringup.launch.py --show-args
```

然后实际启动：

```bash
ros2 launch learning_tools_cpp learning_bringup.launch.py
```

本次 Launch 检查和实际启动均已完成。`--show-args` 只证明 Package、Launch 文件和参数能够被发现及解析；实际启动用于进一步确认节点可以创建并正常退出。

## 第二周遗留问题

Day13 已发现以下问题，本日暂不扩展修复范围：

1. `embodied_core` 的部分测试忽略带有 `[[nodiscard]]` 标记的 `tick()` 返回值，构建时产生警告；
2. 5 个 Python Package 没有收集到测试，pytest 返回 code 5，导致 `colcon test` 未全部通过。

这些问题不影响本次选择性构建和 Launch 学习验收，但不能记录为“全工作区测试通过”。

## 今日结论

今天从干净终端复现了 ROS 2 工程链路：项目环境负责提供 ROS 2 与 Python，`colcon` 根据 Package manifest 建立构建拓扑，构建产物进入 `install/`，加载 overlay 后 ROS 2 CLI 才能稳定发现当前工作区的 Package 和 Launch 文件。

第二周已经串联起自定义 Interface、Package、依赖声明、colcon 选择性构建、overlay 和 Launch。遇到 CLI 子命令缺失时，应先查看当前版本的 `-h` 输出，再选择 `ros2 pkg xml`、`colcon graph` 等当前发行版实际支持的工具。

## 算法支线

完成 LeetCode 347“前 K 个高频元素”，代码位于 `test/day14.cpp`。

第一版使用 `unordered_map` 统计每个元素的出现次数，再把键值对复制到 `vector` 中，按照频率降序排序并取前 `k` 个元素。

设数组长度为 `n`，不同元素数量为 `m`：

- 统计频率：O(n)；
- 排序：O(m log m)；
- 取结果：O(k)；
- 总时间复杂度：O(n + m log m)；
- 额外空间复杂度：O(m)。

该方法能够正确解决基础问题，但不满足题目的进阶复杂度要求。后续学习 `priority_queue` 时，可以用容量为 `k` 的小顶堆将候选维护降为 O(m log k)。
