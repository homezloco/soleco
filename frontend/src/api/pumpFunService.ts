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
  getLatestTokens(qty: number = 10, include_nsfw: boolean = true) {
    logRequest('/soleco/pumpfun/coins/latest', { qty, include_nsfw });
    return apiClient.get('/soleco/pumpfun/coins/latest', {
      params: { 
        qty,
        include_nsfw
      },
      timeout: 60000 // Increase timeout to 60 seconds
    }).then(response => {
      // Deduplicate tokens based on mint
      if (Array.isArray(response.data)) {
        const uniqueTokens = [];
        const mints = new Set();
        
        for (const token of response.data) {
          if (!mints.has(token.mint)) {
            mints.add(token.mint);
            uniqueTokens.push(token);
          }
        }
        
        return uniqueTokens;
      }
      
      return response.data;
    })
    .catch(error => {
      logError('Error fetching latest tokens:', error);
      // Return empty array instead of throwing to avoid breaking the UI
      return [];
    });
  },

  // Get latest trades
  getLatestTrades(qty: number = 10) {
    logRequest('/soleco/pumpfun/trades/latest', { qty, include_nsfw: true, include_all: true });
    return apiClient.get('/soleco/pumpfun/trades/latest', {
      params: { 
        qty,
        include_nsfw: true,
        include_all: true
      },
      timeout: 60000 // Increase timeout to 60 seconds
    }).then(response => {
      // Deduplicate trades based on signature
      if (Array.isArray(response.data)) {
        const uniqueTrades = [];
        const signatures = new Set();
        
        for (const trade of response.data) {
          if (!signatures.has(trade.signature)) {
            signatures.add(trade.signature);
            uniqueTrades.push(trade);
          }
        }
        
        return uniqueTrades;
      }
      
      return response.data;
    })
    .catch(error => {
      logError('Error fetching latest trades:', error);
      // Check if it's a 422 error and provide more detailed logging
      if (error.response && error.response.status === 422) {
        logError('422 Unprocessable Entity error details:', error.response.data);
      }
      // Return empty array instead of throwing to avoid breaking the UI
      return [];
    });
  },

  // Get king of the hill
  getKingOfTheHill(include_nsfw: boolean = true) {
    const cacheBuster = new Date().getTime();
    console.log(`[DEBUG] Calling getKingOfTheHill with include_nsfw=${include_nsfw}, cacheBuster=${cacheBuster}`);
    console.log(`[DEBUG] API URL: /soleco/pumpfun/coins/king-of-the-hill`);
    
    logRequest('/soleco/pumpfun/coins/king-of-the-hill', { include_nsfw, _: cacheBuster });
    return apiClient.get('/soleco/pumpfun/coins/king-of-the-hill', {
      params: {
        include_nsfw,
        _: cacheBuster // Add cache-busting parameter
      },
      timeout: 60000 // Increase timeout to 60 seconds
    }).then(response => {
      console.log('[DEBUG] getKingOfTheHill response:', response);
      return response.data;
    })
    .catch(error => {
      logError('Error fetching king of the hill:', error);
      console.error('[DEBUG] getKingOfTheHill error details:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        config: error.config
      });
      // Check if there's a response with error details
      if (error.response) {
        logError(`${error.response.status} error details:`, error.response.data);
      }
      // Return a default object instead of null to avoid breaking the UI
      return {
        mint: '',
        name: 'No King of the Hill',
        symbol: 'NONE',
        virtual_sol_reserves: 0,
        virtual_token_reserves: 0,
        king_of_the_hill_timestamp: Date.now() / 1000,
        previous_kings: []
      };
    });
  },

  // Search tokens
  searchTokens(query: string, limit: number = 10) {
    logRequest('/soleco/pumpfun/search', { q: query, limit, include_nsfw: true, include_all: true, include_metadata: true, skip_validation: true });
    return apiClient.get('/soleco/pumpfun/search', {
      params: { 
        q: query, 
        limit,
        include_nsfw: true,
        include_all: true,
        include_metadata: true,
        skip_validation: true
      },
      timeout: 60000
    }).then(response => response.data)
    .catch(error => {
      logError('Error searching tokens:', error);
      return [];
    });
  },

  // The getFeaturedTokens function has been removed because the endpoint is not functional.
  // The featured tokens endpoint is no longer available in the Pump.fun API.

  // Get SOL price
  getSolPrice() {
    logRequest('/soleco/pumpfun/sol-price');
    return apiClient.get('/soleco/pumpfun/sol-price', {
      timeout: 60000
    }).then(response => {
      logDebug('SOL price:', response.data);
      return response.data;
    })
    .catch(error => {
      logError('Error fetching SOL price:', error);
      // Check if there's a response with error details
      if (error.response) {
        logError(`${error.response.status} error details:`, error.response.data);
      }
      // Return a default value instead of null to avoid breaking the UI
      return { price: 0, price_change_24h: 0 };
    });
  },

  // Get candlesticks for a token
  getCandlesticks(mint: string, timeframe: '1m' | '5m' | '15m' | '1h' | '4h' | '1d' = '1h') {
    logRequest(`/soleco/pumpfun/candlesticks/${mint}`, {});
    return apiClient.get(`/soleco/pumpfun/candlesticks/${mint}`, {
      params: {
        timeframe
      },
      timeout: 60000
    }).then(response => {
      logDebug(`Candlesticks for ${mint}:`, response.data);
      return response.data;
    })
    .catch(error => {
      logError(`Error fetching candlesticks for ${mint}:`, error);
      return [];
    });
  },

  // Get all trades for a token
  getTokenTrades(mint: string, limit: number = 50) {
    logRequest(`/soleco/pumpfun/trades/all/${mint}`, { limit });
    return apiClient.get(`/soleco/pumpfun/trades/all/${mint}`, {
      params: {
        limit
      },
      timeout: 60000
    }).then(response => {
      logDebug(`Trades for ${mint}:`, response.data);
      return response.data;
    })
    .catch(error => {
      logError(`Error fetching trades for ${mint}:`, error);
      return [];
    });
  },

  // Get trade count for a token
  getTradeCount(mint: string) {
    logRequest(`/soleco/pumpfun/trades/count/${mint}`, {});
    return apiClient.get(`/soleco/pumpfun/trades/count/${mint}`, {
      timeout: 60000
    }).then(response => {
      logDebug(`Trade count for ${mint}:`, response.data);
      return response.data;
    })
    .catch(error => {
      logError(`Error fetching trade count for ${mint}:`, error);
      return { count: 0 };
    });
  },

  // Get token details
  getTokenDetails(mint: string) {
    logRequest(`/soleco/pumpfun/coins/${mint}`, {});
    return apiClient.get(`/soleco/pumpfun/coins/${mint}`, {
      timeout: 60000
    }).then(response => {
      logDebug(`Token details for ${mint}:`, response.data);
      return response.data;
    })
    .catch(error => {
      logError(`Error fetching token details for ${mint}:`, error);
      // Check if there's a response with error details
      if (error.response) {
        logError(`${error.response.status} error details:`, error.response.data);
      }
      // Return a default token object with the requested mint
      return {
        mint: mint,
        name: 'Unknown Token',
        symbol: 'UNKNOWN',
        virtual_sol_reserves: 0,
        virtual_token_reserves: 0,
        created_timestamp: Date.now() / 1000
      };
    });
  },

  // Get token price history
  getTokenPriceHistory(mint: string, period: string = '1d') {
    logRequest(`/soleco/pumpfun/coins/${mint}/price-history`, { period });
    return apiClient.get(`/soleco/pumpfun/coins/${mint}/price-history`, {
      params: { 
        period
      },
      timeout: 60000
    }).then(response => response.data)
    .catch(error => {
      logError(`Error fetching price history for ${mint}:`, error);
      return [];
    });
  },

  // Get token analytics
  getTokenAnalytics(mint: string) {
    logRequest(`/soleco/pumpfun/analytics/${mint}`, {});
    return apiClient.get(`/soleco/pumpfun/analytics/${mint}`, {
      timeout: 60000
    }).then(response => {
      logDebug(`Analytics for ${mint}:`, response.data);
      return response.data;
    })
    .catch(error => {
      logError(`Error fetching analytics for ${mint}:`, error);
      // Check if there's a response with error details
      if (error.response) {
        logError(`${error.response.status} error details:`, error.response.data);
      }
      // Return a default analytics object
      return {
        mint: mint,
        name: 'Unknown Token',
        total_volume: 0,
        price_high: 0,
        price_low: 0,
        trade_count: 0,
        holder_count: 0,
        created_at: new Date().toISOString(),
        price_change_24h: 0,
        volume_change_24h: 0
      };
    });
  },

  // Get market overview
  getMarketOverview(include_nsfw: boolean = true) {
    logRequest('/soleco/pumpfun/market-overview', { include_nsfw });
    return apiClient.get('/soleco/pumpfun/market-overview', {
      params: {
        include_nsfw
      },
      timeout: 60000
    }).then(response => {
      logDebug('Market overview:', response.data);
      
      // Transform the response to match what the UI expects
      const data = response.data;
      return {
        total_tokens: data.total_tokens_tracked || 0,
        total_volume_24h: data.total_volume_24h || 0,
        total_trades_24h: 0, // Not provided by the backend currently
        new_tokens_24h: 0, // Not provided by the backend currently
        sol_price: data.sol_price || 0,
        sol_price_change_24h: 0, // Not provided by the backend currently
        most_active_tokens: [] // Featured tokens endpoint is not available
      };
    })
    .catch(error => {
      logError('Error fetching market overview:', error);
      // Check if there's a response with error details
      if (error.response) {
        logError(`${error.response.status} error details:`, error.response.data);
      }
      // Return a default object instead of null to avoid breaking the UI
      return {
        total_tokens: 0,
        total_volume_24h: 0,
        total_trades_24h: 0,
        new_tokens_24h: 0,
        sol_price: 0,
        sol_price_change_24h: 0,
        most_active_tokens: []
      };
    });
  },

  // Get top performing tokens
  getTopPerformers(params: {
    metric?: string;
    limit?: number;
    hours?: number;
    include_nsfw?: boolean;
    refresh?: boolean;
  } = {}) {
    const defaultParams = {
      metric: 'volume_24h',
      limit: 10,
      hours: 24,
      include_nsfw: true,
      refresh: false
    };
    
    const queryParams = { ...defaultParams, ...params };
    
    logRequest('/soleco/pumpfun/top-performers', queryParams);
    return apiClient.get('/soleco/pumpfun/top-performers', {
      params: queryParams,
      timeout: 60000
    }).then(response => {
      logDebug('Top performers:', response.data);
      return response.data;
    })
    .catch(error => {
      logError('Error fetching top performers:', error);
      // Check if there's a response with error details
      if (error.response) {
        logError(`${error.response.status} error details:`, error.response.data);
      }
      // Return an empty array to avoid breaking the UI
      return [];
    });
  },

  // Get token history
  getTokenHistory(mint: string) {
    logRequest(`/soleco/pumpfun/token-history/${mint}`, {});
    return apiClient.get(`/soleco/pumpfun/token-history/${mint}`, {
      timeout: 60000
    }).then(response => {
      logDebug('Token history:', response.data);
      return response.data;
    })
    .catch(error => {
      logError(`Error fetching history for ${mint}:`, error);
      // Check if there's a response with error details
      if (error.response) {
        logError(`${error.response.status} error details:`, error.response.data);
      }
      // Return a default history object
      const now = new Date().toISOString();
      return {
        mint: mint,
        name: 'Unknown Token',
        price_history: [{ timestamp: now, price: 0 }],
        volume_history: [{ timestamp: now, volume: 0 }],
        holder_history: [{ timestamp: now, holders: 0 }]
      };
    });
  }
};
