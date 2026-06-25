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
echo     2. Go chu 'antigravity' (hoac 'claude') roi nhan Enter de khoi dong.
echo     3. Moi cau lenh thuc thi se tu dong yeu cau duyet tren dien thoai.
echo.
echo ============================================================
echo.

:: Backup the original shell path (vital for executing approved commands)
set ORIGINAL_COMSPEC=%COMSPEC%

:: Redirect shell command execution to AgentGuard
set COMSPEC=%~dp0agentguard-shell.bat
set CLAUDE_CODE_SHELL=%~dp0agentguard-shell.bat

:: Start a nested command prompt session keeping this environment active
"%ORIGINAL_COMSPEC%" /k
