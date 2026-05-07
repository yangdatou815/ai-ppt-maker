@echo off
REM stop.bat - kill uvicorn that start.bat launched (8080..8090)
REM   优先级：CLI 参数 > APM_PORT > .run\port 文件 > 扫描 8080..8090
setlocal enabledelayedexpansion
chcp 65001 > nul

set "_SCRIPT_DIR=%~dp0"
if "%_SCRIPT_DIR:~-1%"=="\" set "_SCRIPT_DIR=%_SCRIPT_DIR:~0,-1%"
if exist "%_SCRIPT_DIR%\backend\pyproject.toml" (
    set "PROJ_ROOT=%_SCRIPT_DIR%"
) else if exist "%_SCRIPT_DIR%\..\backend\pyproject.toml" (
    for %%I in ("%_SCRIPT_DIR%\..") do set "PROJ_ROOT=%%~fI"
) else (
    set "PROJ_ROOT=%CD%"
)

set "PORT_FILE=%PROJ_ROOT%\.run\port"
set "PORTS="

if not "%~1"=="" (
    set "PORTS=%~1"
    goto :do_kill
)
if not "%APM_PORT%"=="" (
    set "PORTS=%APM_PORT%"
    goto :do_kill
)
if exist "%PORT_FILE%" (
    for /f "usebackq tokens=* delims=" %%P in ("%PORT_FILE%") do set "PORTS=%%P"
    if defined PORTS goto :do_kill
)
set "PORTS=8080 8081 8082 8083 8084 8085 8086 8087 8088 8089 8090"

:do_kill
set "ANY_KILLED=0"
for %%P in (!PORTS!) do (
    set "FOUND_ON_PORT=0"
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING"') do (
        call :check_and_kill %%P %%p
        set "FOUND_ON_PORT=1"
    )
    if "!FOUND_ON_PORT!"=="0" echo   [INFO] port %%P: no process
)

if exist "%PORT_FILE%" del /f /q "%PORT_FILE%" >nul 2>nul

if "!ANY_KILLED!"=="0" (echo done - nothing to stop) else (echo done)
endlocal
goto :eof

:check_and_kill
set "_PORT=%~1"
set "_PID=%~2"
if "%APM_STOP_FORCE%"=="1" (
    echo   kill port %_PORT% PID=%_PID% ^(forced^)
    taskkill /PID %_PID% /F >nul 2>nul
    set "ANY_KILLED=1"
    goto :eof
)
set "_MATCH=0"
for /f "usebackq skip=1 tokens=*" %%C in (`wmic process where "ProcessId=%_PID%" get CommandLine /format:list 2^>nul`) do (
    echo %%C | findstr /i /c:"app.main" /c:"ai-ppt-maker" /c:"uvicorn" >nul 2>nul
    if not errorlevel 1 set "_MATCH=1"
)
if "%_MATCH%"=="1" (
    echo   kill port %_PORT% PID=%_PID%
    taskkill /PID %_PID% /F >nul 2>nul
    set "ANY_KILLED=1"
) else (
    echo   [SKIP] port %_PORT% PID=%_PID% - not ai-ppt-maker ^(use APM_STOP_FORCE=1 to override^)
)
goto :eof
