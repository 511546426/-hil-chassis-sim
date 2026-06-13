#!/usr/bin/env bash
# P3-C2：Planner + agent(brain=auto) — 导航任务自动选 rl brain
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$PROJECT_ROOT/scripts/env.sh"

export CHASSIS_DEMO_ROOT="$PROJECT_ROOT"
PLANNER_BACKEND="${PLANNER_BACKEND:-llm_mock}"
TASK_TEXT="${TASK_TEXT:-please go to the red box}"
POLICY="${POLICY:-$PROJECT_ROOT/runs/nav_ppo/full/nav_policy.onnx}"
STANDOFF="${STANDOFF:-0.35}"
ARRIVE_DIST="${ARRIVE_DIST:-0.30}"

WS_DIR="$PROJECT_ROOT/ros2_ws"
SIM_NODE="$WS_DIR/install/chassis_simulation/lib/chassis_simulation/simulation_node"
MONITOR="$PROJECT_ROOT/scripts/eval_rl_hil_monitor.py"
SEND_TASK="$PROJECT_ROOT/scripts/send_task.py"

if [[ ! -f "$POLICY" ]]; then
  echo "错误: 未找到 ONNX 策略: $POLICY"
  exit 1
fi

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/eval_planner_auto_nav.XXXXXX")"
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

echo "==> 编译"
cd "$WS_DIR"
colcon build --packages-select embodied_msgs embodied_planner chassis_agent_cpp chassis_simulation \
  --symlink-install
# shellcheck disable=SC1091
source "$WS_DIR/install/setup.bash"

echo "==> 启动 simulation_node"
SIMULATION_HEADLESS=1 SIMULATION_LOG_ONLY=1 \
  "$CHASSIS_PYTHON" "$SIM_NODE" >"$LOG_DIR/sim.log" 2>&1 &
SIM_PID=$!
sleep 2

echo "==> 启动 task_planner_node (backend=$PLANNER_BACKEND)"
ros2 run embodied_planner task_planner_node --ros-args \
  -p "planner_backend:=$PLANNER_BACKEND" \
  >"$LOG_DIR/planner.log" 2>&1 &
PLANNER_PID=$!
sleep 1

echo "==> 启动 agent_node (brain=auto policy=$POLICY)"
ros2 run chassis_agent_cpp agent_node --ros-args \
  -p brain:=auto \
  -p "policy:=$POLICY" \
  -p "standoff:=$STANDOFF" \
  -p "arrive_dist:=$ARRIVE_DIST" \
  >"$LOG_DIR/agent.log" 2>&1 &
AGENT_PID=$!
sleep 2

echo "==> 发送任务: $TASK_TEXT"
"$CHASSIS_PYTHON" "$SEND_TASK" "$TASK_TEXT" --wait-sec 2

echo "==> 监控导航"
set +e
"$CHASSIS_PYTHON" "$MONITOR" \
  --standoff "$STANDOFF" \
  --arrive-dist "$ARRIVE_DIST" \
  --max-steps 500 \
  --timeout-sec 20
RC=$?
set -e

if [[ "$RC" -eq 0 ]]; then
  echo "P3-C2 auto-nav PASS"
else
  echo "P3-C2 auto-nav FAIL"
  tail -20 "$LOG_DIR/agent.log" || true
fi
exit "$RC"
