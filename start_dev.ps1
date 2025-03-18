# PowerShell script to start the development environment
# This script will start both the backend and frontend

Write-Host "Starting Soleco development environment..."

# 1. Run the setup script to ensure port forwarding is set up
Write-Host "Setting up port forwarding..."
Start-Process powershell -ArgumentList "-File `"$PSScriptRoot\setup_dev_environment.ps1`"" -Verb RunAs -Wait

# 2. Start the backend in WSL (in a new terminal)
Write-Host "Starting backend server in WSL..."
Start-Process wt -ArgumentList "wsl -d Ubuntu -e bash -c `"cd /mnt/c/Users/Shane\ Holmes/CascadeProjects/windsurf-project/soleco/backend && ./restart_server.sh && bash`""

# 3. Wait a moment for the backend to start
Write-Host "Waiting for backend to start..."
Start-Sleep -Seconds 5

# 4. Start the frontend
Write-Host "Starting frontend..."
Set-Location -Path "$PSScriptRoot\frontend"
npm run dev
