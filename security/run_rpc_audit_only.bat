@echo off
REM Run only the RPC verification tools without the other audit modules

echo Running RPC verification audit...

REM Run the mock RPC verification
echo Running mock RPC verification...
python mock_rpc_verification.py
echo.

REM Run a detailed mock RPC verification
echo Running detailed mock RPC verification...
python mock_rpc_verification.py --detailed --output mock_rpc_detailed_verification.json
echo.

echo All RPC verification complete. Reports saved to:
echo - mock_rpc_verification.json
echo - mock_rpc_detailed_verification.json

pause
