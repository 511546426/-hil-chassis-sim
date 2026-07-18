# ROS 2 × 具身仿真项目：12 周学习与落地计划

> 适用对象：熟悉 C++ 基础，正在通过本仓库系统学习 ROS 2。
> 周期：12 周，可按掌握程度顺延，不为赶日历牺牲质量。
> 默认投入：工作日每天 2 小时，周末至少一次连续 3 小时联调。
> 主语言：C++；Python 用于 MuJoCo 仿真、测试辅助和后续训练。
> 核心闭环：**官方概念 → 独立手写 → 审计本项目 → 改造本项目 → 自动验收**。

---

## 1. 最终目标

12 周结束时，不以“看完多少教程”或“写了多少练习节点”为完成标准，而以以下成果验收：

1. 能独立解释本项目所有节点、Topic、Service、Action、TF 和包依赖。
2. 将“推红箱”实现为标准 ROS 2 Action，支持 feedback、cancel、timeout 和明确 Result。
3. 建立 `odom → base_link → arm_* → gripper_link` 坐标树，并能在 RViz 中检查。
4. 能用 rosbag2 和 diagnostics 记录、定位、复现一次任务失败。
5. 仓库提供统一构建和测试入口，覆盖 C++、Python 与 headless 集成测试。
6. 自动执行至少 20 个 episode，输出成功率、耗时和失败原因。
7. 新增第二个任务时复用现有 Skill，而不是复制一套 Agent/FSM。

暂不作为本阶段主线：

- 新增 LLM Planner backend；
- 继续扩展 RL/Hybrid Brain；
- 训练新策略；
- 增加更多演示脚本；
- 接真实硬件。

现有 Planner、RL 和 ONNX 代码保留为后续专题，不删除，但前 12 周不继续扩张。

---

## 2. 学习原则

### 2.1 每周固定闭环

| 时间 | 工作 | 必须留下的证据 |
|---|---|---|
| 周一 | 学官方概念 | 一页以内笔记，能用自己的话解释 |
| 周二 | 在 `learning_tools_cpp` 写最小实验 | 可编译、可运行的独立节点 |
| 周三 | 审计本项目对应实现 | 问题清单或接口表，不只摘抄代码 |
| 周四 | 改造主项目 | 小而完整的代码提交 |
| 周五 | 补错误路径与测试 | 至少一个失败场景 |
| 周末 | 联调、复盘、演示 | 一条验收命令、一份结果记录 |

任何一周如果验收失败，不自动进入下一周。先记录失败原因，再补齐当前里程碑。

### 2.2 每日两小时建议

| 内容 | 时间 | 说明 |
|---|---:|---|
| 算法/C++ 基础 | 30–45 min | 若不准备算法面试，可缩短到 20 min |
| ROS 2 官方材料 | 15–20 min | 只读本周主题，不漫游文档 |
| 手写或项目改造 | 45–60 min | 当天主要产出 |
| 运行、排错、笔记 | 15–25 min | 记录命令、现象和结论 |

周末必须安排连续时间。ROS 2 的编译、启动与跨进程排错不适合被切成十分钟碎片。

### 2.3 “掌握”的判据

每个知识点必须通过四关：

1. **能说**：不用术语堆砌，能解释它解决什么问题。
2. **能写**：不复制主项目，独立写一个最小示例。
3. **能选**：能说明为什么这里用 Topic、Service 或 Action。
4. **能排错**：故意制造一个错误，并能用 CLI、日志或测试定位。

### 2.4 版本与资料规则

- 先执行 `echo "$ROS_DISTRO"` 确认实际发行版。
- 优先阅读与本机发行版一致的官方文档。
- 若只能参考 Rolling 文档，笔记中标记版本差异，不直接假定 API 相同。
- 项目文档描述与代码冲突时，以测试和运行结果为准，并更新过期文档。

---

## 3. 学习代码与产品代码的边界

### 3.1 练习包

主练习包使用：

```text
ros2_ws/src/learning_tools_cpp/
├── CMakeLists.txt
├── package.xml
├── src/
├── include/learning_tools_cpp/
├── launch/
└── test/
```

规则：

