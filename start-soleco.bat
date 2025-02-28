@echo off
echo ===== Soleco Development Environment Starter =====

:: Define ports
set FRONTEND_PORT=5181
set BACKEND_PORT=8001

echo.
echo Checking for processes using port %FRONTEND_PORT%...

:: Find and kill processes using frontend port
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') DO (
  echo Found process %%P using port %FRONTEND_PORT%. Killing process...
  taskkill /F /PID %%P
  timeout /t 1 /nobreak > nul
  echo Process killed.
)

:: Check if backend is running
echo.
echo Checking if backend server is running on port %BACKEND_PORT%...
netstat -ano | findstr :%BACKEND_PORT% | findstr LISTENING > nul
if errorlevel 1 (
  echo Backend server is not running. Starting backend server...
  start "Soleco Backend" wsl -- cd /mnt/c/Users/Shane\ Holmes/CascadeProjects/windsurf-project/soleco/backend && python -m app.main
  echo Backend server started.
  echo Waiting for backend to initialize...
  timeout /t 5 /nobreak > nul
) else (
  echo Backend server is already running on port %BACKEND_PORT%.
)

:: Start the frontend development server
echo.
echo Starting frontend development server on port %FRONTEND_PORT%...
cd frontend
start "Soleco Frontend" wsl -- cd /mnt/c/Users/Shane\ Holmes/CascadeProjects/windsurf-project/soleco/frontend && npm run dev

echo.
echo Soleco development environment is now running:
echo - Frontend: http://localhost:%FRONTEND_PORT%
echo - Backend: http://localhost:%BACKEND_PORT%/api
echo.
echo Press any key to shut down all Soleco services...
pause > nul

:: Shutdown services
echo.
echo Shutting down Soleco services...

:: Kill frontend processes
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') DO (
  echo Stopping frontend process %%P...
  taskkill /F /PID %%P
)

:: Kill backend processes
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :%BACKEND_PORT% ^| findstr LISTENING') DO (
  echo Stopping backend process %%P...
  taskkill /F /PID %%P
)

echo.
echo Soleco services have been shut down.
echo.
