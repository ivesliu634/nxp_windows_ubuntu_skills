@echo off
REM ---------------------------------------------------------------------------
REM fetch-bcu.cmd - make sure bcu.exe is present in this bin/ directory.
REM
REM bcu.exe is a third-party binary released by NXP on GitHub. It is NOT
REM redistributed inside this skill package; each user provides it. This script
REM is a CONVENIENCE downloader, not the only way to get it - GitHub access can
REM be blocked by corporate proxies/firewalls, so if the download fails this
REM script tells you exactly how to grab bcu.exe by hand and where to drop it.
REM
REM Logic:
REM   - If bin\bcu.exe already exists and runs, do nothing (skip download).
REM     Pass -force (or a specific <tag>) to re-download anyway.
REM   - Otherwise try to download from the official releases.
REM   - If the download fails for any reason, print manual-download instructions
REM     and exit non-zero (does NOT pretend it succeeded).
REM
REM Usage:
REM   fetch-bcu.cmd            ensure bcu.exe exists (download only if missing)
REM   fetch-bcu.cmd -force     re-download the LATEST release even if present
REM   fetch-bcu.cmd <tag>      download a specific release tag, e.g. bcu_1.1.128
REM                            (implies -force)
REM
REM Requirements: curl (built into Windows 10/11) and internet access to GitHub.
REM ---------------------------------------------------------------------------
setlocal
REM Capture the script directory NOW: the arg-parse loop below uses shift,
REM which moves %0 too, so %~dp0 must not be relied on after that point.
set "HERE=%~dp0"
set "REPO=nxp-imx/bcu"
set "OUT=%HERE%bcu.exe"
set "TMP=%HERE%bcu.exe.download"
set "RELEASES=https://github.com/%REPO%/releases"


REM --- parse args: -force flag and/or a release tag ---------------------------
set "FORCE=0"
set "TAG="
:parse
if "%~1"=="" goto after_parse
if /i "%~1"=="-force" (set "FORCE=1") else (set "TAG=%~1" & set "FORCE=1")
shift
goto parse
:after_parse

REM --- if already present and not forcing, skip -------------------------------
if "%FORCE%"=="0" if exist "%OUT%" (
    echo bcu.exe already present: %OUT%
    "%OUT%" version >nul 2>&1
    if not errorlevel 1 (
        echo It runs OK. Skipping download. Use -force to re-download.
        endlocal & exit /b 0
    )
    echo WARNING: existing bcu.exe did not run cleanly; will try to re-download.
)

REM --- pick URL ---------------------------------------------------------------
if "%TAG%"=="" (
    set "URL=%RELEASES%/latest/download/bcu.exe"
    echo Fetching LATEST bcu.exe from %REPO% ...
) else (
    set "URL=%RELEASES%/download/%TAG%/bcu.exe"
    echo Fetching bcu.exe tag %TAG% from %REPO% ...
)

REM --- need curl --------------------------------------------------------------
where curl >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: curl not found on this system.
    goto manual
)

REM --- download to temp, then swap in on success ------------------------------
curl -s -L -f -o "%TMP%" "%URL%"
if errorlevel 1 (
    echo.
    echo ERROR: download failed from %URL%
    if exist "%TMP%" del "%TMP%"
    goto manual
)

REM sanity check: a real bcu.exe is a few hundred KB, not an HTML error page
for %%A in ("%TMP%") do set "SZ=%%~zA"
if %SZ% LSS 100000 (
    echo.
    echo ERROR: downloaded file is only %SZ% bytes - likely not a valid bcu.exe.
    if exist "%TMP%" del "%TMP%"
    goto manual
)

move /y "%TMP%" "%OUT%" >nul
echo Saved: %OUT%  (%SZ% bytes)
echo Verifying ...
"%OUT%" version
if errorlevel 1 (
    echo.
    echo ERROR: downloaded bcu.exe did not run. It may be corrupt or blocked.
    goto manual
)
echo.
echo Done. bcu.exe is ready at %OUT%
endlocal & exit /b 0

REM ---------------------------------------------------------------------------
:manual
echo.
echo ============================================================================
echo  Could not fetch bcu.exe automatically. Please download it MANUALLY:
echo.
echo   1. Open:  %RELEASES%
echo   2. Download the Windows asset named  bcu.exe
echo      (for a specific version pick that release, e.g. %RELEASES%/tag/bcu_1.1.128)
echo   3. Put the file here (this exact path):
echo        %HERE%bcu.exe
echo   4. Re-run this script, or run the skill self-check to verify:
echo        "%HERE%..\selfcheck.cmd"

echo.
echo  (This is normal on machines where GitHub is blocked by a proxy/firewall.)
echo ============================================================================
endlocal & exit /b 1