- 最小实验先写在练习包；
- 不复制 `chassis_agent_cpp` 的完整业务逻辑；
- 同一练习通常只写 C++ 版本；
- Python 示例仅在比较 `rclpy` 与 `rclcpp` 或测试仿真边界时增加；
- 练习节点验证概念后，真正有产品价值的实现进入业务包；
- `learning_tools_cpp` 必须纳入版本控制，不能长期停留在未跟踪状态。

### 3.2 主项目黄金路径

本阶段只维护一条主路径：

```text
ExecuteTask Action Client
          ↓
chassis_agent_cpp / Task Action Server
          ↓
embodied_core / RuleBrain + Skills
          ↓
/control_cmd
          ↓
chassis_simulation / MuJoCo
          ↓
/world_state + TF + diagnostics
```

Python Agent、RLBrain、HybridBrain 和 LLM Planner 作为对照或选修，不与主路径同时扩展。

---

## 4. 十二周总览

| 周 | ROS 2 主题 | 练习包产出 | 主项目交付 | 周验收 |
|---|---|---|---|---|
| W1 | Node、Topic、CLI | 状态/命令监控节点 | 节点与 Topic 清单 | 能画并解释数据流 |
| W2 | Interface、Package、Launch | 双节点 launch | 包依赖与启动入口梳理 | 干净选择性构建 |
| W3 | Parameter、Namespace、Remap | 参数化监控节点 | 减少硬编码名称和目标 | launch 参数可切换 |
| W4 | Service、异步 Client | reset client | reset 生命周期测试 | 连续复位 20 次 |
| W5 | Action 基础 | 最小 Action server/client | `ExecuteTask.action` 契约 | CLI 可发目标和取消 |
| W6 | Action 状态机 | feedback/cancel/timeout 实验 | 推红箱 Action 化 | 成功、取消、超时均可验收 |
| W7 | TF2 | broadcaster/listener | 项目坐标树 | `view_frames` 无断链 |
| W8 | URDF/Xacro、RViz | 最小 robot description | 底盘/机械臂描述 | RViz 状态与仿真一致 |
| W9 | QoS、Executor、Callback Group | 丢包和阻塞实验 | Topic QoS 审计 | 每个接口有选择依据 |
| W10 | rosbag2、diagnostics | 录制/回放与诊断节点 | 任务诊断信息 | 可复现一次失败 |
| W11 | 测试、CI、工程入口 | gtest/launch test | 统一 build/test | 干净环境一条命令验证 |
| W12 | Capstone、Benchmark | 不再新增练习节点 | 20 episode + 第二任务设计 | 报告、演示、复盘 |

---

## 5. 逐周执行计划

### W1：Node、Topic 与 ROS Graph

目标：不再把 ROS 2 节点理解成“带回调的类”，而是理解进程、节点、图发现与通信关系。

| 日 | 任务 |
|---|---|
| D1 | 阅读 Node 与 ROS graph；运行 `ros2 node list/info`，记录 demo 中所有节点。 |
| D2 | 阅读 Topic；运行 `topic list/info/echo/hz`，观察 `/control_cmd`、`/world_state`。 |
| D3 | 完成或重写 `topic_logger_node`，订阅 `/chassis_state`，禁止复制业务节点。 |
| D4 | 写 `cmd_monitor_node`，订阅 `EmbodiedCommand`，输出关键字段。 |
| D5 | 给日志增加节流；观察 50 Hz Topic 不节流时的影响。 |
| D6 | 审计项目全部 Topic：发布者、订阅者、频率、用途、过期风险。 |
| D7 | 画节点图和数据流图，闭卷口述一次完整控制闭环。 |

交付：`docs/ROS_GRAPH.md` 或个人笔记中的接口表。

验收：

```bash
ros2 node list
ros2 topic info /control_cmd -v
ros2 topic hz /world_state
```

必须回答：为什么 `/control_cmd` 是 Topic？如果两个节点同时发布会发生什么？

### W2：Interface、Package、colcon 与 Launch

目标：理解 `.msg/.srv/.action` 的生成链、包依赖和 workspace overlay。

