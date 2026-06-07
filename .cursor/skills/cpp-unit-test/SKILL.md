---
name: cpp-unit-test
description: >-
  Generates and runs gtest unit tests for embodied_core C++ changes: reads git diff,
  updates test/ and CMakeLists.txt, runs scripts/run_embodied_core_tests.sh, prints
  Markdown report. Use when the user mentions 单元测试, UT, gtest, colcon test,
  跑测试, test report, or after changing ros2_ws/src/embodied_core.
---

# embodied_core C++ 单元测试

为 **`embodied_core`**（及后续同风格纯 C++ 库）自动生成 gtest、编译、执行并输出报告。

## 范围

| 包含 | 不包含（转其他方式） |
|------|----------------------|
| `ros2_ws/src/embodied_core/**` | `chassis_simulation`, `chassis_common`（MuJoCo） |
| `test/test_*.cpp`, `CMakeLists.txt` | `chassis_agent_cpp` 节点 spin / 话题 |
| `./scripts/run_embodied_core_tests.sh` | `./scripts/hil_demo.sh` 全链路 HIL |

## 执行流程

### 1. 定位改动

```bash
git diff --name-only HEAD
git diff HEAD -- ros2_ws/src/embodied_core/
```

- 用户指定文件 → 优先用指定范围
- 只处理 `include/embodied_core/*`, `src/*.cpp` 中的 **public** API
- 跳过：空改动、仅注释、仅 `package.xml` 版本号

### 2. 映射测试文件

| 源模块 | 测试文件 |
|--------|----------|
| `world_view.*` | `test/test_world_view.cpp` |
| `navigation.*` | `test/test_navigation.cpp` |
| `navigate_skill.*` | `test/test_navigate_skill.cpp` |
| `manipulate_skill.*` | `test/test_manipulate_skill.cpp` |
| `push_red_box_fsm.*` | `test/test_push_red_box_fsm.cpp` |

模块专用用例见 [reference.md](./reference.md)。

### 3. 生成 / 增量更新测试

每个 public 函数至少：

- 1 正常路径
- 2 边界
- 1 错误/空输入

规范：

- 辅助函数构造 `WorldView`（照抄 `test_world_view.cpp` 的 `make_world_with` / `box()`）
- `ASSERT_*` → 后续依赖；`EXPECT_*` → 普通断言
- 浮点：`EXPECT_DOUBLE_EQ` 或 `EXPECT_NEAR(..., 1e-9)`
- 命名：`TEST(ClassNameTest, scenario_snake_case)`

### 4. 更新 CMakeLists.txt

在 `if(BUILD_TESTING)` 中为新文件添加：

```cmake
ament_add_gtest(test_<模块>
  test/test_<模块>.cpp
)
target_link_libraries(test_<模块> ${PROJECT_NAME})
target_include_directories(test_<模块> PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
```

### 5. 编译 + 执行 + 报告（优先用脚本）

```bash
/home/changwei/changwei/project/scripts/run_embodied_core_tests.sh
```

仅重跑：`--no-build`。纯文本：`--plain`。

脚本失败时读 `ros2_ws/log/latest_test/embodied_core/` 与终端输出，修 **测试或 CMake**，默认 **不改** `src/`。

### 6. 汇报格式

将脚本 Markdown 输出贴给用户，并补充：

- 本次 diff 覆盖的源文件列表
- 新增/修改的用例名
- 失败时：**测试写错** vs **被测代码 bug**（bug 只指出方向，除非用户说「可以改 src」）

## 约束

- **默认只改** `test/`、`CMakeLists.txt`、本 skill 相关脚本
- 测试 **不依赖** ROS runtime、MuJoCo、网络
- 测试 **相互独立**
- 风格与 `test/test_world_view.cpp` 一致
- FSM **不要**一次测 6 态全链；按 [reference.md](./reference.md) 测关键转移

## 集成 / HIL（不生成 gtest）

用户改仿真或要端到端验证时，提示：

```bash
./scripts/hil_demo.sh --agent      # Python 对照
./scripts/hil_demo.sh --agent-cpp  # C++ Agent（M2 后）
```

## 示例触发

- 「我给 navigation 写了 pure_pursuit，帮我 UT」
- 「跑 embodied_core 测试并出报告」
- 「根据 git diff 补单元测试」

## 参考

- [reference.md](./reference.md) — navigation / FSM 用例表
- [examples.md](./examples.md) — 命令与输出样例
