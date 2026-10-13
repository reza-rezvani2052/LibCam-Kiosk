@echo off
setlocal

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
pushd "%PROJECT_ROOT%" || exit /b 1
set "CLEANUP_FAILED=0"

REM Delete the generated Qt resource module.
if exist "resources_rc.py" (
    del /q "resources_rc.py"
    if errorlevel 1 (
        echo Failed to delete: resources_rc.py
        set "CLEANUP_FAILED=1"
    ) else (
        echo Deleted: resources_rc.py
    )
)

REM Delete generated Qt UI modules only from their current project directories.
for %%D in (app\ui\main_window app\ui\common) do (
    if exist "%%D" (
        for %%F in ("%%D\ui_*.py") do (
            if exist "%%~F" (
                del /q "%%~F"
                if errorlevel 1 (
                    echo Failed to delete: %%~F
                    set "CLEANUP_FAILED=1"
                ) else (
                    echo Deleted: %%~F
                )
            )
        )
    )
)

REM Remove root-level Python bytecode cache, if present.
if exist "__pycache__" (
    rmdir /s /q "__pycache__"
    if errorlevel 1 (
        echo Failed to delete: __pycache__
        set "CLEANUP_FAILED=1"
    ) else (
        echo Deleted: __pycache__
    )
)

REM Use PowerShell to find all nested __pycache__ directories reliably.
REM Search only project-owned directories; intentionally exclude .venv and dependencies.
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference = 'Stop'; $failed = $false;" ^
    "foreach ($root in @('app', 'build_tools', 'data', 'docs', 'resources', 'scripts', 'tests', 'tools')) {" ^
    "  if (Test-Path -LiteralPath $root -PathType Container) {" ^
    "    try {" ^
    "      $caches = @(Get-ChildItem -LiteralPath $root -Directory -Filter '__pycache__' -Recurse -Force -ErrorAction Stop | Sort-Object { $_.FullName.Length } -Descending);" ^
    "      foreach ($cache in $caches) {" ^
    "        try { Remove-Item -LiteralPath $cache.FullName -Recurse -Force -ErrorAction Stop; Write-Output ('Deleted: ' + $cache.FullName) }" ^
    "        catch { [Console]::Error.WriteLine('Failed to delete: ' + $cache.FullName + ' - ' + $_.Exception.Message); $failed = $true }" ^
    "      }" ^
    "    } catch { [Console]::Error.WriteLine('Failed while searching ' + $root + ': ' + $_.Exception.Message); $failed = $true }" ^
    "  }" ^
    "}" ^
    "if ($failed) { exit 1 } else { exit 0 }"
if errorlevel 1 (
    echo Failed to remove one or more nested __pycache__ directories.
    set "CLEANUP_FAILED=1"
)

echo.
if "%CLEANUP_FAILED%"=="0" (
    echo Cleanup completed.
) else (
    echo Cleanup finished with errors.
)

pause
popd
endlocal & exit /b %CLEANUP_FAILED%
