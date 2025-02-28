import { apiClient } from './client';

export interface PumpTokenStats {
  address: string;
  holder_count: number;
  total_supply: number;
  creation_date?: string;
  last_activity?: string;
  volume_24h: number;
  price_change_24h: number;
  market_cap: number;
}

export interface PumpTokenActivity {
  timestamp: string;
  transaction_type: string;
  amount: number;
  price?: number;
  transaction_signature: string;
}

export const pumpAnalyticsApi = {
  // Get recent pump tokens
  getRecentPumpTokens: async (params: {
    limit?: number;
    include_stats?: boolean;
    min_holder_count?: number;
    min_volume?: number;
  }) => {
    const response = await apiClient.get('/soleco/mints/new/recent', { 
      params,
      timeout: 60000 // 60 second timeout
    });
    return response.data;
  },

  // Get new pump tokens
  getNewPumpTokens: async (params: {
    time_window?: number;
    min_holder_count?: number;
    exclude_zero_volume?: boolean;
  }) => {
    const response = await apiClient.get('/soleco/mints/new/pump', { 
      params,
      timeout: 60000 // 60 second timeout
    });
    return response.data;
  },

  // Search pump tokens
  searchPumpTokens: async (params: {
    query: string;
    match_type?: 'exact' | 'contains' | 'prefix';
    include_inactive?: boolean;
    sort_by?: 'volume' | 'holders' | 'market_cap' | 'creation_date';
  }) => {
    const response = await apiClient.get('/soleco/mints/search', { 
      params,
      timeout: 60000 // 60 second timeout
    });
    return response.data;
  },

  // Get token analytics
  getTokenAnalytics: async (
    tokenAddress: string,
    params: {
      time_range?: '1h' | '24h' | '7d' | '30d';
      include_holders?: boolean;
      include_transactions?: boolean;
    }
  ) => {
    const response = await apiClient.get(`/soleco/mints/analytics/${tokenAddress}`, { 
      params,
      timeout: 60000 // 60 second timeout
    });
    return response.data;
  },

  // Get trending pump tokens
  getTrendingPumpTokens: async (params: {
    timeframe: '1h' | '24h' | '7d';
    sort_metric?: 'volume' | 'price_change' | 'holder_growth';
    min_market_cap?: number;
  }) => {
    try {
      const response = await apiClient.get('/soleco/pump_trending/pump/trending', { 
        params,
        timeout: 90000 // 90 second timeout for this specific endpoint
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching trending pump tokens:', error);
      throw error;
    }
  }
};
