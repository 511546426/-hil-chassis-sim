# W02D09 — Package、依赖与构建链路

日期：2026-07-22
状态：PASS

## 今日目标

理解 ROS 2 Package 的边界，以及 `package.xml`、`CMakeLists.txt`、colcon 和 workspace overlay 在构建链路中的职责。本日以建立整体认识为主，不要求记忆 CMake 或 XML 的具体语法。

## Package 的判断方式

Workspace 的 `src` 目录可以包含多个 Package，但不能简单认为它的每个子目录都是 Package。更准确的判断标准是：目录中存在 `package.xml`，并能被 colcon 识别。

```text
ros2_ws/                         Workspace
└── src/
    ├── embodied_msgs/           Package：有 package.xml
    │   ├── msg/                 普通子目录，不是 Package
    │   └── srv/                 普通子目录，不是 Package
    └── chassis_simulation/      Package：有 package.xml
```

Package 是功能和依赖的组织边界，不等于节点。一个 Package 可以包含零个、一个或多个节点，也可以只包含接口、库、launch 文件或测试。例如 `embodied_msgs` 是纯接口包，本身不需要运行节点。

检查 workspace 中的 Package：

```bash
cd /home/changwei/changwei/project/ros2_ws
colcon list
find src -name package.xml
```

## `package.xml` 与 `CMakeLists.txt`

二者共同描述一个 CMake 类型的 ROS 2 Package，但职责不同：

| 文件 | 核心职责 | 简化理解 |
|---|---|---|
| `package.xml` | 包名、版本、维护信息和依赖声明 | 我是谁、我依赖谁 |
| `CMakeLists.txt` | 查找依赖、生成接口、编译、链接、安装和测试 | 我具体怎样构建 |

`package.xml` 中常见依赖：

- `buildtool_depend`：构建工具依赖；
- `build_depend`：编译期间依赖；
- `exec_depend`：运行期间依赖；
- `depend`：覆盖常见的构建和运行依赖；
- `test_depend`：测试期间依赖。

`embodied_msgs/CMakeLists.txt` 的关键结构：

```cmake
project(embodied_msgs)

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/EmbodiedCommand.msg"
  "msg/EmbodiedWorldState.msg"
  # 其他接口
  DEPENDENCIES std_msgs geometry_msgs
)

ament_package()
```

- `project` 设置当前项目名称；
- `find_package` 查找构建所需依赖，`REQUIRED` 表示缺失时构建失败；
- `rosidl_generate_interfaces` 将列出的 `.msg`、`.srv` 等定义生成多语言代码和类型支持；
- `DEPENDENCIES` 声明接口字段引用的外部接口包；
- `ament_package` 完成 ROS 2 Package 的注册和导出。

## 构建依赖链

业务代码使用的消息头文件由接口包构建生成：

```text
EmbodiedCommand.msg
        ↓
构建 embodied_msgs
        ↓
生成 embodied_command.hpp 和类型支持
        ↓
构建 chassis_agent_cpp 等下游包
        ↓
业务节点使用 EmbodiedCommand
```

colcon 读取各包的 `package.xml`，建立依赖图，并按拓扑顺序构建，而不是简单按照目录名称排序。

```bash
colcon list --topological-order
colcon build --packages-select embodied_msgs
```

构建产生的主要目录：

- `build/`：构建中间文件；
- `install/`：可被其他包和终端使用的安装结果；
- `log/`：构建日志。

构建结束后执行：

```bash
source install/setup.bash
```

这是将当前 workspace 的安装结果叠加到系统 ROS 2 环境，使当前终端能够找到项目 Package、接口和可执行程序。正确顺序是先 source 系统 ROS 2，再 source workspace overlay。

## 实际工程策略

后续 `package.xml` 和 `CMakeLists.txt` 的具体编写可以由 AI 辅助完成，不需要背诵语法，但必须保留基本审查能力：

1. 判断节点或接口应该属于哪个 Package；
2. 判断新增功能依赖哪些包；
3. 新增依赖时检查两个构建文件是否同步；
4. 新增 `.msg/.srv/.action` 时检查是否加入接口生成列表；
5. 新增节点时检查编译、链接、安装或 Python 入口；
6. 修改后亲自构建，并根据错误验证生成结果。

常见错误的检查方向：

| 现象 | 优先检查 |
|---|---|
| `package not found` | 环境是否 source、依赖是否安装或声明 |
| 找不到生成的消息头文件 | 接口是否加入生成列表、接口包是否先构建 |
| `undefined reference` | 目标是否正确链接所需库或 typesupport |
| 构建成功但 `ros2` 找不到包 | 是否 source 了对应 `install/setup.bash` |

## 验收结果

- 能区分 Workspace、Package、子目录和节点；
- 知道含有 `package.xml` 且能被 colcon 识别的目录才是 Package；
- 能说明 `package.xml` 和 `CMakeLists.txt` 的职责差异；
- 能解释接口包为什么必须先于依赖它的业务包构建；
- 能说明 colcon 根据依赖图决定构建顺序；
- 能解释 `build`、`install`、`log` 和 workspace overlay；
- 明确后续采用“AI 生成配置、人工审查依赖、实际构建验证”的工作方式。

验收结论：PASS。

## 今日结论

今天的重点不是记忆构建语法，而是理解完整链路：

```text
package.xml 声明依赖
  → colcon 建立依赖图
  → CMakeLists.txt 执行构建
  → install 保存可使用的结果
  → source 将结果加入当前终端环境
```

## 算法支线

完成 LeetCode 20“有效的括号”的思路与实现。栈只保存尚未匹配的左括号：遇到左括号入栈；遇到右括号时，若栈为空或与栈顶不匹配，立即返回 `false`；匹配则出栈；遍历结束后只有栈为空才有效。

不能把不匹配的右括号继续入栈，因为不匹配已经证明括号嵌套顺序错误。

- 时间复杂度：O(n)；
- 额外空间复杂度：O(n)；
- 代码文件：`test/day09.cpp`。
