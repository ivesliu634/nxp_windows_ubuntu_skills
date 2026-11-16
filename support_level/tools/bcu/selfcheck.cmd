@echo off
REM No-board self-check for the bcu skill package.
REM Confirms bin\bcu.exe exists and runs (version + lsboard), without a board attached.
REM Paths are resolved relative to this script's own directory, so the package is portable.
REM Exit code 0 means the tool binary is usable; 1 means a failure was detected.
setlocal
set "SKILL_DIR=%~dp0"
set "BCU=%SKILL_DIR%bin\bcu.exe"

echo == bcu no-board self-check ==

if not exist "%BCU%" (
    echo FAIL: bcu.exe not found at "%BCU%"
    echo RESULT HAS_FAILURES
    exit /b 1
)
echo FOUND "%BCU%"

echo.
echo -- bcu version --
"%BCU%" version
if errorlevel 1 (
    echo FAIL: bcu version returned non-zero
    echo RESULT HAS_FAILURES
    exit /b 1
)

echo.
echo -- bcu lsboard (list supported board models) --
"%BCU%" lsboard
if errorlevel 1 (
    echo FAIL: bcu lsboard returned non-zero
    echo RESULT HAS_FAILURES
    exit /b 1
)

echo.
echo RESULT ALL_GOOD
echo (tool binary is usable; this does NOT require a board to be connected)
endlocal
exit /b 0
