#!/bin/bash
# Bash script demonstrating how to use the Soleco CLI in shell scripts
# This script shows common CLI commands and how to process their output

set -e  # Exit on error

echo -e "\e[32mSoleco CLI Shell Script Example\e[0m"

# Check if soleco is installed
if ! command -v soleco &> /dev/null; then
    echo -e "\e[31mError: Soleco CLI not found. Please install it first.\e[0m"
    echo -e "\e[33mRun: pip install -e .\e[0m"
    exit 1
fi

# Get version
VERSION=$(soleco --version)
echo -e "\e[36mUsing Soleco CLI version: $VERSION\e[0m"

# Configure API URL if needed
echo -e "\n\e[36mConfiguring Soleco CLI...\e[0m"
soleco set-config api_url http://localhost:8000

# Display current configuration
echo -e "\n\e[36mCurrent configuration:\e[0m"
soleco config

# Get network status and save to file
echo -e "\n\e[36mFetching network status...\e[0m"
soleco network status --format json --output network_status.json

# Read the JSON file and extract information
if [ -f network_status.json ]; then
    NETWORK_STATUS=$(jq -r '.data.status' network_status.json 2>/dev/null || echo "unknown")
    
    if [ "$NETWORK_STATUS" == "healthy" ]; then
        echo -e "\e[32mNetwork is HEALTHY\e[0m"
    else
        echo -e "\e[33mNetwork status: $NETWORK_STATUS\e[0m"
    fi
    
    # Extract summary information if available
    if jq -e '.data.network_summary' network_status.json &>/dev/null; then
        TOTAL_NODES=$(jq -r '.data.network_summary.total_nodes' network_status.json)
        RPC_NODES=$(jq -r '.data.network_summary.rpc_nodes_available' network_status.json)
        LATEST_VERSION=$(jq -r '.data.network_summary.latest_version' network_status.json)
        
        echo -e "\e[36mTotal nodes: $TOTAL_NODES\e[0m"
        echo -e "\e[36mRPC nodes available: $RPC_NODES\e[0m"
        echo -e "\e[36mLatest version: $LATEST_VERSION\e[0m"
    fi
fi

# List RPC nodes and save to CSV
echo -e "\n\e[36mListing RPC nodes...\e[0m"
soleco rpc list --format csv --output rpc_nodes.csv

# Count the number of RPC nodes
if [ -f rpc_nodes.csv ]; then
    # Skip header line
    NODE_COUNT=$(($(wc -l < rpc_nodes.csv) - 1))
    echo -e "\e[36mFound $NODE_COUNT RPC nodes\e[0m"
    
    # Group by version (requires csvkit)
    if command -v csvcut &> /dev/null && command -v csvstat &> /dev/null; then
        echo -e "\n\e[36mRPC Node Versions:\e[0m"
        csvcut -c version rpc_nodes.csv | tail -n +2 | sort | uniq -c | sort -nr | while read count version; do
            echo -e "  $version: $count nodes"
        done
    fi
fi

# Get recent mints
echo -e "\n\e[36mFetching recent mints...\e[0m"
soleco mint recent --format json --output recent_mints.json

# Analyze recent mints
if [ -f recent_mints.json ]; then
    # Count new mint addresses and pump tokens
    if command -v jq &> /dev/null; then
        TOTAL_NEW_MINTS=$(jq '[.data.mints[].new_mint_addresses | length] | add' recent_mints.json)
        TOTAL_PUMP_TOKENS=$(jq '[.data.mints[].pump_token_addresses | length] | add' recent_mints.json)
        
        echo -e "\e[36mTotal new mint addresses: $TOTAL_NEW_MINTS\e[0m"
        echo -e "\e[36mTotal pump tokens: $TOTAL_PUMP_TOKENS\e[0m"
        
        # Display pump tokens if any
        if [ "$TOTAL_PUMP_TOKENS" -gt 0 ]; then
            echo -e "\n\e[33mRecent pump tokens:\e[0m"
            jq -r '.data.mints[].pump_token_addresses[]' recent_mints.json | while read token; do
                echo -e "  - $token"
            done
        fi
    fi
fi

# Get system diagnostics
echo -e "\n\e[36mFetching system diagnostics...\e[0m"
soleco diagnostics info

echo -e "\n\e[32mScript completed!\e[0m"
echo -e "Check the generated files for exported data:"
echo -e "  - network_status.json"
echo -e "  - rpc_nodes.csv"
echo -e "  - recent_mints.json"
