#!/usr/bin/env bash
# 加载 LLM API Key（DeepSeek 等）到环境变量
# 用法: source scripts/load_llm_key.sh
# 优先级:
#   1) 已设置的 DEEPSEEK_API_KEY / OPENAI_API_KEY
#   2) configs/planner_llm.local.env（本地，gitignore）
#   3) ~/.claude/settings.json → ANTHROPIC_AUTH_TOKEN（Claude Code 配的 DeepSeek）

_load_llm_key_from_file() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  # shellcheck disable=SC1090
  set -a
  source "$f"
  set +a
  return 0
}

_load_llm_key_from_claude() {
  local settings="${HOME}/.claude/settings.json"
  [[ -f "$settings" ]] || return 1
  if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
    return 0
  fi
  local token
  token="$(
    python3 - <<'PY' 2>/dev/null
import json, os
p = os.path.expanduser("~/.claude/settings.json")
try:
    with open(p, encoding="utf-8") as f:
        env = json.load(f).get("env", {})
    print(env.get("DEEPSEEK_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN") or "")
except Exception:
    print("")
PY
  )"
  if [[ -n "$token" ]]; then
    export DEEPSEEK_API_KEY="$token"
    return 0
  fi
  return 1
}

# CHASSIS_DEMO_ROOT may already be set by env.sh
if [[ -z "${CHASSIS_DEMO_ROOT:-}" ]]; then
  _LK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
  export CHASSIS_DEMO_ROOT="$_LK_DIR"
fi

if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  : # already set
elif _load_llm_key_from_file "$CHASSIS_DEMO_ROOT/configs/planner_llm.local.env"; then
  :
elif _load_llm_key_from_claude; then
  :
fi

if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  export DEEPSEEK_API_KEY
  # OpenAI SDK / 部分工具也认 OPENAI_API_KEY
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
  fi
fi
