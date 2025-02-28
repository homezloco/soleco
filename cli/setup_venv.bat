@echo off
REM Setup script for Soleco CLI development environment
REM This script creates a virtual environment and installs dependencies

echo Setting up Soleco CLI development environment...

REM Check if Python is installed
python --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

REM Activate virtual environment and install dependencies
echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
pip install -e ".[dev]"

echo.
echo Setup complete! You can now use the Soleco CLI.
echo.
echo To activate the virtual environment in the future, run:
echo   venv\Scripts\activate.bat
echo.
echo To run the CLI in development mode:
echo   python -m soleco_cli.cli
echo.
echo To run tests:
echo   python run_tests.py
echo.

REM Keep the virtual environment active
echo Virtual environment is now active.
