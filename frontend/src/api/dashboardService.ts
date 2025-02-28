import { apiClient } from './client';

// Network Status Types
export interface NetworkSummary {
  total_nodes?: number;
  rpc_nodes_available?: number;
  rpc_availability_percentage?: number;
  latest_version?: string;
  nodes_on_latest_version_percentage?: number;
  version_distribution?: {
    version: string;
    count: number;
    percentage: number;
  }[];
  total_versions_in_use?: number;
  total_feature_sets_in_use?: number;
  // Validator-related fields
  total_stake?: number;
  active_validators?: number;
  delinquent_validators?: number;
  delinquent_stake?: number;
  processing_errors?: number;
  active_stake_percentage?: number;
  delinquent_stake_percentage?: number;
}

export interface ClusterNodes {
  total_nodes: number;
  stake_distribution: {
    total_stake: number;
    active_validators: number;
    delinquent_validators: number;
    delinquent_stake: number;
    processing_errors: number;
    top_10_validators: number;
    top_20_validators: number;
  };
}

export interface NetworkStatus {
  status: string;
  errors: string[];
  timestamp: string;
  network_summary: NetworkSummary;
  cluster_nodes?: ClusterNodes;
  network_version?: any;
  epoch_info?: any;
  performance_metrics?: {
    samples_analyzed: number;
    average_slots_per_sample: number;
    average_transactions_per_sample: number;
    average_non_vote_transactions_per_sample: number;
    recent_tps: number;
    recent_non_vote_tps: number;
    sample_period_secs: number;
    slot_time_ms: number;
    slots_per_second: number;
    block_time_ms: number;
  };
}

// RPC Nodes Types
export interface RPCNode {
  pubkey: string;
  rpc_endpoint: string;
  version: string;
  feature_set: number;
  gossip?: string;
  shred_version?: number;
  is_healthy?: boolean;
}

export interface RPCNodesResponse {
  total_nodes: number;
  version_distribution: {
    version: string;
    count: number;
    percentage: number;
  }[] | Record<string, number>;
  well_known_rpc_urls: string[];
  solana_official_urls: string[];
  conversion_stats: {
    attempted: number;
    successful: number;
    failed: number;
    skipped: number;
  };
  converted_rpc_urls: string[];
  timestamp: string;
  execution_time_ms: number;
}

// Mint Analytics Types
export interface MintResult {
  block_number: number;
  timestamp: string;
  mint_addresses: string[];
  new_mint_addresses: string[];
  pump_token_addresses: string[];
  success: boolean;
}

export interface MintAnalyticsResponse {
  success: boolean;
  timestamp?: string;
  block_range?: {
    start: number;
    end: number;
  };
  results?: MintResult[];
  summary: {
    total_blocks?: number;
    total_mints?: number;
    total_pump_tokens?: number;
    total_new_mints?: number;
    blocks_processed?: number;
  };
  new_mints?: string[];
  pump_tokens?: string[];
  stats?: {
    total_all_mints: number;
    total_new_mints: number;
    total_pump_tokens: number;
    mint_operations: number;
    token_operations: number;
  };
}

// Performance Metrics Types
export interface PerformanceMetrics {
  status: string;
  timestamp: string;
  performance_samples: {
    slot: number;
    numTransactions: number;
    numNonVoteTransactions: number;
    numSlots: number;
    samplePeriodSecs: number;
  }[];
  tps_statistics: {
    current_tps: number;
    max_tps: number;
    min_tps: number;
    average_tps: number;
  };
  block_production_statistics: {
    total_blocks: number;
    total_slots: number;
    current_slot: number;
    leader_slots: number;
    blocks_produced: number;
    skipped_slots: number;
    skipped_slot_percentage: number;
  };
}

