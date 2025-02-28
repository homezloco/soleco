@echo off
REM Install the pre-commit hook for Soleco security checks

echo Installing pre-commit hook for Soleco security checks...

REM Get the git root directory
for /f "tokens=*" %%a in ('git rev-parse --show-toplevel') do set GIT_ROOT=%%a

REM Check if the git root was found
if "%GIT_ROOT%"=="" (
    echo Error: Not in a git repository
    exit /b 1
)

REM Create the hooks directory if it doesn't exist
if not exist "%GIT_ROOT%\.git\hooks" (
    mkdir "%GIT_ROOT%\.git\hooks"
)

REM Copy the pre-commit hook
copy /Y "%~dp0pre-commit-hook.py" "%GIT_ROOT%\.git\hooks\pre-commit"

REM Make sure the pre-commit hook is executable (not needed on Windows, but for completeness)
echo @echo off > "%GIT_ROOT%\.git\hooks\pre-commit.bat"
echo python "%GIT_ROOT%\.git\hooks\pre-commit" %%* >> "%GIT_ROOT%\.git\hooks\pre-commit.bat"

echo Pre-commit hook installed successfully.
echo To test it, try making a commit with a security issue.

REM Install required dependencies
echo Installing required dependencies...
pip install bandit safety

echo Done!
