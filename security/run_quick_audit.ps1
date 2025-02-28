# Run a quick security audit on transaction validation

Write-Host "Running quick transaction validation audit..." -ForegroundColor Green

# Get the current directory
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Run the quick audit script
python "$currentDir\quick_transaction_audit.py"

Write-Host "`nAudit complete. Check quick_transaction_audit_report.json for results." -ForegroundColor Green

# Open the report if the user wants to
$openReport = Read-Host "Do you want to view the report now? (y/n)"
if ($openReport -eq "y" -or $openReport -eq "Y") {
    $reportPath = Join-Path -Path $currentDir -ChildPath "quick_transaction_audit_report.json"
    if (Test-Path $reportPath) {
        # Try to open with a JSON viewer if available, otherwise use notepad
        try {
            Start-Process $reportPath
        } catch {
            notepad $reportPath
        }
    } else {
        Write-Host "Report file not found: $reportPath" -ForegroundColor Red
    }
}
