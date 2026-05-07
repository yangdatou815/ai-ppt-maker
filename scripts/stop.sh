#!/usr/bin/env bash
# stop.sh — 关闭由 start.sh 启动的 uvicorn (8080..8090)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PORT_FILE="$REPO_ROOT/.run/port"

pids_on_port() {
    local p="$1"
    ss -ltnp 2>/dev/null | awk -v pat=":$p$" '$4 ~ pat {print}' \
        | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u
}

is_apm_process() {
    local pid="$1"
    [ "${APM_STOP_FORCE:-0}" = "1" ] && return 0
    local cmdfile="/proc/$pid/cmdline"
    [ -r "$cmdfile" ] || return 1
    local cmd
    cmd=$(tr '\0' ' ' < "$cmdfile" 2>/dev/null || true)
    case "$cmd" in
        *"app.main"*)        return 0 ;;
        *"ai-ppt-maker"*)    return 0 ;;
        *uvicorn*app.main*)  return 0 ;;
    esac
    return 1
}

kill_port() {
    local p="$1"
    local pids; pids=$(pids_on_port "$p")
    if [ -z "$pids" ]; then echo "[INFO] 端口 $p 无运行进程"; return 1; fi
    local targets="" skipped=""
    for pid in $pids; do
        if is_apm_process "$pid"; then targets="$targets $pid"; else skipped="$skipped $pid"; fi
    done
    if [ -n "$skipped" ]; then echo "[SKIP] 端口 $p 上非 ai-ppt-maker 进程: $skipped (强杀: APM_STOP_FORCE=1)"; fi
    if [ -z "$targets" ]; then return 1; fi
    echo "[INFO] kill 端口 $p: $targets"
    for pid in $targets; do kill "$pid" 2>/dev/null || true; done
    sleep 1
    for pid in $targets; do kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true; done
    return 0
}

KILLED=0
EXPLICIT_PORT="${1:-${APM_PORT:-}}"
if [ -n "$EXPLICIT_PORT" ]; then
    kill_port "$EXPLICIT_PORT" && KILLED=1
elif [ -f "$PORT_FILE" ]; then
    P=$(cat "$PORT_FILE")
    kill_port "$P" && KILLED=1
    rm -f "$PORT_FILE"
else
    for P in 8080 8081 8082 8083 8084 8085 8086 8087 8088 8089 8090; do
        kill_port "$P" && KILLED=1
    done
fi

if [ "$KILLED" = "0" ]; then echo "done - nothing to stop"; else echo "done"; fi
