@echo off
echo Checking for processes using port 5181...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5181') do (
    echo Killing process with PID %%a
    taskkill /F /PID %%a 2>nul
)
echo Starting frontend with original configuration...
cd /d "%~dp0"
npm run dev
pause
