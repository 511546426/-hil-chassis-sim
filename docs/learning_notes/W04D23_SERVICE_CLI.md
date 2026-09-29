# W04D23 — Service CLI 与仿真 Reset 验证

日期：2026-09-29
状态：PASS

## 今日目标

使用 ROS 2 CLI 完整检查和调用 `/sim/reset_episode`，理解 `.srv` 的 Request/Response 契约，分别验证默认位姿、自定义位置和朝向复位，并观察 Service Server 停止后的行为，为 Day24 编写异步 C++ Reset Client 做准备。

## 运行时发现

加载项目环境和 workspace overlay：

```bash
cd /home/changwei/changwei/project
source scripts/env.sh
cd ros2_ws
source install/setup.bash
```

单独启动 Simulation：

```bash
ros2 launch chassis_simulation hil_demo.launch.py
```

保持节点运行后，ROS Graph 中出现 Simulation 提供的 Topic 和 Service。与 Topic 一样，Service 只有在 Server 节点运行时才能被发现；源码中存在 `create_service()` 不代表端点会永久存在。

## Service 发现与类型

列出仿真 Service：

```bash
ros2 service list |
  rg '/sim/'
```

主要端点：

```text
/sim/reset_episode
/sim/set_virtual_grasp
```

查看 Reset 类型：

```bash
ros2 service type /sim/reset_episode
```

结果：

```text
embodied_msgs/srv/ResetEpisode
```

按接口类型查找当前端点：

```bash
ros2 service find embodied_msgs/srv/ResetEpisode
```

Simulation 运行时至少能找到 `/sim/reset_episode`；如果 Agent 同时运行，还能找到复用相同接口类型的 `/agent/reset_episode`。

## `.srv` 接口定义

执行：

```bash
ros2 interface show embodied_msgs/srv/ResetEpisode
```

接口为：

```text
float64 base_x 0.0
float64 base_y 0.0
float64 base_yaw 0.0
---
bool success
string message
```

`---` 上方是 Request，下方是 Response。三个 Request 字段都有默认值，因此 `{}` 并非“没有请求数据”，而是使用：

```yaml
base_x: 0.0
base_y: 0.0
base_yaw: 0.0
```

Response 使用 `success` 表示业务结果，并通过 `message` 提供说明。

## 默认位姿 Reset

调用：

```bash
ros2 service call \
  /sim/reset_episode \
  embodied_msgs/srv/ResetEpisode \
  "{}"
```

调用返回成功 Response，仿真将底盘复位到默认原点附近。

状态通过以下命令验证：

```bash
ros2 topic echo /chassis_state --once
```

Odometry 中的 `position.x` 和 `position.y` 接近 `0.0`。物理仿真和浮点计算可能产生很小误差，因此验证时不要求输出文本严格等于零。

## 自定义位置 Reset

调用：

```bash
ros2 service call \
  /sim/reset_episode \
  embodied_msgs/srv/ResetEpisode \
  "{base_x: 1.0, base_y: 0.5, base_yaw: 0.0}"
```

再次读取：

```bash
ros2 topic echo /chassis_state --once
```

底盘位置接近 `(1.0, 0.5)`。这证明 Request 字段不仅被 CLI 接收，也进入服务端并实际改变了仿真状态。

Service 验证不能只看 `success: true`，还应检查操作后的 Topic 状态是否符合请求。

## 自定义朝向 Reset

调用：

```bash
ros2 service call \
  /sim/reset_episode \
  embodied_msgs/srv/ResetEpisode \
  "{base_x: 0.0, base_y: 0.0, base_yaw: 1.57}"
```

`1.57 rad` 约为 90°。Odometry 使用四元数表示 Orientation，因此输出不会直接显示 `1.57`。对于平面 90° yaw，四元数的 `z` 和 `w` 通常接近 `0.707`。

这次操作验证了 Request 中的朝向字段能够生效，也区分了欧拉角输入和四元数状态输出。

## 世界状态检查

执行：

```bash
ros2 topic echo /world_state --once
```

检查：

- `base_x` 与 `base_y`；
- 红箱和蓝箱位置；
- 机械臂和夹爪状态；
- episode 相关状态是否回到初始值。

Simulation Reset 不只修改 Odometry，它还负责机器人、场景物体、tracker 和虚拟抓取等仿真状态的复位。

## 连续调用验证

依次使用不同 Request：

```text
(0.0, 0.0, 0.0)
(1.0, 0.0, 0.0)
(-1.0, 0.5, -1.57)
```

每次调用后读取 `/chassis_state`，状态均随最新 Request 更新。这说明 Server 能够重复处理 Reset，而不是一次性接口。

Day27 将把手动连续调用扩展为自动 20 次 Reset，并检查每次初始状态和失败次数。

## 通信成功与业务成功

Service 调用存在两个层次：

1. Client 找到 Server、发送 Request 并收到 Response；
2. Response 的 `success` 为 `true`，且实际状态符合请求。

Server 即使业务处理失败，也可以正常返回：

```text
success: false
message: "失败原因"
```

因此 Client 不能仅以“收到了 Response”判断 Reset 成功。后续自动 Client 还应验证业务字段，必要时再检查状态 Topic。

## Service 不可用场景

停止 Simulation 后：

```bash
ros2 service list |
  rg '/sim/reset_episode'
```

不再有输出。此时执行：

```bash
ros2 service call \
  /sim/reset_episode \
  embodied_msgs/srv/ResetEpisode \
  "{}"
```

CLI 会等待 Service 出现，需要通过 `Ctrl+C` 中断。这说明 Client 不能假定 Server 永远在线，也不能无限等待。

Day24 的 C++ Client 需要显式使用 `wait_for_service()`，并决定等待周期、总超时和失败退出策略。

## 同步 CLI 与异步 Client

`ros2 service call` 的使用流程表现为：

```text
发送 Request
→ 阻塞等待
→ 输出 Response
→ 命令结束
```

Day24 的 C++ Client 将使用：

```text
创建 Client
→ wait_for_service
→ async_send_request
→ Future
→ spin 等待完成
```

“异步发送”不等于自动具备超时处理。程序仍需控制服务发现等待时间和 Response 等待时间，并避免永久阻塞。

## 今日结论

今天从接口发现、类型查询、契约阅读、默认 Request、自定义 Request、状态验证、连续调用和服务不可用路径，完成了 `/sim/reset_episode` 的 CLI 闭环。

Service 适合短时请求/响应，但可靠 Client 仍必须处理 Server 不可用、Response 超时和业务失败。CLI 适合手动检查接口，重复调用和自动验收应由程序化 Client 完成。

## 算法支线

完成 LeetCode 222“完全二叉树的节点个数”，代码位于 `test/day23.cpp`。

基础递归 `左子树节点数 + 右子树节点数 + 1` 适用于所有二叉树。优化版本利用题目保证的完全二叉树性质：如果当前子树最左高度等于最右高度，则它是满二叉树，可以直接返回：

```text
2^height - 1
```

否则继续递归统计左右子树。

复杂度：

- 时间复杂度：O(log² n)；
- 递归调用栈：O(log n)。

“左右边界高度相等就一定是满二叉树”的结论依赖完全二叉树前提，不能直接用于任意普通二叉树。
