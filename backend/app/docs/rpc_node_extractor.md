# Solana RPC Node Extractor

The RPC Node Extractor is a feature that extracts and analyzes available RPC nodes from the Solana network. It provides information about RPC node availability, version distribution, and optionally performs health checks on a sample of nodes.

## API Endpoint

```
GET /solana/network/rpc-nodes
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| include_details | boolean | false | Include detailed information for each RPC node |
| health_check | boolean | false | Perform health checks on a sample of RPC nodes |

### Response Format

```json
{
  "status": "success",
  "timestamp": "2025-02-26T04:45:12.123456+00:00",
  "total_rpc_nodes": 293,
  "version_distribution": [
    {
      "version": "2.1.11",
      "count": 132,
      "percentage": 45.05
    },
    {
      "version": "2.1.14",
      "count": 41,
      "percentage": 14.00
    },
    {
      "version": "2.1.13",
      "count": 33,
      "percentage": 11.26
    },
    {
      "version": "2.2.0",
      "count": 28,
      "percentage": 9.56
    },
    {
      "version": "2.0.21",
      "count": 9,
      "percentage": 3.07
    }
  ],
  "health_sample_size": 20,
  "estimated_health_percentage": 85.00,
  "rpc_nodes": [
    {
      "pubkey": "8SQEcP4FaYQySktNQeyxF3w8pvArx3oMEh7fPrzkN9pu",
      "rpc_endpoint": "127.0.0.1:8899",
      "version": "2.1.11",
      "feature_set": 3271415109,
      "gossip": "127.0.0.1:8001",
      "shred_version": 12
    },
    // ... more nodes if include_details=true
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| status | string | Status of the request ("success" or "error") |
| timestamp | string | ISO-formatted timestamp of when the data was retrieved |
| total_rpc_nodes | integer | Total number of RPC nodes found in the network |
| version_distribution | array | Distribution of node versions (top 5 most common) |
| health_sample_size | integer | Number of nodes sampled for health check (if health_check=true) |
| estimated_health_percentage | number | Percentage of sampled nodes that are healthy (if health_check=true) |
| rpc_nodes | array | Detailed information about each RPC node (if include_details=true) |

## Implementation Details

The RPC Node Extractor works by:

1. Retrieving the list of all cluster nodes from the Solana network
2. Filtering nodes that have an RPC endpoint
3. Analyzing version distribution and other statistics
4. Optionally performing health checks on a sample of nodes

Health checks are performed by sending a `getHealth` RPC request to each node in the sample and checking if the response indicates the node is healthy.

## Usage Examples

### Get Basic RPC Node Information

```
GET /solana/network/rpc-nodes
```

Returns basic information about RPC nodes, including total count and version distribution.

### Get Detailed RPC Node Information

```
GET /solana/network/rpc-nodes?include_details=true
```

Returns basic information plus detailed information about each RPC node.

### Get RPC Node Health Information

```
GET /solana/network/rpc-nodes?health_check=true
```

Returns basic information plus health statistics based on a sample of nodes.

### Get Complete RPC Node Information

```
GET /solana/network/rpc-nodes?include_details=true&health_check=true
```

Returns all available information about RPC nodes, including details and health statistics.
