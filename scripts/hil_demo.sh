#!/usr/bin/env bash
# 一键启动 HIL 演示：simulation_node（后台）+ controller_node 或 agent_node
# 日志写入临时文件，可用 tail -f 分终端查看；退出后自动删除
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROS_SETUP="/opt/ros/lyrical/setup.bash"
WS_DIR="$PROJECT_ROOT/ros2_ws"
WS_SETUP="$WS_DIR/install/setup.bash"
VENV_PYTHON="$PROJECT_ROOT/ros2_sim_venv/bin/python3"
SIM_NODE="$WS_DIR/install/chassis_simulation/lib/chassis_simulation/simulation_node"
CTL_NODE="$WS_DIR/install/chassis_controller/lib/chassis_controller/controller_node"
AGENT_NODE="$WS_DIR/install/chassis_agent/lib/chassis_agent/agent_node"
AGENT_CPP_NODE="$WS_DIR/install/chassis_agent_cpp/lib/chassis_agent_cpp/agent_node"
BUILD_PACKAGES=(embodied_msgs chassis_common chassis_simulation chassis_controller chassis_agent)
BUILD_PACKAGES_CPP=(embodied_msgs embodied_core chassis_common chassis_simulation chassis_agent_cpp)

FORCE_BUILD=0
SKIP_BUILD=0
AGENT_MODE=0
AGENT_CPP_MODE=0

usage() {
  cat <<EOF
用法: $(basename "$0") [选项]

  --agent      启动 Python agent_node（自主导航到红箱 + ARM_REACH）
  --agent-cpp  启动 C++ agent_node（M3 推红箱 FSM：导航→伸臂→夹爪→倒车）
  --build      强制重新编译后再启动
  --no-build   跳过编译检查（install 不存在时直接报错）
  -h, --help   显示此帮助

默认：若尚未编译，或源码比 install 更新，则自动增量编译相关包。
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT_MODE=1; shift ;;
    --agent-cpp) AGENT_CPP_MODE=1; shift ;;
    --build) FORCE_BUILD=1; shift ;;
    --no-build) SKIP_BUILD=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知选项: $1"; usage; exit 1 ;;
  esac
done

if [[ "$AGENT_MODE" -eq 1 && "$AGENT_CPP_MODE" -eq 1 ]]; then
  echo "错误: --agent 与 --agent-cpp 不能同时使用"
  exit 1
fi

if [[ ! -f "$ROS_SETUP" ]]; then
  echo "错误: 未找到 $ROS_SETUP"
  exit 1
fi
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "错误: 未找到 $VENV_PYTHON，请先创建 ros2_sim_venv"
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
  export PATH="$PROJECT_ROOT/ros2_sim_venv/bin:$PATH"
}

needs_build() {
  if [[ ! -f "$WS_SETUP" || ! -f "$SIM_NODE" ]]; then
    return 0
  fi
  if [[ "$AGENT_CPP_MODE" -eq 1 ]]; then
    [[ ! -f "$AGENT_CPP_NODE" ]]
  elif [[ "$AGENT_MODE" -eq 1 ]]; then
    [[ ! -f "$AGENT_NODE" ]]
  else
    [[ ! -f "$CTL_NODE" ]]
  fi
}

sources_changed() {
  local marker
  if [[ "$AGENT_CPP_MODE" -eq 1 ]]; then
    marker="$AGENT_CPP_NODE"
    [[ -f "$marker" ]] || marker="$SIM_NODE"
  elif [[ "$AGENT_MODE" -eq 1 ]]; then
    marker="$AGENT_NODE"
    [[ -f "$marker" ]] || marker="$SIM_NODE"
  else
    marker="$CTL_NODE"
  fi
  [[ -f "$marker" ]] || return 0
  local src_root="$WS_DIR/src"
  local -a watch_dirs=(
    "$src_root/chassis_common"
    "$src_root/chassis_simulation"
    "$src_root/embodied_msgs"
  )
  if [[ "$AGENT_CPP_MODE" -eq 1 ]]; then
    watch_dirs+=("$src_root/embodied_core" "$src_root/chassis_agent_cpp")
  elif [[ "$AGENT_MODE" -eq 1 ]]; then
    watch_dirs+=("$src_root/chassis_agent")
  else
    watch_dirs+=("$src_root/chassis_controller")
  fi
  find "${watch_dirs[@]}" \
    -type f \( -name '*.py' -o -name '*.cpp' -o -name '*.hpp' -o -name '*.msg' \
      -o -name '*.xml' -o -name 'CMakeLists.txt' -o -name 'package.xml' \) \
    -newer "$marker" 2>/dev/null | grep -q .
}

