#!/usr/bin/env bash
# P3-M4：HIL 分层推箱 — HybridBrain（RL 导航 + Rule 操作）
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$PROJECT_ROOT/scripts/env.sh"

WS_DIR="$PROJECT_ROOT/ros2_ws"
SIM_NODE="$WS_DIR/install/chassis_simulation/lib/chassis_simulation/simulation_node"
AGENT_NODE="$WS_DIR/install/chassis_agent_cpp/lib/chassis_agent_cpp/agent_node"
MONITOR="$PROJECT_ROOT/scripts/eval_hybrid_hil_monitor.py"

POLICY="${1:-$PROJECT_ROOT/runs/nav_ppo/full/nav_policy.onnx}"
PUSH_MIN_DIST="${PUSH_MIN_DIST:-0.20}"
MAX_STEPS="${MAX_STEPS:-1500}"
TIMEOUT_SEC="${TIMEOUT_SEC:-45}"

resolve_policy_path() {
  local path="$1"
  if [[ "$path" == /* ]]; then
    printf '%s\n' "$path"
    return
  fi
  if [[ -f "$PROJECT_ROOT/$path" ]]; then
    printf '%s\n' "$PROJECT_ROOT/$path"
    return
  fi
  if [[ -f "$path" ]]; then
    printf '%s\n' "$(cd "$(dirname "$path")" && pwd)/$(basename "$path")"
    return
  fi
  printf '%s\n' "$path"
}

POLICY="$(resolve_policy_path "$POLICY")"

if [[ ! -f "$POLICY" ]]; then
  BEST_ZIP="$PROJECT_ROOT/runs/nav_ppo/full/best_model.zip"
  if [[ -f "$BEST_ZIP" ]]; then
    echo "未找到 $POLICY，从 best_model 导出 ONNX..."
    "$PROJECT_ROOT/scripts/export_and_verify_onnx.sh" "$BEST_ZIP"
    POLICY="$(dirname "$BEST_ZIP")/nav_policy.onnx"
  else
    echo "错误: 未找到 ONNX 策略: $POLICY"
    exit 1
  fi
fi

_running_pids() {
  pgrep -f "${SIM_NODE}" 2>/dev/null || true
  pgrep -f "${AGENT_NODE}" 2>/dev/null || true
}

_existing="$(_running_pids | sort -u | tr '\n' ' ')"
if [[ -n "${_existing// }" ]]; then
  echo "错误: 已有 HIL 进程在运行"
  exit 1
fi

echo "==> 编译 HIL 依赖包"
cd "$WS_DIR"
colcon build --packages-select \
  embodied_msgs embodied_core embodied_policy_cpp \
  chassis_common chassis_simulation chassis_agent_cpp \
  --symlink-install
# shellcheck disable=SC1091
source "$WS_DIR/install/setup.bash"

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/eval_hybrid_hil.XXXXXX")"
SIM_LOG="$LOG_DIR/simulation.log"
AGENT_LOG="$LOG_DIR/agent.log"
SIM_PID=""
AGENT_PID=""

cleanup() {
  for pid in "$AGENT_PID" "$SIM_PID"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
  rm -rf "$LOG_DIR"
}
trap cleanup EXIT INT TERM

echo "==> 启动 simulation_node (headless)"
SIMULATION_HEADLESS=1 SIMULATION_LOG_ONLY=1 \
  "$CHASSIS_PYTHON" "$SIM_NODE" </dev/null >>"$SIM_LOG" 2>&1 &
SIM_PID=$!
sleep 2
if ! kill -0 "$SIM_PID" 2>/dev/null; then
  echo "simulation_node 启动失败:"
  tail -n 30 "$SIM_LOG" || true
  exit 1
fi

echo "==> 启动 agent_node (brain=hybrid)"
ros2 run chassis_agent_cpp agent_node --ros-args \
  -p "brain:=hybrid" \
  -p "policy:=$POLICY" \
  -p "task:=push_red_box" \
  -p "standoff:=0.35" \
  -p "arrive_dist:=0.30" \
  >>"$AGENT_LOG" 2>&1 &
AGENT_PID=$!
sleep 2
if ! kill -0 "$AGENT_PID" 2>/dev/null; then
  echo "agent_node 启动失败:"
  tail -n 30 "$AGENT_LOG" || true
  exit 1
fi
if grep -qE 'Load model .* failed|what\(\):|FATAL' "$AGENT_LOG" 2>/dev/null; then
  echo "agent_node 加载失败:"
  tail -n 30 "$AGENT_LOG" || true
  exit 1
fi

echo "==> 监控推箱 (policy=$POLICY push_min_dist=$PUSH_MIN_DIST)"
set +e
"$CHASSIS_PYTHON" "$MONITOR" \
  --push-min-dist "$PUSH_MIN_DIST" \
  --max-steps "$MAX_STEPS" \
  --timeout-sec "$TIMEOUT_SEC"
RC=$?
set -e

if [[ "$RC" -eq 0 ]]; then
  echo "P3-M4 PASS"
else
  echo "P3-M4 FAIL — 最近 agent 日志:"
  tail -n 30 "$AGENT_LOG" || true
fi
exit "$RC"
