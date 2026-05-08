@echo off
REM ============================================================
REM scripts\_common.bat - Windows 安装/部署脚本共享函数库
REM
REM 专业安装器 UI（CMD 版）：
REM   step header N/M plus percent, single-line progress bar, elapsed seconds
REM   :ui_banner / :ui_step / :ui_ok / :ui_warn / :ui_fail / :ui_summary
REM
REM 系统工具：
REM   :refresh_path   - winget 安装后从注册表刷新本进程 PATH
REM   :find_python    - 跳过 Microsoft Store stub，定位真实 python.exe -> PY_EXE
REM
REM 所有全局变量以 _UI_ / _MS_ 开头，避免和调用者冲突。
REM
REM 约定：调用者 setlocal enabledelayedexpansion 后用 "call :ui_step ..." 调用；
REM       调用者通过 set LOG=... 指定日志文件。
REM
REM 本文件由 deploy.bat 直接 `call`。install.bat 由 scripts/build_install.py
REM 在打包时内联此文件的函数段，以满足"单文件一键安装"约束。
REM ============================================================

REM 被 call 时直接跳过函数定义区到 :_common_loaded 标签
goto :_common_loaded

REM ====================== UI: banner ======================
:ui_banner
REM %~1 = title, %~2 = subtitle (optional)
echo.
echo +------------------------------------------------------------+
echo ^|   %~1
if not "%~2"=="" echo ^|   %~2
echo +------------------------------------------------------------+
echo.
exit /b 0

REM ====================== UI: init ======================
:ui_init
REM %~1 = total steps
set "_UI_TOTAL=%~1"
set "_UI_CUR=0"
set "_UI_SUMMARY_FILE=%TEMP%\_ms_summary_%RANDOM%%RANDOM%.txt"
type nul > "%_UI_SUMMARY_FILE%" 2>nul
call :_init_colors
exit /b 0

REM ====================== UI: colors ======================
REM Captures ANSI ESC into _C_ESC and exposes _C_GREEN / _C_RED / _C_YELLOW /
REM _C_CYAN / _C_BOLD / _C_RESET. Win10 1607+ conhost renders them; older or
REM redirected output sees plain text. Set NO_COLOR=1 to disable.
:_init_colors
if defined _C_RESET exit /b 0
set "_C_RESET="
set "_C_GREEN="
set "_C_RED="
set "_C_YELLOW="
set "_C_CYAN="
set "_C_BOLD="
if defined NO_COLOR exit /b 0
REM Persist Virtual-Terminal level so cmd renders ANSI sequences. Idempotent.
reg add "HKCU\Console" /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>nul
REM Capture the ESC byte using the well-known prompt-and-rem trick.
REM Output of `prompt #$E#` (after the dummy for body fires it) is "#<ESC>#".
REM `for /f "delims=#"` then strips the surrounding '#' and leaves us with
REM the bare ESC character.
for /f "delims=#" %%E in ('"prompt #$E# & echo on & for %%a in (1) do rem"') do (
    if not defined _C_ESC set "_C_ESC=%%E"
)
if not defined _C_ESC exit /b 0
set "_C_RESET=%_C_ESC%[0m"
set "_C_GREEN=%_C_ESC%[32m"
set "_C_RED=%_C_ESC%[31m"
set "_C_YELLOW=%_C_ESC%[33m"
set "_C_CYAN=%_C_ESC%[36m"
set "_C_BOLD=%_C_ESC%[1m"
exit /b 0

REM ====================== UI: step ======================
:ui_step
REM %~1 = label
set /a _UI_CUR=_UI_CUR+1
set "_UI_CUR_LABEL=%~1"
set /a _UI_PCT=_UI_CUR*100/_UI_TOTAL
set "_UI_T0=%TIME%"
echo.
echo ^>^> [%_UI_CUR%/%_UI_TOTAL%] %~1 ^(%_UI_PCT%%%^)
call :_ui_progress_bar %_UI_PCT%
if defined LOG echo [STEP %TIME%] [%_UI_CUR%/%_UI_TOTAL%] %~1 >> "%LOG%"
exit /b 0

REM ====================== UI: progress bar ======================
:_ui_progress_bar
REM %~1 = pct (0-100)
set /a _UI_BAR_FILLED=%~1*30/100
set /a _UI_BAR_EMPTY=30-_UI_BAR_FILLED
set "_UI_BAR_STR="
for /l %%i in (1,1,%_UI_BAR_FILLED%) do set "_UI_BAR_STR=!_UI_BAR_STR!#"
for /l %%i in (1,1,%_UI_BAR_EMPTY%) do set "_UI_BAR_STR=!_UI_BAR_STR!-"
echo    [!_UI_BAR_STR!] %~1%%
exit /b 0

REM ====================== UI: ok ======================
:ui_ok
REM %~1 = optional note
call :_ui_elapsed
if "%~1"=="" (
    echo    !_C_GREEN![OK]!_C_RESET! done ^(!_UI_ELAPSED!s^)
) else (
    echo    !_C_GREEN![OK]!_C_RESET! %~1 ^(!_UI_ELAPSED!s^)
)
echo OK^|%_UI_CUR_LABEL%^|!_UI_ELAPSED! >> "%_UI_SUMMARY_FILE%"
if defined LOG echo [OK %TIME%] %_UI_CUR_LABEL% took !_UI_ELAPSED!s >> "%LOG%"
exit /b 0

