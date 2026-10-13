@echo off
setlocal

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
pushd "%PROJECT_ROOT%" || exit /b 1
set "PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Virtual environment not found: %PYTHON%
    echo.
    echo Run the following commands first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    popd
    endlocal
    exit /b 1
)

echo Preparing generated UI/QRC modules...
"%PYTHON%" tools\build\build_qml_resources.py
set "PREPARE_EXIT_CODE=%ERRORLEVEL%"
if not "%PREPARE_EXIT_CODE%"=="0" (
    echo.
    echo Failed to prepare generated UI/QRC modules.
    pause
    popd
    endlocal & exit /b %PREPARE_EXIT_CODE%
)

"%PYTHON%" kiosk_main.py %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Application exited with error code %EXIT_CODE%.
)
pause
popd
endlocal & exit /b %EXIT_CODE%
