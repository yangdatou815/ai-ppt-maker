# install_remote.ps1 — Windows 一键安装 ai-ppt-maker
# 用法: irm https://gitee.com/yangdatou815/ai-ppt-maker/raw/main/scripts/install_remote.ps1 | iex
#
# 功能:
#   1. 检测已有安装并备份
#   2. 从 Gitee Release 下载最新 windows-x86_64 包
#   3. 解压到 ~/ai-ppt-maker/
#   4. 检查 Ollama 是否已安装
#   5. 提示启动

$ErrorActionPreference = "Stop"

$OWNER = "yangdatou815"
$REPO = "ai-ppt-maker"
$INSTALL_DIR = "$env:USERPROFILE\ai-ppt-maker"
$API_BASE = "https://gitee.com/api/v5"

Write-Host ""
Write-Host "=== ai-ppt-maker 安装脚本 (Windows) ===" -ForegroundColor Cyan
Write-Host ""

# --- Detect latest release ---
Write-Host "[*] 查询最新版本..." -ForegroundColor Green
try {
    $releases = Invoke-RestMethod "$API_BASE/repos/$OWNER/$REPO/releases/latest" -ErrorAction Stop
    $tag = $releases.tag_name
} catch {
    # Fallback: list all releases and pick first
    try {
        $all = Invoke-RestMethod "$API_BASE/repos/$OWNER/$REPO/releases"
        $tag = $all[0].tag_name
    } catch {
        Write-Host "[!] 无法获取版本信息: $_" -ForegroundColor Red
        exit 1
    }
}
Write-Host "    最新版本: $tag" -ForegroundColor Green

# --- Check if already installed ---
if (Test-Path "$INSTALL_DIR\ai-ppt-maker\ai-ppt-maker.exe") {
    Write-Host "[i] 检测到已有安装: $INSTALL_DIR" -ForegroundColor Yellow

    # Try to get current version
    $currentBin = "$INSTALL_DIR\ai-ppt-maker\ai-ppt-maker.exe"
    Write-Host "    将备份旧版本并安装 $tag" -ForegroundColor Yellow

    $backupDir = "$INSTALL_DIR.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Write-Host "    备份到: $backupDir" -ForegroundColor Yellow
    Rename-Item $INSTALL_DIR $backupDir
}

# --- Determine download URL ---
$PLATFORM = "windows-x86_64"
$FILENAME = "$REPO-$tag-$PLATFORM.zip"
$DOWNLOAD_URL = "https://gitee.com/$OWNER/$REPO/releases/download/$tag/$FILENAME"

Write-Host "[*] 下载: $FILENAME" -ForegroundColor Green
Write-Host "    URL: $DOWNLOAD_URL" -ForegroundColor DarkGray

$TMP_ZIP = "$env:TEMP\$FILENAME"
try {
    Invoke-WebRequest -Uri $DOWNLOAD_URL -OutFile $TMP_ZIP -UseBasicParsing
} catch {
    Write-Host "[!] 下载失败: $_" -ForegroundColor Red
    Write-Host "    请手动下载: https://gitee.com/$OWNER/$REPO/releases" -ForegroundColor Yellow
    exit 1
}

$fileSize = (Get-Item $TMP_ZIP).Length / 1MB
Write-Host "    已下载: $([math]::Round($fileSize, 1)) MB" -ForegroundColor Green

# --- Extract ---
Write-Host "[*] 解压到 $INSTALL_DIR ..." -ForegroundColor Green
$TMP_EXTRACT = "$env:TEMP\apm-extract-$(Get-Random)"
Expand-Archive -Path $TMP_ZIP -DestinationPath $TMP_EXTRACT -Force

# The zip contains a folder like "ai-ppt-maker-v0.7.0-windows-x86_64/"
$innerDir = Get-ChildItem $TMP_EXTRACT | Select-Object -First 1
if ($null -eq $innerDir) {
    Write-Host "[!] 解压失败: 空压缩包" -ForegroundColor Red
    exit 1
}

# Move to install dir
New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
Copy-Item -Path "$($innerDir.FullName)\*" -Destination $INSTALL_DIR -Recurse -Force

# Cleanup temp files
Remove-Item $TMP_ZIP -Force -ErrorAction SilentlyContinue
Remove-Item $TMP_EXTRACT -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[✓] 安装完成: $INSTALL_DIR" -ForegroundColor Green

# --- Check dependencies ---
Write-Host ""
Write-Host "[*] 检查依赖..." -ForegroundColor Green

# Check Ollama
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($null -ne $ollama) {
    Write-Host "    Ollama: 已安装 ($($ollama.Source))" -ForegroundColor Green
    # Check if running
    try {
        $null = Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 2
        Write-Host "    Ollama 服务: 运行中" -ForegroundColor Green
    } catch {
        Write-Host "    Ollama 服务: 未运行 (启动后请运行 'ollama serve')" -ForegroundColor Yellow
    }
} else {
    Write-Host "    Ollama: 未安装" -ForegroundColor Yellow
    Write-Host "    请访问 https://ollama.com/download 安装 Ollama" -ForegroundColor Yellow
}

# Check curl (needed by start.bat)
$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if ($null -ne $curl) {
    Write-Host "    curl: 已安装" -ForegroundColor Green
} else {
    Write-Host "    curl: 未找到 (start.bat 需要)" -ForegroundColor Yellow
}

# --- Done ---
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "安装完成！" -ForegroundColor Cyan
Write-Host ""
Write-Host "启动方式:" -ForegroundColor White
Write-Host "  cd $INSTALL_DIR" -ForegroundColor White
Write-Host "  .\start.bat" -ForegroundColor White
Write-Host ""
Write-Host "前提条件:" -ForegroundColor White
Write-Host "  1. Ollama 已安装并运行 (ollama serve)" -ForegroundColor White
Write-Host "  2. 模型已下载 (ollama pull qwen2.5:7b-instruct)" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
