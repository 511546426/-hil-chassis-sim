#!/usr/bin/env bash
# 双终端 HIL 演示辅助脚本（在第一个终端运行）
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROS_SETUP="/opt/ros/lyrical/setup.bash"
WS_SETUP="$PROJECT_ROOT/ros2_ws/install/setup.bash"
VENV_PYTHON="$PROJECT_ROOT/ros2_sim_venv/bin/python3"

if [[ ! -f "$ROS_SETUP" ]]; then
  echo "错误: 未找到 $ROS_SETUP"
  exit 1
fi
if [[ ! -f "$WS_SETUP" ]]; then
  echo "错误: 请先编译工作区 (colcon build)"
  exit 1
fi
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "错误: 未找到 $VENV_PYTHON，请先创建 ros2_sim_venv"
  exit 1
fi

# shellcheck disable=SC1090
source "$ROS_SETUP"
# shellcheck disable=SC1090
source "$WS_SETUP"

echo "============================================================"
echo "终端 1（当前）: simulation_node"
echo "终端 2（请另开）: 运行以下命令启动 controller_node"
echo ""
echo "  source $ROS_SETUP"
echo "  source $WS_SETUP"
echo "  ros2 run chassis_controller controller_node"
echo ""
echo "在 controller 终端输入 w/s/a/d + 回车，q + 回车退出"
echo "============================================================"
echo ""

exec "$VENV_PYTHON" \
  "$PROJECT_ROOT/ros2_ws/install/chassis_simulation/lib/chassis_simulation/simulation_node"
