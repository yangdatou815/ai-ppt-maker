@echo off
REM start.bat - daily launcher (Windows)
REM Steps:
REM   1. Locate backend\.venv\Scripts\python.exe
REM   2. Ensure Ollama is running (best-effort)
REM   3. Start FastAPI on first free port in 8080..8090
REM      (uvicorn serves API + frontend\dist as SPA)
REM   4. Open default browser

setlocal enabledelayedexpansion
chcp 65001 > nul

set "_SCRIPT_DIR=%~dp0"
if "%_SCRIPT_DIR:~-1%"=="\" set "_SCRIPT_DIR=%_SCRIPT_DIR:~0,-1%"
if exist "%_SCRIPT_DIR%\backend\pyproject.toml" (
    set "PROJ_ROOT=%_SCRIPT_DIR%"
) else if exist "%_SCRIPT_DIR%\..\backend\pyproject.toml" (
    for %%I in ("%_SCRIPT_DIR%\..") do set "PROJ_ROOT=%%~fI"
) else (
    echo [ERROR] Cannot locate backend\pyproject.toml from %_SCRIPT_DIR%
    pause & exit /b 1
)
cd /d "%PROJ_ROOT%"

echo ============================================================
echo ai-ppt-maker - 启动
echo ============================================================

set "VENV_PY=%PROJ_ROOT%\backend\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [错误] backend\.venv 不存在, 请先运行 scripts\deploy.bat
    pause & exit /b 1
)

if not exist "%PROJ_ROOT%\frontend\dist\index.html" (
    echo [警告] frontend\dist 不存在, 仅启动后端 API; 请先运行 scripts\deploy.bat 构建前端
)

set NO_PROXY=127.0.0.1,localhost
set no_proxy=127.0.0.1,localhost

echo 检查 Ollama 服务...
set "OLLAMA_OK=0"
curl -s --max-time 3 http://127.0.0.1:11434/api/tags >nul 2>nul
if not errorlevel 1 set "OLLAMA_OK=1"
if "!OLLAMA_OK!"=="1" (
    echo Ollama 运行中 [OK]
    goto :ollama_check_done
)
echo [警告] Ollama 未响应, 尝试启动...
where ollama >nul 2>nul
if errorlevel 1 (
    echo [警告] 找不到 ollama, LLM 调用将 fallback 到 Mock
    goto :ollama_check_done
)
start "" /b ollama serve
echo 已尝试启动 ollama serve ^(后台^)
timeout /t 3 /nobreak >nul
curl -s --max-time 3 http://127.0.0.1:11434/api/tags >nul 2>nul
if not errorlevel 1 (
    echo Ollama 启动成功 [OK]
) else (
    echo [警告] Ollama 启动后仍未响应
)
:ollama_check_done

set PORT=
for %%P in (8080 8081 8082 8083 8084 8085 8086 8087 8088 8089 8090) do (
    if not defined PORT (
        netstat -an | findstr ":%%P " | findstr "LISTENING" >nul
        if errorlevel 1 set "PORT=%%P"
    )
)
if not defined PORT (
    echo [ERROR] no free port in 8080..8090
    pause & exit /b 1
)
echo Using port !PORT!

if not exist "%PROJ_ROOT%\.run" mkdir "%PROJ_ROOT%\.run" >nul 2>nul
>"%PROJ_ROOT%\.run\port" echo !PORT!

start "" /min cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:!PORT!"

echo Starting FastAPI on http://127.0.0.1:!PORT!
echo Press Ctrl+C to stop
cd /d "%PROJ_ROOT%\backend"
"%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port !PORT!
endlocal
