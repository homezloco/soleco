@echo off
echo Checking for processes using port 5181...

:: Find and kill processes using port 5181
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :5181 ^| findstr LISTENING') DO (
  echo Found process %%P using port 5181. Killing process...
  taskkill /F /PID %%P
  timeout /t 1 /nobreak > nul
  echo Process killed.
)

:: Start the development server using WSL
echo Starting development server on port 5181...
wsl -- cd /mnt/c/Users/Shane\ Holmes/CascadeProjects/windsurf-project/soleco/frontend && bash ./start-dev.sh
