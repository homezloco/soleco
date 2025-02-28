# Solana RPC Node Extractor

## Overview

The Solana RPC Node Extractor is a specialized component of the Soleco platform that discovers, analyzes, and monitors RPC nodes in the Solana network. It provides comprehensive information about available RPC nodes, their versions, and health status.

## Key Features

### 1. RPC Node Discovery

- **Comprehensive Discovery**: Extracts all available RPC nodes from the Solana network
- **Version Analysis**: Provides version distribution statistics for RPC nodes
- **Feature Set Information**: Captures feature set and shred version details for each node

### 2. Health Monitoring

- **Health Checks**: Performs health checks on a sample of RPC nodes
- **Response Time Measurement**: Measures response time for each node
- **Availability Tracking**: Tracks which nodes are available and responsive

### 3. DNS Optimization

- **Reduced DNS Resolver Timeout**: Optimized DNS resolver with reduced timeout (0.5s) and lifetime (1s)
- **Negative Caching**: Implements negative caching to avoid repeated lookups for failed DNS resolutions
- **Concurrent Lookup Limiting**: Limits concurrent DNS lookups to prevent overwhelming the DNS resolver

### 4. URL Processing

- **Provider Identification**: Early checks for known RPC providers to avoid unnecessary DNS lookups
- **Pattern Matching**: Improved pattern matching for RPC provider identification
- **Caching**: Efficient caching with configurable TTL (1 hour)
- **URL Formatting**: Optimized URL formatting for batches of endpoints

## Usage

### API Endpoint

The RPC Node Extractor is exposed through the `/api/soleco/solana/network/rpc-nodes` endpoint with the following query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_details` | boolean | `false` | Include detailed information for each RPC node |
| `health_check` | boolean | `false` | Perform health checks on a sample of RPC nodes |
| `include_well_known` | boolean | `true` | Include well-known RPC endpoints in the response |
| `prioritize_clean_urls` | boolean | `true` | Prioritize user-friendly URLs in the response |
| `include_raw_urls` | boolean | `false` | Include raw, unconverted RPC URLs in the response |
| `skip_dns_lookup` | boolean | `false` | Skip DNS lookups for faster response time |
| `max_conversions` | integer | `30` | Maximum number of IP addresses to attempt to convert to hostnames |

### Example Response

```json
{
  "total_nodes": 123,
  "version_distribution": {
    "1.14.17": 45,
    "1.14.16": 30,
    "1.14.15": 25,
    "1.14.14": 15,
    "other": 8
  },
  "well_known_rpc_urls": [
    "https://api.mainnet-beta.solflare.network",
    "https://solana-api.projectserum.com",
    "https://rpc.ankr.com/solana",
    "https://ssc-dao.genesysgo.net",
    "https://mainnet.helius-rpc.com"
  ],
  "solana_official_urls": [
    "https://api.mainnet-beta.solana.com",
    "https://api.devnet.solana.com",
    "https://api.testnet.solana.com"
  ],
  "raw_rpc_urls": [
    "https://1.2.3.4:8899",
    "https://5.6.7.8:8899"
  ],
  "converted_rpc_urls": [
    "https://example-node.solana.com:8899",
    "https://another-node.solana.org:8899"
  ],
  "health_check_results": {
    "sample_size": 20,
    "healthy_percentage": 85.0,
    "average_response_time": 1.25
  },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

## Implementation Details

### Node Discovery Process

1. **Cluster Node Query**: Uses the Solana RPC `getClusterNodes` method to get all nodes
2. **RPC Endpoint Extraction**: Filters nodes to only those with RPC endpoints
3. **Version Analysis**: Groups nodes by version and calculates distribution statistics
4. **Health Sampling**: Performs health checks on a random sample of nodes

### Health Check Process

1. **Endpoint Selection**: Selects a random sample of nodes to check
2. **Basic Health Query**: Sends a `getHealth` RPC request to each node
3. **Response Time Measurement**: Measures the time taken to respond
4. **Result Aggregation**: Aggregates results into health statistics

### URL Processing

1. **IP Detection**: Detects if an endpoint is an IP address
2. **DNS Lookup**: Performs reverse DNS lookup for IP addresses
3. **Provider Matching**: Attempts to match domains to known RPC providers
4. **URL Formatting**: Formats endpoints as proper URLs with appropriate protocol and port

## Performance Considerations

- **DNS Lookup Optimization**: DNS lookups can be slow, so they are optimized and can be skipped
- **Sample-Based Health Checks**: Health checks are performed on a sample to avoid overwhelming the network
- **Caching**: Results are cached to improve performance for repeated queries
- **Concurrent Processing**: URL formatting and health checks are performed concurrently

## Testing

The RPC Node Extractor includes comprehensive testing:

- **Unit Tests**: Tests for individual components like URL formatting and DNS lookup
- **Integration Tests**: Tests for the complete node discovery process
- **Health Check Tests**: Tests for the health check functionality
- **Performance Tests**: Tests to ensure optimal performance under load
