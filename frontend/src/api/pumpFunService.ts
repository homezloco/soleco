import { apiClient } from './client';

// Debug flag to control console logging
const DEBUG = process.env.NODE_ENV === 'development';

// Helper function for logging
const logDebug = (message: string, data?: any) => {
  if (DEBUG) {
    if (data) {
      console.log(message, data);
    } else {
      console.log(message);
    }
  }
};

// Helper function for error logging
const logError = (message: string, error: any) => {
  console.error(message, error);
  if (DEBUG && error.response) {
    console.error(`${error.response.status} error details:`, error.response.data);
  }
};

// Helper function to handle API errors with fallback data
const handleApiError = <T>(error: any, fallbackData: T, endpoint: string): T => {
  logError(`Error fetching from ${endpoint}:`, error);
  
  // If it's a 404 error, return the fallback data
  if (error.response && error.response.status === 404) {
    console.warn(`Endpoint ${endpoint} not found (404), using fallback data`);
    return fallbackData;
  }
  
  // For other errors, throw the error to be handled by the caller
  throw error;
};

// Helper function to log the full URL being requested
const logRequest = (url: string, params?: any) => {
  if (DEBUG) {
    const baseUrl = import.meta.env.VITE_BACKEND_URL || '/api';
    const fullUrl = `${baseUrl}${url}`;
    console.log(`Making request to: ${fullUrl}`, params ? { params } : '');
  }
};

// Types for PumpFun API responses
export interface PumpFunToken {
  mint: string;
  name?: string;
  symbol?: string;
  description?: string;
  image_uri?: string;
  video_uri?: string;
  metadata_uri?: string;
  twitter?: string;
  telegram?: string;
  bonding_curve?: string;
  associated_bonding_curve?: string;
  creator?: string;
  created_timestamp?: number;
  raydium_pool?: string;
  complete?: boolean;
  virtual_sol_reserves?: number;
  virtual_token_reserves?: number;
  total_supply?: number;
  website?: string;
  show_name?: boolean;
  market_cap?: number;
  reply_count?: number;
  last_reply?: string;
  nsfw?: boolean;
  market_id?: string;
  inverted?: boolean;
  is_currently_live?: boolean;
  username?: string;
  profile_image?: string;
  usd_market_cap?: number;
  hidden?: boolean;
  last_trade_timestamp?: number;
  real_sol_reserves?: number;
  livestream_ban_expiry?: number;
  is_banned?: boolean;
  initialized?: boolean;
  updated_at?: string;
  real_token_reserves?: number;
}

export interface PumpFunTrade {
  signature: string;
  mint: string;
  sol_amount: number;
  token_amount: number;
  is_buy: boolean;
  user: string;
  timestamp: number;
  symbol: string;
  image_uri?: string;
  slot: number;
}

export interface KingOfTheHill {
  mint: string;
  name: string;
  symbol: string;
  description?: string;
  image_uri?: string;
  video_uri?: string;
  metadata_uri?: string;
  twitter?: string;
  telegram?: string;
  bonding_curve?: string;
  associated_bonding_curve?: string;
  creator?: string;
  created_timestamp?: number;
  raydium_pool?: string;
  complete?: boolean;
  virtual_sol_reserves?: number;
  virtual_token_reserves?: number;
  total_supply?: number;
  website?: string;
  show_name?: boolean;
  king_of_the_hill_timestamp?: number;
  market_cap?: number;
  reply_count?: number;
  last_reply?: string;
  nsfw?: boolean;
  market_id?: string;
  inverted?: boolean;
  is_currently_live?: boolean;
  username?: string;
  profile_image?: string;
  usd_market_cap?: number;
  hidden?: boolean;
  last_trade_timestamp?: number;
  real_sol_reserves?: number;
  livestream_ban_expiry?: number;
  is_banned?: boolean;
  initialized?: boolean;
  updated_at?: string;
  real_token_reserves?: number;
  previous_kings?: Array<{
    name: string;
    duration: number;
    mint?: string;
    symbol?: string;
  }>;
}

export interface TokenAnalytics {
  mint: string;
  name: string;
  total_volume: number;
  price_high: number;
  price_low: number;
  trade_count: number;
  holder_count: number;
  created_at: string;
  price_change_24h: number;
  volume_change_24h: number;
}

export interface MarketOverview {
  total_tokens: number;
  total_volume_24h: number;
  total_trades_24h: number;
  new_tokens_24h: number;
  sol_price: number;
  sol_price_change_24h: number;
  most_active_tokens: PumpFunToken[];
}

