@echo off
title AgentGuard Secured Terminal
echo ============================================================
echo      KHOI DONG TERMINAL DUOC BAO VE BOI AGENTGUARD
echo ============================================================
echo.
echo [!] Dang cau hinh moi truong chan lenh...
echo [!] Da thiet lap ORIGINAL_COMSPEC de thuc thi lenh thuc te.
echo [!] Da thay the COMSPEC va CLAUDE_CODE_SHELL sang AgentGuard.
echo.
echo [*] HUONG DAN:
echo     1. Dam bao file 'run.bat' (Server) dang duoc chay o cua so khac.
echo     2. Go 'cursor .' (neu dung Cursor) hoac 'code .' (neu dung VS Code) de mo IDE.
echo     3. Moi cau lenh tu Antigravity hoac Claude se yeu cau duyet tren Web/Mobile.
echo.
echo ============================================================
echo.

:: Backup the original shell path (vital for executing approved commands)
if "%ORIGINAL_COMSPEC%"=="" (
    set ORIGINAL_COMSPEC=%COMSPEC%
)

:: Redirect shell command execution to AgentGuard C# binary wrappers
set COMSPEC=%~dp0bin\cmd.exe
set CLAUDE_CODE_SHELL=%~dp0bin\cmd.exe

:: Prepend the bin directory to PATH to intercept powershell commands
set PATH=%~dp0bin;%PATH%

:: Start a nested command prompt session keeping this environment active
"%ORIGINAL_COMSPEC%" /k
