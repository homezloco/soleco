# Optimize the performance of security audits

Write-Host "Analyzing codebase structure to optimize audit performance..." -ForegroundColor Green

# Get the current directory
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Run the optimization script
python "$currentDir\optimize_audit_performance.py"

Write-Host "`nOptimization complete. See audit_config.json for the configuration." -ForegroundColor Green

# Ask if the user wants to update the audit scripts to use the new configuration
$updateScripts = Read-Host "Do you want to update the audit scripts to use the new configuration? (y/n)"
if ($updateScripts -eq "y" -or $updateScripts -eq "Y") {
    Write-Host "Updating audit scripts to use the new configuration..." -ForegroundColor Yellow
    
    # Update the transaction validation audit script
    $transactionAuditPath = Join-Path -Path $currentDir -ChildPath "test_transaction_validation_audit.py"
    if (Test-Path $transactionAuditPath) {
        $content = Get-Content $transactionAuditPath -Raw
        if ($content -notmatch "load_config") {
            $content = $content -replace "def main\(\):", "def load_config():`n    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audit_config.json')`n    if os.path.exists(config_path):`n        with open(config_path, 'r') as f:`n            return json.load(f)`n    return None`n`ndef main():"
            $content = $content -replace "findings = run_transaction_validation_audit\(backend_dir\)", "config = load_config()`n    if config and 'audit_modules' in config and 'transaction_validation' in config['audit_modules']:`n        module_config = config['audit_modules']['transaction_validation']`n        include_dirs = [os.path.join(backend_dir, d) for d in module_config['include_dirs']]`n        exclude_dirs = [os.path.join(backend_dir, d) for d in module_config['exclude_dirs']]`n        timeout = module_config.get('timeout', 120)`n        findings = run_transaction_validation_audit(backend_dir, include_dirs=include_dirs, exclude_dirs=exclude_dirs, timeout=timeout)`n    else:`n        findings = run_transaction_validation_audit(backend_dir)"
            Set-Content -Path $transactionAuditPath -Value $content
            Write-Host "Updated $transactionAuditPath" -ForegroundColor Green
        } else {
            Write-Host "$transactionAuditPath already uses configuration" -ForegroundColor Yellow
        }
    }
    
    # Update the Solana security audit script
    $solanaAuditPath = Join-Path -Path $currentDir -ChildPath "test_solana_security_audit.py"
    if (Test-Path $solanaAuditPath) {
        $content = Get-Content $solanaAuditPath -Raw
        if ($content -notmatch "load_config") {
            $content = $content -replace "def main\(\):", "def load_config():`n    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audit_config.json')`n    if os.path.exists(config_path):`n        with open(config_path, 'r') as f:`n            return json.load(f)`n    return None`n`ndef main():"
            $content = $content -replace "findings = run_solana_security_audit\(backend_dir\)", "config = load_config()`n    if config and 'audit_modules' in config and 'solana_security' in config['audit_modules']:`n        module_config = config['audit_modules']['solana_security']`n        include_dirs = [os.path.join(backend_dir, d) for d in module_config['include_dirs']]`n        exclude_dirs = [os.path.join(backend_dir, d) for d in module_config['exclude_dirs']]`n        timeout = module_config.get('timeout', 120)`n        findings = run_solana_security_audit(backend_dir, include_dirs=include_dirs, exclude_dirs=exclude_dirs, timeout=timeout)`n    else:`n        findings = run_solana_security_audit(backend_dir)"
            Set-Content -Path $solanaAuditPath -Value $content
            Write-Host "Updated $solanaAuditPath" -ForegroundColor Green
        } else {
            Write-Host "$solanaAuditPath already uses configuration" -ForegroundColor Yellow
        }
    }
    
    Write-Host "Audit scripts updated to use the new configuration." -ForegroundColor Green
}
