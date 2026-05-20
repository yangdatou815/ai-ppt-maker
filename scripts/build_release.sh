#!/usr/bin/env bash
# build_release.sh — 构建发布包（含 PyInstaller 打包 + Ollama 安装脚本）
#
# 输出: dist/ai-ppt-maker-{version}-{platform}.tar.gz
#   内含:
#     ai-ppt-maker/          - PyInstaller onedir bundle
#     install-ollama.sh      - Ollama 安装辅助脚本
#     start.sh               - 用户启动入口
#     README-用户指南.txt     - 简单说明
#
# 用法:
#     ./scripts/build_release.sh
#
# 前置条件:
#     - Python 3.9+ with pip
#     - Node.js (npm run build)
#     - PyInstaller (pip install pyinstaller)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

VERSION=$(python3 -c "from backend.app import __version__; print(__version__)" 2>/dev/null || echo "0.0.0")
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
RELEASE_NAME="ai-ppt-maker-${VERSION}-${PLATFORM}-${ARCH}"

echo "=== Building release: $RELEASE_NAME ==="

# --- 1. Build frontend ---
echo "[1/4] Building frontend..."
if [ -d "frontend" ] && command -v npm >/dev/null 2>&1; then
    (cd frontend && npm install --legacy-peer-deps && npm run build)
else
    echo "  [WARN] Skipping frontend build (npm not found or no frontend/)"
fi

# --- 2. Install PyInstaller if needed ---
echo "[2/4] Preparing PyInstaller..."
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    pip3 install pyinstaller -q
fi

# --- 3. Run PyInstaller ---
echo "[3/4] Building executable..."
cd "$REPO_ROOT"
pyinstaller scripts/ai-ppt-maker.spec --noconfirm --clean \
    --distpath "$REPO_ROOT/dist/bundle" \
    --workpath "$REPO_ROOT/build/pyinstaller"

# --- 4. Assemble release package ---
echo "[4/4] Assembling release package..."
RELEASE_DIR="$REPO_ROOT/dist/$RELEASE_NAME"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# Copy PyInstaller output
cp -r "$REPO_ROOT/dist/bundle/ai-ppt-maker" "$RELEASE_DIR/ai-ppt-maker"

# Create user-facing start script
cat > "$RELEASE_DIR/start.sh" << 'STARTEOF'
#!/usr/bin/env bash
# 启动 ai-ppt-maker
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$SCRIPT_DIR/ai-ppt-maker/ai-ppt-maker"
PORT="${APM_PORT:-8080}"
HOST="${APM_HOST:-127.0.0.1}"

# Bypass proxy for local connections
export no_proxy="${no_proxy:+$no_proxy,}127.0.0.1,localhost"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}127.0.0.1,localhost"

echo "=== ai-ppt-maker 启动诊断 ==="
echo "  binary : $BIN"
echo "  host   : $HOST:$PORT"
echo "  date   : $(date)"
echo ""

# macOS: remove quarantine if present
if [[ "$(uname)" == "Darwin" ]]; then
    if xattr -l "$BIN" 2>/dev/null | grep -q "com.apple.quarantine"; then
        echo "[i] 移除 macOS 隔离标记..."
        xattr -dr com.apple.quarantine "$SCRIPT_DIR/ai-ppt-maker/" 2>/dev/null || true
    fi
fi

# Check binary exists and is executable
if [ ! -x "$BIN" ]; then
    echo "[!] 找不到可执行文件: $BIN"
    echo "    请确认解压正确，或运行: chmod +x $BIN"
    exit 1
fi

# Kill stale process on same port (if any)
if lsof -i :"$PORT" -t >/dev/null 2>&1; then
    STALE_PID=$(lsof -i :"$PORT" -t 2>/dev/null | head -1)
    echo "[!] 端口 $PORT 被进程 $STALE_PID 占用，正在清理..."
    kill "$STALE_PID" 2>/dev/null || true
    sleep 1
fi

# Check Ollama
echo "[*] 检查 Ollama..."
if ! curl -sS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "[!] Ollama 未运行。请先启动 Ollama："
    echo "    ollama serve"
    echo ""
    echo "    如未安装 Ollama："
    echo "    bash install-ollama.sh"
    exit 1
fi
echo "[✓] Ollama OK"

# Check model
MODEL="${APM_LLM_MODEL:-qwen2.5:7b-instruct}"
if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo "[i] 模型 $MODEL 未下载，正在拉取（约5GB，首次需10-30分钟）..."
    ollama pull "$MODEL"
