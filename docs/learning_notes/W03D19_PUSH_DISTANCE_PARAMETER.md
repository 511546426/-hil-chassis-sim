# W03D19 — 推箱成功距离参数化

日期：2026-09-09
状态：PASS（GUI smoke test 受执行环境限制）

## 今日目标

根据 Day18 的硬编码审计结果，选择低风险配置 `push_min_dist`，将其从 Core 中的默认配置暴露为 `chassis_agent_cpp` 的 ROS 2 Parameter。默认值保持 `0.20 m`，并补充有限正数校验、实际值日志和回归验证。

## 选择 `push_min_dist` 的原因

`PushRedBoxFSM::Config` 已经定义：

```cpp
double push_min_dist{0.20};
```

FSM 在 BackUp 阶段使用该值判断任务是否完成：

```cpp
if (has_box_push_origin_ && moved >= config_.push_min_dist) {
  // transition to Done
}
```

因此核心算法已经具备配置能力，只缺少 ROS 节点层的入口。与修改控制周期或泛化红箱任务相比，这项改造范围小、默认行为不变，也容易验证正常路径和错误路径。

## 参数声明

在 `agent_node.cpp` 中定义默认值：

```cpp
constexpr double kDefaultPushMinDist = 0.20;
```

在 `AgentNode` 构造函数中声明：

```cpp
declare_parameter("push_min_dist", kDefaultPushMinDist);
```

现在可以通过 ROS 2 CLI 在启动时覆盖推动距离，不再需要修改 FSM 头文件后重新编译 Core。

## 参数传递链路

参数从节点进入 FSM 的路径是：

```text
ROS Parameter: push_min_dist
  → AgentNode
  → RuleBrain::Config
  → PushRedBoxFSM::Config
  → BackUp 阶段完成判断
```

`rule_brain_config_from_node()` 读取参数并赋值：

```cpp
const double push_min_dist =
    node.get_parameter("push_min_dist").as_double();

cfg.fsm.push_min_dist = push_min_dist;
```

这里不仅声明参数，还把值真正传入了运行逻辑。只完成 `declare_parameter()` 而不更新 Config，不会改变 FSM 行为。

## 合法性校验

有效推动距离必须是有限正数：

```cpp
if (!std::isfinite(push_min_dist) || push_min_dist <= 0.0) {
  throw std::invalid_argument(
      "push_min_dist must be finite and greater than 0");
}
```

校验拒绝：

- 零；
- 负数；
- `NaN`；
- 正负无穷大。

错误配置在节点启动阶段立即失败，比静默使用默认值更容易定位。

## 日志与真实配置一致

参数化前，启动日志写死：

```text
倒车推箱（≥ 0.2 m）
```

参数化后打印实际 Config：

```cpp
RCLCPP_INFO(
    get_logger(),
    "  任务: NAV → REACH → 夹爪 → 倒车推箱（≥ %.2f m）",
    rule_cfg_.fsm.push_min_dist);
```

这样 CLI 覆盖参数后，日志不会继续显示过期的默认值。

## 构建验证

执行：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
cd ros2_ws

colcon build \
  --symlink-install \
  --packages-up-to chassis_agent_cpp
```

结果：

```text
Summary: 4 packages finished [30.8s]
```

构建范围包括：

```text
embodied_core
embodied_msgs
embodied_policy_cpp
chassis_agent_cpp
```

## 启动参数验证

使用默认值启动时，日志显示：

```text
任务: NAV → REACH → 夹爪 → 倒车推箱（≥ 0.20 m）
```

使用 CLI 覆盖：

```bash
ros2 run chassis_agent_cpp agent_node \
  --ros-args \
  -p brain:=rule \
  -p push_min_dist:=0.10
```

日志随之显示：

```text
任务: NAV → REACH → 夹爪 → 倒车推箱（≥ 0.10 m）
```

这证明参数覆盖值已经进入 RuleBrain 和 FSM 配置，而不只是存在于参数服务器。

使用零值启动：

```bash
ros2 run chassis_agent_cpp agent_node \
  --ros-args \
  -p brain:=rule \
  -p push_min_dist:=0.0
```

节点拒绝启动并报告：

```text
push_min_dist must be finite and greater than 0
```

正常默认值、CLI 覆盖值和非法值路径均完成验证。

## 回归测试

执行受影响的 C++ Package 测试：

```bash
colcon test \
  --packages-select embodied_core chassis_agent_cpp

colcon test-result --verbose
```

结果：

```text
Summary: 2 packages finished [1min 0s]
Summary: 71 tests, 0 errors, 0 failures, 0 skipped
```

Core 与 C++ Agent 的 71 项测试全部通过。

## Smoke test 环境限制

默认 smoke test 命令为：

```bash
./scripts/m5_smoke_test.sh
```

首次运行被执行环境禁止写入 `~/.ros/log`。将 `ROS_LOG_DIR` 指向 `/tmp` 后，Simulation 已进入启动流程，但 GLFW 无法连接当前环境的 Wayland Display：

```text
Wayland: Failed to connect to display
ERROR: could not initialize GLFW
```

因此本次自动执行环境未完成端到端 smoke test。失败发生在显示系统初始化阶段，不是参数解析、FSM 或编译错误。默认参数下的最终 GUI/smoke 回归仍可在具有桌面显示权限的本机终端执行：

```bash
cd /home/changwei/changwei/project
./scripts/m5_smoke_test.sh
```

本次已有构建、默认与覆盖参数启动、非法值拒绝，以及 71 项 C++ 测试作为代码验证证据。

## 当前实现边界

`push_min_dist` 只在节点启动时读取。Day19 不支持任务执行期间动态修改该值，因为运行中改变成功条件需要明确以下语义：

- 是否影响已经开始的 episode；
- 是否只对下一个任务生效；
- 改小阈值后是否立即完成当前任务；
- Agent、日志和测试配置如何保持一致。

Day20 将参数暴露到 Launch，使用户无需编写较长的 `--ros-args` 命令。当前不修改全局 Topic、控制周期或红箱任务架构。

## 今日结论

今天完成了从硬编码审计到低风险工程改造的闭环。`push_min_dist` 现在具有明确默认值、ROS Parameter 入口、有限正数校验、Config 传递链路和真实值日志。默认值保持 `0.20 m`，不会主动改变现有任务契约。

这次改造也说明：参数化不等于只声明一个 Parameter。完整参数化需要把值传到实际业务对象、验证合法范围、让日志反映真实配置，并补充正常与错误路径验证。

## 算法支线

完成 LeetCode 226“翻转二叉树”，代码位于 `test/day19.cpp`。

递归处理每个非空节点：交换左右孩子，再递归翻转交换后的左右子树，最后返回当前根节点。空节点直接返回 `nullptr`。

设树有 `n` 个节点、树高为 `h`：

- 时间复杂度：O(n)；
- 递归调用栈：O(h)；
- 平衡树调用栈为 O(log n)；
- 退化链表时最坏为 O(n)。
