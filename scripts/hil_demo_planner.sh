#!/usr/bin/env bash
# 一键启动 HIL：simulation + task_planner + agent(brain=auto)，可交互发任务
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$PROJECT_ROOT/scripts/env.sh"

export CHASSIS_DEMO_ROOT="$PROJECT_ROOT"

ROS_SETUP="/opt/ros/lyrical/setup.bash"
WS_DIR="$PROJECT_ROOT/ros2_ws"
WS_SETUP="$WS_DIR/install/setup.bash"
PYTHON="${CHASSIS_PYTHON:-python}"
SIM_NODE="$WS_DIR/install/chassis_simulation/lib/chassis_simulation/simulation_node"
SEND_TASK="$PROJECT_ROOT/scripts/send_task.py"
TASK_REPL="$PROJECT_ROOT/scripts/task_repl.py"
POLICY="${POLICY:-$PROJECT_ROOT/runs/nav_ppo/full/nav_policy.onnx}"

PLANNER_BACKEND="${PLANNER_BACKEND:-template}"
TASK_TEXT="${TASK_TEXT:-}"
HEADLESS=0
SEND_INITIAL=0
INTERACTIVE=0

BUILD_PACKAGES=(
  embodied_msgs embodied_core embodied_policy_cpp embodied_planner
  chassis_common chassis_simulation chassis_agent_cpp
)

usage() {
  cat <<EOF
用法: $(basename "$0") [选项]

  后台: simulation_node + task_planner_node
  前台: agent_node_cpp (brain=auto，按 /task_plan 自动选 rule/rl)

选项:
  --interactive     前台交互 REPL 发任务（无需另开终端）
  --task TEXT       启动后自动发送一条任务（/task_request）
  --headless        无 MuJoCo 3D 窗口（SIMULATION_HEADLESS=1）
  -h, --help        显示帮助

环境变量:
  PLANNER_BACKEND   template | llm_mock | llm  (默认 template)
  POLICY            nav ONNX 路径 (auto/rl 任务需要)
  TASK_TEXT         同 --task

示例:
  $(basename "$0") --interactive
  $(basename "$0") --task "推红箱"
  PLANNER_BACKEND=llm_mock $(basename "$0") --interactive

交互 REPL 命令: 直接输入任务 | reset | help | quit
另开终端也可: python scripts/send_task.py "去红箱"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task)
      TASK_TEXT="$2"
      SEND_INITIAL=1
      shift 2
      ;;
    --interactive) INTERACTIVE=1; shift ;;
    --headless) HEADLESS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "未知选项: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ -n "$TASK_TEXT" ]]; then
  SEND_INITIAL=1
fi

if [[ ! -f "$ROS_SETUP" ]]; then
  echo "错误: 未找到 $ROS_SETUP"
  exit 1
fi

_running_pids() {
  pgrep -f "${SIM_NODE}" 2>/dev/null || true
  pgrep -f "chassis_agent_cpp/agent_node" 2>/dev/null || true
  pgrep -f "embodied_planner/task_planner_node" 2>/dev/null || true
}

_existing="$(_running_pids | sort -u | tr '\n' ' ')"
if [[ -n "${_existing// }" ]]; then
  echo "错误: 已有 HIL / planner 进程在运行，请先结束旧进程"
  ps -fp ${_existing} 2>/dev/null || true
  exit 1
fi

source_ros() {
  set +u
  # shellcheck disable=SC1090
  source "$ROS_SETUP"
  if [[ -f "$WS_SETUP" ]]; then
    # shellcheck disable=SC1090
    source "$WS_SETUP"
  fi
  set -u
}

needs_build() {
  [[ ! -f "$WS_SETUP" || ! -f "$SIM_NODE" ]] && return 0
  [[ ! -f "$WS_DIR/install/chassis_agent_cpp/lib/chassis_agent_cpp/agent_node" ]] && return 0
  [[ ! -f "$WS_DIR/install/embodied_planner/lib/embodied_planner/task_planner_node" ]] && return 0
  return 1
}

