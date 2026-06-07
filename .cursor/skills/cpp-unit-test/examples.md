# 命令与输出样例

## 一键跑测试 + 报告

```bash
/home/changwei/changwei/project/scripts/run_embodied_core_tests.sh
```

## 仅重跑（已编译）

```bash
/home/changwei/changwei/project/scripts/run_embodied_core_tests.sh --no-build
```

## 手动等价命令

```bash
cd /home/changwei/changwei/project/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --packages-select embodied_core --cmake-args -DBUILD_TESTING=ON
colcon test --packages-select embodied_core --return-code-on-test-failure
python3 ../scripts/parse_gtest_xml.py build/embodied_core/test_results --markdown
```

## 报告样例（Markdown）

```markdown
## embodied_core 单元测试报告

**合计**: 10/10 通过

| 套件 | 用例 | 结果 | 耗时(s) |
|------|------|------|---------|
| WorldViewTest | find_object_empty | ✅ PASS | 0. |
| WorldViewTest | distance_pythagorean | ✅ PASS | 0. |
```

## Agent 工作流样例

用户：「我改了 navigation.cpp，补 UT 并跑报告」

1. `git diff -- ros2_ws/src/embodied_core/src/navigation.cpp`
2. 新建或更新 `test/test_navigation.cpp`
3. 更新 `CMakeLists.txt` 注册 `test_navigation`
4. `./scripts/run_embodied_core_tests.sh`
5. 粘贴 Markdown 报告 + 说明新增用例
