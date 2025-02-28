# Run all security audits and generate a combined report

Write-Host "Running comprehensive security audit..." -ForegroundColor Green

# Set the path to the backend directory
$BACKEND_DIR = Join-Path -Path $PSScriptRoot -ChildPath "..\backend"

# Optimize audit performance first
Write-Host "Optimizing audit performance..." -ForegroundColor Yellow
python (Join-Path -Path $PSScriptRoot -ChildPath "optimize_audit_performance.py")
Write-Host ""

# Run the quick security audit
Write-Host "Running quick security audit..." -ForegroundColor Yellow
python (Join-Path -Path $PSScriptRoot -ChildPath "quick_security_audit.py")
Write-Host ""

# Run the quick RPC verification
Write-Host "Running quick RPC verification..." -ForegroundColor Yellow
python (Join-Path -Path $PSScriptRoot -ChildPath "quick_rpc_verification.py")
Write-Host ""

# Run the comprehensive audit
python (Join-Path -Path $PSScriptRoot -ChildPath "run_comprehensive_audit.py") --codebase-path $BACKEND_DIR --output-report comprehensive_audit_report.json --html --verbose

Write-Host "`nSecurity audit complete. Report saved to comprehensive_audit_report.json and comprehensive_audit_report.html" -ForegroundColor Green

Write-Host "`nRunning specific audit modules for detailed reports..." -ForegroundColor Green

# Run RPC error handling audit
python (Join-Path -Path $PSScriptRoot -ChildPath "test_rpc_error_handling_audit.py")
Write-Host ""

# Run blockchain security audit
python (Join-Path -Path $PSScriptRoot -ChildPath "test_blockchain_security_audit.py")
Write-Host ""

# Run transaction validation audit
python (Join-Path -Path $PSScriptRoot -ChildPath "test_transaction_validation_audit.py")
Write-Host ""

# Run Solana security audit
python (Join-Path -Path $PSScriptRoot -ChildPath "test_solana_security_audit.py")
Write-Host ""

# Verify RPC improvements
python (Join-Path -Path $PSScriptRoot -ChildPath "verify_rpc_improvements.py")
Write-Host ""

# Check Solana RPC error handling
python (Join-Path -Path $PSScriptRoot -ChildPath "check_solana_rpc_errors.py")
Write-Host ""

# Generate consolidated report
python (Join-Path -Path $PSScriptRoot -ChildPath "generate_consolidated_report.py")
Write-Host ""

Write-Host "All audits complete. Reports saved to:" -ForegroundColor Green
Write-Host "- quick_security_audit_report.json" -ForegroundColor Cyan
Write-Host "- quick_rpc_verification.json" -ForegroundColor Cyan
Write-Host "- comprehensive_audit_report.json" -ForegroundColor Cyan
Write-Host "- comprehensive_audit_report.html" -ForegroundColor Cyan
Write-Host "- rpc_error_handling_audit_report.json" -ForegroundColor Cyan
Write-Host "- blockchain_security_audit_report.json" -ForegroundColor Cyan
Write-Host "- transaction_validation_audit_report.json" -ForegroundColor Cyan
Write-Host "- solana_security_audit_report.json" -ForegroundColor Cyan
Write-Host "- solana_rpc_errors_report.json" -ForegroundColor Cyan
Write-Host "- rpc_improvements_verification.json" -ForegroundColor Cyan
Write-Host "- consolidated_security_report.json" -ForegroundColor Cyan
Write-Host "- consolidated_security_report.html" -ForegroundColor Cyan

Write-Host "`nTo view the consolidated HTML report, open consolidated_security_report.html in a web browser." -ForegroundColor Yellow

# Open the HTML report if the user wants to
$openReport = Read-Host "Do you want to open the consolidated HTML report now? (y/n)"
if ($openReport -eq "y" -or $openReport -eq "Y") {
    $reportPath = Join-Path -Path $PSScriptRoot -ChildPath "consolidated_security_report.html"
    if (Test-Path $reportPath) {
        Start-Process $reportPath
    } else {
        Write-Host "Report file not found: $reportPath" -ForegroundColor Red
    }
}
