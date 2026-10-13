# W04D27 — Service 连续调用可靠性验证

日期：2026-10-13  
状态：PASS

## 今日目标

完成“找树左下角的值”递归算法，并通过连续调用 `/sim/reset_episode` 验证 ROS2 Service Server 在重复请求下的稳定性。

## 算法：找树左下角的值

文件：`test/day27.cpp`

递归函数携带当前深度：

```cpp
void dfs(TreeNode* node, int depth);
```

同时维护：

- `max_depth`：目前遇到的最大深度；
- `result`：最底层最左节点的值。

遍历顺序为“当前节点、左子树、右子树”。当满足：

```cpp
depth > max_depth
```

时更新答案。由于左子树先遍历，同一层第一次访问到的节点就是最左节点；使用 `>` 而不是 `>=` 可以避免同层右侧节点覆盖答案。

复杂度：时间 `O(n)`；递归栈空间 `O(h)`。

## ROS2：Service 连续调用验证

启动仿真：

```bash
cd ~/changwei/project
source scripts/env.sh
cd ros2_ws
source install/setup.bash
ros2 launch chassis_simulation hil_demo.launch.py
```

确认服务：

```bash
ros2 service list | rg '/sim/reset_episode'
ros2 service type /sim/reset_episode
ros2 service info /sim/reset_episode
```

## ROS2 CLI 版本兼容

当前 ROS2 版本的 `ros2 service call` 不支持 `--spin-time` 参数。之前使用该参数会出现：

```text
ros2: error: unrecognized arguments: --spin-time 1
```

删除该参数即可。一次 `ros2 service call` 会等待 Response 并在完成后退出。

## 连续调用命令

```bash
for i in $(seq 1 20); do
  x=$(awk "BEGIN {printf \"%.2f\", ($i - 10) * 0.1}")

  echo "第 ${i} 次调用，base_x=${x}"

  ros2 service call \
    /sim/reset_episode \
    embodied_msgs/srv/ResetEpisode \
    "{base_x: ${x}, base_y: 0.0, base_yaw: 0.0}"

  sleep 0.2
done
```

每次请求使用不同的 `base_x`，验证 Server 能够重复接收并处理不同参数，而不是只能成功处理第一次请求。

如果需要限制单次调用等待时间，可以使用系统命令：

```bash
timeout 3s ros2 service call \
  /sim/reset_episode \
  embodied_msgs/srv/ResetEpisode \
  "{base_x: 0.5, base_y: 0.0, base_yaw: 0.0}"
```

当前版本支持的 CLI 参数可通过以下命令确认：

```bash
ros2 service call -h
```

## 验证结果

连续调用验证结果：

```text
总请求次数：20
成功次数：20
失败次数：0
超时次数：0
```

每次调用均正常收到 Response，说明 `/sim/reset_episode` 能够稳定处理连续请求。必要时可在调用后检查状态：

```bash
ros2 topic echo /chassis_state --once
ros2 topic echo /world_state --once
```

Service 验证应同时关注通信结果和状态结果：收到 `success: true` 表示业务调用成功，Topic 状态则用于确认 Reset 确实生效。

## 编译检查

```bash
g++ -std=c++17 -Wall -Wextra -pedantic -fsyntax-only test/day27.cpp
git diff --check
```

算法语法检查和笔记格式检查通过，Day27 ROS2 连续 Service 调用验证通过。
