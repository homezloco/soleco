# PowerShell script to set up port forwarding from Windows to WSL
# This script needs to be run as Administrator

# Get the WSL IP address
$wslIP = bash -c "ip addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'"
Write-Host "WSL IP address: $wslIP"

# Remove any existing port forwarding for port 8001
netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=127.0.0.1

# Add port forwarding from Windows localhost:8001 to WSL IP:8001
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=127.0.0.1 connectport=8001 connectaddress=$wslIP

# Show the current port forwarding configuration
Write-Host "Current port forwarding configuration:"
netsh interface portproxy show all

Write-Host "Port forwarding has been set up. You can now access your WSL services at localhost:8001"
