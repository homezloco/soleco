# Run a quick security audit

Write-Host "Running quick security audit..." -ForegroundColor Green

# Get the current directory
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Run the quick audit
python "$currentDir\quick_security_audit.py"

Write-Host "`nAudit complete. See quick_security_audit_report.json for results." -ForegroundColor Green

# Ask if the user wants to open the report
$openReport = Read-Host "Do you want to view the report now? (y/n)"
if ($openReport -eq "y" -or $openReport -eq "Y") {
    $reportPath = Join-Path -Path $currentDir -ChildPath "quick_security_audit_report.json"
    if (Test-Path $reportPath) {
        # Open the report in the default JSON viewer
        Start-Process $reportPath
    } else {
        Write-Host "Report file not found: $reportPath" -ForegroundColor Red
    }
}
