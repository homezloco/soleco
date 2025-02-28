@echo off
REM Run all security audits and generate a combined report

echo Running comprehensive security audit...

REM Set the path to the backend directory
set BACKEND_DIR=..\backend

REM Optimize audit performance first
echo Optimizing audit performance...
python optimize_audit_performance.py
echo.

REM Run the quick security audit
echo Running quick security audit...
python quick_security_audit.py
echo.

REM Run the quick RPC verification
echo Running quick RPC verification...
python quick_rpc_verification.py
echo.

REM Run the comprehensive audit
python run_comprehensive_audit.py --codebase-path %BACKEND_DIR% --output-report comprehensive_audit_report.json --html --verbose

echo.
echo Security audit complete. Report saved to comprehensive_audit_report.json and comprehensive_audit_report.html

echo.
echo Running specific audit modules for detailed reports...

REM Run RPC error handling audit
python test_rpc_error_handling_audit.py
echo.

REM Run blockchain security audit
python test_blockchain_security_audit.py
echo.

REM Run transaction validation audit
python test_transaction_validation_audit.py
echo.

REM Run Solana security audit
python test_solana_security_audit.py
echo.

REM Verify RPC improvements
python verify_rpc_improvements.py
echo.

REM Check Solana RPC error handling
python check_solana_rpc_errors.py
echo.

REM Generate consolidated report
python generate_consolidated_report.py
echo.

echo All audits complete. Reports saved to:
echo - quick_security_audit_report.json
echo - quick_rpc_verification.json
echo - comprehensive_audit_report.json
echo - comprehensive_audit_report.html
echo - rpc_error_handling_audit_report.json
echo - blockchain_security_audit_report.json
echo - transaction_validation_audit_report.json
echo - solana_security_audit_report.json
echo - solana_rpc_errors_report.json
echo - rpc_improvements_verification.json
echo - consolidated_security_report.json
echo - consolidated_security_report.html

echo.
echo To view the consolidated HTML report, open consolidated_security_report.html in a web browser.

REM Ask if the user wants to open the HTML report
set /p open_report=Do you want to open the consolidated HTML report now? (y/n): 
if /i "%open_report%"=="y" (
    start consolidated_security_report.html
)

pause
