@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set IMAGE_NAME=lost4/tg-telegram-imagebed
set TAG=latest
set PLATFORMS=linux/amd64,linux/arm64
set BUILDER_NAME=multiarch-builder

echo =========================================
echo Multi-arch Docker build script
echo =========================================
echo Image: %IMAGE_NAME%:%TAG%
echo Platforms: %PLATFORMS%
echo.

REM Check buildx is available
docker buildx version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] docker buildx not available. Start Docker Desktop first.
    pause
    exit /b 1
)

REM Check and create builder
echo Setting up buildx builder...
docker buildx inspect %BUILDER_NAME% >nul 2>&1
if errorlevel 1 (
    echo Creating new buildx builder...
    docker buildx create --name %BUILDER_NAME% --driver docker-container --use
) else (
    echo Using existing buildx builder...
    docker buildx use %BUILDER_NAME%
)

echo.
echo Building multi-arch image...
echo.

REM Build and push
docker buildx build --platform %PLATFORMS% -t %IMAGE_NAME%:%TAG% --push --file Dockerfile .

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo =========================================
echo Build complete
echo =========================================
echo docker pull %IMAGE_NAME%:%TAG%
echo.

pause
endlocal
