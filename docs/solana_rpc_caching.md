# Solana RPC Caching Implementation

This document outlines the caching implementation for Solana RPC API queries in the Soleco application.

## Overview

The Solana RPC caching system is designed to:

1. Reduce load on Solana RPC nodes
2. Improve application performance by reducing API call latency
3. Provide a consistent user experience even when RPC nodes are experiencing issues
4. Allow for forced refresh of data when needed

## Components

### Backend Components

1. **Cache Storage**: SQLite database for storing cached responses
2. **Cache TTL Constants**: Centralized cache time-to-live values in `constants/cache.py`
3. **Cached Endpoints**:
   - `/network/status` - Comprehensive network status information
   - `/performance/metrics` - Performance metrics including TPS and block production
   - `/rpc-nodes` - Available RPC nodes with version distribution
   - `/token/{token_address}` - Token information

### Frontend Components

1. **API Service**: `solanaService.ts` - Service for making API calls to the Solana endpoints
2. **Custom Hooks**:
   - `useSolanaQuery.ts` - React Query hook with refresh capability
3. **UI Components**:
   - `NetworkStatusCard.tsx` - Displays network status information
   - `PerformanceMetricsCard.tsx` - Shows performance metrics
   - `RpcNodesCard.tsx` - Lists available RPC nodes
   - `SolanaMonitoringDashboard.tsx` - Combines all components

## Caching Strategy

### Cache Keys

Cache keys are constructed based on:
- Endpoint path
- Query parameters

### Cache TTL (Time-to-Live)

Different endpoints have different TTL values based on how frequently the data changes:

| Endpoint | TTL | Description |
|----------|-----|-------------|
| Network Status | 5 minutes | Overall network health and status |
| Performance Metrics | 3 minutes | TPS and block production stats |
| RPC Nodes | 10 minutes | Available RPC nodes and versions |
| Token Info | 15 minutes | Token metadata and details |

### Refresh Mechanism

All endpoints support a `refresh` query parameter that forces a fresh fetch from the Solana RPC API, bypassing the cache.

## Frontend Implementation

### React Query Integration

The application uses React Query for data fetching and caching on the frontend. Two custom hooks have been created to enhance the caching capabilities:

1. **useSolanaQuery**: A custom hook for Solana API queries with refresh capability
   ```typescript
   const { 
     data, 
     isLoading, 
     error, 
     refresh,
     isRefetching 
   } = useSolanaQuery(
     ['network-status'],
     (refresh) => solanaApi.getNetworkStatus(true, refresh),
     {
       refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
       staleTime: 2 * 60 * 1000, // Consider data stale after 2 minutes
     }
   );
   ```

2. **useRefreshablePumpFunQuery**: A custom hook for PumpFun API queries with refresh capability
   ```typescript
   const { 
     data, 
     isLoading, 
     error, 
     refresh,
     isRefetching 
   } = useRefreshablePumpFunQuery(
     'market-overview',
     (refresh) => pumpFunApi.getMarketOverview(true, 5, refresh),
     { refetchInterval: 5 * 60 * 1000 }
   );
   ```

### Refresh Implementation

Both hooks implement a refresh mechanism that:

1. Sets a refresh parameter to `true` when the `refresh()` function is called
2. Passes this parameter to the API function
3. Resets the parameter after a short timeout
4. Tracks the refreshing state with `isRefetching`

This approach ensures that:
- The backend knows when to bypass its cache
- The UI can show a loading indicator during refresh
- The cache key in React Query changes, forcing a refetch

### UI Components

The UI components use the `RefreshButton` component to provide a consistent way for users to manually refresh data:

```tsx
<RefreshButton 
  isLoading={isRefetching} 
  onClick={refresh} 
  tooltipLabel="Refresh network status" 
/>
```

## Error Handling

The caching system includes robust error handling:

### Backend Error Handling

1. **Coroutine Handling**:
   - Properly awaits coroutines in the NetworkStatusHandler
   - Enhanced `_get_data_with_timeout` method to properly check if the input is a coroutine

2. **Response Processing**:
   - Improved handling of nested structures in RPC responses
   - Added recursive search for validator data in complex response structures

3. **Serialization**:
   - Enhanced serialization to better handle various response types
   - Added specific handling for Pubkey objects, coroutines, and objects with special methods

### Frontend Error Handling

1. **API Service Level**:
   - Try/catch blocks around API calls
   - Detailed error logging
   - Consistent error format returned to components

2. **Component Level**:
   - Error states in UI components
   - Fallback UI when data is unavailable
   - Retry mechanisms

## Performance Considerations

1. **Minimizing API Calls**:
   - Default stale time of 2 minutes
   - Default cache time of 10 minutes
   - Configurable refetch intervals per endpoint

2. **Optimizing Bundle Size**:
   - Lazy loading of components
   - Code splitting by route

3. **Rendering Optimization**:
   - Memoization of expensive calculations
   - Virtualized lists for large datasets

## Future Improvements

1. **Persistent Cache**:
   - Implement IndexedDB for offline support
   - Persist cache between sessions

2. **Real-time Updates**:
   - WebSocket integration for real-time data
   - Subscription-based updates for critical metrics

3. **Advanced Caching Strategies**:
   - Implement staggered cache invalidation
   - Background refresh of soon-to-expire cache entries
