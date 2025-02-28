@echo off
REM Generate a consolidated security report from all individual reports

echo Generating consolidated security report...
python generate_consolidated_report.py

echo.
echo Report generation complete.

REM Ask if the user wants to open the HTML report
set /p open_report=Do you want to open the HTML report now? (y/n): 
if /i "%open_report%"=="y" (
    start consolidated_security_report.html
)

pause