// Dashboard API Service
export const dashboardApi = {
  // Get network status
  getNetworkStatus(summaryOnly: boolean = true): Promise<NetworkStatus> {
    return apiClient.get('/soleco/solana/network/status', {
      params: { summary_only: summaryOnly },
      timeout: 30000
    }).then(response => {
      const data = response.data;
      
      // Log warning if validators data is missing (all zeros)
      if (data && data.network_summary && 
          data.network_summary.total_stake === 0 &&
          data.network_summary.active_validators === 0 &&
          data.network_summary.delinquent_validators === 0) {
        console.warn('Warning: Validator data is unavailable in network status response');
      }
      
      return data;
    }).catch(error => {
      console.error('Error fetching network status:', error);
      // Return a minimal valid response to prevent UI errors
      return {
        status: 'error',
        errors: [error.message || 'Failed to fetch network status'],
        timestamp: new Date().toISOString(),
        network_summary: {
          total_nodes: 0,
          rpc_nodes_available: 0,
          rpc_availability_percentage: 0,
          latest_version: 'unknown',
          nodes_on_latest_version_percentage: 0,
          version_distribution: [],
          total_versions_in_use: 0,
          total_feature_sets_in_use: 0,
          total_stake: 0,
          active_validators: 0,
          delinquent_validators: 0,
          delinquent_stake: 0,
          processing_errors: 0,
          active_stake_percentage: 0,
          delinquent_stake_percentage: 0
        }
      };
    });
  },
  
  // Get RPC nodes
  getRPCNodes(includeDetails: boolean = false, healthCheck: boolean = false): Promise<RPCNodesResponse> {
    return apiClient.get('/soleco/network/rpc-nodes', {
      params: { 
        include_details: includeDetails,
        health_check: healthCheck,
        skip_dns_lookup: false,
        include_raw_urls: true,
        prioritize_clean_urls: true,
        include_well_known: true
      },
      timeout: 60000 // This can take longer
    }).then(response => {
      const data = response.data;
      
      // Ensure version_distribution is in the expected format
      if (data && data.version_distribution) {
        console.log('Original version_distribution type:', typeof data.version_distribution);
        
        // If it's an object but not an array, convert it to the expected format
        if (typeof data.version_distribution === 'object' && 
            !Array.isArray(data.version_distribution)) {
          console.log('Converting version_distribution object to array format');
          // Keep the original format for compatibility
        }
      }
      
      return data;
    }).catch(error => {
      console.error('Error fetching RPC nodes:', error);
      // Return a minimal valid response to prevent UI errors
      return {
        total_nodes: 0,
        version_distribution: [],
        well_known_rpc_urls: [],
        solana_official_urls: [],
        conversion_stats: {
          attempted: 0,
          successful: 0,
          failed: 0,
          skipped: 0
        },
        converted_rpc_urls: [],
        timestamp: new Date().toISOString(),
        execution_time_ms: 0
      };
    });
  },
  
  // Get recent mints
  getRecentMints(blocks: number = 2): Promise<MintAnalyticsResponse> {
    return apiClient.get('/soleco/mints/new/recent', {
      params: { blocks },
      timeout: 30000
    }).then(response => response.data);
  },
  
  // Get mint statistics
  getMintStatistics(timeframe: '1h' | '24h' | '7d' = '24h') {
    return apiClient.get('/soleco/mints/statistics', {
      params: { timeframe },
      timeout: 30000
    }).then(response => response.data);
  },
  
  // Get performance metrics
  getPerformanceMetrics(): Promise<PerformanceMetrics> {
    return apiClient.get('/soleco/solana/performance/metrics', {
      timeout: 30000
    }).then(response => response.data);
  },
  
  // Get recent pump tokens
  getRecentPumpTokens(limit: number = 10, includeStats: boolean = true) {
    return apiClient.get('/soleco/pump_trending/pump/recent', {
      params: { 
        limit,
        include_stats: includeStats
      },
      timeout: 30000
    }).then(response => response.data);
  },
  
  // Get trending pump tokens
  getTrendingPumpTokens(timeframe: '1h' | '24h' | '7d' = '24h') {
    return apiClient.get('/soleco/pump_trending/pump/trending', {
      params: { timeframe },
      timeout: 30000
    }).then(response => response.data);
  },

  // Get network status history
  getNetworkStatusHistory(hours: number = 24, limit: number = 24) {
    return apiClient.get('/soleco/analytics/network/history', {
      params: { hours, limit },
      timeout: 30000
    })
    .then(response => {
      console.log('Network Status History raw response:', response);
      // Check if response.data is an object with a data property
      if (response.data && typeof response.data === 'object' && 'data' in response.data) {
        return response.data.data;
      }
      // Otherwise return the data directly
      return response.data || [];
    })
    .catch(error => {
      console.error('Error fetching network status history:', error);
      return [];
    });
  },

  // Get mint analytics history
  getMintAnalyticsHistory(blocks: number = 2, hours: number = 24, limit: number = 24) {
    return apiClient.get('/soleco/analytics/mint/history', {
      params: { blocks, hours, limit },
      timeout: 30000
    })
    .then(response => {
      console.log('Mint Analytics History raw response:', response);
      // Check if response.data is an object with a data property
      if (response.data && typeof response.data === 'object' && 'data' in response.data) {
        return response.data.data;
      }
      // Otherwise return the data directly
      return response.data || [];
    })
    .catch(error => {
      console.error('Error fetching mint analytics history:', error);
      return [];
    });
  },

  // Get pump tokens history
  getPumpTokensHistory(timeframe: string = '24h', sortMetric: string = 'volume', hours: number = 24, limit: number = 24) {
    console.log(`Getting pump tokens history: timeframe=${timeframe}, sortMetric=${sortMetric}, hours=${hours}, limit=${limit}`);
    return apiClient.get('/soleco/analytics/pump/history', {
      params: { timeframe, sort_metric: sortMetric, hours, limit },
      timeout: 30000
    })
    .then(response => {
      console.log('Pump tokens history response:', response);
      return response.data || [];
    })
    .catch(error => {
      console.error('Error fetching pump tokens history:', error);
      return [];
    });
  },

  // Get RPC nodes history
  getRPCNodesHistory(hours: number = 24, limit: number = 24) {
    return apiClient.get('/soleco/analytics/rpc/history', {
      params: { hours, limit },
      timeout: 30000
    })
    .then(response => response.data || [])
    .catch(error => {
      console.error('Error fetching RPC nodes history:', error);
      return [];
    });
  },

  // Get performance metrics history
  getPerformanceMetricsHistory(hours: number = 24, limit: number = 24) {
    return apiClient.get('/soleco/analytics/performance/history', {
      params: { hours, limit },
      timeout: 30000
    })
    .then(response => response.data || [])
    .catch(error => {
      console.error('Error fetching performance metrics history:', error);
      return [];
    });
  }
};

