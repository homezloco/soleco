import axios from 'axios';

// Base URL for the backend API
const API_BASE_URL = '/api/soleco/solana';

// Define types for API responses
export interface NetworkStatus {
  status: string;
  timestamp: string;
  network_summary: {
    total_nodes: number;
    rpc_nodes_available: number;
    rpc_availability_percentage: number;
    latest_version: string;
    nodes_on_latest_version_percentage: number;
    version_distribution: Record<string, number>;
    total_versions_in_use: number;
    total_feature_sets_in_use: number;
  };
  cluster_nodes?: any;
  network_version?: any;
  epoch_info?: any;
  performance_metrics?: any;
  errors?: any[];
}

export interface EnhancedNetworkStatus {
  status: string;
  timestamp: string;
  node_count: number;
  active_nodes: number;
  delinquent_nodes: number;
  version_distribution: Record<string, { count: number; percentage: number }>;
  feature_set_distribution: Record<string, { count: number; percentage: number }>;
  stake_distribution: {
    high: { count: number; stake: number; stake_percentage: number };
    medium: { count: number; stake: number; stake_percentage: number };
    low: { count: number; stake: number; stake_percentage: number };
    delinquent: { count: number; stake: number; stake_percentage: number };
  };
  average_tps?: number;
  errors: Array<{
    source: string;
    error: string;
    type?: string;
    timestamp: string;
  }>;
}

export interface PerformanceMetrics {
  status: string;
  timestamp: string;
  performance_samples: {
    mean_tps: number;
    max_tps: number;
    min_tps: number;
    tps_std_dev: number;
    recent_tps: number[];
  };
  block_production: {
    total_slots: number;
    total_blocks_produced: number;
    total_slots_skipped: number;
    slot_production_rate: number;
    skip_rate: number;
    leader_slots_by_identity: Record<string, number>;
    blocks_produced_by_identity: Record<string, number>;
    skipped_slots_by_identity: Record<string, number>;
  };
}

export interface RpcNodes {
  status: string;
  timestamp: string;
  total_rpc_nodes: number;
  version_distribution: Record<string, number>;
  health_sample_size?: number;
  estimated_health_percentage?: number;
  rpc_nodes?: any[];
}

export interface TokenInfo {
  status: string;
  timestamp: string;
  token_info: {
    address: string;
    mint: string;
    supply: string;
    decimals: number;
    name?: string;
    symbol?: string;
    wallet_balance?: string;
    [key: string]: any;
  };
}

// Define the API service
export const solanaApi = {
  /**
   * Get Solana network status
   */
  getNetworkStatus: async (summaryOnly: boolean = true, refresh: boolean = false): Promise<NetworkStatus> => {
    const response = await axios.get(`${API_BASE_URL}/network/status`, {
      params: { 
        summary_only: summaryOnly,
        refresh
      }
    });
    return response.data;
  },

  /**
   * Get enhanced Solana network status with comprehensive metrics
   */
  async getEnhancedNetworkStatus(refresh: boolean = false): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE_URL}/solana/enhanced-network-status`, {
        params: { refresh }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching enhanced network status:', error);
      // Return a structured error response
      return {
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString()
      };
    }
  },

  /**
   * Get Solana performance metrics
   */
  getPerformanceMetrics: async (refresh: boolean = false): Promise<PerformanceMetrics> => {
    const response = await axios.get(`${API_BASE_URL}/performance/metrics`, {
      params: { refresh }
    });
    return response.data;
  },

  /**
   * Get available RPC nodes
   */
  getRpcNodes: async (
    includeDetails: boolean = false, 
    healthCheck: boolean = false, 
    includeAll: boolean = false,
    refresh: boolean = false,
    useEnhancedExtractor: boolean = true
  ): Promise<RpcNodes> => {
    const response = await axios.get(`${API_BASE_URL}/rpc-nodes`, {
      params: { 
        include_details: includeDetails, 
        health_check: healthCheck, 
        include_all: includeAll,
        refresh,
        use_enhanced_extractor: useEnhancedExtractor
      }
    });
    return response.data;
  },

  /**
   * Get token information
   */
  getTokenInfo: async (
    tokenAddress: string, 
    walletAddress?: string,
    refresh: boolean = false
  ): Promise<TokenInfo> => {
    const response = await axios.get(`${API_BASE_URL}/token/${tokenAddress}`, {
      params: { 
        wallet_address: walletAddress,
        refresh
      }
    });
    return response.data;
  }
};
