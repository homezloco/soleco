@echo off
echo Checking for processes using port 5181...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5181') do (
    echo Killing process with PID %%a
    taskkill /F /PID %%a
)
echo Starting frontend in debug mode...
cd /d "%~dp0"
set NODE_OPTIONS=--inspect
npm run dev
pause