| 日 | 任务 |
|---|---|
| D8 | 阅读自定义 Interface；逐字段解释 `EmbodiedCommand` 和 `EmbodiedWorldState`。 |
| D9 | 阅读 `embodied_msgs/CMakeLists.txt`、各业务包 `package.xml`。 |
| D10 | 给练习包写最小 launch，同时启动两个监控节点。 |
| D11 | 加 launch argument 和条件启动。 |
| D12 | 练习 `--packages-select`、`--packages-up-to`，记录 build/install/log 的作用。 |
| D13 | 审计 README 的构建和启动命令，实际执行一次。 |
| D14 | 从干净 shell 重新 source、build、launch，整理包依赖图。 |

验收：

```bash
cd ros2_ws
colcon build --symlink-install --packages-up-to chassis_agent_cpp
ros2 launch learning_tools_cpp learning_bringup.launch.py
```

必须回答：为什么消息包要先生成？source 系统 ROS 与 workspace overlay 的顺序为什么重要？

### W3：Parameter、Namespace 与 Remapping

目标：把“能改源码才能改行为”变成“通过参数和启动配置改变行为”。

| 日 | 任务 |
|---|---|
| D15 | 阅读 Parameter，给监控节点增加 `log_every_n` 与 `topic_name`。 |
| D16 | 用 CLI get/set 参数，观察静态读取与动态更新的区别。 |
| D17 | 学 namespace 和 remapping，让同一个监控节点启动两份且不冲突。 |
| D18 | 审计项目中的绝对 Topic 名、硬编码红箱坐标和控制频率。 |
| D19 | 选择一个低风险硬编码项改成参数，并补默认值与范围校验。 |
| D20 | 在 launch 中暴露该参数，不要求用户改 shell 脚本。 |
| D21 | 记录参数表：名称、类型、默认值、合法范围、运行时可否修改。 |

验收：同一个 launch 能选择 `box_red` 或 `box_blue`，非法参数给出明确错误。

### W4：Service 与异步调用

目标：理解短时请求/响应、服务可用性、异步 Future 和超时处理。

| 日 | 任务 |
|---|---|
| D22 | 比较 Topic、Service、Action，结合本项目各举一个例子。 |
| D23 | 用 CLI 检查并调用 `/sim/reset_episode`。 |
| D24 | 在练习包写异步 reset client，使用 `wait_for_service`。 |
| D25 | 增加服务不可用和响应超时处理。 |
| D26 | 阅读 reset 服务端，检查异常时是否返回结构化失败。 |
| D27 | 写自动脚本连续 reset 20 次，并检查 base/box 初始状态。 |
| D28 | 复盘 reset 与正在运行的 Agent 是否存在竞态，形成问题记录。 |

验收：20 次 reset 全部成功；服务未启动时 client 不崩溃、不永久等待。

### W5：ROS 2 Action 基础

目标：理解长任务为什么不能只靠 Topic 或 Service 表达。

先在练习包完成官方 Action 示例，再设计项目接口。建议新增：

```text
# ExecuteTask.action
string task_id
string target_object
---
bool success
string message
float64 elapsed_sec
float64 object_displacement
---
string phase
float64 distance_to_target
float64 elapsed_sec
```

| 日 | 任务 |
|---|---|
| D29 | 阅读 Action 概念，画 Goal/Feedback/Result 时序图。 |
| D30 | 写最小 C++ Action Server。 |
| D31 | 写 Action Client，打印 feedback 和 result。 |
| D32 | 实现 goal reject 与单任务并发策略。 |
| D33 | 实现 cancel。 |
| D34 | 在 `embodied_msgs` 设计 `ExecuteTask.action`，只定义契约，不接业务。 |
| D35 | 用 CLI 发 goal、观察 feedback、执行 cancel，完成接口评审。 |

验收：

```bash
ros2 interface show embodied_msgs/action/ExecuteTask
ros2 action list
ros2 action info /execute_task
```

### W6：将推红箱任务 Action 化

目标：主项目第一次真正完成 ROS 2 任务生命周期。

