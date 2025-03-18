# PowerShell script to set up the development environment
# This script needs to be run as Administrator

Write-Host "Setting up the development environment for Soleco..."

# 1. Get the WSL IP address
$wslIP = bash -c "ip addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'"
Write-Host "WSL IP address: $wslIP"

# 2. Set up port forwarding from Windows localhost:8001 to WSL IP:8001
Write-Host "Setting up port forwarding..."
# Remove any existing port forwarding for port 8001
netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=127.0.0.1
# Add port forwarding
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=127.0.0.1 connectport=8001 connectaddress=$wslIP
# Show the current port forwarding configuration
Write-Host "Current port forwarding configuration:"
netsh interface portproxy show all

Write-Host "Port forwarding has been set up. You can now access your WSL services at localhost:8001"

# 3. Verify that the backend is accessible
Write-Host "Verifying backend access..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/docs" -Method HEAD -ErrorAction Stop
    Write-Host "Backend is accessible at http://localhost:8001/docs (Status: $($response.StatusCode))"
} catch {
    Write-Host "Warning: Backend is not accessible at http://localhost:8001/docs. Make sure your backend server is running."
}

Write-Host "Development environment setup complete!"
Write-Host "You can now start your frontend with 'npm run dev' in the frontend directory."
Write-Host "Remember to run your backend server in WSL with './restart_server.sh' in the backend directory."
