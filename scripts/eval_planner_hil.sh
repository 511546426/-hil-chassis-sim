#!/usr/bin/env bash
# P3-C2：Planner + agent 冒烟 — send_task 推红箱
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$PROJECT_ROOT/scripts/env.sh"

WS_DIR="$PROJECT_ROOT/ros2_ws"
SIM_NODE="$WS_DIR/install/chassis_simulation/lib/chassis_simulation/simulation_node"
MONITOR="$PROJECT_ROOT/scripts/eval_hybrid_hil_monitor.py"
SEND_TASK="$PROJECT_ROOT/scripts/send_task.py"

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/eval_planner_hil.XXXXXX")"
SIM_PID=""
PLANNER_PID=""
AGENT_PID=""

cleanup() {
  for pid in "$AGENT_PID" "$PLANNER_PID" "$SIM_PID"; do
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
  rm -rf "$LOG_DIR"
}
trap cleanup EXIT INT TERM

echo "==> 编译 C2 依赖"
cd "$WS_DIR"
colcon build --packages-select \
  embodied_msgs embodied_core embodied_policy_cpp embodied_planner \
  chassis_common chassis_simulation chassis_agent_cpp \
  --symlink-install
# shellcheck disable=SC1091
source "$WS_DIR/install/setup.bash"

echo "==> 启动 simulation_node"
SIMULATION_HEADLESS=1 SIMULATION_LOG_ONLY=1 \
  "$CHASSIS_PYTHON" "$SIM_NODE" >"$LOG_DIR/sim.log" 2>&1 &
SIM_PID=$!
sleep 2

PLANNER_BACKEND="${PLANNER_BACKEND:-template}"
TASK_TEXT="${TASK_TEXT:-推红箱}"

echo "==> 启动 task_planner_node (backend=$PLANNER_BACKEND)"
ros2 run embodied_planner task_planner_node --ros-args \
  -p "planner_backend:=$PLANNER_BACKEND" \
  >"$LOG_DIR/planner.log" 2>&1 &
PLANNER_PID=$!
sleep 1

echo "==> 启动 agent_node (brain=rule)"
ros2 run chassis_agent_cpp agent_node --ros-args -p brain:=rule \
  >"$LOG_DIR/agent.log" 2>&1 &
AGENT_PID=$!
sleep 2

echo "==> 发送任务: $TASK_TEXT"
"$CHASSIS_PYTHON" "$SEND_TASK" "$TASK_TEXT" --wait-sec 1

echo "==> 监控推箱"
set +e
"$CHASSIS_PYTHON" "$MONITOR" --push-min-dist 0.20 --max-steps 1500 --timeout-sec 45
RC=$?
set -e

if [[ "$RC" -eq 0 ]]; then
  echo "P3-C2 PASS"
else
  echo "P3-C2 FAIL"
  tail -20 "$LOG_DIR/agent.log" || true
fi
exit "$RC"
