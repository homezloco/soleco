@echo off
REM Check for Solana-specific RPC error handling issues

echo Checking for Solana RPC error handling issues...
python check_solana_rpc_errors.py

echo.
echo Check complete. See solana_rpc_errors_report.json for results.
pause
