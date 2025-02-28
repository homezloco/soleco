 # Solana RPC Nodes API

The Solana RPC Nodes API provides information about available RPC nodes on the Solana network, including their count, version distribution, and optionally their health status.

### Endpoint

```
GET /api/soleco/solana/network/rpc-nodes
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_details` | boolean | `false` | Include detailed information for each RPC node |
| `health_check` | boolean | `false` | Perform health checks on a sample of RPC nodes |
| `include_well_known` | boolean | `true` | Include well-known RPC endpoints in the response |
| `prioritize_clean_urls` | boolean | `true` | Prioritize user-friendly URLs in the response |
| `include_raw_urls` | boolean | `false` | Include raw, unconverted RPC URLs in the response |
| `skip_dns_lookup` | boolean | `false` | Skip DNS lookups for faster response time |
| `max_conversions` | integer | `30` | Maximum number of IP addresses to attempt to convert to hostnames |

### Response

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
    "https://example-node.com:8899"
  ],
  "conversion_stats": {
    "attempted": 10,
    "successful": 5,
    "failed": 5,
    "skipped": 90
  },
  "execution_time_ms": 1234.56,
  "health_check_results": {
    "healthy_nodes": 45,
    "unhealthy_nodes": 5,
    "health_check_sample_size": 50,
    "health_percentage": 90.0
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_nodes` | integer | Total number of RPC nodes found |
| `version_distribution` | object | Distribution of node versions (top 5) |
| `well_known_rpc_urls` | array | List of well-known RPC endpoints from Soleco |
| `solana_official_urls` | array | List of official Solana RPC endpoints |
| `raw_rpc_urls` | array | List of raw, unconverted RPC URLs (if requested) |
| `converted_rpc_urls` | array | List of successfully converted RPC URLs (if DNS lookups are enabled) |
| `conversion_stats` | object | Statistics about DNS conversions (if DNS lookups are enabled) |
| `rpc_nodes` | array | Array of RPC node details (if requested) |
| `execution_time_ms` | number | Execution time in milliseconds |
| `health_check_results` | object | Results of health checks on a sample of RPC nodes (if requested) |

### RPC Node Object

Each RPC node object contains:

| Field | Type | Description |
|-------|------|-------------|
| `pubkey` | string | The node's public key |
| `rpc_url` | string | The RPC endpoint URL/address |
| `version` | string | The node's Solana version |
| `feature_set` | integer | The node's feature set |

### Conversion Statistics Object

The conversion statistics object contains:

| Field | Type | Description |
|-------|------|-------------|
| `attempted` | integer | Number of IP addresses attempted to convert |
| `successful` | integer | Number of successful conversions |
| `failed` | integer | Number of failed conversions |
| `skipped` | integer | Number of IP addresses skipped (not attempted) |

### Performance Considerations

When using the RPC Nodes API, consider the following performance implications:

1. **DNS Lookups**: DNS lookups can be slow, especially for a large number of IP addresses. Use `skip_dns_lookup=true` to bypass DNS lookups for faster response times.

2. **Health Checks**: Health checks involve making RPC requests to a sample of nodes, which can be time-consuming. Only use `health_check=true` when you need this information.

3. **Max Conversions**: The `max_conversions` parameter limits the number of IP addresses that will be converted to hostnames. A higher value will result in more converted URLs but slower response times.

4. **Caching**: The API caches DNS lookups and provider matches for 1 hour to improve performance. If you need the most up-to-date information, be aware that some data may be cached.

5. **Connection Pool**: The Soleco backend maintains a connection pool of RPC endpoints, prioritizing the fastest and most reliable endpoints. The pool automatically adapts based on endpoint performance, ensuring optimal connectivity.

## RPC Stats API

### Endpoint: `/api/soleco/solana/network/solana/rpc/stats`

This endpoint provides detailed statistics about all RPC endpoints, including private endpoints with API keys.

**Note:** This endpoint includes all RPC endpoints, including private ones with API keys. For a filtered view that excludes private endpoints, use the `/api/soleco/solana/network/solana/rpc/filtered-stats` endpoint.

#### Response Format:

```json
{
  "stats": {
    "https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY": {
      "success_count": 120,
      "failure_count": 2,
      "avg_latency": 0.235,
      "current_failures": 0,
      "in_pool": true,
      "success_rate": 98.36
    },
    "http://example-rpc-node.com:8899": {
      "success_count": 85,
      "failure_count": 15,
      "avg_latency": 0.456,
      "current_failures": 2,
      "in_pool": true,
      "success_rate": 85.0
    }
    // Additional endpoints...
  },
  "summary": {
    "total_endpoints": 12,
    "endpoints_in_pool": 5,
    "total_requests": 1250,
    "total_successes": 1180,
    "total_failures": 70,
    "overall_success_rate": 94.4
  },
  "top_performers": [
    {
      "endpoint": "https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY",
      "avg_latency": 0.235,
      "success_rate": 98.36,
      "success_count": 120,
      "failure_count": 2
    },
    {
      "endpoint": "http://another-fast-node.com:8899",
      "avg_latency": 0.312,
      "success_rate": 96.55,
      "success_count": 112,
      "failure_count": 4
    }
    // Additional top performers...
  ]
}
```

### Endpoint: `/api/soleco/solana/network/solana/rpc/filtered-stats`

This endpoint provides the same detailed statistics as the `/rpc/stats` endpoint but filters out any private endpoints with API keys (like Helius) for security reasons.

**Security Note**: This endpoint is safe to use in public-facing applications as it excludes endpoints with private API keys.

#### Response Format:

```json
{
  "stats": {
    "http://example-rpc-node.com:8899": {
      "success_count": 85,
      "failure_count": 15,
      "avg_latency": 0.456,
      "current_failures": 2,
      "in_pool": true,
      "success_rate": 85.0
    }
    // Additional public endpoints...
  },
  "summary": {
    "total_endpoints": 11,
    "active_endpoints": 8,
    "average_latency": 0.523,
    "total_success": 1060,
    "total_failures": 68,
    "overall_success_rate": 93.98
  },
  "top_performers": [
    {
      "endpoint": "http://fast-public-node.com:8899",
      "avg_latency": 0.312,
      "success_rate": 96.55,
      "success_count": 112,
      "failure_count": 4
    },
    {
      "endpoint": "http://another-good-node.com:8899",
      "avg_latency": 0.389,
      "success_rate": 94.23,
      "success_count": 98,
      "failure_count": 6
    }
    // Additional top performers (excluding private endpoints)...
  ]
}
```

#### Field Descriptions:

- **stats**: Object containing statistics for each RPC endpoint
  - **success_count**: Number of successful RPC calls
  - **failure_count**: Number of failed RPC calls
  - **avg_latency**: Average latency in seconds (using exponential moving average)
  - **current_failures**: Number of consecutive failures
  - **in_pool**: Whether the endpoint is currently in the active connection pool
  - **success_rate**: Percentage of successful calls (success_count / (success_count + failure_count) * 100)

- **summary**: Object containing summary statistics across all endpoints
  - **total_endpoints**: Total number of endpoints
  - **endpoints_in_pool** or **active_endpoints**: Number of endpoints in the active connection pool
  - **total_requests** or **total_success**: Total number of successful requests
  - **total_failures**: Total number of failed requests
  - **overall_success_rate**: Overall success rate across all endpoints

- **top_performers**: Array of top performing endpoints sorted by success rate and latency
  - Each object contains the endpoint URL and its performance metrics

#### Usage Notes:

1. The `/rpc/stats` endpoint includes all RPC endpoints, including private ones with API keys.
2. The `/rpc/filtered-stats` endpoint excludes private endpoints (like Helius) for security reasons.
3. Top performers are sorted by success rate (descending) and then by latency (ascending).
4. Endpoints with no successful requests will not appear in the top performers list.
5. The statistics are reset when the server is restarted.

#### Security Considerations:

- The `/rpc/filtered-stats` endpoint should be used in public-facing applications to avoid exposing API keys.
- The `/rpc/stats` endpoint should only be used in internal or admin-only interfaces.

## RPC Endpoint Performance Statistics

### Endpoint

```
GET /api/soleco/solana/rpc/stats
```

### Response

```json
{
  "stats": {
    "http://173.231.14.98:8899": {
      "success_count": 980,
      "failure_count": 20,
      "avg_latency": 1.459,
      "current_failures": 0,
      "in_pool": true,
      "success_rate": 98.0
    },
    "http://107.182.163.194:8899": {
      "success_count": 850,
      "failure_count": 30,
      "avg_latency": 1.671,
      "current_failures": 0,
      "in_pool": true,
      "success_rate": 96.6
    },
    "http://145.40.126.95:8899": {
      "success_count": 720,
      "failure_count": 8,
      "avg_latency": 1.278,
      "current_failures": 0,
      "in_pool": true,
      "success_rate": 98.9
    }
  },
  "summary": {
    "total_endpoints": 3,
    "endpoints_in_pool": 3,
    "total_requests": 2845,
    "total_successes": 2820,
    "total_failures": 25,
    "overall_success_rate": 99.12
  },
  "top_performers": [
    {
      "endpoint": "http://173.231.14.98:8899",
      "avg_latency": 1.459,
      "success_rate": 98.0,
      "success_count": 980,
      "failure_count": 20
    },
    {
      "endpoint": "http://107.182.163.194:8899",
      "avg_latency": 1.671,
      "success_rate": 96.6,
      "success_count": 850,
      "failure_count": 30
    },
    {
      "endpoint": "http://145.40.126.95:8899",
      "avg_latency": 1.278,
      "success_rate": 98.9,
      "success_count": 720,
      "failure_count": 8
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `stats` | object | Statistics for each endpoint |
| `stats.[endpoint].success_count` | integer | Number of successful requests |
| `stats.[endpoint].failure_count` | integer | Number of failed requests |
| `stats.[endpoint].avg_latency` | float | Average latency in seconds |
| `stats.[endpoint].current_failures` | integer | Current failure count in the pool |
| `stats.[endpoint].in_pool` | boolean | Whether the endpoint is currently in the connection pool |
| `stats.[endpoint].success_rate` | float | Success rate as a percentage |
| `summary` | object | Summary statistics across all endpoints |
| `summary.total_endpoints` | integer | Total number of endpoints |
| `summary.endpoints_in_pool` | integer | Number of endpoints currently in the pool |
| `summary.total_requests` | integer | Total number of requests across all endpoints |
| `summary.total_successes` | integer | Total number of successful requests |
| `summary.total_failures` | integer | Total number of failed requests |
| `summary.overall_success_rate` | float | Overall success rate as a percentage |
| `top_performers` | array | List of top performing endpoints by latency |

### Example Usage

```bash
# Get basic RPC node information
curl -X GET "https://api.soleco.io/api/soleco/solana/network/rpc-nodes"

# Get detailed RPC node information with health checks
curl -X GET "https://api.soleco.io/api/soleco/solana/network/rpc-nodes?include_details=true&health_check=true"

# Get RPC node information with raw URLs and without DNS lookups
curl -X GET "https://api.soleco.io/api/soleco/solana/network/rpc-nodes?include_raw_urls=true&skip_dns_lookup=true"