# W02D08 — 自定义 Interface 与字符串栈

日期：2026-07-21
状态：PASS

## 今日目标

今天进入第二周。ROS 2 主线是理解自定义消息从 `.msg` 文件到 C++/Python 类型的生成过程，并逐字段解释 `EmbodiedCommand` 与 `EmbodiedWorldState`；算法支线进入字符串与栈，练习 LeetCode 1047“删除字符串中的所有相邻重复项”。

本日以接口阅读、构建和 CLI 检查为主，不新增 ROS 2 节点。实际学习进一步延伸到 DDS，以及 Topic、Service、Action 三种通信模型的选择。

## ROS 2：Interface 是什么

Interface 是节点之间共享的数据契约，而不是节点的业务实现。

- `.msg`：单向数据结构，常用于 Topic；
- `.srv`：请求与响应两段结构，适合短时调用；
- `.action`：Goal、Result、Feedback 三段结构，适合可反馈、可取消的长任务。

本项目的 `embodied_msgs` 是纯接口包。`rosidl_generate_interfaces` 读取接口文件，为不同语言生成类型支持代码；业务包依赖生成后的接口，而不是解析 `.msg` 文本。

可以把 ROS 2 `.msg` 类比为 Protobuf 的 `message`：两者都描述数据结构并生成多语言代码。但 `.msg` 不是通信协议；ROS 2 在接口之上提供 Topic、Service 和 Action，底层通常由 DDS 负责发现、序列化、传输和 QoS。

生成链路：

```text
*.msg
  → rosidl_generate_interfaces(...)
  → C/C++、Python 类型与中间件类型支持
  → 业务节点 include/import
  → DDS 序列化并跨进程传输
```

## Topic、Service 与 Action

| 模型 | 交互方式 | 是否返回结果 | 反馈/取消 | 本项目示例 |
|---|---|---|---|---|
| Topic | 发布—订阅 | 无内置结果 | 无 | `/world_state`、`/control_cmd` |
| Service | 一次请求—响应 | 一次响应 | 无标准持续反馈或取消 | `/sim/reset_episode` |
| Action | 长任务生命周期 | 最终 Result | 支持 Feedback 和 Cancel | 后续的推红箱任务 |

- Topic 适合持续、高频数据。发布者不需要知道有多少订阅者，也不会等待逐条回应。
- Service 适合能较快完成的一次性操作。Client 发送 Request，Service Server 返回 Response。
- Action 适合导航、抓取、推箱等耗时任务。Client 发送 Goal，Action Server 可以接受或拒绝，执行期间发布 Feedback，并最终返回 Result；Client 还可以请求 Cancel。
- `Server` 不是第四种通信方式，而是 Service 或 Action 中负责处理请求、执行任务的一端。

选择口诀：持续广播用 Topic；快速的一问一答用 Service；需要进度、取消和最终结果的长任务用 Action。

## DDS 的位置

DDS（Data Distribution Service）是数据分发中间件标准，不是单个软件。ROS 2 通过 `rmw` 抽象适配 Fast DDS、Cyclone DDS 等实现：

```text
业务节点
  → rclcpp / rclpy
  → rcl
  → rmw
  → DDS 实现
  → UDP / TCP / 共享内存等传输方式
```

DDS 主要负责发现发布者和订阅者、匹配 Topic 与消息类型、序列化和传输数据，以及按照 QoS 决定可靠性、缓存和历史数据行为。

## `EmbodiedCommand` 字段审计

文件：`ros2_ws/src/embodied_msgs/msg/EmbodiedCommand.msg`

| 字段 | 类型 | 单位/范围 | 语义 |
|---|---|---|---|
| `target_linear_x` | `float64` | 速度单位由项目约定 | 期望底盘线速度，不是实测速度 |
| `target_steering_angle` | `float64` | rad | 期望转向角 |
| `emergency_brake` | `bool` | true/false | 紧急制动意图，应优先于普通运动命令 |
| `arm_shoulder` | `float64` | rad | 肩关节目标角 |
| `arm_elbow` | `float64` | rad | 肘关节目标角 |
| `arm_wrist` | `float64` | rad | 腕关节目标角 |
| `gripper` | `float64` | 约定 0.0–1.0 | 0.0 张开，1.0 闭合 |

关键结论：它描述“控制器希望执行什么”，不证明机器人已经达到这些状态。该消息目前没有 `Header`，因此无法仅靠消息本身判断命令的产生时间和坐标系。

## `EmbodiedWorldState` 字段审计

文件：`ros2_ws/src/embodied_msgs/msg/EmbodiedWorldState.msg`

