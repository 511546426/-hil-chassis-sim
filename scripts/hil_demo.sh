#!/usr/bin/env bash
# 一键启动 HIL：simulation_node（后台）+ C++ Agent 推红箱（默认）或键盘遥控（--teleop）
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROS_SETUP="/opt/ros/lyrical/setup.bash"
WS_DIR="$PROJECT_ROOT/ros2_ws"
WS_SETUP="$WS_DIR/install/setup.bash"
EMBODIED_PYTHON_DEFAULT="${HOME}/miniconda3/envs/embodied/bin/python"
PYTHON="${CHASSIS_PYTHON:-$EMBODIED_PYTHON_DEFAULT}"
SIM_NODE="$WS_DIR/install/chassis_simulation/lib/chassis_simulation/simulation_node"
CTL_NODE="$WS_DIR/install/chassis_controller/lib/chassis_controller/controller_node"
AGENT_CPP_NODE="$WS_DIR/install/chassis_agent_cpp/lib/chassis_agent_cpp/agent_node"
BUILD_PACKAGES_AGENT=(embodied_msgs embodied_core chassis_common chassis_simulation chassis_agent_cpp)
BUILD_PACKAGES_TELEOP=(embodied_msgs chassis_common chassis_simulation chassis_controller)

TELEOP_MODE=0

usage() {
  cat <<EOF
用法: $(basename "$0") [选项]

  （无参）     C++ Agent 自动推红箱（导航→伸臂→夹爪→倒车≥0.2m）
  --teleop     键盘遥控 controller_node
  -h, --help   显示此帮助

示例:
  $(basename "$0")
  $(basename "$0") --teleop

首次运行或源码更新后会自动增量编译。强制全量编译:
  source scripts/env.sh && cd ros2_ws && colcon build --symlink-install
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --teleop) TELEOP_MODE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知选项: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -f "$ROS_SETUP" ]]; then
  echo "错误: 未找到 $ROS_SETUP"
  exit 1
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "错误: 未找到 $PYTHON"
  echo "请先创建统一环境: conda env create -f environment.yml"
  echo "或: source scripts/env.sh"
  exit 1
fi

_running_hil_pids() {
  pgrep -f "${PYTHON} ${SIM_NODE}" 2>/dev/null || true
  pgrep -f "${AGENT_CPP_NODE}" 2>/dev/null || true
  pgrep -f "${CTL_NODE}" 2>/dev/null || true
}

_existing_hil="$(_running_hil_pids | sort -u | tr '\n' ' ')"
if [[ -n "${_existing_hil// }" ]]; then
  echo "错误: 已有 HIL 进程在运行（simulation_node 或 agent/controller）"
  echo "请先结束旧进程，例如:"
  echo "  pkill -9 -f '${WS_DIR}/install/chassis_simulation/lib/chassis_simulation/simulation_node'"
  echo "  pkill -9 -f '${WS_DIR}/install/chassis_agent_cpp/lib/chassis_agent_cpp/agent_node'"
  ps -fp ${_existing_hil} 2>/dev/null || true
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
  export PATH="$(dirname "$PYTHON"):$PATH"
  export CHASSIS_PYTHON="$PYTHON"
}

needs_build() {
  if [[ ! -f "$WS_SETUP" || ! -f "$SIM_NODE" ]]; then
    return 0
  fi
  if [[ "$TELEOP_MODE" -eq 1 ]]; then
    [[ ! -f "$CTL_NODE" ]]
  else
    [[ ! -f "$AGENT_CPP_NODE" ]]
  fi
}

sources_changed() {
  local marker
  if [[ "$TELEOP_MODE" -eq 1 ]]; then
    marker="$CTL_NODE"
  else
    marker="$AGENT_CPP_NODE"
  fi
  [[ -f "$marker" ]] || marker="$SIM_NODE"
  [[ -f "$marker" ]] || return 0

  local src_root="$WS_DIR/src"
  local -a watch_dirs=(
    "$src_root/chassis_common"
    "$src_root/chassis_simulation"
    "$src_root/embodied_msgs"
  )
  if [[ "$TELEOP_MODE" -eq 1 ]]; then
    watch_dirs+=("$src_root/chassis_controller")
  else
    watch_dirs+=("$src_root/embodied_core" "$src_root/chassis_agent_cpp")
  fi
  find "${watch_dirs[@]}" \
    -type f \( -name '*.py' -o -name '*.cpp' -o -name '*.hpp' -o -name '*.msg' \
      -o -name '*.srv' -o -name '*.xml' -o -name 'CMakeLists.txt' -o -name 'package.xml' \) \
    -newer "$marker" 2>/dev/null | grep -q .
}

