# Solana RPC Nodes Testing Report

## Overview

This report documents the results of testing Solana RPC nodes discovered through the Soleco API. The testing was performed to assess the connectivity and functionality of various RPC endpoints in the Solana network.

## Testing Methodology

The testing process involved:

1. **Discovery**: RPC nodes were discovered using the `/api/soleco/solana/network/rpc-nodes` endpoint
2. **Connectivity Testing**: Each node was tested for connectivity using both HTTP and HTTPS protocols
3. **Functionality Testing**: Working nodes were tested for basic RPC functionality (getVersion, getSlot)
4. **Performance Measurement**: Response times were measured for each successful connection

## Key Findings

- **Total Nodes Tested**: 344
- **Working Nodes**: 86
- **Success Rate**: 25%
- **Protocol Distribution**:
  - HTTP: Most working nodes used HTTP protocol
  - HTTPS: Only a few official endpoints worked with HTTPS

## Top Performing Nodes

The following nodes had the fastest response times:

1. `http://38.58.176.230:8899` (1.567s)
2. `http://74.50.65.226:8899` (2.153s)
3. `http://147.28.171.53:8899` (4.316s)
4. `http://67.213.115.207:8899` (4.491s)
5. `http://208.85.17.92:8899` (4.497s)

## Common Failure Patterns

The following patterns were observed in failed connections:

1. **Timeouts**: The majority of failed connections were due to request timeouts
2. **SSL/TLS Errors**: Some HTTPS endpoints failed due to SSL certificate issues
3. **API Key Requirements**: Some endpoints like Ankr require API keys
4. **DNS Resolution Issues**: Some endpoints couldn't be resolved

## Recommendations

Based on the testing results, we recommend:

1. **For Production Use**: 
   - Use the official Solana RPC endpoints with proper rate limiting
   - Implement a fallback mechanism to switch between multiple endpoints
   - Consider using the top 5 fastest endpoints we discovered as backup options

2. **For Development/Testing**: 
   - Use the HTTP endpoints we discovered for testing purposes
   - Maintain a list of working endpoints and periodically verify their availability

3. **For High Availability**: 
   - Implement a load balancer that distributes requests across multiple working endpoints
   - Regularly monitor endpoint health and response times
   - Automatically switch to backup endpoints when primary ones fail

## Detailed Results

The complete test results are available in the `rpc_test_results.json` file. This file contains detailed information about each tested endpoint, including:

- Endpoint URL
- Connection status
- Solana version (if available)
- Current slot (if available)
- Response time
- Error details (for failed connections)

## Conclusion

Our testing revealed that while the official Solana RPC endpoints remain the most reliable option, there are numerous alternative endpoints available that can be used as backups or for specific use cases. The success rate of 25% indicates that a significant portion of the RPC nodes listed in the Solana network are actually accessible and functional.

The discovery of 86 working RPC nodes provides a valuable resource for applications that need to connect to the Solana blockchain. By implementing a proper fallback mechanism and regularly monitoring endpoint health, developers can ensure reliable access to the Solana network even during periods of high network congestion.

---

*Report generated on: February 26, 2025*
