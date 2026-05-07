#!/usr/bin/env bash
# cleanup.sh — 一键卸载 (Linux / macOS)
#
#   --dry-run / --yes / --with-model / --with-ollama / --purge
#   等价环境变量：APM_DRY_RUN / APM_CLEAN_YES / APM_CLEAN_MODEL / APM_CLEAN_OLLAMA / APM_PURGE
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -f "$REPO_ROOT/backend/pyproject.toml" ]; then
    echo "[FATAL] 不像是 ai-ppt-maker 项目根: $REPO_ROOT" >&2
    exit 3
fi

DRY_RUN="${APM_DRY_RUN:-0}"
ASSUME_YES="${APM_CLEAN_YES:-0}"
WITH_MODEL="${APM_CLEAN_MODEL:-0}"
WITH_OLLAMA="${APM_CLEAN_OLLAMA:-0}"
PURGE="${APM_PURGE:-0}"

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)    DRY_RUN=1 ;;
        --yes|-y)     ASSUME_YES=1 ;;
        --with-model) WITH_MODEL=1 ;;
        --with-ollama) WITH_OLLAMA=1 ;;
        --purge)      PURGE=1 ;;
        -h|--help)    echo "cleanup.sh [--dry-run] [--yes] [--with-model] [--with-ollama] [--purge]"; exit 0 ;;
        *)            echo "未知参数: $1"; exit 1 ;;
    esac
    shift
done

if [ "$PURGE" = "1" ]; then
    case "$REPO_ROOT" in
        /|/home|/home/*/|"$HOME"|"$HOME/")
            echo "[FATAL] 拒绝在 $REPO_ROOT 上 purge"; exit 3 ;;
    esac
    grep -q '^name = "ai-ppt-maker-backend"' "$REPO_ROOT/backend/pyproject.toml" \
        || { echo "[FATAL] 不是 ai-ppt-maker，拒绝 purge"; exit 3; }
fi

echo "项目: $REPO_ROOT"
echo "选项: with-model=$WITH_MODEL with-ollama=$WITH_OLLAMA purge=$PURGE dry-run=$DRY_RUN"

if [ "$ASSUME_YES" != "1" ] && [ "$DRY_RUN" != "1" ]; then
    read -r -p "确认执行清理? [y/N] " ans
    case "$ans" in [yY]|[yY][eE][sS]) ;; *) echo "已取消"; exit 0 ;; esac
fi

run() {
    if [ "$DRY_RUN" = "1" ]; then echo "[DRY] $*"; else "$@"; fi
}

# 1. stop.sh
echo "[1] 停止运行中的服务"
[ -x "$SCRIPT_DIR/stop.sh" ] && run bash "$SCRIPT_DIR/stop.sh" >/dev/null 2>&1 || true

# 2. backend venv
echo "[2] 删除 backend/.venv"
[ -d "$REPO_ROOT/backend/.venv" ] && run rm -rf "$REPO_ROOT/backend/.venv"

# 3. frontend node_modules + dist
echo "[3] 删除 frontend/node_modules 与 frontend/dist"
[ -d "$REPO_ROOT/frontend/node_modules" ] && run rm -rf "$REPO_ROOT/frontend/node_modules"
[ -d "$REPO_ROOT/frontend/dist" ]         && run rm -rf "$REPO_ROOT/frontend/dist"

# 4. 运行/构建产物
echo "[4] 删除运行/构建产物"
for d in .run .pytest_cache htmlcov; do
    [ -d "$REPO_ROOT/$d" ] && run rm -rf "$REPO_ROOT/$d"
done
for f in .coverage coverage.xml install.log deploy.log; do
    [ -f "$REPO_ROOT/$f" ] && run rm -f "$REPO_ROOT/$f"
done
if [ "$DRY_RUN" = "1" ]; then
    echo "[DRY] find ... __pycache__ / *.egg-info"
else
    find "$REPO_ROOT" -type d \( -name __pycache__ -o -name '*.egg-info' \) -prune -exec rm -rf {} + 2>/dev/null || true
fi

# 5. Ollama 模型
if [ "$WITH_MODEL" = "1" ]; then
    echo "[5] 删除 Ollama 模型"
    MODEL="${APM_LLM_MODEL:-qwen2.5:7b-instruct}"
    if command -v ollama >/dev/null 2>&1; then
        run ollama rm "$MODEL" || true
    else
        echo "ollama 未安装，跳过"
    fi
fi

# 6. Ollama 二进制
if [ "$WITH_OLLAMA" = "1" ]; then
    echo "[6] 卸载 Ollama 二进制"
    if [ -x /usr/local/bin/ollama ]; then run sudo rm -f /usr/local/bin/ollama; fi
    [ -d "$HOME/.ollama" ] && run rm -rf "$HOME/.ollama"
fi

# 7. Purge
if [ "$PURGE" = "1" ]; then
    echo "[7] 删除整个项目目录: $REPO_ROOT"
    cd "$REPO_ROOT/.."
    run rm -rf "$REPO_ROOT"
fi

if [ "$DRY_RUN" = "1" ]; then
    echo "DRY-RUN 完成"
else
    echo "卸载完成。如需重装：./scripts/deploy.sh"
fi