| 日 | 任务 |
|---|---|
| D36 | 将 Action Server 接入 `chassis_agent_cpp`，接收 `push_red_box`。 |
| D37 | 将 FSM phase、距离和耗时转换为 feedback。 |
| D38 | 将 DONE/FAILED 映射为 Result。 |
| D39 | 增加总超时和各阶段超时。 |
| D40 | 实现 cancel 后零速、松开虚拟抓取并安全结束。 |
| D41 | 处理目标不存在、重复 goal、reset 中 goal 等错误路径。 |
| D42 | 写成功、取消、超时三条 headless 验收记录。 |

完成定义：没有 goal 时 Agent 不应自行开始任务；任务退出后不能继续发布旧控制意图。

### W7：TF2 与坐标系

目标：消除“所有坐标天然在同一平面和同一 frame”的隐式假设。

| 日 | 任务 |
|---|---|
| D43 | 学 TF2 frame、静态/动态变换、时间戳。 |
| D44 | 在练习包写 broadcaster 和 listener。 |
| D45 | 设计 `odom → base_link → arm links → gripper_link`。 |
| D46 | 发布 base 动态 TF。 |
| D47 | 发布机械臂关节相关 TF；明确哪些来自 joint state。 |
| D48 | 将一个距离计算改为显式 frame 语义或写迁移设计。 |
| D49 | 用 `tf2_tools view_frames`、`tf2_echo` 检查断链和时间问题。 |

验收：能解释 `odom`、`base_link` 和物体 frame 的职责，不能只说“它们都是坐标”。

### W8：URDF/Xacro 与 RViz

目标：让机器人结构成为标准描述，而不是只存在于 MuJoCo XML 和代码常量中。

| 日 | 任务 |
|---|---|
| D50 | 学 URDF link/joint，画本项目机器人运动链。 |
| D51 | 写最小底盘 URDF。 |
| D52 | 增加 3DOF 机械臂与夹爪。 |
| D53 | 用 Xacro 参数化尺寸和关节限制。 |
| D54 | 接入 `robot_state_publisher` 和现有 `/arm_state`。 |
| D55 | 在 RViz 检查 TF、RobotModel、Odometry。 |
| D56 | 记录 MuJoCo 模型与 URDF 的重复信息，制定单一来源策略。 |

验收：RViz 中机器人姿态随仿真变化，TF 树与 W7 设计一致。

### W9：QoS、Executor 与 Callback Group

目标：不再机械使用队列深度 10，而是根据数据语义选择通信策略。

| 日 | 任务 |
|---|---|
| D57 | 学 reliability、durability、history、depth 和 deadline。 |
| D58 | 用练习 Topic 对比 reliable 与 best effort。 |
| D59 | 人为阻塞 callback，观察单线程 executor 的影响。 |
| D60 | 学 callback group 与多线程 executor，写最小对比实验。 |
| D61 | 审计 `/control_cmd`、`/world_state`、`/task_plan`、Action feedback。 |
| D62 | 修改一个有充分依据的 QoS 配置，并验证兼容性。 |
| D63 | 输出 `docs/ROS_INTERFACES.md`，记录所有接口语义与 QoS。 |

重点问题：控制命令是否允许堆积？晚加入节点是否应该收到旧任务？状态丢一帧是否比延迟更糟？

### W10：rosbag2、日志与 Diagnostics

目标：从“看终端猜故障”升级为可记录、可查询、可复现。

| 日 | 任务 |
|---|---|
| D64 | 录制 `/world_state`、`/control_cmd`、Action 状态。 |
| D65 | 查看 bag info，并在无 Agent 时回放观测。 |
| D66 | 制造一次超时或接触失败，保存 bag 和日志。 |
| D67 | 学 ROS 日志级别、节流和 logger 配置。 |
| D68 | 学 diagnostics，设计仿真频率、Agent 状态、任务状态诊断项。 |
| D69 | 实现最小诊断发布。 |
| D70 | 仅靠 bag、诊断和日志写出一次故障分析。 |

验收：另一终端或隔天能依照记录复现并解释失败，不依赖记忆。

### W11：测试、CI 与统一入口

目标：让“项目可运行”不再依赖作者电脑上的隐式状态。

