@echo off
echo ===== Soleco Services Restart Script =====

:: Define ports
set FRONTEND_PORT=5181
set BACKEND_PORT=8001

echo Checking for processes using ports %FRONTEND_PORT% and %BACKEND_PORT%...

:: Kill frontend processes
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') DO (
  echo Found process %%P using port %FRONTEND_PORT%. Killing process...
  taskkill /F /PID %%P
  timeout /t 1 /nobreak > nul
  echo Frontend process killed.
)

:: Kill backend processes
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :%BACKEND_PORT% ^| findstr LISTENING') DO (
  echo Found process %%P using port %BACKEND_PORT%. Killing process...
  taskkill /F /PID %%P
  timeout /t 1 /nobreak > nul
  echo Backend process killed.
)

:: Start backend
echo Starting backend service on port %BACKEND_PORT%...
start cmd /k "cd /d %~dp0backend && python -m app.main"

:: Wait for backend to initialize
echo Waiting for backend to initialize...
timeout /t 5 /nobreak > nul

:: Start frontend
echo Starting frontend development server on port %FRONTEND_PORT%...
start cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Services restarted successfully!
echo Backend running on http://localhost:%BACKEND_PORT%
echo Frontend running on http://localhost:%FRONTEND_PORT%
echo.
echo Press any key to exit this script...
pause > nul
