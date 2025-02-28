# Run only the RPC verification tools without the other audit modules

Write-Host "Running RPC verification audit..." -ForegroundColor Green

# Run the mock RPC verification
Write-Host "Running mock RPC verification..." -ForegroundColor Yellow
python (Join-Path -Path $PSScriptRoot -ChildPath "mock_rpc_verification.py")
Write-Host ""

# Run a detailed mock RPC verification
Write-Host "Running detailed mock RPC verification..." -ForegroundColor Yellow
python (Join-Path -Path $PSScriptRoot -ChildPath "mock_rpc_verification.py") --detailed --output mock_rpc_detailed_verification.json
Write-Host ""

Write-Host "All RPC verification complete. Reports saved to:" -ForegroundColor Green
Write-Host "- mock_rpc_verification.json" -ForegroundColor Cyan
Write-Host "- mock_rpc_detailed_verification.json" -ForegroundColor Cyan

Write-Host "`nPress any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
