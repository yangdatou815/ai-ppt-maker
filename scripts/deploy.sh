#!/usr/bin/env bash
# deploy.sh — 首次部署脚本（Linux / macOS）
#
# 流程：
#   1. 后端 venv (backend/.venv) + pip install -e ".[dev]"
#   2. 前端 npm install + npm run build → frontend/dist
#   3. Ollama 检查 + ollama pull <model>
#
# 幂等：重复运行安全。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# shellcheck source=./_ui.sh
source "$SCRIPT_DIR/_ui.sh"

ui_banner "ai-ppt-maker · 一键部署" "Linux / macOS"
ui_init 4

find_python() {
    for c in python3.13 python3.12 python3.11 python3; do
        if command -v "$c" >/dev/null 2>&1; then
            local ver
            ver=$("$c" -c 'import sys;print(".".join(map(str,sys.version_info[:2])))' 2>/dev/null || echo "0.0")
            local major minor; IFS=. read -r major minor <<<"$ver"
            if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
                echo "$c"; return 0
            fi
        fi
    done
    return 1
}

# --- 1. Python ---
ui_step "检查 Python (>=3.11)"
if ! PYTHON=$(find_python); then
    ui_fail "找不到 Python >= 3.11"
    ui_summary || true
    exit 1
fi
ui_info "Python: $PYTHON ($($PYTHON --version 2>&1))"
ui_ok

# --- 2. backend venv + 依赖 ---
ui_step "后端 venv + pip install"
VENV_DIR="$REPO_ROOT/backend/.venv"
if [ ! -d "$VENV_DIR" ]; then
    ui_info "创建虚拟环境：$VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
else
    ui_info "虚拟环境已存在，跳过创建"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
ui_info "升级 pip..."
pip install -q --upgrade pip
ui_info "安装 backend 依赖 (pip install -e .[dev])..."
( cd "$REPO_ROOT/backend" && pip install -q -e ".[dev]" )
ui_ok

# --- 3. Node + 前端构建 ---
ui_step "前端 npm install + build"
if ! command -v node >/dev/null 2>&1; then
    ui_fail "未找到 Node.js (>=18)，请先安装：https://nodejs.org"
    ui_summary || true
    exit 1
fi
ui_info "Node: $(node --version)"
( cd "$REPO_ROOT/frontend" && npm install --no-audit --no-fund && npm run build )
ui_ok

# --- 4. Ollama ---
ui_step "检查 Ollama + 拉取模型"
OLLAMA_BIN=""
if [ -n "${APM_OLLAMA_BIN:-}" ] && [ -x "$APM_OLLAMA_BIN" ]; then
    OLLAMA_BIN="$APM_OLLAMA_BIN"
elif command -v ollama >/dev/null 2>&1; then
    OLLAMA_BIN="$(command -v ollama)"
fi

if [ -z "$OLLAMA_BIN" ] && [ "${APM_AUTO_INSTALL:-1}" = "1" ]; then
    ui_info "未检测到 ollama，尝试 https://ollama.com/install.sh"
    if command -v curl >/dev/null 2>&1 && curl -fsSL https://ollama.com/install.sh | sh; then
        command -v ollama >/dev/null 2>&1 && OLLAMA_BIN="$(command -v ollama)"
    fi
fi

OLLAMA_STATUS="ok"
if [ -n "$OLLAMA_BIN" ] && [ "${APM_AUTO_PULL:-1}" = "1" ]; then
    MODEL="${APM_LLM_MODEL:-qwen2.5:7b-instruct}"
    if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        ui_info "启动 ollama serve（后台）"
        nohup "$OLLAMA_BIN" serve >/tmp/ollama-serve.log 2>&1 &
        for _ in 1 2 3 4 5 6 7 8 9 10; do
            curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
            sleep 1
        done
    fi
    ui_info "ollama pull $MODEL"
    if ! "$OLLAMA_BIN" pull "$MODEL"; then
        ui_warn "模型拉取失败，稍后手动: $OLLAMA_BIN pull $MODEL"
        OLLAMA_STATUS="warn"
    fi
elif [ -z "$OLLAMA_BIN" ]; then
    ui_warn "未发现 ollama，跳过模型拉取；M2 起 LLM 调用将失败"
    OLLAMA_STATUS="warn"
fi

if [ "$OLLAMA_STATUS" = "warn" ]; then
    ui_ok_warn "Ollama 部分完成"
else
    ui_ok
fi

ui_summary || true
echo
echo "下一步："
echo "  · 启动服务：./scripts/start.sh"
echo "  · 浏览器: http://127.0.0.1:8080"