fi
echo "[✓] 模型 $MODEL 就绪"

# Start
echo ""
echo "[*] 启动 ai-ppt-maker on http://$HOST:$PORT ..."
echo "    按 Ctrl+C 停止"
echo ""
exec "$BIN"
STARTEOF
chmod +x "$RELEASE_DIR/start.sh"

# Create Windows start script
cat > "$RELEASE_DIR/start.bat" << 'BATEOF'
@echo off
chcp 65001 > nul
setlocal
set "SCRIPT_DIR=%~dp0"
set "BIN=%SCRIPT_DIR%ai-ppt-maker\ai-ppt-maker.exe"
set "PORT=8080"

echo === ai-ppt-maker 启动诊断 ===
echo   binary : %BIN%
echo   port   : %PORT%
echo.

if not exist "%BIN%" (
    echo [!] 找不到可执行文件: %BIN%
    echo     请确认解压正确。
    pause
    exit /b 1
)

REM Check if port is occupied
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul 2>nul
if not errorlevel 1 (
    echo [!] 端口 %PORT% 已被占用，可能是上次未正常关闭。
    echo     请关闭占用程序或设置 APM_PORT 环境变量使用其他端口。
    echo.
)

echo [*] 检查 Ollama...
curl -sS --max-time 3 http://127.0.0.1:11434/api/tags >nul 2>nul
if errorlevel 1 (
    echo [!] Ollama 未运行。请先启动 Ollama：
    echo     ollama serve
    echo.
    echo     如未安装：https://ollama.com/download
    pause
    exit /b 1
)
echo [√] Ollama OK

echo.
echo [*] 启动 ai-ppt-maker on http://127.0.0.1:%PORT% ...
echo     按 Ctrl+C 停止
echo.
start "" "http://127.0.0.1:%PORT%"
"%BIN%"
endlocal
BATEOF

# Create Ollama install helper
cat > "$RELEASE_DIR/install-ollama.sh" << 'OLLAMAEOF'
#!/usr/bin/env bash
# 安装 Ollama + 拉取默认模型
set -euo pipefail

echo "=== 安装 Ollama ==="
if command -v ollama >/dev/null 2>&1; then
    echo "Ollama 已安装: $(ollama --version)"
else
    echo "下载安装中..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

echo ""
echo "=== 拉取模型 ==="
MODEL="${APM_LLM_MODEL:-qwen2.5:7b-instruct}"
echo "模型: $MODEL (约5GB)"

# Ensure ollama serve is running
if ! curl -sS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "启动 ollama serve..."
    nohup ollama serve >/dev/null 2>&1 &
    sleep 3
fi

ollama pull "$MODEL"
echo ""
echo "=== 安装完成 ==="
echo "运行 ./start.sh 启动服务"
OLLAMAEOF
chmod +x "$RELEASE_DIR/install-ollama.sh"

# Create user guide
cat > "$RELEASE_DIR/README-用户指南.txt" << 'GUIDEEOF'
ai-ppt-maker 用户指南
=====================

首次使用：
  1. 安装 Ollama（AI 引擎）：
     macOS/Linux: bash install-ollama.sh
     Windows:     访问 https://ollama.com/download 下载安装

  2. 启动服务：
     macOS/Linux: ./start.sh
     Windows:     双击 start.bat

  3. 浏览器访问: http://127.0.0.1:8080

日常使用：
  确保 Ollama 在后台运行，然后运行 start.sh / start.bat 即可。

环境变量（高级）：
  APP_PORT=8080        服务端口
  APM_LLM_MODEL=...   Ollama 模型名（默认 qwen2.5:7b-instruct）
  OLLAMA_BASE_URL=...  Ollama 地址（默认 http://127.0.0.1:11434）
GUIDEEOF

# Create tarball
cd "$REPO_ROOT/dist"
tar czf "${RELEASE_NAME}.tar.gz" "$RELEASE_NAME"
rm -rf "$RELEASE_NAME"

echo ""
echo "=== Build complete ==="
echo "Release package: dist/${RELEASE_NAME}.tar.gz"
echo ""
echo "分发给用户后，用户只需："
echo "  1. 解压 tar.gz"
echo "  2. 运行 bash install-ollama.sh（首次）"
echo "  3. 运行 ./start.sh"
