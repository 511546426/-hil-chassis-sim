#!/usr/bin/env bash
# P3-C3-3：HIL 批量评估入口
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$PROJECT_ROOT/scripts/env.sh"

export CHASSIS_DEMO_ROOT="$PROJECT_ROOT"

WS_DIR="$PROJECT_ROOT/ros2_ws"
SUITE="${SUITE:-quick}"
EPISODES="${EPISODES:-0}"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --suite)
      SUITE="$2"
      shift 2
      ;;
    --episodes)
      EPISODES="$2"
      shift 2
      ;;
    --list-suites)
      EXTRA_ARGS+=(--list-suites)
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

echo "==> 编译 HIL 依赖"
cd "$WS_DIR"
colcon build --packages-select \
  embodied_msgs embodied_core embodied_policy_cpp embodied_planner \
  chassis_common chassis_simulation chassis_agent_cpp \
  --symlink-install
# shellcheck disable=SC1091
source "$WS_DIR/install/setup.bash"

CMD=(
  "$CHASSIS_PYTHON" "$PROJECT_ROOT/scripts/hil_benchmark.py"
  --suite "$SUITE"
)
if [[ "$EPISODES" -gt 0 ]]; then
  CMD+=(--episodes "$EPISODES")
fi
CMD+=("${EXTRA_ARGS[@]}")

echo "==> 运行 benchmark suite=$SUITE"
"${CMD[@]}"
