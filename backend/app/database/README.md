# Soleco Database Cache

This module implements a SQLite database for caching API responses and storing historical data for the Soleco dashboard.

## Features

1. **API Response Caching**
   - Reduces load on external APIs and the Solana blockchain
   - Improves performance by serving cached data instantly
   - Configurable TTL (Time to Live) for each endpoint

2. **Historical Data Storage**
   - Stores time-series data for network status, mint analytics, pump tokens, etc.
   - Enables historical trend analysis
   - Provides data for historical charts in the dashboard

3. **Middleware Integration**
   - Seamlessly integrates with FastAPI via middleware
   - Automatically caches API responses
   - Adds cache headers to responses

## Database Schema

The database consists of the following tables:

1. **cache** - Stores API responses
   - `endpoint` - API endpoint (PRIMARY KEY)
   - `data` - JSON response data
   - `params` - JSON query parameters
   - `timestamp` - When the data was cached
   - `ttl` - Time to live in seconds

2. **network_status_history** - Stores network status history
   - `id` - Auto-incrementing ID (PRIMARY KEY)
   - `status` - Network status (healthy, degraded, etc.)
   - `timestamp` - When the data was recorded
   - `data` - Full JSON response data

3. **mint_analytics_history** - Stores mint analytics history
   - `id` - Auto-incrementing ID (PRIMARY KEY)
   - `blocks` - Number of blocks analyzed
   - `new_mints_count` - Number of new mint addresses
   - `pump_tokens_count` - Number of pump tokens
   - `timestamp` - When the data was recorded
   - `data` - Full JSON response data

4. **pump_tokens_history** - Stores pump tokens history
   - `id` - Auto-incrementing ID (PRIMARY KEY)
   - `timeframe` - Timeframe (1h, 24h, 7d)
   - `sort_metric` - Sort metric (volume, price_change, holder_growth)
   - `tokens_count` - Number of tokens
   - `timestamp` - When the data was recorded
   - `data` - Full JSON response data

5. **rpc_nodes_history** - Stores RPC nodes history
   - `id` - Auto-incrementing ID (PRIMARY KEY)
   - `total_nodes` - Total number of RPC nodes
   - `timestamp` - When the data was recorded
   - `data` - Full JSON response data

6. **performance_metrics_history** - Stores performance metrics history
   - `id` - Auto-incrementing ID (PRIMARY KEY)
   - `max_tps` - Maximum transactions per second
   - `avg_tps` - Average transactions per second
   - `timestamp` - When the data was recorded
   - `data` - Full JSON response data

## API Endpoints

The following endpoints are available for accessing historical data:

1. **GET /api/soleco/analytics/network/status/history**
   - Returns network status history
   - Query parameters:
     - `limit` - Maximum number of records to return (default: 24)
     - `hours` - Number of hours to look back (default: 24)

2. **GET /api/soleco/analytics/mint/history**
   - Returns mint analytics history
   - Query parameters:
     - `blocks` - Number of blocks analyzed (default: 2)
     - `limit` - Maximum number of records to return (default: 24)
     - `hours` - Number of hours to look back (default: 24)

3. **GET /api/soleco/analytics/pump/tokens/history**
   - Returns pump tokens history
   - Query parameters:
     - `timeframe` - Timeframe (1h, 24h, 7d) (default: 24h)
     - `sort_metric` - Sort metric (volume, price_change, holder_growth) (default: volume)
     - `limit` - Maximum number of records to return (default: 24)
     - `hours` - Number of hours to look back (default: 24)

## Usage

The database cache is automatically used by the API endpoints via middleware. No additional configuration is required.

The database file is stored in the `data` directory at the root of the project as `soleco_cache.db`.

## Benefits

1. **Reduced API Load**: By caching responses, we reduce the load on external APIs and the Solana blockchain.
2. **Improved Performance**: Cached responses are served instantly, improving the user experience.
3. **Historical Data Analysis**: Storing time-series data enables historical trend analysis.
4. **Offline Development**: Developers can work on UI features without requiring constant connection to the Solana network.
5. **Testing Consistency**: Having stored data provides consistent test scenarios.

## Future Improvements

1. **Database Cleanup**: Implement a scheduled task to clean up old cache entries and historical data.
2. **Cache Invalidation**: Add a mechanism to invalidate cache entries when data changes.
3. **Database Migrations**: Add a migration system for database schema changes.
4. **Distributed Caching**: Consider using a distributed cache like Redis for multi-server deployments.
5. **Metrics**: Add metrics for cache hit/miss rates and database performance.
