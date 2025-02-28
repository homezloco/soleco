# Dashboard API Documentation

This document outlines the API endpoints used by the Soleco Dashboard to retrieve and visualize Solana blockchain data.

## Network Status

**Endpoint:** `/solana/network/status`

**Method:** GET

**Query Parameters:**
- `summary_only` (boolean, optional): If true, returns only summary statistics without detailed node information. Default: true.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-06-15T12:00:00Z",
  "network_summary": {
    "total_nodes": 1000,
    "rpc_nodes_available": 500,
    "rpc_availability_percentage": 50,
    "latest_version": "1.14.0",
    "nodes_on_latest_version_percentage": 75,
    "version_distribution": [
      {
        "version": "1.14.0",
        "count": 750,
        "percentage": 75
      },
      {
        "version": "1.13.0",
        "count": 250,
        "percentage": 25
      }
    ],
    "total_versions_in_use": 2,
    "total_feature_sets_in_use": 2
  }
}
```

## RPC Nodes

**Endpoint:** `/solana/network/rpc-nodes`

**Method:** GET

**Query Parameters:**
- `include_details` (boolean, optional): If true, includes detailed information for each RPC node. Default: false.
- `health_check` (boolean, optional): If true, performs health checks on a sample of RPC nodes. Default: false.

**Response:**
```json
{
  "status": "success",
  "timestamp": "2023-06-15T12:00:00Z",
  "total_rpc_nodes": 500,
  "rpc_nodes": [
    {
      "endpoint": "https://api.mainnet-beta.solana.com",
      "version": "1.14.0",
      "features": ["feature1", "feature2"],
      "health_status": "healthy",
      "response_time_ms": 150,
      "last_checked": "2023-06-15T11:55:00Z"
    }
  ],
  "version_distribution": [
    {
      "version": "1.14.0",
      "count": 375,
      "percentage": 75
    },
    {
      "version": "1.13.0",
      "count": 125,
      "percentage": 25
    }
  ]
}
```

## Mint Analytics

**Endpoint:** `/analytics/mints/recent`

**Method:** GET

**Query Parameters:**
- `blocks` (integer, optional): Number of recent blocks to analyze. Default: 5.

**Response:**
```json
{
  "success": true,
  "timestamp": "2023-06-15T12:00:00Z",
  "block_range": {
    "start": 100,
    "end": 95
  },
  "results": [
    {
      "block_number": 100,
      "timestamp": "2023-06-15T11:59:00Z",
      "mint_addresses": ["addr1", "addr2", "addr3"],
      "new_mint_addresses": ["addr1"],
      "pump_token_addresses": ["addr1"],
      "success": true
    }
  ],
  "summary": {
    "total_blocks": 5,
    "total_mints": 10,
    "total_new_mints": 3,
    "total_pump_tokens": 2
  }
}
```

## Pump Tokens

**Endpoint:** `/pump/trending`

**Method:** GET

**Query Parameters:**
- `timeframe` (string, optional): Time period for trending data. Options: "1h", "24h", "7d". Default: "24h".
- `sort_by` (string, optional): Metric to sort by. Options: "volume", "price_change", "holders". Default: "volume".
- `limit` (integer, optional): Maximum number of tokens to return. Default: 10.

**Response:**
```json
{
  "timestamp": "2023-06-15T12:00:00Z",
  "tokens": [
    {
      "address": "token1",
      "name": "Token 1",
      "symbol": "TKN1",
      "price": 0.1,
      "price_change_24h": 5,
      "volume_24h": 10000,
      "holder_count": 100,
      "created_at": "2023-06-14T10:00:00Z"
    }
  ]
}
```

## Performance Metrics

**Endpoint:** `/solana/network/performance`

**Method:** GET

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-06-15T12:00:00Z",
  "performance_samples": [
    {
      "slot": 100,
      "num_transactions": 1000,
      "num_slots": 10,
      "sample_period_secs": 10
    }
  ],
  "summary_stats": {
    "total_transactions": 1000,
    "transactions_per_second_max": 100,
    "transactions_per_second_avg": 50,
    "total_blocks_produced": 100,
    "total_slots_skipped": 10,
    "block_time_avg_ms": 500,
    "slot_skip_rate": 0.1
  }
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": "Bad Request",
  "message": "Invalid parameter: blocks must be a positive integer"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "Failed to connect to Solana RPC node"
}
```

## Rate Limiting

API endpoints are rate-limited to 100 requests per minute per IP address. Exceeding this limit will result in a 429 Too Many Requests response:

```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded. Please try again in 60 seconds."
}
```
