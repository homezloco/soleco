@echo off
echo Starting Soleco frontend...

REM Get the current directory
set FRONTEND_DIR=%~dp0

REM Update the configuration with the WSL IP
echo Updating configuration with WSL IP...
cd "%FRONTEND_DIR%"
node get_wsl_ip.js

REM Start the frontend
echo Starting frontend...
npm run dev