build_workspace() {
  local -a packages
  if [[ "$TELEOP_MODE" -eq 1 ]]; then
    packages=("${BUILD_PACKAGES_TELEOP[@]}")
  else
    packages=("${BUILD_PACKAGES_AGENT[@]}")
  fi
  echo "============================================================"
  echo "编译 ROS 2 工作区（${packages[*]}）..."
  echo "============================================================"
  source_ros
  cd "$WS_DIR"
  colcon build --symlink-install \
    --packages-select "${packages[@]}"
  source_ros
  echo ""
}

if needs_build; then
  echo "未找到 install 产物，自动编译..."
  build_workspace
elif sources_changed; then
  echo "检测到源码更新，自动增量编译..."
  build_workspace
fi

if [[ ! -f "$WS_SETUP" || ! -f "$SIM_NODE" ]]; then
  echo "错误: 缺少编译产物，请先编译:"
  echo "  source scripts/env.sh && cd ros2_ws && colcon build --symlink-install"
  exit 1
fi
if [[ "$TELEOP_MODE" -eq 1 && ! -f "$CTL_NODE" ]]; then
  echo "错误: 缺少 controller_node，请先编译 chassis_controller"
  exit 1
elif [[ "$TELEOP_MODE" -eq 0 && ! -f "$AGENT_CPP_NODE" ]]; then
  echo "错误: 缺少 C++ agent_node，请先编译 chassis_agent_cpp"
  exit 1
fi

source_ros

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hil_demo.XXXXXX")"
SIM_LOG="$LOG_DIR/simulation.log"
CTL_LOG="$LOG_DIR/controller.log"
AGENT_LOG="$LOG_DIR/agent.log"
SIM_PID=""

cleanup() {
  if [[ -n "${SIM_PID}" ]] && kill -0 "${SIM_PID}" 2>/dev/null; then
    echo ""
    echo "正在停止 simulation_node (pid ${SIM_PID})..."
    kill "${SIM_PID}" 2>/dev/null || true
    wait "${SIM_PID}" 2>/dev/null || true
  fi
  if [[ -d "${LOG_DIR}" ]]; then
    rm -rf "${LOG_DIR}"
  fi
}
trap cleanup EXIT INT TERM

echo "============================================================"
if [[ "$TELEOP_MODE" -eq 1 ]]; then
  echo "一键启动 HIL 演示（键盘遥控）"
  echo "  本终端: controller_node"
  echo "  后台:   simulation_node（MuJoCo 3D 窗口）"
  echo ""
  echo "  底盘: w/s 前进后退  a/d 转向  c 回正  空格 停  b 急停"
  echo "  机械臂: i/k 肩升降  j/l 肘左右  u/o 腕俯仰  g 夹爪  q 退出"
else
  echo "一键启动 HIL 演示（推红箱 / C++ Agent）"
  echo "  本终端: chassis_agent_cpp/agent_node"
  echo "  后台:   simulation_node（MuJoCo 3D 窗口）"
  echo ""
  echo "  流程: 导航 → 伸臂 → 夹爪 → 倒车推箱（≥ 0.2 m）"
  echo "  按 Ctrl+C 退出"
fi
echo "------------------------------------------------------------"
echo "日志目录（退出后自动删除）:"
echo "  ${SIM_LOG}"
if [[ "$TELEOP_MODE" -eq 1 ]]; then
  echo "  ${CTL_LOG}"
else
  echo "  ${AGENT_LOG}"
fi
echo ""
echo "另开终端查看日志，例如:"
echo "  tail -f ${SIM_LOG}"
if [[ "$TELEOP_MODE" -eq 1 ]]; then
  echo "  tail -f ${CTL_LOG}"
else
  echo "  tail -f ${AGENT_LOG}"
fi
echo "============================================================"
echo ""

SIMULATION_LOG_ONLY=1 "$PYTHON" "$SIM_NODE" </dev/null >>"${SIM_LOG}" 2>&1 &
SIM_PID=$!

sleep 2
if ! kill -0 "${SIM_PID}" 2>/dev/null; then
  echo "错误: simulation_node 启动失败，最近日志:"
  tail -n 20 "${SIM_LOG}" 2>/dev/null || true
  exit 1
fi

echo "simulation_node 已启动 (pid ${SIM_PID})"
if [[ "$TELEOP_MODE" -eq 1 ]]; then
  echo "controller_node 遥控中...（输出写入 ${CTL_LOG}）"
  echo ""
  ros2 run chassis_controller controller_node >>"${CTL_LOG}" 2>&1
else
  echo "C++ agent_node 运行中...（输出写入 ${AGENT_LOG}）"
  echo ""
  ros2 run chassis_agent_cpp agent_node >>"${AGENT_LOG}" 2>&1
fi
