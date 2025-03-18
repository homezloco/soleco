@echo off
echo Starting Soleco development environment...

REM Get the current directory
set PROJECT_DIR=%~dp0

REM Start the backend in WSL (in a new terminal)
echo Starting backend server in WSL...
start wt wsl -d Ubuntu -e bash -c "cd /mnt/c/Users/Shane\ Holmes/CascadeProjects/windsurf-project/soleco/backend && ./restart_server.sh && bash"

REM Wait a moment for the backend to start
echo Waiting for backend to start...
timeout /t 5

REM Start the frontend
echo Starting frontend...
cd "%PROJECT_DIR%frontend"
call start_frontend.bat
