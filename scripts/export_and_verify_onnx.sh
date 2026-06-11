#!/usr/bin/env bash
# P3-M2：导出 SB3 → ONNX，Python 对齐验证，C++ gtest 数值对齐
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$PROJECT_ROOT/scripts/env.sh"

MODEL="${1:-$PROJECT_ROOT/runs/nav_ppo/full/best_model.zip}"
if [[ ! -f "$MODEL" && -f "${MODEL}.zip" ]]; then
  MODEL="${MODEL}.zip"
fi
if [[ ! -f "$MODEL" ]]; then
  echo "错误: 未找到模型 $MODEL"
  echo "用法: $(basename "$0") [path/to/best_model.zip]"
  exit 1
fi

MODEL_DIR="$(cd "$(dirname "$MODEL")" && pwd)"
ONNX_OUT="$MODEL_DIR/nav_policy.onnx"
VECTORS_HPP="$PROJECT_ROOT/ros2_ws/src/embodied_policy_cpp/test/onnx_test_vectors.hpp"
FIXTURE_ONNX="$PROJECT_ROOT/ros2_ws/src/embodied_policy_cpp/test/fixtures/nav_policy.onnx"

echo "==> 导出 ONNX"
python3 "$PROJECT_ROOT/ros2_ws/src/embodied_gym/embodied_gym/export_onnx.py" \
  "$MODEL" \
  --output "$ONNX_OUT" \
  --test-vectors-hpp "$VECTORS_HPP" \
  --verify

mkdir -p "$(dirname "$FIXTURE_ONNX")"
cp -f "$ONNX_OUT" "$FIXTURE_ONNX"
if [[ -f "${ONNX_OUT}.data" ]]; then
  cp -f "${ONNX_OUT}.data" "${FIXTURE_ONNX}.data"
fi
echo "Fixture: $FIXTURE_ONNX"

echo "==> 编译 embodied_policy_cpp（含 gtest）"
cd "$PROJECT_ROOT/ros2_ws"
export NAV_POLICY_ONNX="$FIXTURE_ONNX"
colcon build --packages-select embodied_core embodied_policy_cpp \
  --cmake-args -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo

echo "==> C++ gtest"
colcon test --packages-select embodied_policy_cpp --return-code-on-test-failure
colcon test-result --verbose

echo ""
echo "PASS: P3-M2 ONNX export + C++ alignment"
