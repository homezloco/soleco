@echo off
REM Run the RPC improvements verification script

echo Verifying RPC improvements...
python verify_rpc_improvements.py

echo.
echo Verification complete. Results saved to rpc_improvements_verification.json

pause
