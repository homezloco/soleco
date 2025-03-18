@echo off
echo Starting Soleco development environment...

REM 1. Run the setup script to ensure port forwarding is set up
echo Setting up port forwarding...
start /wait cmd /c "cd %~dp0 && setup_port_forwarding.bat"

REM 2. Start the backend in WSL (in a new terminal)
echo Starting backend server in WSL...
start wt wsl -d Ubuntu -e bash -c "cd /mnt/c/Users/Shane\ Holmes/CascadeProjects/windsurf-project/soleco/backend && ./restart_server.sh && bash"

REM 3. Wait a moment for the backend to start
echo Waiting for backend to start...
timeout /t 5

REM 4. Start the frontend
echo Starting frontend...
cd "%~dp0frontend"
npm run dev
