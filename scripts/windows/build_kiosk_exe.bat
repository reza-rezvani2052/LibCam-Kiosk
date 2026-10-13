@echo off
setlocal

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
pushd "%PROJECT_ROOT%" || exit /b 1

set "PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

"%PYTHON%" tools\build\build_kiosk_exe.py
set "EXIT_CODE=%ERRORLEVEL%"

pause
popd
exit /b %EXIT_CODE%
