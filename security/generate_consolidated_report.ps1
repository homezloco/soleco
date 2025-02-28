# Generate a consolidated security report from all individual reports

Write-Host "Generating consolidated security report..." -ForegroundColor Green

# Get the current directory
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Run the report generator
python "$currentDir\generate_consolidated_report.py"

Write-Host "`nReport generation complete." -ForegroundColor Green

# Open the report if the user wants to
$openReport = Read-Host "Do you want to view the HTML report now? (y/n)"
if ($openReport -eq "y" -or $openReport -eq "Y") {
    $reportPath = Join-Path -Path $currentDir -ChildPath "consolidated_security_report.html"
    if (Test-Path $reportPath) {
        Start-Process $reportPath
    } else {
        Write-Host "Report file not found: $reportPath" -ForegroundColor Red
    }
}