build_workspace() {
  local -a packages
  if [[ "$AGENT_CPP_MODE" -eq 1 ]]; then
    packages=("${BUILD_PACKAGES_CPP[@]}")
  else
    packages=("${BUILD_PACKAGES[@]}")
  fi
  echo "============================================================"
  echo "编译 ROS 2 工作区（${packages[*]}）..."
  echo "============================================================"
  source_ros
  cd "$WS_DIR"
  colcon build --symlink-install \
    --packages-select "${packages[@]}" \
    --allow-overriding chassis_common
  source_ros
  echo ""
}

if [[ "$FORCE_BUILD" -eq 1 ]]; then
  build_workspace
elif [[ "$SKIP_BUILD" -eq 0 ]]; then
  if needs_build; then
    echo "未找到 install 产物，自动编译..."
    build_workspace
  elif sources_changed; then
    echo "检测到源码更新，自动增量编译..."
    build_workspace
  fi
fi

if [[ ! -f "$WS_SETUP" || ! -f "$SIM_NODE" ]]; then
  echo "错误: 缺少编译产物，请运行:"
  echo "  $0 --build"
  exit 1
fi
if [[ "$AGENT_CPP_MODE" -eq 1 && ! -f "$AGENT_CPP_NODE" ]]; then
  echo "错误: 缺少 C++ agent_node，请运行:"
  echo "  $0 --agent-cpp --build"
  exit 1
elif [[ "$AGENT_MODE" -eq 1 && ! -f "$AGENT_NODE" ]]; then
  echo "错误: 缺少 agent_node，请运行:"
  echo "  $0 --build"
  exit 1
elif [[ "$AGENT_MODE" -eq 0 && "$AGENT_CPP_MODE" -eq 0 && ! -f "$CTL_NODE" ]]; then
  echo "错误: 缺少 controller_node，请运行:"
  echo "  $0 --build"
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
if [[ "$AGENT_CPP_MODE" -eq 1 ]]; then
  echo "一键启动 HIL 演示（C++ Agent 模式 / M3 FSM）"
  echo "  本终端: chassis_agent_cpp/agent_node"
  echo "  后台:   simulation_node（MuJoCo 3D 窗口）"
  echo ""
  echo "  任务: NAV → REACH → 夹爪 → 倒车（M5 后箱子会随动）"
  echo "  按 Ctrl+C 退出"
elif [[ "$AGENT_MODE" -eq 1 ]]; then
  echo "一键启动 HIL 演示（Python Agent 模式）"
  echo "  本终端: agent_node 自主导航"
  echo "  后台:   simulation_node（MuJoCo 3D 窗口）"
  echo ""
  echo "  目标: 导航到红箱 (2.5, 0)，到位后切换 ARM_REACH"
  echo "  按 Ctrl+C 退出"
else
  echo "一键启动 HIL 演示"
  echo "  本终端: controller_node 键盘遥控"
  echo "  后台:   simulation_node（MuJoCo 3D 窗口）"
  echo ""
  echo "  底盘: w/s 前进后退  a/d 转向  c 回正  空格 停  b 急停"
  echo "  机械臂: i/k 肩升降  j/l 肘左右  u/o 腕俯仰  g 夹爪  q 退出"
fi
echo "------------------------------------------------------------"
echo "日志目录（退出后自动删除）:"
echo "  ${SIM_LOG}"
if [[ "$AGENT_MODE" -eq 1 || "$AGENT_CPP_MODE" -eq 1 ]]; then
  echo "  ${AGENT_LOG}"
else
  echo "  ${CTL_LOG}"
fi
echo ""
echo "另开终端查看日志，例如:"
echo "  tail -f ${SIM_LOG}"
if [[ "$AGENT_MODE" -eq 1 || "$AGENT_CPP_MODE" -eq 1 ]]; then
  echo "  tail -f ${AGENT_LOG}"
else
  echo "  tail -f ${CTL_LOG}"
fi
echo "============================================================"
echo ""

SIMULATION_LOG_ONLY=1 "$VENV_PYTHON" "$SIM_NODE" </dev/null >>"${SIM_LOG}" 2>&1 &
SIM_PID=$!

sleep 2
if ! kill -0 "${SIM_PID}" 2>/dev/null; then
  echo "错误: simulation_node 启动失败，最近日志:"
  tail -n 20 "${SIM_LOG}" 2>/dev/null || true
  exit 1
fi

echo "simulation_node 已启动 (pid ${SIM_PID})"
if [[ "$AGENT_CPP_MODE" -eq 1 ]]; then
  echo "C++ agent_node 运行中...（输出写入 ${AGENT_LOG}）"
  echo ""
  ros2 run chassis_agent_cpp agent_node >>"${AGENT_LOG}" 2>&1
elif [[ "$AGENT_MODE" -eq 1 ]]; then
  echo "agent_node 运行中...（输出写入 ${AGENT_LOG}）"
  echo ""
  ros2 run chassis_agent agent_node >>"${AGENT_LOG}" 2>&1
else
  echo "controller_node 遥控中...（输出写入 ${CTL_LOG}）"
  echo ""
  ros2 run chassis_controller controller_node >>"${CTL_LOG}" 2>&1
fi
