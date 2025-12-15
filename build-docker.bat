@echo off
chcp 65001 >nul
REM Docker Build Script for Windows

echo ==========================================
echo   Telegram ImageBed - Docker Build
echo ==========================================
echo.

REM Check .env file
if not exist .env (
    echo [WARNING] .env file not found
    echo Please create .env file first
    echo Reference: .env.example
    pause
    exit /b 1
)

REM Build frontend
echo [1/5] Building frontend...
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        cd ..
        pause
        exit /b 1
    )
)
echo Building frontend...
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed
    cd ..
    pause
    exit /b 1
)
cd ..
echo [OK] Frontend build completed
echo.

REM Build Docker image
echo [2/5] Building Docker image...
docker build -t telegram-imagebed:latest .
if errorlevel 1 (
    echo [ERROR] Docker image build failed
    pause
    exit /b 1
)
echo [OK] Docker image build completed
echo.

REM Stop old container
echo [3/5] Stopping old container...
docker stop telegram-imagebed 2>nul
docker rm telegram-imagebed 2>nul
echo [OK] Old container cleaned
echo.

REM Start new container
echo [4/5] Starting new container...
docker-compose -p telegram-imagebed up -d
if errorlevel 1 (
    echo [ERROR] Failed to start container
    pause
    exit /b 1
)
echo [OK] Container started successfully
echo.

REM Show container status
echo [5/5] Container status:
docker-compose -p telegram-imagebed ps
echo.

echo ==========================================
echo   Build and Deploy Completed!
echo ==========================================
echo.
echo Access URL: http://localhost:18793
echo Admin Panel: http://localhost:18793/admin
echo.
echo View logs: docker-compose -p telegram-imagebed logs -f
echo Stop container: docker-compose -p telegram-imagebed stop
echo.


pause
