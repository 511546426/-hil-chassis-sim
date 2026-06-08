#!/usr/bin/env bash
# 统一开发环境：conda embodied + ROS lyrical + 工作空间
# 用法: source scripts/env.sh  （不要用 bash scripts/env.sh）
# 注意: 被 source 时不要 set -e，否则失败会直接关掉当前终端

_ENV_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
export CHASSIS_DEMO_ROOT="$(cd "$_ENV_SH_DIR/.." && pwd)"

_resolve_conda() {
  if [[ -n "${CONDA_EXE:-}" ]]; then
    echo "$(dirname "$(dirname "$CONDA_EXE")")/etc/profile.d/conda.sh"
    return
  fi
  for candidate in \
    "$HOME/miniconda3/etc/profile.d/conda.sh" \
    "$HOME/anaconda3/etc/profile.d/conda.sh"; do
    if [[ -f "$candidate" ]]; then
      echo "$candidate"
      return
    fi
  done
  echo ""
}

_CONDA_SH="$(_resolve_conda)"
if [[ -z "$_CONDA_SH" ]]; then
  echo "错误: 未找到 conda，请先安装 miniconda/anaconda" >&2
  return 1 2>/dev/null || exit 1
fi
# shellcheck disable=SC1090
source "$_CONDA_SH"
set +u
if ! conda activate embodied; then
  echo "错误: conda activate embodied 失败，请先运行: conda env create -f environment.yml" >&2
  return 1 2>/dev/null || exit 1
fi

if [[ ! -f /opt/ros/lyrical/setup.bash ]]; then
  echo "错误: 未找到 /opt/ros/lyrical/setup.bash" >&2
  return 1 2>/dev/null || exit 1
fi
# shellcheck disable=SC1091
source /opt/ros/lyrical/setup.bash
if [[ -f "$CHASSIS_DEMO_ROOT/ros2_ws/install/setup.bash" ]]; then
  # shellcheck disable=SC1091
  source "$CHASSIS_DEMO_ROOT/ros2_ws/install/setup.bash"
fi

if [[ -z "${CONDA_PREFIX:-}" || ! -x "$CONDA_PREFIX/bin/python" ]]; then
  echo "错误: embodied 环境未正确激活" >&2
  return 1 2>/dev/null || exit 1
fi

export CHASSIS_PYTHON="$CONDA_PREFIX/bin/python"
export PATH="$CONDA_PREFIX/bin:$PATH"
echo "环境就绪: embodied + ROS lyrical ($(basename "$CHASSIS_PYTHON"))"
