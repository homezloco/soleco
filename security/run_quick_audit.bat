@echo off
REM Run a quick security audit on transaction validation

echo Running quick transaction validation audit...
python quick_transaction_audit.py

echo.
echo Audit complete. Check quick_transaction_audit_report.json for results.
pause