| 日 | 任务 |
|---|---|
| D71 | 梳理现有 54 个 C++ 测试和 Python 测试覆盖范围。 |
| D72 | 修复 pytest 默认入口，禁止依赖手工设置隐藏环境变量。 |
| D73 | 给 Action 添加成功、reject、cancel、timeout 测试。 |
| D74 | 学 launch testing，完成一个跨节点 headless 测试。 |
| D75 | 增加统一 `scripts/build.sh` 与 `scripts/test.sh`。 |
| D76 | 增加 CI：build → unit test → lint → headless smoke。 |
| D77 | 从新 shell 或干净容器按 README 验证，修复缺失依赖。 |

统一入口目标：

```bash
./scripts/build.sh
./scripts/test.sh
./scripts/demo.sh --headless
```

### W12：Capstone 与自动 Benchmark

Capstone 不再三选一；核心任务固定为：

> 完成一个可取消、可超时、可诊断、可自动评估的推红箱 ROS 2 Action 系统。

| 日 | 任务 |
|---|---|
| D78 | 冻结功能，列出验收矩阵和已知问题。 |
| D79 | 自动运行 20 个 episode，每次 reset 后发送 Action goal。 |
| D80 | 记录成功率、耗时、碰撞/接触失败和取消行为。 |
| D81 | 修复最高频的一类失败，不新增架构。 |
| D82 | 设计第二任务，例如 `navigate_to_object`，验证 Skill 可复用。 |
| D83 | 更新 README、架构图、接口表和一键演示命令。 |
| D84 | 闭卷演示与复盘：从 Goal 追踪到 Command、WorldState、Result。 |

最终报告至少包含：

| 指标 | 要求 |
|---|---|
| episode 数 | ≥ 20 |
| 成功率 | 如实记录，不为数字修改判据 |
| 平均/P95 耗时 | 必须给出 |
| 失败分类 | 导航、接触、超时、系统错误 |
| cancel | 至少在三个不同 phase 验证 |
| 可复现性 | 给出 commit、配置、随机种子和命令 |

---

## 6. 算法学习支线

算法训练保留，但不再逐日绑定 84 天，避免它反过来控制项目节奏。

| 周 | 主题 | 建议数量 |
|---|---|---:|
| W1 | 数组、哈希、双指针 | 6–8 |
| W2 | 栈、队列、字符串 | 6–8 |
| W3 | 链表、递归 | 5–7 |
| W4 | 二分、排序 | 5–7 |
| W5 | 二叉树基础 | 6–8 |
| W6 | 树、递归状态设计 | 5–7 |
| W7 | 图、BFS、DFS | 6–8 |
| W8 | 回溯 | 5–7 |
| W9 | 动态规划基础 | 5–7 |
| W10 | 贪心、区间 | 5–7 |
| W11 | 综合复习 | 4–6 |
| W12 | 限时复盘 | 3–5 |

算法验收使用“能否闭卷重做”和“能否解释复杂度”，不追求 120 道这种容易诱导刷数量的指标。

---

## 7. 笔记、提交与验收模板

### 7.1 每日笔记

```markdown
# W05D31 — Action Client

## 概念
Action 适合……，因为……

## 今日手写
- 文件：
- 构建命令：
- 运行命令：
- 验收结果：PASS / FAIL

## 与项目联动
- 当前实现：
- 发现的问题：
- 准备修改：

## 故意制造的错误
- 现象：
- 定位命令：
- 根因：

## 尚未解决
- ...
```

### 7.2 每周完成定义

一周只有同时满足以下条件才算完成：

- [ ] 官方概念能闭卷解释；
- [ ] 练习包有独立手写产出；
- [ ] 主项目有真实改进或形成明确审计结论；
- [ ] 至少验证一条失败路径；
- [ ] 验收命令可重复；
- [ ] 相关测试通过；
- [ ] 文档状态与代码一致；
- [ ] 形成一次小而清晰的 Git commit。

### 7.3 提交建议

```bash
git switch -c learning/w05-action
git add ros2_ws/src/learning_tools_cpp docs
git commit -m "learning(w05): add minimal action client and server"
```

进入业务包的改造单独提交，不与练习代码混在一个 commit：

