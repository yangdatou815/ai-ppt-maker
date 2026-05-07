#!/usr/bin/env bash
# scripts/_ui.sh — 通用 UI 函数库（Linux/macOS 安装/部署脚本共享）
#
# 设计目标：专业安装器风格
#   - UTF-8 盒绘标题 + Unicode 图标 (▶ ✔ ✖ ⚠)
#   - 单行进度条：[████░░░░░░] 40% · 12s
#   - 结尾对账摘要表
#   - MS_ASCII=1 时降级 ASCII-only（Windows cmd / 容器日志兼容）
#
# 使用：
#   source "$(dirname "${BASH_SOURCE[0]}")/_ui.sh"
#   ui_init 4                        # 初始化：总共 4 步
#   ui_step "检查 Python"            # 开始一步
#   ui_info "使用 Python: 3.13.2"
#   ui_ok "done"                     # 当前步完成
#   ui_step "..." ; ui_fail "err"    # 当前步失败
#   ui_summary                       # 结尾摘要表
#
# 所有函数 idempotent，多次 source 无副作用（通过 guard）。

[ -n "${_UI_SH_LOADED:-}" ] && return 0
_UI_SH_LOADED=1

# --- ASCII / Unicode 切换 ---
if [ "${MS_ASCII:-0}" = "1" ] || ! locale 2>/dev/null | grep -qiE 'UTF-?8'; then
    _UI_ICON_RUN=">"
    _UI_ICON_OK="[OK]"
    _UI_ICON_WARN="[!!]"
    _UI_ICON_FAIL="[X]"
    _UI_BAR_FULL="#"
    _UI_BAR_EMPTY="-"
    _UI_BOX_H="="
    _UI_BOX_V="|"
    _UI_BOX_TL="+"
    _UI_BOX_TR="+"
    _UI_BOX_BL="+"
    _UI_BOX_BR="+"
else
    _UI_ICON_RUN="▶"
    _UI_ICON_OK="✔"
    _UI_ICON_WARN="⚠"
    _UI_ICON_FAIL="✖"
    _UI_BAR_FULL="█"
    _UI_BAR_EMPTY="░"
    _UI_BOX_H="─"
    _UI_BOX_V="│"
    _UI_BOX_TL="╭"
    _UI_BOX_TR="╮"
    _UI_BOX_BL="╰"
    _UI_BOX_BR="╯"
fi

# --- 颜色 ---
if [ -t 1 ] && [ "${MS_NO_COLOR:-0}" != "1" ]; then
    _UI_RED='\033[0;31m'; _UI_GREEN='\033[0;32m'; _UI_YELLOW='\033[1;33m'
    _UI_CYAN='\033[0;36m'; _UI_BLUE='\033[0;34m'; _UI_DIM='\033[2m'
    _UI_BOLD='\033[1m'; _UI_NC='\033[0m'
else
    _UI_RED=''; _UI_GREEN=''; _UI_YELLOW=''; _UI_CYAN=''; _UI_BLUE=''
    _UI_DIM=''; _UI_BOLD=''; _UI_NC=''
fi

# --- 状态 ---
_UI_TOTAL=0
_UI_CUR=0
_UI_CUR_LABEL=""
_UI_CUR_T0=0
# 摘要表条目：每行 "状态|label|耗时s"；用 \n 分隔以支持 set -u
_UI_SUMMARY=""

ui_init() {
    # $1 = 总步数
    _UI_TOTAL="${1:-0}"
    _UI_CUR=0
    _UI_SUMMARY=""
}

# 画一个"专业"风格盒绘标题（不强行对齐右边框，规避中文宽度计算）
# $1 = 标题, $2 = 副标题(可选)
ui_banner() {
    local title="$1"
    local subtitle="${2:-}"
    local w=60
    local line=""
    local i=0
    while [ $i -lt $w ]; do line="${line}${_UI_BOX_H}"; i=$((i+1)); done
    echo
    echo -e "${_UI_BOLD}${_UI_CYAN}${_UI_BOX_TL}${line}${_UI_BOX_TR}${_UI_NC}"
    echo -e "${_UI_BOLD}${_UI_CYAN}${_UI_BOX_V}${_UI_NC} ${_UI_BOLD}  ${title}${_UI_NC}"
    if [ -n "$subtitle" ]; then
        echo -e "${_UI_BOLD}${_UI_CYAN}${_UI_BOX_V}${_UI_NC} ${_UI_DIM}  ${subtitle}${_UI_NC}"
    fi
    echo -e "${_UI_BOLD}${_UI_CYAN}${_UI_BOX_BL}${line}${_UI_BOX_BR}${_UI_NC}"
    echo
}

# 开启一步
# $1 = label
ui_step() {
    _UI_CUR=$((_UI_CUR + 1))
    _UI_CUR_LABEL="$1"
    _UI_CUR_T0=$SECONDS
    local pct=0
    if [ "$_UI_TOTAL" -gt 0 ]; then
        pct=$(( _UI_CUR * 100 / _UI_TOTAL ))
    fi
    echo
    echo -e "${_UI_BOLD}${_UI_CYAN}${_UI_ICON_RUN} [${_UI_CUR}/${_UI_TOTAL}] $1${_UI_NC} ${_UI_DIM}(${pct}%)${_UI_NC}"
    _ui_progress_bar "$pct"
}

