#!/usr/bin/env bash
# 编译 embodied_core（含 gtest）、运行 colcon test、输出 Markdown 报告
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROS_SETUP="/opt/ros/lyrical/setup.bash"
WS_DIR="$PROJECT_ROOT/ros2_ws"
PKG="embodied_core"
RESULTS_DIR="$WS_DIR/build/${PKG}/test_results"

usage() {
  cat <<EOF
用法: $(basename "$0") [选项]

  --no-build    跳过 colcon build（已编译且仅重跑测试时）
  --plain       纯文本输出（默认 Markdown 表格）
  -h, --help    帮助

环境: 需已安装 ROS lyrical；无需启动 simulation_node。
EOF
}

DO_BUILD=1
MARKDOWN=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build) DO_BUILD=0; shift ;;
    --plain) MARKDOWN=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知选项: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -f "$ROS_SETUP" ]]; then
  echo "错误: 未找到 $ROS_SETUP"
  exit 1
fi

set +u
# shellcheck disable=SC1090
source "$ROS_SETUP"
set -u

cd "$WS_DIR"

if [[ "$DO_BUILD" -eq 1 ]]; then
  echo "==> colcon build --packages-select ${PKG} (-DBUILD_TESTING=ON)"
  colcon build --packages-select "$PKG" \
    --cmake-args -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo
fi

echo "==> colcon test --packages-select ${PKG}"
set +e
colcon test --packages-select "$PKG" --return-code-on-test-failure
TEST_RC=$?
set -e

echo ""
echo "==> 测试报告"
PARSE_ARGS=("$PROJECT_ROOT/scripts/parse_gtest_xml.py" "$RESULTS_DIR")
if [[ "$MARKDOWN" -eq 1 ]]; then
  PARSE_ARGS+=(--markdown)
fi
python3 "${PARSE_ARGS[@]}"
PARSE_RC=$?

# colcon test 失败或解析到 FAIL 都返回非零
if [[ "$TEST_RC" -ne 0 || "$PARSE_RC" -ne 0 ]]; then
  exit 1
fi
