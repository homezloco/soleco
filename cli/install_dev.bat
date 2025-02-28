@echo off
REM Install the Soleco CLI in development mode
echo Installing Soleco CLI in development mode...

REM Install the package in development mode with dev dependencies
pip install -e ".[dev]"

echo.
echo Installation complete!
echo You can now use the Soleco CLI by running:
echo   soleco --help
echo.
echo To run tests:
echo   python run_tests.py
echo.
