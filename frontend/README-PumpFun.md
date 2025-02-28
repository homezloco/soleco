# Pump.fun Analytics Dashboard

This document provides an overview of the Pump.fun Analytics Dashboard integration into the Soleco application.

## Overview

The Pump.fun Analytics Dashboard provides real-time insights and analytics for the Pump.fun platform, a popular Solana meme token trading platform. The dashboard displays various metrics and data points to help users track market activity, discover new tokens, and analyze token performance.

## Components

The Pump.fun Analytics Dashboard consists of the following components:

### 1. Market Overview Card

- Displays key market metrics including:
  - Total tokens on Pump.fun
  - 24-hour trading volume
  - Current SOL price
  - Most active token

### 2. King of the Hill Card

- Shows the current "King of the Hill" token
- Displays remaining time for the current king
- Lists previous kings and their reign duration

### 3. Latest Tokens Card

- Lists recently created tokens on Pump.fun
- Shows token price, creation date, and market cap
- Provides quick links to view tokens on Pump.fun

### 4. Top Performers Card

- Displays top performing tokens based on price change
- Includes tabs for different time periods (1h, 24h, 7d)
- Shows both top runners and featured tokens

### 5. Latest Trades Card

- Shows recent trades across the Pump.fun platform
- Displays trade type (buy/sell), price, amount, and time
- Provides links to view tokens on Pump.fun

### 6. Token Explorer Card

- Allows users to search for specific tokens
- Displays detailed token information including:
  - Price history charts
  - Volume history
  - Holder count
  - Trade count
  - Price change statistics

## API Integration

The dashboard integrates with the Pump.fun API through a dedicated service (`pumpFunService.ts`) that provides methods for fetching various data points:

- Market overview data
- Latest tokens
- Latest trades
- King of the Hill information
- Token search functionality
- Token details and analytics
- Historical price and volume data

## Technical Implementation

- Built using React and TypeScript
- Uses React Query for data fetching and caching
- Implements Chakra UI for responsive design and theming
- Includes Recharts for data visualization
- Features responsive layouts for different screen sizes

## Data Refresh

All components implement automatic data refresh to ensure users have access to the most up-to-date information:

- Market overview: Refreshes every 60 seconds
- King of the Hill: Refreshes every 30 seconds
- Latest tokens: Refreshes every 60 seconds
- Top performers: Refreshes every 60 seconds
- Latest trades: Refreshes every 30 seconds
- Token explorer: Refreshes every 60 seconds when a token is selected

## Error Handling

All components include robust error handling to ensure the dashboard remains functional even when API calls fail:

- Fallback UI for loading states
- Error messages when data cannot be retrieved
- Graceful degradation when partial data is available

## Future Enhancements

Potential future enhancements for the Pump.fun Analytics Dashboard:

1. Advanced filtering options for token discovery
2. Portfolio tracking for owned tokens
3. Price alerts and notifications
4. Social sentiment analysis
5. Integration with trading functionality
6. Historical performance comparison between tokens