| 字段组 | 主要字段 | 语义与注意点 |
|---|---|---|
| 元数据 | `header` | `stamp` 表示观测时刻；`frame_id` 应说明位姿所属坐标系 |
| 底盘 | `base_x/y/yaw/vx/steer` | 当前观测状态，不是控制目标；位置和姿态单位需有明确约定 |
| 机械臂 | `arm_shoulder/elbow/wrist/gripper` | 当前关节与夹爪状态 |
| 物体 | `object_poses[]`、`object_names[]` | 两个并行数组依靠同一下标关联，长度不一致必须视为无效或降级处理 |
| 接触 | `gripper_touching_object`、`touched_object_name` | 布尔值表示是否接触，名称表示接触对象；两者应保持一致 |

`geometry_msgs/Pose` 只含位置和方向，不自带时间戳及坐标系。因此数组中的所有物体位姿必须共同遵循 `header` 的时空语义。

## 构建配置阅读

在 `embodied_msgs/CMakeLists.txt` 中重点找到：

```cmake
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/EmbodiedCommand.msg"
  "msg/EmbodiedWorldState.msg"
  # ...
  DEPENDENCIES std_msgs geometry_msgs
)
```

理解要点：

- `rosidl_default_generators` 在构建期生成语言绑定；
- `DEPENDENCIES` 声明接口字段引用了哪些外部接口包；
- `rosidl_default_runtime` 是使用生成接口时的运行期依赖；
- `member_of_group` 表明这是一个 ROS interface package。

## CLI 实验

本机安装的 ROS 2 发行版为 Lyrical。先加载系统 ROS 2，再构建接口包和加载 workspace overlay：

```bash
cd ros2_ws
source /opt/ros/lyrical/setup.bash
echo "$ROS_DISTRO"
colcon build --packages-select embodied_msgs
source install/setup.bash
```

查看接口：

```bash
ros2 interface show embodied_msgs/msg/EmbodiedCommand
ros2 interface show embodied_msgs/msg/EmbodiedWorldState
ros2 interface package embodied_msgs
ros2 interface packages | grep embodied_msgs
```

Topic 类型检查：

```bash
ros2 topic type /control_cmd
ros2 topic type /world_state
```

若提示接口不存在，依次检查：包是否构建成功、当前终端是否 source 了 `install/setup.bash`、接口名是否使用 `包名/msg/类型名` 格式。

实际操作中，首次使用：

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
```

出现 `/opt/ros//setup.bash` 不存在，是因为新终端中的 `ROS_DISTRO` 还未设置。通过 `ls /opt/ros` 确认安装目录为 `lyrical` 后，改为显式加载 `/opt/ros/lyrical/setup.bash`，此后 `ROS_DISTRO` 才有值。

执行 `ros2 topic type /control_cmd` 没有输出，是因为相关节点未启动，`/control_cmd` 尚未出现在当前 ROS graph。这不等于接口构建失败：`ros2 interface show` 检查已经生成并加载的接口；`ros2 topic type` 查询当前运行系统中的 Topic，后者需要至少有对应的发布或订阅端点。

## 算法支线：LeetCode 1047

题目：给定只含小写字母的字符串，反复删除相邻且相同的两个字符，返回最终字符串。

使用 `std::string` 直接充当栈：

1. 从左到右读取字符；
2. 若结果非空且栈顶等于当前字符，使用 `pop_back()` 删除栈顶；
3. 否则使用 `push_back()` 压入当前字符；
4. 遍历结束后，结果字符串就是答案。

示例：`abbaca → aaca → ca`。

- 时间复杂度：O(n)，每个字符最多入栈、出栈各一次；
- 额外空间复杂度：O(n)；
- 代码文件：`test/day08.cpp`。

容易犯错：只删除原字符串中第一轮可见的重复项；在遍历原字符串时直接 `erase`，导致下标失效或退化为较高时间复杂度。

## 验收结果

- 能说清 `.msg → 生成代码 → 节点使用` 的链路；
- 能区分控制目标 `EmbodiedCommand` 与观测状态 `EmbodiedWorldState`；
- 能解释 `Header` 和 `Pose` 的语义边界；
- 能指出物体名称和位姿并行数组的约束与风险；
- 能说明系统 ROS 环境与 workspace overlay 的 source 顺序；
- 能区分接口已生成与 Topic 已在运行图中出现；
- 能根据任务时效、结果、反馈和取消需求选择 Topic、Service 或 Action；
- 已完成 LeetCode 1047，并能解释栈处理连锁重复的过程和复杂度。

验收结论：PASS。

## 今日结论

Interface 负责定义数据契约，通信模型负责表达交互语义，DDS 负责底层发现和数据分发。`EmbodiedCommand` 是控制目标，`EmbodiedWorldState` 是当前观测；持续状态和控制流适合 Topic，快速复位适合 Service，推红箱这类需要进度、取消和最终结果的任务适合 Action。排错时应区分“接口能否被环境找到”和“运行中的 ROS graph 是否存在对应端点”。