REM ====================== UI: warn ======================
:ui_warn
echo    !_C_YELLOW![!!]!_C_RESET! %~1
if defined LOG echo [WARN %TIME%] %~1 >> "%LOG%"
exit /b 0

REM ====================== UI: ok with warn ======================
:ui_ok_warn
call :_ui_elapsed
echo    !_C_YELLOW![!!]!_C_RESET! %~1 ^(!_UI_ELAPSED!s^)
echo WARN^|%_UI_CUR_LABEL%^|!_UI_ELAPSED! >> "%_UI_SUMMARY_FILE%"
if defined LOG echo [WARN-OK %TIME%] %_UI_CUR_LABEL% took !_UI_ELAPSED!s >> "%LOG%"
exit /b 0

REM ====================== UI: fail ======================
:ui_fail
call :_ui_elapsed
echo    !_C_RED![X]!_C_RESET! %~1 ^(!_UI_ELAPSED!s^)
echo FAIL^|%_UI_CUR_LABEL%^|!_UI_ELAPSED! >> "%_UI_SUMMARY_FILE%"
if defined LOG echo [FAIL %TIME%] %_UI_CUR_LABEL% ^(%~1^) took !_UI_ELAPSED!s >> "%LOG%"
exit /b 0

REM ====================== UI: info ======================
:ui_info
echo    !_C_CYAN![i]!_C_RESET! %~1
if defined LOG echo [INFO %TIME%] %~1 >> "%LOG%"
exit /b 0

REM ====================== UI: summary ======================
:ui_summary
echo.
echo +------------------------------------------------------------+
echo ^|   部署摘要
echo +------------------------------------------------------------+
set "_UI_ANY_FAIL=0"
set "_UI_ANY_WARN=0"
if exist "%_UI_SUMMARY_FILE%" (
    for /f "usebackq tokens=1,2,3 delims=|" %%a in ("%_UI_SUMMARY_FILE%") do (
        if "%%a"=="OK"   echo    !_C_GREEN![OK]!_C_RESET! %%b ^(%%cs^)
        if "%%a"=="WARN" (echo    !_C_YELLOW![!!]!_C_RESET! %%b ^(%%cs^) & set "_UI_ANY_WARN=1")
        if "%%a"=="FAIL" (echo    !_C_RED![X]!_C_RESET!  %%b ^(%%cs^) & set "_UI_ANY_FAIL=1")
    )
    del "%_UI_SUMMARY_FILE%" >nul 2>nul
)
echo.
if "!_UI_ANY_FAIL!"=="1" (
    echo !_C_RED![X]!_C_RESET! 部署存在失败步骤，请查看上方日志
    exit /b 1
)
if "!_UI_ANY_WARN!"=="1" (
    echo !_C_YELLOW![!!]!_C_RESET! 部署完成（有警告）
    exit /b 0
)
echo !_C_GREEN![OK]!_C_RESET! 部署完成，一切就绪
exit /b 0

REM ====================== UI: elapsed helper ======================
:_ui_elapsed
if not defined _UI_T0 (set "_UI_ELAPSED=0" & exit /b 0)
call :_time_to_ms "%_UI_T0%" _UI_T0_MS
call :_time_to_ms "%TIME%"    _UI_T1_MS
set /a _UI_DIFF_MS=_UI_T1_MS-_UI_T0_MS
if !_UI_DIFF_MS! LSS 0 set /a _UI_DIFF_MS+=86400000
set /a _UI_ELAPSED=_UI_DIFF_MS/1000
exit /b 0

REM ====================== time parser: HH:MM:SS.cs -> ms ======================
:_time_to_ms
set "_TS=%~1"
for /f "tokens=1-4 delims=:., " %%a in ("%_TS%") do (
    set /a %~2=^(^(1%%a-100^)*3600 + ^(1%%b-100^)*60 + ^(1%%c-100^)^)*1000 + ^(1%%d-100^)*10
)
exit /b 0

REM ====================== system: PATH refresh from registry ======================
:refresh_path
set "_NEWPATH="
for /f "usebackq tokens=2*" %%A in (`reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul`) do set "_NEWPATH=%%B"
for /f "usebackq tokens=2*" %%A in (`reg query "HKCU\Environment" /v Path 2^>nul`) do set "_NEWPATH=!_NEWPATH!;%%B"
if defined _NEWPATH (
    set "PATH=!_NEWPATH!"
    if defined LOG echo [PATH-REFRESH %TIME%] done >> "%LOG%"
)
exit /b 0

REM ====================== system: find real Python ======================
:find_python
set "PY_EXE="
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PY_EXE (
        call :_is_real_python "%%P" _IS_REAL
        if "!_IS_REAL!"=="1" set "PY_EXE=%%P"
    )
)
if defined PY_EXE exit /b 0
where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do if not defined PY_EXE set "PY_EXE=%%P"
)
if defined PY_EXE exit /b 0
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" if not defined PY_EXE set "PY_EXE=%%D\python.exe"
)
exit /b 0

REM Judge if %~1 is a real Python (vs Microsoft Store 0-byte stub)
:_is_real_python
set "%~2=0"
echo %~1 | findstr /i "WindowsApps" >nul
if not errorlevel 1 (
    for %%F in ("%~1") do if %%~zF LEQ 1024 exit /b 0
)
set "%~2=1"
exit /b 0

REM ============================================================
REM 加载完成标签 —— 被 call 时从 goto :_common_loaded 跳到此处
REM ============================================================
:_common_loaded
exit /b 0