export const fetchPumpTokensHistory = async (
  timeframe: string = '24h',
  sortMetric: string = 'volume',
  hours: number = 24,
  limit: number = 24
): Promise<any[]> => {
  console.log(`Fetching pump tokens history for timeframe: ${timeframe}, sortMetric: ${sortMetric}, hours: ${hours}, limit: ${limit}`);
  try {
    const response = await dashboardApi.getPumpTokensHistory(timeframe, sortMetric, hours, limit);
    
    // Check if response exists and has data
    if (!response) {
      console.error('Pump tokens history response is undefined or null');
      return [];
    }
    
    // Log the response for debugging
    console.log('Pump tokens history response:', response);
    
    // Handle different response formats
    if (Array.isArray(response)) {
      return response;
    } else if (response && typeof response === 'object') {
      // If response is an object with a data property that is an array
      if (response.data && Array.isArray(response.data)) {
        return response.data;
      }
      
      // If response is just an object, wrap it in an array
      return [response];
    }
    
    console.error('Unexpected pump tokens history response format:', response);
    return [];
  } catch (error) {
    console.error('Error fetching pump tokens history:', error);
    return [];
  }
};

export const fetchNetworkStatusHistory = async (hours: number = 24): Promise<any[]> => {
  console.log(`Fetching network status history for the past ${hours} hours`);
  try {
    const response = await dashboardApi.getNetworkStatusHistory(hours);
    
    // Check if response exists and has data
    if (!response) {
      console.error('Network status history response is undefined or null');
      return [];
    }
    
    // Log the response for debugging
    console.log('Network status history response:', response);
    
    // Handle different response formats
    if (Array.isArray(response)) {
      return response;
    } else if (response && typeof response === 'object') {
      // If response is an object with a data property that is an array
      if (response.data && Array.isArray(response.data)) {
        return response.data;
      }
      
      // If response is just an object, wrap it in an array
      return [response];
    }
    
    console.error('Unexpected network status history response format:', response);
    return [];
  } catch (error) {
    console.error('Error fetching network status history:', error);
    return [];
  }
};

export const fetchMintAnalyticsHistory = async (blocks: number = 2, hours: number = 24): Promise<any[]> => {
  console.log(`Fetching mint analytics history for the past ${hours} hours (blocks: ${blocks})`);
  try {
    const response = await dashboardApi.getMintAnalyticsHistory(blocks, hours);
    
    // Check if response exists and has data
    if (!response) {
      console.error('Mint analytics history response is undefined or null');
      return [];
    }
    
    // Log the response for debugging
    console.log('Mint analytics history response:', response);
    
    // Handle different response formats
    if (Array.isArray(response)) {
      return response;
    } else if (response && typeof response === 'object') {
      // If response is an object with a data property that is an array
      if (response.data && Array.isArray(response.data)) {
        return response.data;
      }
      
      // If response is just an object, wrap it in an array
      return [response];
    }
    
    console.error('Unexpected mint analytics history response format:', response);
    return [];
  } catch (error) {
    console.error('Error fetching mint analytics history:', error);
    return [];
  }
};