if needs_build; then
  echo "==> 编译依赖包"
  source_ros
  cd "$WS_DIR"
  colcon build --packages-select "${BUILD_PACKAGES[@]}" --symlink-install
fi

source_ros

if [[ ! -f "$POLICY" ]]; then
  echo "警告: POLICY 不存在 ($POLICY)，nav/rl 类任务会失败；推箱(rule) 仍可用"
fi

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hil_demo_planner.XXXXXX")"
SIM_LOG="$LOG_DIR/simulation.log"
PLANNER_LOG="$LOG_DIR/planner.log"
AGENT_LOG="$LOG_DIR/agent.log"
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

SIM_EXPORT=(SIMULATION_LOG_ONLY=1)
if [[ "$HEADLESS" -eq 1 ]]; then
  SIM_EXPORT+=(SIMULATION_HEADLESS=1)
fi

echo "============================================================"
echo "一键启动 Planner HIL (backend=$PLANNER_BACKEND, brain=auto)"
echo "  后台: simulation_node + task_planner_node"
echo "  前台: agent_node_cpp"
echo ""
echo "日志: $LOG_DIR"
echo "  tail -f $AGENT_LOG"
if [[ "$INTERACTIVE" -eq 1 ]]; then
  echo ""
  echo "交互模式: 本终端 REPL 发任务，agent 日志在后台输出"
else
  echo ""
  echo "另开终端发任务:"
  echo "  source scripts/env.sh"
  echo "  python scripts/send_task.py \"推红箱\""
  echo "  或: $(basename "$0") --interactive"
fi
echo "============================================================"
echo ""

env "${SIM_EXPORT[@]}" "$PYTHON" "$SIM_NODE" >>"$SIM_LOG" 2>&1 &
SIM_PID=$!
sleep 2
if ! kill -0 "$SIM_PID" 2>/dev/null; then
  echo "simulation_node 启动失败:"
  tail -20 "$SIM_LOG" || true
  exit 1
fi

ros2 run embodied_planner task_planner_node --ros-args \
  -p "planner_backend:=$PLANNER_BACKEND" \
  >>"$PLANNER_LOG" 2>&1 &
PLANNER_PID=$!
sleep 1.5

AGENT_ARGS=(
  -p brain:=auto
  -p "policy:=$POLICY"
  -p listen_task_plan:=true
)
ros2 run chassis_agent_cpp agent_node --ros-args "${AGENT_ARGS[@]}" \
  >>"$AGENT_LOG" 2>&1 &
AGENT_PID=$!
sleep 2
if ! kill -0 "$AGENT_PID" 2>/dev/null; then
  echo "agent_node 启动失败:"
  tail -20 "$AGENT_LOG" || true
  exit 1
fi

if [[ "$SEND_INITIAL" -eq 1 && -n "$TASK_TEXT" ]]; then
  echo "==> 发送初始任务: $TASK_TEXT"
  "$PYTHON" "$SEND_TASK" "$TASK_TEXT" --wait-sec 1
fi

if [[ "$INTERACTIVE" -eq 1 ]]; then
  echo ""
  tail -f "$AGENT_LOG" &
  TAIL_PID=$!
  cleanup_tail() {
    kill "$TAIL_PID" 2>/dev/null || true
    wait "$TAIL_PID" 2>/dev/null || true
  }
  trap 'cleanup_tail; cleanup' EXIT INT TERM
  "$PYTHON" "$TASK_REPL"
  cleanup_tail
  exit 0
fi

echo "运行中… Ctrl+C 退出"
echo ""

set +e
tail -f "$AGENT_LOG" &
TAIL_PID=$!
wait "$AGENT_PID" 2>/dev/null
kill "$TAIL_PID" 2>/dev/null || true
wait "$TAIL_PID" 2>/dev/null || true
