# W02D12 — colcon 选择性构建与工作区目录

日期：2026-08-19
状态：PASS

## 今日目标

练习使用 `colcon build` 控制 ROS 2 工作区的构建范围，理解 `--packages-select`、`--packages-up-to` 和 `--symlink-install` 的作用，并明确 `build/`、`install/`、`log/` 三个目录在构建链路中的职责。

## 工作区与 Package 检查

先加载系统 ROS 2 环境，再进入工作区：

```bash
conda deactivate
source /opt/ros/lyrical/setup.bash
cd /home/changwei/changwei/project/ros2_ws
colcon list
```

`colcon list` 会从工作区的 `src/` 中发现 Package，并显示包名、源码路径和构建类型。当前项目同时包含：

- `ament_cmake` 类型的 C++ 包；
- `ament_python` 类型的 Python 包。

这一步检查的是源码空间中有哪些包，并不代表这些包已经成功构建或已经加载到当前终端。

## `--packages-select`

只构建指定包：

```bash
colcon build \
  --symlink-install \
  --packages-select learning_tools_cpp
```

`--packages-select` 只把明确指定的包加入本次构建，不会主动补充构建它在当前工作区中的依赖。它适合下面的情况：

- 依赖包已经构建完成；
- 只修改了一个包，希望缩短增量构建时间；
- 希望单独验证某个包是否能够通过编译。

如果指定包依赖的自定义消息或库还没有生成，单独构建可能失败。此时不能简单地把错误理解为目标包源码有问题，还要检查依赖是否已经构建并加载。

## `--packages-up-to`

构建目标包以及它在当前工作区中的依赖：

```bash
colcon build \
  --symlink-install \
  --packages-up-to chassis_agent_cpp
```

使用下面的命令可以先观察构建范围和依赖关系：

```bash
colcon graph --packages-up-to chassis_agent_cpp
```

当前工作区中，构建 `chassis_agent_cpp` 会涉及：

```text
embodied_msgs
embodied_core
embodied_policy_cpp
chassis_agent_cpp
```

`colcon` 会按照拓扑顺序构建，先处理被依赖的包，再处理目标包。这也是自定义消息包通常需要先生成的原因：业务包编译时已经要引用消息包生成的 C++ 类型和 typesupport。

两种参数的核心区别是：

| 参数 | 构建范围 | 典型用途 |
|---|---|---|
| `--packages-select` | 只构建指定包 | 已有完整依赖后的快速增量构建 |
| `--packages-up-to` | 目标包及其工作区依赖 | 首次构建或依赖发生变化 |

## `--symlink-install`

`--symlink-install` 会尽可能让安装空间中的资源指向源码，而不是每次都复制一份。它适合开发阶段频繁修改 Python、Launch 和配置文件。

需要注意：

- C++ 源码变化后仍然需要重新编译；
- 新增可执行程序或修改 CMake 安装规则后仍然需要重新构建；
- 它减少的是部分资源复制，并不等于所有修改都无需构建。

## `build/`、`install/` 与 `log/`

执行 `colcon build` 后，工作区形成下面的结构：

```text
ros2_ws/
├── src/       源码空间
├── build/     构建空间
├── install/   安装空间
└── log/       日志空间
```

三个目录的职责分别是：

| 目录 | 作用 |
|---|---|
| `build/` | 保存编译中间文件、CMake 缓存以及每个包的构建状态 |
| `install/` | 保存可执行程序、库、接口、Launch 和环境脚本等安装结果 |
| `log/` | 保存每次构建的标准输出、错误输出和事件日志 |

ROS 2 命令通常使用 `install/` 中的结果，而不是直接运行 `src/` 中的文件。因此，源码目录里存在 Package 或 Launch 文件，不代表 `ros2 run`、`ros2 launch` 一定能够找到它。

构建失败时，应优先查看终端中最早出现的有效错误，再到 `log/latest_build/` 查看具体包的完整日志，避免只看最后一条连锁失败信息。

## Overlay 与验证

构建完成后需要加载工作区 overlay：

```bash
source install/setup.bash
```

完整顺序是：

```text
source 系统 ROS 2
  → colcon 构建工作区
  → source 工作区 install/setup.bash
  → 使用 ros2 命令验证安装结果
```

使用以下命令检查 Package 和可执行程序：

```bash
ros2 pkg prefix learning_tools_cpp
ros2 pkg executables learning_tools_cpp
ros2 launch learning_tools_cpp learning_bringup.launch.py --show-args
```

如果构建成功但 `ros2` 找不到包，首先检查当前终端是否重新执行了 `source install/setup.bash`。新开终端后环境不会自动继承，也需要按顺序重新 source。

## 验收结果

- 能使用 `colcon list` 查看工作区 Package；
- 能解释 `--packages-select` 与 `--packages-up-to` 的构建范围；
- 能使用 `colcon graph` 查看目标包的工作区依赖；
- 理解 `--symlink-install` 适合开发阶段，但不能代替 C++ 重新编译；
- 能说明 `build/`、`install/`、`log/` 的职责；
- 知道 ROS 2 实际使用的是安装空间中的结果；
- 能按系统 ROS 2、构建、workspace overlay 的顺序加载环境；
- 能通过 `ros2 pkg` 和 `ros2 launch --show-args` 验证安装结果。

验收结论：PASS。

## 今日结论

今天把 ROS 2 构建过程从“一条固定命令”拆解成了可理解的工程链路：`colcon` 根据 Package 依赖确定构建范围，在 `build/` 中完成构建，将可运行结果放入 `install/`，并把过程记录到 `log/`。开发时可以用 `--packages-select` 加快单包迭代，用 `--packages-up-to` 保证目标包及其依赖处于可用状态。

## 算法支线

完成 LeetCode 150“逆波兰表达式求值”。从左到右扫描 token：遇到数字时压入栈，遇到运算符时弹出两个操作数，计算后再把结果压回栈。

弹出顺序必须注意：第一个弹出的是右操作数，第二个弹出的是左操作数。对于减法和除法，应计算 `left - right` 和 `left / right`，不能颠倒。

- 时间复杂度：O(n)；
- 额外空间复杂度：O(n)；
- 每个数字只入栈、出栈一次；
- 最终栈顶元素就是表达式结果；
- 代码文件：`test/day12.cpp`。
