# Solana RPC Integration

This document provides an overview of the Solana RPC integration in the Soleco application, including recent improvements and configuration options.

## Overview

The Solana RPC integration provides a robust connection to the Solana blockchain, with features such as:

- Connection pooling with automatic failover
- Endpoint discovery and testing
- Performance-based endpoint selection
- SSL verification configuration
- Error handling and diagnostics

## Key Components

- `solana_rpc.py`: Core RPC client implementation
- `solana_connection.py`: Connection pool management
- `solana_rpc_constants.py`: Default endpoints and configuration
- `solana_ssl_config.py`: SSL verification configuration
- `update_rpc_pool.py`: Script to update the connection pool
- `diagnose_rpc_endpoints.py`: Script to diagnose endpoint issues

## Recent Improvements

### 1. Endpoint Selection

We've removed problematic endpoints from the default list:
- Removed `https://solana.public-rpc.com` due to consistent failures
- Removed `https://solana-mainnet.rpcfast.com` due to reliability issues
- Removed `https://rpc.ankr.com/solana` due to API key issues
- Removed `https://mainnet.rpcpool.com` due to HTTP 403 errors
- Removed testnet and devnet endpoints from production use
- Removed several other problematic endpoints with DNS resolution issues or JSON decode errors:
  - `https://ssc-dao.genesysgo.net`
  - `https://api.metaplex.solana.com`
  - `https://solana-mainnet.g.alchemy.com/v2/demo`
  - `https://mainnet.solana.rpc.extrnode.com`

> **Important**: Testnet and devnet endpoints have been completely removed from `SOLANA_OFFICIAL_ENDPOINTS` to ensure they are never used in production. If you need to work with testnet or devnet for development purposes, you should explicitly specify those endpoints in your development configuration.

### 2. SSL Verification

Added support for endpoint-specific SSL verification:
- Global SSL verification setting in `SolanaConnectionPool`
- Endpoint-specific SSL bypass in `solana_ssl_config.py`
- Automatic detection and handling of SSL issues

### 3. Error Handling

Enhanced error handling for persistent failures:
- Added tracking of persistent failures in endpoint testing
- Improved diagnostics for SSL and API key issues
- Added circuit breaker pattern for rate-limited endpoints

## Configuration

### SSL Verification

SSL verification can be configured at multiple levels:

1. **Global Setting**:
   ```python
   # Disable SSL verification for all endpoints
   pool = await get_connection_pool(ssl_verify=False)
   ```

2. **Endpoint-Specific**:
   ```python
   # Add a specific endpoint to the SSL bypass list
   from app.utils.solana_ssl_config import add_ssl_bypass_endpoint
   add_ssl_bypass_endpoint("https://example.com")
   ```

3. **Pattern-Based**:
   ```python
   # Add a pattern for endpoints that should bypass SSL verification
   from app.utils.solana_ssl_config import add_ssl_bypass_pattern
   add_ssl_bypass_pattern(r"https://.*\.example\.com")
   ```

### RPC Pool Update

The RPC pool can be updated using the `update_rpc_pool.py` script:

```bash
# Basic usage
python -m app.scripts.update_rpc_pool

# Quick update with known endpoints only
python -m app.scripts.update_rpc_pool --quick

# Enable SSL verification
python -m app.scripts.update_rpc_pool --ssl-verify

# Customize number of endpoints
python -m app.scripts.update_rpc_pool --max-endpoints 10
```

### Endpoint Diagnostics

Use the `diagnose_rpc_endpoints.py` script to diagnose issues with specific endpoints:

```bash
# Test default endpoints
python -m app.scripts.diagnose_rpc_endpoints

# Test specific endpoints
python -m app.scripts.diagnose_rpc_endpoints --endpoints https://endpoint1.com https://endpoint2.com

# Bypass SSL verification
python -m app.scripts.diagnose_rpc_endpoints --ssl-bypass

# Enable verbose output
python -m app.scripts.diagnose_rpc_endpoints --verbose
```

## Best Practices

1. **API Keys**: Only use API keys with their specific services (e.g., Helius API key only with Helius endpoints)
2. **SSL Verification**: Only bypass SSL verification when necessary, and with appropriate warnings
3. **Endpoint Selection**: Prioritize reliable endpoints with low latency
4. **Error Handling**: Implement proper error handling for all RPC calls
5. **Rate Limiting**: Respect rate limits and implement appropriate backoff strategies

## Troubleshooting

If you encounter issues with the Solana RPC integration, try the following:

1. Run the diagnostics script to identify problematic endpoints:
   ```bash
   python -m app.scripts.diagnose_rpc_endpoints --verbose
   ```

2. Update the connection pool with known good endpoints:
   ```bash
   python -m app.scripts.update_rpc_pool --quick
   ```

3. Check the logs for specific error messages and take appropriate action.

4. If SSL issues persist, consider adding the problematic endpoint to the SSL bypass list.
