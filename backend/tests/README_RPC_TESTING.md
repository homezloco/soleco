# Solana RPC Node Testing

This directory contains scripts for testing Solana RPC nodes to determine their connectivity, functionality, and performance.

## Overview

The testing process involves:

1. Discovering RPC nodes from the Soleco API
2. Testing each node for connectivity and basic functionality
3. Identifying the fastest and most reliable nodes
4. Generating reports on the test results

## Testing Scripts

### 1. `test_discovered_rpc_nodes.py`

This script discovers and tests all available Solana RPC nodes:

- Calls the `/api/soleco/solana/network/rpc-nodes` endpoint to get a list of RPC nodes
- Tests each node for connectivity using both HTTP and HTTPS
- Generates a report of working nodes

Usage:
```bash
python -m app.tests.test_discovered_rpc_nodes
```

### 2. `test_top_rpc_nodes.py`

This script focuses on testing the top-performing RPC nodes that were discovered in previous tests:

- Tests a curated list of the fastest and most reliable RPC nodes
- Performs more comprehensive testing including health checks and block height queries
- Compares performance with official Solana RPC endpoints

Usage:
```bash
python -m app.tests.test_top_rpc_nodes
```

### 3. `test_specific_rpc_nodes.py`

This script allows testing specific RPC endpoints:

- Tests user-specified RPC endpoints
- Handles both HTTP and HTTPS protocols
- Provides detailed error information for failed connections

Usage:
```bash
python -m app.tests.test_specific_rpc_nodes
```

## Test Results

The test results are saved to JSON files:

- `rpc_test_results.json`: Results from testing all discovered RPC nodes
- `top_rpc_nodes_results.json`: Results from testing the top-performing RPC nodes

## Key Findings

Our testing revealed:

- A success rate of approximately 25% for discovered RPC nodes
- Most working nodes use the HTTP protocol rather than HTTPS
- The fastest nodes respond in 1.5-5 seconds
- Common failure patterns include timeouts, SSL errors, and API key requirements

## Top Performing Nodes

The following nodes consistently performed well in our tests:

1. `http://38.58.176.230:8899`
2. `http://74.50.65.226:8899`
3. `http://147.28.171.53:8899`
4. `http://67.213.115.207:8899`
5. `http://208.85.17.92:8899`

## Recommendations

For applications that need to connect to the Solana network:

1. Use the official Solana RPC endpoints as primary options
2. Implement a fallback mechanism using the top-performing nodes we discovered
3. Regularly test and update the list of working nodes
4. Consider implementing a load balancer for high-availability applications

## Documentation

For more detailed information, see the comprehensive report in:

`/app/docs/solana_rpc_nodes_report.md`
