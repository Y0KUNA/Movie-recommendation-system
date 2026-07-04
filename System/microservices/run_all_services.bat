@echo off
REM Batch script to run all microservices on Windows
REM Usage: run_all_services.bat

setlocal enabledelayedexpansion

REM Check if running in the correct directory
if not exist "api-gateway" (
    echo Error: Please run this script from the microservices directory
    exit /b 1
)

echo Starting all microservices...
echo.

REM Create separate terminal windows for each service
echo Starting Movie Service on port 5001...
start "Movie Service" cmd /k "cd movie-service && pip install -r requirements.txt && python app.py"

timeout /t 3 /nobreak

echo Starting Vector Service on port 5003...
start "Vector Service" cmd /k "cd vector-service && pip install -r requirements.txt && python app.py"

timeout /t 3 /nobreak

echo Starting Recommendation Service on port 5002...
start "Recommendation Service" cmd /k "cd recommendation-service && pip install -r requirements.txt && python app.py"

timeout /t 3 /nobreak

echo Starting User Service on port 5004...
start "User Service" cmd /k "cd user-service && pip install -r requirements.txt && python app.py"

timeout /t 3 /nobreak

echo Starting API Gateway on port 5000...
start "API Gateway" cmd /k "cd api-gateway && pip install -r requirements.txt && python app.py"

timeout /t 2 /nobreak

echo.
echo All services are starting...
echo.
echo Services URLs:
echo - API Gateway: http://localhost:5000
echo - Movie Service: http://localhost:5001
echo - Recommendation Service: http://localhost:5002
echo - Vector Service: http://localhost:5003
echo - User Service: http://localhost:5004
echo.
echo Check service health: http://localhost:5000/health/services
echo.
pause
