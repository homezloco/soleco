# Soleco Dashboard

The Soleco Dashboard provides a comprehensive view of the Solana blockchain ecosystem, visualizing real-time data from various Solana APIs.

## Features

### 1. Network Status
- Overall network health status
- Total nodes and RPC availability
- Version distribution of nodes
- Latest version adoption percentage

### 2. Mint Analytics
- Visualization of mint addresses across recent blocks
- Tracking of all mints, new mints, and pump tokens
- Block-by-block breakdown of mint activity
- Summary statistics for total mint counts

### 3. RPC Nodes
- Total RPC node count and health status
- Version distribution visualization
- Detailed node information (optional)
- Health check capabilities for node reliability

### 4. Pump Tokens
- Trending pump tokens with price and volume data
- Customizable timeframes (1h, 24h, 7d)
- Sorting by different metrics (volume, price change, holder growth)
- Direct links to token details

### 5. Performance Metrics
- Transactions per second (TPS) visualization
- Block production statistics
- Network performance indicators
- Slot skip rate and block time metrics

## Components

The dashboard is composed of the following components:

- `Dashboard.tsx` - Main container component
- `NetworkStatusCard.tsx` - Network health and version distribution
- `MintAnalyticsCard.tsx` - Mint address analytics and charts
- `RPCNodesCard.tsx` - RPC node information and health
- `PumpTokensCard.tsx` - Trending pump token data
- `PerformanceMetricsCard.tsx` - Network performance metrics

## API Integration

The dashboard integrates with the following API endpoints:

- `/solana/network/status` - Network status information
- `/solana/network/rpc-nodes` - RPC node data
- `/analytics/mints/recent` - Recent mint analytics
- `/pump/trending` - Trending pump tokens
- `/solana/network/performance` - Performance metrics

## Usage

The dashboard is accessible as the first tab in the main application interface. Each card can be refreshed independently, and some cards offer additional customization options:

- Mint Analytics: Select number of blocks to analyze
- RPC Nodes: Toggle detailed view and health checks
- Pump Tokens: Select timeframe and sorting metric

## Data Refresh

Components automatically refresh their data at different intervals:
- Network Status: Every 60 seconds
- Mint Analytics: Every 60 seconds
- RPC Nodes: Every 5 minutes
- Pump Tokens: Every 2 minutes
- Performance Metrics: Every 60 seconds

## Dependencies

- Chakra UI for component styling
- Recharts for data visualization
- React Query for data fetching and caching
