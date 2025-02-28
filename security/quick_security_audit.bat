@echo off
REM Run a quick security audit

echo Running quick security audit...
python quick_security_audit.py

echo.
echo Audit complete. See quick_security_audit_report.json for results.
pause
