# Soleco API Reference

## Overview

This document provides a comprehensive reference for all API endpoints available in the Soleco platform. The API is organized into logical sections based on functionality.

## Base URL

All API endpoints are prefixed with:

```
/api/soleco
```

## Authentication

Currently, the API does not require authentication. This may change in future versions.

## Response Format

All API responses follow a standard JSON format:

```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

For error responses:

```json
{
  "status": "error",
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2023-04-15T12:34:56Z"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse. Current limits are:

- 100 requests per minute per IP address
- 1000 requests per hour per IP address

Rate limit headers are included in responses:

- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests in the current window
- `X-RateLimit-Reset`: Time when the rate limit resets (Unix timestamp)

## API Endpoints

### Solana Network Status

#### Get Network Status

```
GET /solana/network/status
```

Retrieves comprehensive status information about the Solana network.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_validators` | boolean | `true` | Include validator information |
| `include_performance` | boolean | `true` | Include performance metrics |
| `include_block_production` | boolean | `true` | Include block production information |
| `include_cluster_nodes` | boolean | `true` | Include cluster node information |

**Response:**

```json
{
  "status": "success",
  "data": {
    "network_status": "healthy",
    "cluster_nodes": {
      "total": 1500,
      "rpc_nodes": 250,
      "version_distribution": {
        "1.14.17": 45,
        "1.14.16": 30,
        "1.14.15": 25,
        "other": 150
      }
    },
    "validators": {
      "total": 1200,
      "active": 1150,
      "delinquent": 50,
      "stake_distribution": {
        "top_10_percent": 45.5,
        "top_25_percent": 68.2,
        "top_50_percent": 85.7
      }
    },
    "performance": {
      "current_slot": 123456789,
      "current_block_height": 123456700,
      "transactions_per_second": 2500,
      "average_confirmation_time": 0.5
    },
    "block_production": {
      "total_blocks_produced": 123456700,
      "total_slots": 123456789,
      "slot_skip_rate": 0.0007
    }
  },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

### RPC Nodes

#### Get RPC Nodes

```
GET /solana/network/rpc-nodes
```

Retrieves information about available RPC nodes on the Solana network.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_details` | boolean | `false` | Include detailed information for each RPC node |
| `health_check` | boolean | `false` | Perform health checks on a sample of RPC nodes |
| `include_well_known` | boolean | `true` | Include well-known RPC endpoints in the response |
| `prioritize_clean_urls` | boolean | `true` | Prioritize user-friendly URLs in the response |
| `include_raw_urls` | boolean | `false` | Include raw, unconverted RPC URLs in the response |
| `skip_dns_lookup` | boolean | `false` | Skip DNS lookups for faster response time |
| `max_conversions` | integer | `30` | Maximum number of IP addresses to attempt to convert to hostnames |

**Response:**

```json
{
  "status": "success",
  "data": {
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
    "converted_rpc_urls": [
      "https://example-node.solana.com:8899",
      "https://another-node.solana.org:8899"
    ]
  },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

#### Get RPC Stats

```
GET /solana/network/solana/rpc/stats
```

Retrieves detailed statistics about RPC endpoint performance.

**Response:**

```json
{
  "status": "success",
  "data": {
    "stats": {
      "https://mainnet.helius-rpc.com": {
        "success_count": 980,
        "failure_count": 20,
        "avg_latency": 0.45,
        "success_rate": 98.0
      },
      "https://api.mainnet-beta.solana.com": {
        "success_count": 950,
        "failure_count": 50,
        "avg_latency": 0.75,
        "success_rate": 95.0
      }
    },
    "summary": {
      "total_requests": 2000,
      "total_successes": 1930,
      "total_failures": 70,
      "overall_success_rate": 96.5,
      "avg_latency_across_all": 0.60
    }
  },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

#### Get Filtered RPC Stats

```
GET /solana/network/solana/rpc/filtered-stats
```

Retrieves detailed statistics about RPC endpoint performance, excluding private endpoints with API keys.

**Response:**

Similar to the `/rpc/stats` endpoint but with private endpoints filtered out.

### Mint Analytics

#### Extract Mint Addresses

```
GET /solana/mints/extract
```

Extracts mint addresses from a specific block.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `block_number` | integer | (required) | The block number to extract mint addresses from |

**Response:**

```json
{
  "status": "success",
  "data": {
    "block_number": 123456789,
    "mint_addresses": [
      "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
      "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "So11111111111111111111111111111111111111112"
    ],
    "new_mint_addresses": [
      "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    ],
    "pump_token_addresses": [
      "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    ],
    "stats": {
      "total_mint_addresses": 3,
      "total_new_mint_addresses": 1,
      "total_pump_tokens": 1
    }
  },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

#### Get Recent New Mints

```
GET /solana/mints/new/recent
```

Retrieves recently created mint addresses.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `100` | Maximum number of mint addresses to return |
| `include_pump_tokens` | boolean | `true` | Include pump tokens in the response |

**Response:**

```json
{
  "status": "success",
  "data": {
    "new_mint_addresses": [
      {
        "address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        "block_number": 123456789,
        "timestamp": "2023-04-15T12:30:00Z"
      },
      {
        "address": "8xLXtg3CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsV",
        "block_number": 123456788,
        "timestamp": "2023-04-15T12:29:45Z"
      }
    ],
    "pump_tokens": [
      {
        "address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        "block_number": 123456789,
        "timestamp": "2023-04-15T12:30:00Z"
      }
    ],
    "stats": {
      "total_new_mint_addresses": 2,
      "total_pump_tokens": 1
    }
  },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

### Diagnostics

#### Get Diagnostic Information

```
GET /diagnostics
```

Retrieves diagnostic information about the Soleco platform.

**Response:**

```json
{
  "status": "success",
  "data": {
    "version": "1.0.0",
    "uptime": 86400,
    "memory_usage": {
      "total": 1024,
      "used": 512,
      "free": 512
    },
    "solana_connection": {
      "status": "connected",
      "endpoint": "https://mainnet.helius-rpc.com",
      "latency": 0.45
    },
    "system_info": {
      "os": "Linux",
      "python_version": "3.9.7",
      "cpu_usage": 25.5,
      "disk_usage": 45.2
    }
  },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_PARAMETER` | Invalid parameter value |
| `MISSING_PARAMETER` | Required parameter is missing |
| `RPC_ERROR` | Error communicating with Solana RPC |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded |
| `INTERNAL_ERROR` | Internal server error |
| `RESOURCE_NOT_FOUND` | Requested resource not found |
| `TIMEOUT` | Operation timed out |

## Pagination

Endpoints that return lists support pagination using the following query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number |
| `limit` | integer | `100` | Number of items per page |

Paginated responses include the following metadata:

```json
{
  "status": "success",
  "data": [...],
  "pagination": {
    "total_items": 1000,
    "total_pages": 10,
    "current_page": 1,
    "items_per_page": 100,
    "next_page": 2,
    "prev_page": null
  },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

## Versioning

The API uses versioning to ensure backward compatibility. The current version is v1.

Future versions will be accessible via:

```
/api/soleco/v2/...
```

## SDK Support

Official SDKs for the Soleco API are available in:

- JavaScript/TypeScript
- Python
- Rust

See the [SDK Documentation](sdk.md) for more information.
