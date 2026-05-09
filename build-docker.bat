@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM Windows launcher for build-docker.sh

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "SCRIPT_SH=%SCRIPT_DIR%\build-docker.sh"

echo =========================================
echo Docker build launcher
echo =========================================
echo.

if not exist "%SCRIPT_SH%" (
    echo [ERROR] Script not found: "%SCRIPT_SH%"
    goto :fail
)

set "GIT_BASH="
for %%I in (
    "%ProgramFiles%\Git\bin\bash.exe"
    "%ProgramFiles%\Git\usr\bin\bash.exe"
    "%LocalAppData%\Programs\Git\bin\bash.exe"
    "%LocalAppData%\Programs\Git\usr\bin\bash.exe"
) do (
    if exist "%%~I" set "GIT_BASH=%%~I"
)

if defined GIT_BASH (
    echo [INFO] Using Git Bash
    echo [INFO] Bash: "%GIT_BASH%"
    echo.
    call "%GIT_BASH%" -lc "docker version >/dev/null 2>&1"
    if errorlevel 1 (
        echo [WARN] Docker is not available in Git Bash, trying WSL...
    ) else (
        if /I "%DOCKER_LAUNCHER_DRY_RUN%"=="1" (
        echo [DRY-RUN] Skipped actual execution
        goto :success
    )
    pushd "%SCRIPT_DIR%"
    call "%GIT_BASH%" -lc "./build-docker.sh"
    set "RUN_EXIT=!ERRORLEVEL!"
    popd
    if not "!RUN_EXIT!"=="0" goto :runner_fail
    goto :success
    )
)

where.exe wsl.exe >nul 2>&1
if not errorlevel 1 (
    for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$p=[System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath('%SCRIPT_SH%')); $drive=$p.Substring(0,1).ToLower(); $rest=$p.Substring(2).Replace('\\','/'); Write-Output ('/mnt/' + $drive + $rest)"`) do set "WSL_DIR=%%I"
    if not defined WSL_DIR (
        echo [ERROR] Failed to convert the repository path for WSL
        goto :fail
    )
    echo [INFO] Using WSL
    echo [INFO] WSL dir: "%WSL_DIR%"
    echo.
    wsl.exe docker version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker is not available in WSL. Start Docker Desktop first.
        goto :fail
    )
    if /I "%DOCKER_LAUNCHER_DRY_RUN%"=="1" (
        echo [DRY-RUN] Skipped actual execution
        goto :success
    )
    wsl.exe bash -lc "cd '%WSL_DIR%' && ./build-docker.sh"
    if errorlevel 1 goto :runner_fail
    goto :success
)

echo [ERROR] Neither Git Bash nor WSL was found
echo [HINT] Install Git for Windows or enable WSL and try again
goto :fail

:runner_fail
echo.
echo [ERROR] build-docker.sh failed
goto :fail

:success
echo.
echo [OK] Launcher finished
endlocal
exit /b 0

:fail
echo.
pause
endlocal
exit /b 1
