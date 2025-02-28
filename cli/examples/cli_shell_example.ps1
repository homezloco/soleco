#!/usr/bin/env pwsh
# PowerShell script demonstrating how to use the Soleco CLI in shell scripts
# This script shows common CLI commands and how to process their output

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "Soleco CLI Shell Script Example" -ForegroundColor Green

# Check if soleco is installed
try {
    $version = soleco --version
    Write-Host "Using Soleco CLI version: $version" -ForegroundColor Cyan
}
catch {
    Write-Host "Error: Soleco CLI not found. Please install it first." -ForegroundColor Red
    Write-Host "Run: pip install -e ." -ForegroundColor Yellow
    exit 1
}

# Configure API URL if needed
Write-Host "`nConfiguring Soleco CLI..." -ForegroundColor Cyan
soleco set-config api_url http://localhost:8000

# Display current configuration
Write-Host "`nCurrent configuration:" -ForegroundColor Cyan
soleco config

# Get network status and save to file
Write-Host "`nFetching network status..." -ForegroundColor Cyan
soleco network status --format json --output network_status.json

# Read the JSON file and extract information
if (Test-Path network_status.json) {
    $networkStatus = Get-Content network_status.json | ConvertFrom-Json
    
    if ($networkStatus.data.status -eq "healthy") {
        Write-Host "Network is HEALTHY" -ForegroundColor Green
    } else {
        Write-Host "Network status: $($networkStatus.data.status)" -ForegroundColor Yellow
    }
    
    if ($networkStatus.data.network_summary) {
        $summary = $networkStatus.data.network_summary
        Write-Host "Total nodes: $($summary.total_nodes)" -ForegroundColor Cyan
        Write-Host "RPC nodes available: $($summary.rpc_nodes_available)" -ForegroundColor Cyan
        Write-Host "Latest version: $($summary.latest_version)" -ForegroundColor Cyan
    }
}

# List RPC nodes and save to CSV
Write-Host "`nListing RPC nodes..." -ForegroundColor Cyan
soleco rpc list --format csv --output rpc_nodes.csv

# Count the number of RPC nodes
if (Test-Path rpc_nodes.csv) {
    $rpcNodes = Import-Csv rpc_nodes.csv
    $nodeCount = $rpcNodes.Count
    Write-Host "Found $nodeCount RPC nodes" -ForegroundColor Cyan
    
    # Group by version
    $versionGroups = $rpcNodes | Group-Object -Property version
    Write-Host "`nRPC Node Versions:" -ForegroundColor Cyan
    foreach ($group in $versionGroups) {
        Write-Host "  $($group.Name): $($group.Count) nodes" -ForegroundColor White
    }
}

# Get recent mints
Write-Host "`nFetching recent mints..." -ForegroundColor Cyan
soleco mint recent --format json --output recent_mints.json

# Analyze recent mints
if (Test-Path recent_mints.json) {
    $recentMints = Get-Content recent_mints.json | ConvertFrom-Json
    
    $totalNewMints = 0
    $totalPumpTokens = 0
    
    foreach ($mint in $recentMints.data.mints) {
        $totalNewMints += $mint.new_mint_addresses.Count
        $totalPumpTokens += $mint.pump_token_addresses.Count
    }
    
    Write-Host "Total new mint addresses: $totalNewMints" -ForegroundColor Cyan
    Write-Host "Total pump tokens: $totalPumpTokens" -ForegroundColor Cyan
    
    # Display pump tokens if any
    if ($totalPumpTokens -gt 0) {
        Write-Host "`nRecent pump tokens:" -ForegroundColor Yellow
        foreach ($mint in $recentMints.data.mints) {
            foreach ($token in $mint.pump_token_addresses) {
                Write-Host "  - $token" -ForegroundColor White
            }
        }
    }
}

# Get system diagnostics
Write-Host "`nFetching system diagnostics..." -ForegroundColor Cyan
soleco diagnostics info

Write-Host "`nScript completed!" -ForegroundColor Green
Write-Host "Check the generated files for exported data:" -ForegroundColor White
Write-Host "  - network_status.json" -ForegroundColor White
Write-Host "  - rpc_nodes.csv" -ForegroundColor White
Write-Host "  - recent_mints.json" -ForegroundColor White
