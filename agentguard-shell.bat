@echo off
:: Store original COMSPEC shell path before we intercept it
if "%ORIGINAL_COMSPEC%"=="" (
    set ORIGINAL_COMSPEC=%COMSPEC%
)
python "%~dp0shell_interceptor.py" %*
