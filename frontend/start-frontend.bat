@echo off
echo ===== Soleco Frontend Starter =====

:: Define frontend port
set FRONTEND_PORT=5181

echo Checking for processes using port %FRONTEND_PORT%...

:: Find and kill processes using frontend port
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') DO (
  echo Found process %%P using port %FRONTEND_PORT%. Killing process...
  taskkill /F /PID %%P
  timeout /t 1 /nobreak > nul
  echo Process killed.
)

:: Start the frontend development server
echo Starting frontend development server on port %FRONTEND_PORT%...
cd /d %~dp0
npm run dev
