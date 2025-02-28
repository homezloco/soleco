# Run the RPC improvements verification script

Write-Host "Verifying RPC improvements..." -ForegroundColor Green
python (Join-Path -Path $PSScriptRoot -ChildPath "verify_rpc_improvements.py")

Write-Host "`nVerification complete. Results saved to rpc_improvements_verification.json" -ForegroundColor Green

Write-Host "`nPress any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
