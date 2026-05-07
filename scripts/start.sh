#!/usr/bin/env bash
# start.sh — 日常启动 (Linux / macOS)
#   后端 uvicorn 同时 serve API + frontend/dist (SPA)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

VENV_DIR="$REPO_ROOT/backend/.venv"
if [ ! -d "$VENV_DIR" ]; then
    error "backend/.venv 不存在，请先运行 ./scripts/deploy.sh"
    exit 1
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [ ! -f "$REPO_ROOT/frontend/dist/index.html" ]; then
    warn "frontend/dist 不存在，仅启动后端 API；请先 ./scripts/deploy.sh 构建前端"
fi

OLLAMA_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
export no_proxy="${no_proxy:-127.0.0.1,localhost}"
export NO_PROXY="${NO_PROXY:-127.0.0.1,localhost}"

info "检查 Ollama: $OLLAMA_URL"
if curl -s --max-time 3 "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
    info "Ollama OK"
else
    warn "Ollama 未响应；M2 后才需要 LLM"
fi

PORT="${APM_PORT:-8080}"
HOST="${APM_HOST:-127.0.0.1}"
PORT_TAKEN() { ss -ln 2>/dev/null | grep -q ":$1 "; }
if PORT_TAKEN "$PORT"; then
    for P in 8080 8081 8082 8083 8084 8085 8086 8087 8088 8089 8090; do
        if ! PORT_TAKEN "$P"; then PORT="$P"; break; fi
    done
fi
URL="http://$HOST:$PORT"
info "启动 Web: $URL"

mkdir -p "$REPO_ROOT/.run"
echo "$PORT" > "$REPO_ROOT/.run/port"

(
    sleep 2
    if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true
    elif command -v open      >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 || true
    fi
) &

cd "$REPO_ROOT/backend"
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
