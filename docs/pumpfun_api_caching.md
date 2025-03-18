# Pump.fun API Caching Implementation

This document outlines the caching implementation for Pump.fun API queries in the Soleco application.

## Overview

The Pump.fun API caching system is designed to:

1. Reduce load on the Pump.fun API
2. Improve application performance by reducing API call latency
3. Provide a consistent user experience even when the API is experiencing issues
4. Allow for forced refresh of data when needed

## Components

### Frontend Components

1. **API Service**: `pumpFunService.ts` - Service for making API calls to the Pump.fun endpoints
2. **Custom Hooks**:
   - `useRefreshablePumpFunQuery.ts` - React Query hook with refresh capability
3. **UI Components**:
   - `PumpFunMarketOverviewCard.tsx` - Displays market overview information
   - `PumpFunTokenListCard.tsx` - Shows list of tokens
   - `PumpFunTradesCard.tsx` - Shows recent trades

## Caching Strategy

### Cache Keys

Cache keys are constructed based on:
- Endpoint path
- Query parameters

### Cache TTL (Time-to-Live)

Different endpoints have different TTL values based on how frequently the data changes:

| Endpoint | TTL | Description |
|----------|-----|-------------|
| Market Overview | 5 minutes | Overall market statistics |
| Latest Tokens | 3 minutes | Recently created tokens |
| Latest Trades | 2 minutes | Recent trading activity |
| Token Details | 10 minutes | Detailed token information |
| SOL Price | 5 minutes | Current SOL price |

## API Endpoints with Refresh Support

All Pump.fun API endpoints now support a `refresh` parameter:

```typescript
// Get latest tokens with refresh parameter
getLatestTokens(
  include_nsfw: boolean = false, 
  qty: number = 10, 
  refresh: boolean = false
): Promise<PumpFunToken[]>

// Get latest trades with refresh parameter
getLatestTrades(
  include_nsfw: boolean = false, 
  qty: number = 10, 
  refresh: boolean = false
): Promise<PumpFunTrade[]>

// Get king of the hill tokens with refresh parameter
getKingOfTheHill(
  include_nsfw: boolean = false, 
  refresh: boolean = false
): Promise<PumpFunToken[]>

// Search tokens with refresh parameter
searchTokens(
  query: string, 
  include_nsfw: boolean = false, 
  refresh: boolean = false
): Promise<PumpFunToken[]>

// Get SOL price with refresh parameter
getSolPrice(
  refresh: boolean = false
): Promise<number>

// Get candlesticks with refresh parameter
getCandlesticks(
  token_address: string, 
  timeframe: string = '1h', 
  refresh: boolean = false
): Promise<PumpFunCandlestick[]>

// Get token trades with refresh parameter
getTokenTrades(
  token_address: string, 
  qty: number = 10, 
  refresh: boolean = false
): Promise<PumpFunTrade[]>

// Get trade count with refresh parameter
getTradeCount(
  token_address: string, 
  refresh: boolean = false
): Promise<number>

// Get token details with refresh parameter
getTokenDetails(
  token_address: string, 
  refresh: boolean = false
): Promise<PumpFunTokenDetails>

// Get token price history with refresh parameter
getTokenPriceHistory(
  token_address: string, 
  refresh: boolean = false
): Promise<PumpFunPricePoint[]>

// Get token analytics with refresh parameter
getTokenAnalytics(
  token_address: string, 
  refresh: boolean = false
): Promise<PumpFunTokenAnalytics>

// Get market overview with refresh parameter
getMarketOverview(
  include_nsfw: boolean = false, 
  qty: number = 5, 
  refresh: boolean = false
): Promise<PumpFunMarketOverview>

// Get top performers with refresh parameter
getTopPerformers(
  timeframe: string = '24h', 
  include_nsfw: boolean = false, 
  refresh: boolean = false
): Promise<PumpFunTopPerformers>

// Get token history with refresh parameter
getTokenHistory(
  token_address: string, 
  refresh: boolean = false
): Promise<PumpFunTokenHistory>
```

## Frontend Implementation

### React Query Integration

The application uses React Query for data fetching and caching on the frontend. The custom hook has been created to enhance the caching capabilities:

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

The hook implements a refresh mechanism that:

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
  onClick={handleRefresh} 
  tooltipLabel="Refresh market overview" 
/>
```

## Error Handling

The caching system includes robust error handling:

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
