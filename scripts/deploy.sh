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
    for c in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "$c" >/dev/null 2>&1; then
            local ver
            ver=$("$c" -c 'import sys;print(".".join(map(str,sys.version_info[:2])))' 2>/dev/null || echo "0.0")
            local major minor; IFS=. read -r major minor <<<"$ver"
            if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
                echo "$c"; return 0
            fi
        fi
    done
    return 1
}

# --- 1. Python ---
ui_step "检查 Python (>=3.9)"
if ! PYTHON=$(find_python); then
    ui_fail "找不到 Python >= 3.9"
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
find_node() {
    # 1. plain $PATH
    if command -v node >/dev/null 2>&1; then
        command -v node
        return 0
    fi
    # 2. nvm default
    for d in "$HOME/.nvm/versions/node"/*/bin; do
        [ -x "$d/node" ] && { echo "$d/node"; return 0; }
    done
    # 3. n / volta
    for d in "$HOME/n/bin" "$HOME/.volta/bin"; do
        [ -x "$d/node" ] && { echo "$d/node"; return 0; }
    done
    # 4. workspace-local prebuilt tarball (e.g. node-v20.18.0-linux-x64/bin/node
    #    sitting next to the repo). This is the layout used on locked-down
    #    corporate dev hosts where users unzip an offline node release.
    for d in "$REPO_ROOT/.."/node-v*-linux-*/bin "$REPO_ROOT/.."/node-v*-darwin-*/bin; do
        [ -x "$d/node" ] && { echo "$d/node"; return 0; }
    done
    return 1
}

NODE_BIN=""
if NODE_BIN=$(find_node); then
    NODE_DIR="$(dirname "$NODE_BIN")"
    case ":$PATH:" in
        *":$NODE_DIR:"*) ;;
        *) export PATH="$NODE_DIR:$PATH"; ui_info "PATH += $NODE_DIR" ;;
    esac
fi

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
find_ollama() {
    # 1. explicit override
    if [ -n "${APM_OLLAMA_BIN:-}" ] && [ -x "$APM_OLLAMA_BIN" ]; then
        echo "$APM_OLLAMA_BIN"; return 0
    fi
    # 2. plain $PATH
    if command -v ollama >/dev/null 2>&1; then
        command -v ollama
        return 0
    fi
    # 3. workspace-local prebuilt tarball next to the repo, e.g.
    #    /var/fpwork/<user>/ollama/bin/ollama on locked-down dev hosts.
    for d in "$REPO_ROOT/.."/ollama/bin "$REPO_ROOT/.."/ollama; do
        [ -x "$d/ollama" ] && { echo "$d/ollama"; return 0; }
    done
    # 4. user-local install (the pattern ollama.com/install.sh uses without sudo).
    for d in "$HOME/.local/bin" "$HOME/bin" "/usr/local/bin"; do
        [ -x "$d/ollama" ] && { echo "$d/ollama"; return 0; }
    done
    return 1
}

OLLAMA_BIN=""
if OLLAMA_BIN=$(find_ollama); then
    OLLAMA_DIR="$(dirname "$OLLAMA_BIN")"
    case ":$PATH:" in
        *":$OLLAMA_DIR:"*) ;;
        *) export PATH="$OLLAMA_DIR:$PATH"; ui_info "PATH += $OLLAMA_DIR" ;;
    esac
fi

# Skip remote install entirely unless the user opts in. The official
# install.sh elevates to sudo and writes to /usr/local — that's invasive
# on shared dev hosts. Operators on isolated machines can either drop a
# pre-extracted tarball next to the repo (auto-detected above), or set
# APM_AUTO_INSTALL=1 to let the script run the upstream installer.
if [ -z "$OLLAMA_BIN" ] && [ "${APM_AUTO_INSTALL:-0}" = "1" ]; then
    ui_info "未检测到 ollama，尝试 https://ollama.com/install.sh (APM_AUTO_INSTALL=1)"
    if command -v curl >/dev/null 2>&1 && curl -fsSL https://ollama.com/install.sh | sh; then
        OLLAMA_BIN=$(find_ollama || true)
    fi
elif [ -z "$OLLAMA_BIN" ]; then
    ui_info "未检测到 ollama；如需自动安装请重跑：APM_AUTO_INSTALL=1 ./scripts/deploy.sh"
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
