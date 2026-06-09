#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$PROJECT_ROOT/scripts/env.sh"

PY="${CHASSIS_PYTHON:-$CONDA_PREFIX/bin/python}"
SIM_NODE="$PROJECT_ROOT/ros2_ws/install/chassis_simulation/lib/chassis_simulation/simulation_node"
LOG_DIR="$(mktemp -d /tmp/m5_hil.XXXXXX)"
SIM_LOG="$LOG_DIR/sim.log"
AGENT_LOG="$LOG_DIR/agent.log"

cleanup() {
  if [[ -n "${SIM_PID:-}" ]] && kill -0 "${SIM_PID}" 2>/dev/null; then
    kill "${SIM_PID}" 2>/dev/null || true
    wait "${SIM_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "M5 smoke test logs: $LOG_DIR"
SIMULATION_LOG_ONLY=1 "$PY" "$SIM_NODE" >"$SIM_LOG" 2>&1 &
SIM_PID=$!
sleep 5

if ! kill -0 "${SIM_PID}" 2>/dev/null; then
  echo "simulation_node failed to start:"
  tail -40 "$SIM_LOG"
  exit 1
fi

timeout 90 ros2 run chassis_agent_cpp agent_node >"$AGENT_LOG" 2>&1 || true

echo "=== SIM virtual grasp ==="
grep -E 'virtual grasp' "$SIM_LOG" || echo "(none)"
echo "=== AGENT virtual grasp / FSM ==="
grep -E 'virtual grasp|FSM ' "$AGENT_LOG" || echo "(none)"

python3 - "$SIM_LOG" "$AGENT_LOG" <<'PY'
import sys
from pathlib import Path

sim = Path(sys.argv[1]).read_text(errors='replace')
agent = Path(sys.argv[2]).read_text(errors='replace')
checks = [
    ('sim grasp ON', 'virtual grasp ON' in sim or 'attached box_red' in sim),
    ('agent grasp ON', 'virtual grasp ON' in agent),
    ('BackUp transition', 'CloseGripper -> BackUp' in agent),
    ('Done transition', 'BackUp -> Done' in agent),
    ('sim grasp OFF', 'virtual grasp OFF' in sim or 'released box_red' in sim),
]
failed = 0
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
    if not ok:
        failed += 1
sys.exit(1 if failed else 0)
PY