# 画单行进度条
# $1 = pct (0-100)
_ui_progress_bar() {
    local pct=$1
    local width=30
    local filled=$(( pct * width / 100 ))
    local empty=$(( width - filled ))
    local bar=""
    local i=0
    while [ $i -lt $filled ]; do bar="${bar}${_UI_BAR_FULL}"; i=$((i+1)); done
    i=0
    while [ $i -lt $empty ]; do bar="${bar}${_UI_BAR_EMPTY}"; i=$((i+1)); done
    echo -e "  ${_UI_DIM}[${_UI_NC}${_UI_GREEN}${bar}${_UI_NC}${_UI_DIM}] ${pct}%${_UI_NC}"
}

# 当前步 - 普通 info（细节）
ui_info() { echo -e "  ${_UI_DIM}${_UI_NC}${_UI_BLUE}ℹ${_UI_NC} $*" 2>/dev/null || echo "  i $*"; }

# 当前步 - 警告
ui_warn() {
    echo -e "  ${_UI_YELLOW}${_UI_ICON_WARN}${_UI_NC} $*"
}

# 当前步完成（OK）
# $1 = 可选备注
ui_ok() {
    local elapsed=$(( SECONDS - _UI_CUR_T0 ))
    local note="${1:-}"
    if [ -n "$note" ]; then
        echo -e "  ${_UI_GREEN}${_UI_ICON_OK}${_UI_NC} ${_UI_GREEN}${note}${_UI_NC} ${_UI_DIM}(${elapsed}s)${_UI_NC}"
    else
        echo -e "  ${_UI_GREEN}${_UI_ICON_OK}${_UI_NC} ${_UI_GREEN}完成${_UI_NC} ${_UI_DIM}(${elapsed}s)${_UI_NC}"
    fi
    _UI_SUMMARY="${_UI_SUMMARY}OK|${_UI_CUR_LABEL}|${elapsed}"$'\n'
}

# 当前步带警告完成
ui_ok_warn() {
    local elapsed=$(( SECONDS - _UI_CUR_T0 ))
    local note="${1:-有警告}"
    echo -e "  ${_UI_YELLOW}${_UI_ICON_WARN}${_UI_NC} ${_UI_YELLOW}${note}${_UI_NC} ${_UI_DIM}(${elapsed}s)${_UI_NC}"
    _UI_SUMMARY="${_UI_SUMMARY}WARN|${_UI_CUR_LABEL}|${elapsed}"$'\n'
}

# 当前步失败（不退出，调用方决定是否 exit）
ui_fail() {
    local elapsed=$(( SECONDS - _UI_CUR_T0 ))
    local note="${1:-失败}"
    echo -e "  ${_UI_RED}${_UI_ICON_FAIL}${_UI_NC} ${_UI_RED}${note}${_UI_NC} ${_UI_DIM}(${elapsed}s)${_UI_NC}"
    _UI_SUMMARY="${_UI_SUMMARY}FAIL|${_UI_CUR_LABEL}|${elapsed}"$'\n'
}

# 结尾打印摘要表
ui_summary() {
    echo
    local w=60
    local line=""
    local i=0
    while [ $i -lt $w ]; do line="${line}${_UI_BOX_H}"; i=$((i+1)); done
    echo -e "${_UI_BOLD}${_UI_BOX_TL}${line}${_UI_BOX_TR}${_UI_NC}"
    echo -e "${_UI_BOLD}${_UI_BOX_V}${_UI_NC} ${_UI_BOLD}  部署摘要${_UI_NC}"
    echo -e "${_UI_BOLD}${_UI_BOX_BL}${line}${_UI_BOX_BR}${_UI_NC}"
    local any_fail=0
    local any_warn=0
    if [ -n "$_UI_SUMMARY" ]; then
        # 使用 printf 和 while read 处理每行
        while IFS='|' read -r status label elapsed; do
            [ -z "$status" ] && continue
            local icon color
            case "$status" in
                OK)   icon="$_UI_ICON_OK";   color="$_UI_GREEN"  ;;
                WARN) icon="$_UI_ICON_WARN"; color="$_UI_YELLOW"; any_warn=1 ;;
                FAIL) icon="$_UI_ICON_FAIL"; color="$_UI_RED";    any_fail=1 ;;
                *)    icon="?";              color="$_UI_DIM"    ;;
            esac
            printf "  ${color}%s${_UI_NC} %-45s ${_UI_DIM}%5ss${_UI_NC}\n" "$icon" "$label" "$elapsed"
        done <<EOF
$_UI_SUMMARY
EOF
    fi
    echo
    if [ "$any_fail" = "1" ]; then
        echo -e "${_UI_RED}${_UI_BOLD}${_UI_ICON_FAIL} 部署存在失败步骤，请查看上方日志${_UI_NC}"
        return 1
    elif [ "$any_warn" = "1" ]; then
        echo -e "${_UI_YELLOW}${_UI_BOLD}${_UI_ICON_WARN} 部署完成（有警告）${_UI_NC}"
    else
        echo -e "${_UI_GREEN}${_UI_BOLD}${_UI_ICON_OK} 部署完成，一切就绪${_UI_NC}"
    fi
    return 0
}