export interface Candlestick {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TokenHistory {
  mint: string;
  name: string;
  price_history: Array<{
    timestamp: string;
    price: number;
  }>;
  volume_history: Array<{
    timestamp: string;
    volume: number;
  }>;
  holder_history: Array<{
    timestamp: string;
    holders: number;
  }>;
}

// PumpFun API Service
export const pumpFunApi = {
  // Get latest tokens
  async getLatestTokens(
    qty: number = 10, 
    refresh: boolean = false
  ): Promise<PumpFunToken[]> {
    try {
      logRequest('/soleco/pumpfun/coins/latest', { qty, refresh });
      const response = await apiClient.get('/soleco/pumpfun/coins/latest', {
        params: {
          qty,
          refresh
        }
      });
      logDebug('Latest tokens response:', response.data);
      
      // Additional check for duplicate tokens
      if (Array.isArray(response.data)) {
        const seenMints = new Set<string>();
        const uniqueTokens = response.data.filter((token: PumpFunToken) => {
          if (!token.mint) return false;
          if (seenMints.has(token.mint)) return false;
          seenMints.add(token.mint);
          return true;
        });
        return uniqueTokens;
      }
      
      return response.data;
    } catch (error) {
      return handleApiError(error, [], '/soleco/pumpfun/coins/latest');
    }
  },

  // Get latest trades
  async getLatestTrades(
    qty: number = 10, 
    include_all: boolean = true,
    include_nsfw: boolean = true,
    refresh: boolean = false
  ): Promise<PumpFunTrade[]> {
    try {
      logRequest('/soleco/pumpfun/trades/latest', { qty, include_all, include_nsfw, refresh });
      const response = await apiClient.get('/soleco/pumpfun/trades/latest', {
        params: {
          qty,
          include_all,
          include_nsfw,
          refresh
        }
      });
      logDebug('Latest trades response:', response.data);
      
      // Additional check for duplicate trades
      if (Array.isArray(response.data)) {
        const seenSignatures = new Set<string>();
        const uniqueTrades = response.data.filter((trade: PumpFunTrade) => {
          if (!trade.signature) return false;
          if (seenSignatures.has(trade.signature)) return false;
          seenSignatures.add(trade.signature);
          return true;
        });
        return uniqueTrades;
      }
      
      return response.data;
    } catch (error) {
      return handleApiError(error, [], '/soleco/pumpfun/trades/latest');
    }
  },

  // Get king of the hill
  async getKingOfTheHill(
    include_nsfw: boolean = false,
    refresh: boolean = false
  ): Promise<KingOfTheHill> {
    try {
      // Use the FastAPI backend endpoint
      logRequest('/soleco/pumpfun/coins/king-of-the-hill', { include_nsfw, refresh });
      const response = await apiClient.get('/soleco/pumpfun/coins/king-of-the-hill', {
        params: {
          include_nsfw, // Note: parameter name is 'include_nsfw' in our FastAPI
          refresh
        }
      });
      
      logDebug('King of the hill response:', response.data);
      return response.data;
    } catch (error) {
      // Create a fallback object for KingOfTheHill with required fields
      const fallback: KingOfTheHill = {
        mint: '',
        name: 'No King of the Hill Available',
        symbol: 'N/A',
        description: 'Data currently unavailable',
        market_cap: 0,
        king_of_the_hill_timestamp: Date.now(),
        previous_kings: []
      };
      return handleApiError(error, fallback, '/soleco/pumpfun/coins/king-of-the-hill');
    }
  },

  // Search tokens
  async searchTokens(
    query: string, 
    limit: number = 10,
    refresh: boolean = false
  ): Promise<PumpFunToken[]> {
    try {
      logRequest('/soleco/pumpfun/search', { query, limit, refresh });
      const response = await apiClient.get('/soleco/pumpfun/search', {
        params: {
          query,
          limit,
          refresh
        }
      });
      logDebug('Search tokens response:', response.data);
      return response.data;
    } catch (error) {
      logError('Error searching tokens:', error);
      throw error;
    }
  },

  // The getFeaturedTokens function has been removed because the endpoint is not functional.
  // The featured tokens endpoint is no longer available in the Pump.fun API.

  // Get SOL price
  async getSolPrice(refresh: boolean = false): Promise<number> {
    try {
      logRequest('/soleco/pumpfun/sol-price', { refresh });
      const response = await apiClient.get('/soleco/pumpfun/sol-price', {
        params: { refresh }
      });
      logDebug('SOL price response:', response.data);
      return response.data;
    } catch (error) {
      // Return a default SOL price as fallback
      return handleApiError(error, 0, '/soleco/pumpfun/sol-price');
    }
  },

  // Get candlesticks for a token
  async getCandlesticks(
    mint: string, 
    timeframe: '1m' | '5m' | '15m' | '1h' | '4h' | '1d' = '1h',
    refresh: boolean = false
  ): Promise<Candlestick[]> {
    try {
      logRequest(`/soleco/pumpfun/token/${mint}/candlesticks`, { interval: timeframe, refresh });
      const response = await apiClient.get(`/soleco/pumpfun/token/${mint}/candlesticks`, {
        params: {
          interval: timeframe,
          refresh
        }
      });
      logDebug('Candlesticks response:', response.data);
      return response.data;
    } catch (error) {
      logError(`Error fetching candlesticks for ${mint}:`, error);
      throw error;
    }
  },

  // Get all trades for a token
  async getTokenTrades(
    mint: string, 
    limit: number = 50,
    refresh: boolean = false
  ): Promise<PumpFunTrade[]> {
    try {
      logRequest(`/soleco/pumpfun/token/${mint}/trades`, { limit, refresh });
      const response = await apiClient.get(`/soleco/pumpfun/token/${mint}/trades`, {
        params: {
          limit,
          refresh
        }
      });
      logDebug('Token trades response:', response.data);
      return response.data;
    } catch (error) {
      logError(`Error fetching trades for ${mint}:`, error);
      throw error;
    }
  },

  // Get trade count for a token
  async getTradeCount(
    mint: string,
    refresh: boolean = false
  ): Promise<number> {
    try {
      logRequest(`/soleco/pumpfun/token/${mint}/trade-count`, { refresh });
      const response = await apiClient.get(`/soleco/pumpfun/token/${mint}/trade-count`, {
        params: { refresh }
      });
      logDebug('Trade count response:', response.data);
      return response.data.count;
    } catch (error) {
      logError(`Error fetching trade count for ${mint}:`, error);
      throw error;
    }
  },

  // Get token details
  async getTokenDetails(
    mint: string,
    refresh: boolean = false
  ): Promise<PumpFunToken> {
    try {
      logRequest(`/soleco/pumpfun/token/${mint}`, { refresh });
      const response = await apiClient.get(`/soleco/pumpfun/token/${mint}`, {
        params: { refresh }
      });
      logDebug('Token details response:', response.data);
      return response.data;
    } catch (error) {
      logError(`Error fetching token details for ${mint}:`, error);
      throw error;
    }
  },

  // Get token price history
  async getTokenPriceHistory(
    mint: string, 
    period: string = '1d',
    refresh: boolean = false
  ): Promise<any> {
    try {
      logRequest(`/soleco/pumpfun/token/${mint}/price-history`, { period, refresh });
      const response = await apiClient.get(`/soleco/pumpfun/token/${mint}/price-history`, {
        params: {
          period,
          refresh
        }
      });
      logDebug('Token price history response:', response.data);
      return response.data;
    } catch (error) {
      logError(`Error fetching price history for ${mint}:`, error);
      throw error;
    }
  },

  // Get token analytics
  async getTokenAnalytics(
    mint: string,
    refresh: boolean = false
  ): Promise<TokenAnalytics> {
    try {
      logRequest(`/soleco/pumpfun/token/${mint}/analytics`, { refresh });
      const response = await apiClient.get(`/soleco/pumpfun/token/${mint}/analytics`, {
        params: { refresh }
      });
      logDebug('Token analytics response:', response.data);
      return response.data;
    } catch (error) {
      logError(`Error fetching analytics for ${mint}:`, error);
      throw error;
    }
  },

  // Get market overview
  async getMarketOverview(
    include_nsfw: boolean = true,
    latest_limit: number = 5,
    refresh: boolean = false
  ): Promise<MarketOverview> {
    try {
      logRequest('/soleco/pumpfun/market-overview', { include_nsfw, latest_limit, refresh });
      const response = await apiClient.get('/soleco/pumpfun/market-overview', {
        params: {
          include_nsfw,
          latest_limit,
          refresh
        }
      });
      logDebug('Market overview response:', response.data);
      return response.data;
    } catch (error) {
      // Create a minimal fallback object for MarketOverview
      const fallback: MarketOverview = {
        total_tokens: 0,
        total_volume_24h: 0,
        total_trades_24h: 0,
        new_tokens_24h: 0,
        sol_price: 0,
        sol_price_change_24h: 0,
        most_active_tokens: []
      };
      return handleApiError(error, fallback, '/soleco/pumpfun/market-overview');
    }
  },

  // Get top performing tokens
  async getTopPerformers(params: {
    metric?: string;
    limit?: number;
    hours?: number;
    include_nsfw?: boolean;
    refresh?: boolean;
  } = {}): Promise<PumpFunToken[]> {
    const { 
      metric = 'volume_24h', 
      limit = 10, 
      hours = 24, 
      include_nsfw = true,
      refresh = false
    } = params;
    
    try {
      logRequest('/soleco/pumpfun/top-performers', { metric, limit, hours, include_nsfw, refresh });
      const response = await apiClient.get('/soleco/pumpfun/top-performers', {
        params: {
          metric,
          limit,
          hours,
          include_nsfw,
          refresh
        }
      });
      logDebug('Top performers response:', response.data);
      return response.data;
    } catch (error) {
      logError('Error fetching top performers:', error);
      throw error;
    }
  },

  // Get token history
  async getTokenHistory(
    mint: string,
    time_range: string = '24h',
    refresh: boolean = false
  ): Promise<TokenHistory> {
    try {
      logRequest(`/soleco/pumpfun/token/${mint}/history`, { time_range, refresh });
      const response = await apiClient.get(`/soleco/pumpfun/token/${mint}/history`, {
        params: {
          time_range,
          refresh
        }
      });
      logDebug('Token history response:', response.data);
      return response.data;
    } catch (error) {
      logError(`Error fetching history for ${mint}:`, error);
      throw error;
    }
  }
};
