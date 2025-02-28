# Run the quick RPC improvements verification script

Write-Host "Running quick RPC improvements verification..." -ForegroundColor Green
python (Join-Path -Path $PSScriptRoot -ChildPath "quick_rpc_verification.py")

Write-Host "`nVerification complete. Results saved to quick_rpc_verification.json" -ForegroundColor Green

Write-Host "`nPress any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
