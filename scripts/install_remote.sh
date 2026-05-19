#!/usr/bin/env bash
# install_remote.sh — 用户一键安装脚本（自动检测系统 + 下载对应包）
#
# 用法（用户侧）:
#     curl -fsSL https://gitee.com/yangdatou815/ai-ppt-maker/raw/main/scripts/install_remote.sh | bash
#
# 或指定版本:
#     curl -fsSL .../install_remote.sh | bash -s -- v0.8.0
#
# 逻辑:
#   1. 检测 OS + 架构
#   2. 从 Gitee Release 下载对应平台的 tar.gz
#   3. 解压到 ~/ai-ppt-maker/
#   4. 安装 Ollama（如果没有）
#   5. 提示启动

set -euo pipefail

# --- Config ---
OWNER="yangdatou815"
REPO="ai-ppt-maker"
INSTALL_DIR="${APM_INSTALL_DIR:-$HOME/ai-ppt-maker}"
API_BASE="https://gitee.com/api/v5"

# --- Colors ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*" >&2; }

# --- Detect platform ---
detect_platform() {
    local os arch
    case "$(uname -s)" in
        Darwin) os="darwin" ;;
        Linux)  os="linux" ;;
        MINGW*|MSYS*|CYGWIN*) os="windows" ;;
        *) error "不支持的操作系统: $(uname -s)"; exit 1 ;;
    esac
    case "$(uname -m)" in
        x86_64|amd64) arch="x86_64" ;;
        arm64|aarch64) arch="arm64" ;;
        i386|i686) arch="x86" ;;
        *) error "不支持的架构: $(uname -m)"; exit 1 ;;
    esac
    echo "${os}-${arch}"
}

echo -e "${BOLD}"
echo "  ╔══════════════════════════════════╗"
echo "  ║   ai-ppt-maker 安装程序         ║"
echo "  ╚══════════════════════════════════╝"
echo -e "${NC}"

PLATFORM=$(detect_platform)
info "平台: $PLATFORM"

# --- Determine version ---
VERSION="${1:-latest}"
if [ "$VERSION" = "latest" ]; then
    info "获取最新版本..."
    VERSION=$(curl -sS "${API_BASE}/repos/${OWNER}/${REPO}/releases/latest" \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name',''))" 2>/dev/null || echo "")
    if [ -z "$VERSION" ]; then
        # Fallback: list releases and pick first
        VERSION=$(curl -sS "${API_BASE}/repos/${OWNER}/${REPO}/releases" \
            | python3 -c "import sys,json; rs=json.load(sys.stdin); print(rs[0]['tag_name'] if rs else '')" 2>/dev/null || echo "")
    fi
    if [ -z "$VERSION" ]; then
        error "无法获取最新版本。请指定版本：bash install_remote.sh v0.7.0"
        exit 1
    fi
fi
info "版本: $VERSION"

# --- Find matching asset ---
ASSET_NAME="ai-ppt-maker-${VERSION}-${PLATFORM}.tar.gz"
info "查找包: $ASSET_NAME"

# Get release assets
DOWNLOAD_URL=$(curl -sS "${API_BASE}/repos/${OWNER}/${REPO}/releases/tags/${VERSION}" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
assets = data.get('assets', [])
target = '${ASSET_NAME}'
for a in assets:
    if a.get('name') == target:
        print(a.get('browser_download_url', ''))
        break
" 2>/dev/null || echo "")

if [ -z "$DOWNLOAD_URL" ]; then
    error "找不到 $PLATFORM 平台的安装包"
    echo ""
    echo "  可用的包（请到 Release 页面查看）："
    echo "  https://gitee.com/${OWNER}/${REPO}/releases/tag/${VERSION}"
    echo ""
    echo "  如果是新平台，需要开发者在该平台上构建并上传。"
    exit 1
fi

info "下载地址: $DOWNLOAD_URL"

# --- Download ---
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

echo ""
info "下载中..."
curl -fSL --progress-bar -o "$TMPDIR/$ASSET_NAME" "$DOWNLOAD_URL"
info "下载完成"

# --- Install ---
echo ""
info "安装到: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
tar xzf "$TMPDIR/$ASSET_NAME" -C "$INSTALL_DIR" --strip-components=1

chmod +x "$INSTALL_DIR/start.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/install-ollama.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/ai-ppt-maker/ai-ppt-maker" 2>/dev/null || true

# macOS: remove quarantine attribute to avoid Gatekeeper blocking
if [ "$(uname -s)" = "Darwin" ]; then
    xattr -dr com.apple.quarantine "$INSTALL_DIR" 2>/dev/null || true
    info "已移除 macOS 隔离标记"
fi

info "安装完成"

# --- Ollama check ---
echo ""
if command -v ollama >/dev/null 2>&1; then
    info "Ollama 已安装: $(ollama --version 2>&1 | head -1)"
else
    warn "未检测到 Ollama（AI 引擎），请安装："
    echo ""
    echo "    cd $INSTALL_DIR && bash install-ollama.sh"
    echo ""
    echo "    或手动安装: https://ollama.com/download"
fi

# --- Done ---
echo ""
echo -e "${BOLD}=== 安装成功 ===${NC}"
echo ""
echo "  启动服务："
echo "    cd $INSTALL_DIR && ./start.sh"
echo ""
echo "  浏览器访问："
echo "    http://127.0.0.1:8080"
echo ""
