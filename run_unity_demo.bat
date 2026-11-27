@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_unity_demo.ps1"
if errorlevel 1 (
    echo.
    echo No se pudo iniciar la demostracion. Revisa el mensaje anterior.
    pause
)
