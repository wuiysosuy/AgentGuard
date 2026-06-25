@echo off
title AgentGuard Server
echo ============================================================
echo            AGENTGUARD STARTUP SCRIPT
echo ============================================================
echo.
echo [1/2] Dang kiem tra va cai dat cac thu vien phu thuoc...
python -m pip install flask requests qrcode

echo.
echo [2/2] Dang khoi dong AgentGuard Server...
echo.
python "%~dp0server.py"

pause
