#!/usr/bin/env bash
# upload_release.sh — 构建 + 上传到 Gitee Release
#
# 自动检测当前系统，构建对应平台的包，然后上传到 Gitee Release。
#
# 用法:
#     ./scripts/upload_release.sh [version]
#
# 示例:
#     ./scripts/upload_release.sh          # 自动读取版本号
#     ./scripts/upload_release.sh v0.8.0   # 指定版本
#
# 环境变量:
#     GITEE_TOKEN  — Gitee 私人令牌（必需）
#     APM_SKIP_BUILD=1  — 跳过构建，只上传已有的 dist/*.tar.gz
#
# 前置:
#     pip install pyinstaller
#     npm (for frontend build)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# --- Config ---
OWNER="yangdatou815"
REPO="ai-ppt-maker"
API_BASE="https://gitee.com/api/v5"

# --- Detect platform ---
detect_platform() {
    local os arch
    case "$(uname -s)" in
        Darwin) os="darwin" ;;
        Linux)  os="linux" ;;
        MINGW*|MSYS*|CYGWIN*) os="windows" ;;
        *) os="$(uname -s | tr '[:upper:]' '[:lower:]')" ;;
    esac
    case "$(uname -m)" in
        x86_64|amd64) arch="x86_64" ;;
        arm64|aarch64) arch="arm64" ;;
        *) arch="$(uname -m)" ;;
    esac
    echo "${os}-${arch}"
}

PLATFORM=$(detect_platform)
echo "Platform: $PLATFORM"

# --- Version ---
if [ -n "${1:-}" ]; then
    VERSION="$1"
else
    VERSION="v$(python3 -c "import sys; sys.path.insert(0,'backend'); from app import __version__; print(__version__)" 2>/dev/null || echo "0.0.0")"
fi
echo "Version: $VERSION"

RELEASE_NAME="ai-ppt-maker-${VERSION}-${PLATFORM}"
TARBALL="dist/${RELEASE_NAME}.tar.gz"

# --- Build ---
if [ "${APM_SKIP_BUILD:-0}" != "1" ]; then
    echo ""
    echo "=== Building release package ==="
    bash "$SCRIPT_DIR/build_release.sh"
    # Rename the output to include version tag
    BUILT=$(ls dist/ai-ppt-maker-*-${PLATFORM}.tar.gz 2>/dev/null | head -1)
    if [ -n "$BUILT" ] && [ "$BUILT" != "$TARBALL" ]; then
        mv "$BUILT" "$TARBALL"
    fi
fi

if [ ! -f "$TARBALL" ]; then
    echo "[ERROR] Tarball not found: $TARBALL"
    echo "  Run without APM_SKIP_BUILD or check build_release.sh output"
    exit 1
fi

TARBALL_SIZE=$(du -h "$TARBALL" | cut -f1)
echo "Package: $TARBALL ($TARBALL_SIZE)"

# --- Upload to Gitee Release ---
if [ -z "${GITEE_TOKEN:-}" ]; then
    echo ""
    echo "[ERROR] GITEE_TOKEN 未设置。"
    echo "  请在 Gitee 个人设置 → 私人令牌 中创建 token，然后："
    echo "  export GITEE_TOKEN=your_token_here"
    echo ""
    echo "  构建已完成，包在: $TARBALL"
    echo "  可手动上传到: https://gitee.com/$OWNER/$REPO/releases"
    exit 0
fi

echo ""
echo "=== Uploading to Gitee Release ==="

# Check if release exists
RELEASE_ID=$(curl -s "${API_BASE}/repos/${OWNER}/${REPO}/releases/tags/${VERSION}?access_token=${GITEE_TOKEN}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")

if [ -z "$RELEASE_ID" ]; then
    echo "Creating release $VERSION..."
    RELEASE_ID=$(curl -s -X POST "${API_BASE}/repos/${OWNER}/${REPO}/releases" \
        -H "Content-Type: application/json" \
        -d "{
            \"access_token\": \"${GITEE_TOKEN}\",
            \"tag_name\": \"${VERSION}\",
            \"name\": \"${VERSION}\",
            \"body\": \"ai-ppt-maker ${VERSION}\\n\\n平台包：${PLATFORM}\",
            \"target_commitish\": \"main\"
        }" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
    echo "  Release created: ID=$RELEASE_ID"
else
    echo "  Release $VERSION exists: ID=$RELEASE_ID"
fi

if [ -z "$RELEASE_ID" ]; then
    echo "[ERROR] Failed to create/find release"
    exit 1
fi

# Upload asset
echo "Uploading $TARBALL..."
UPLOAD_RESP=$(curl -s -X POST \
    "${API_BASE}/repos/${OWNER}/${REPO}/releases/${RELEASE_ID}/attach_files" \
    -H "Content-Type: multipart/form-data" \
    -F "access_token=${GITEE_TOKEN}" \
    -F "file=@${TARBALL}")

DOWNLOAD_URL=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('browser_download_url', d.get('message','UNKNOWN')))" 2>/dev/null || echo "")

echo ""
echo "=== Done ==="
echo "Download URL: $DOWNLOAD_URL"
echo ""
echo "用户安装命令："
echo "  curl -fsSL https://gitee.com/$OWNER/$REPO/raw/main/scripts/install_remote.sh | bash"