```bash
git commit -m "feat(agent): expose push-box task as ROS action"
```

不要提交 API Key、本地 LLM 配置、训练模型、`build/`、`install/` 或 `log/`。

---

## 8. ROS 2 必会命令

```bash
# 环境与图
echo "$ROS_DISTRO"
ros2 node list
ros2 node info /simulation_node

# Topic
ros2 topic list
ros2 topic info /control_cmd -v
ros2 topic echo /world_state --once
ros2 topic hz /world_state

# Interface / Service / Action
ros2 interface show embodied_msgs/msg/EmbodiedCommand
ros2 service list
ros2 service call /sim/reset_episode embodied_msgs/srv/ResetEpisode \
  "{base_x: 0.0, base_y: 0.0, base_yaw: 0.0}"
ros2 action list
ros2 action info /execute_task

# Parameter / TF
ros2 param list
ros2 param describe /simulation_node max_linear_accel
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_tools view_frames

# Bag
ros2 bag record /world_state /control_cmd
ros2 bag info <bag-directory>
ros2 bag play <bag-directory>

# Build / Test
colcon list
colcon build --symlink-install --packages-up-to chassis_agent_cpp
colcon test --packages-select embodied_core chassis_agent_cpp
colcon test-result --verbose
```

---

## 9. 十二周末自测

1. Topic、Service、Action 各解决什么问题？本项目各有哪些实例？
2. `/control_cmd` 为什么不应积压旧消息？你选择了什么 QoS？
3. Action cancel 到达时，怎样保证机器人安全停止？
4. reset 与 Agent callback 同时发生时，可能有什么竞态？
5. `odom → base_link → gripper_link` 每段变换由谁发布？
6. MuJoCo 模型和 URDF 各自承担什么职责，如何避免长期漂移？
7. 如何录制一次任务失败，并让别人复现？
8. Python 测试为什么曾经无法直接收集？现在怎样由统一入口解决？
9. 从 `ExecuteTask` Goal 到 Result，经过哪些节点、接口和核心类？
10. 如果接入真机，哪些模块保留，哪些模块必须替换？

如果上述问题不能结合代码、命令和运行现象回答，就不算真正掌握。

---

## 10. 后续选修顺序

完成本计划后，再按以下顺序恢复现有高级功能：

1. 第二任务与 Skill 复用；
2. 控制源仲裁和硬件急停接口；
3. ros2_control 与真机驱动适配；
4. RL 导航基线复验与 ONNX 部署；
5. Planner/LLM 仅输出受约束的 Task Goal；
6. 多机器人、生命周期节点或组件化部署。

进入 RL 的前提：reset 稳定、观测契约固定、规则基线可重复、benchmark 自动化。
进入 LLM 的前提：Action 任务接口稳定、输入有 schema 校验、LLM 不直接发布控制命令。

---

## 11. 进度表

| 周 | 主题 | 练习完成 | 项目改造完成 | 失败路径已测 | 周验收通过 | 备注 |
|---|---|---|---|---|---|---|
| W1 | Node / Topic | [ ] | [ ] | [ ] | [ ] | |
| W2 | Interface / Launch | [ ] | [ ] | [ ] | [ ] | |
| W3 | Parameter / Remap | [ ] | [ ] | [ ] | [ ] | |
| W4 | Service | [ ] | [ ] | [ ] | [ ] | |
| W5 | Action 基础 | [ ] | [ ] | [ ] | [ ] | |
| W6 | 推箱 Action | [ ] | [ ] | [ ] | [ ] | |
| W7 | TF2 | [ ] | [ ] | [ ] | [ ] | |
| W8 | URDF / RViz | [ ] | [ ] | [ ] | [ ] | |
| W9 | QoS / Executor | [ ] | [ ] | [ ] | [ ] | |
| W10 | rosbag / Diagnostics | [ ] | [ ] | [ ] | [ ] | |
| W11 | Testing / CI | [ ] | [ ] | [ ] | [ ] | |
| W12 | Capstone | [ ] | [ ] | [ ] | [ ] | |

文档版本：2026-07-15 v3.0。每周复盘时只调整尚未开始的周，不为符合原日历伪造完成状态。
