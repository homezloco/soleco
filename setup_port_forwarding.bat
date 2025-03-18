@echo off
echo Setting up port forwarding from Windows to WSL...

REM Get the WSL IP address
FOR /F "tokens=*" %%g IN ('wsl -e bash -c "ip addr show eth0 ^| grep -oP \"(?<=inet\s)\d+(\.\d+){3}\""') do (SET WSL_IP=%%g)
echo WSL IP address: %WSL_IP%

REM Add port forwarding from Windows localhost:8001 to WSL IP:8001
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=127.0.0.1 connectport=8001 connectaddress=%WSL_IP%

REM Show the current port forwarding configuration
echo Current port forwarding configuration:
netsh interface portproxy show all

echo Port forwarding has been set up. You can now access your WSL services at localhost:8001
pause
