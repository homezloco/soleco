import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ChakraProvider } from '@chakra-ui/react';
import Dashboard from './Dashboard';
import { 
  NetworkStatusCard,
  MintAnalyticsCard,
  RPCNodesCard,
  PumpTokensCard,
  PerformanceMetricsCard
} from './components';

// Create a test wrapper with all the necessary providers
const createTestWrapper = (Component: React.ComponentType) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider>
        <Component />
      </ChakraProvider>
    </QueryClientProvider>
  );
};

// Mock the API calls
jest.mock('../../api/dashboardService', () => ({
  dashboardApi: {
    getNetworkStatus: jest.fn().mockResolvedValue({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      network_summary: {
        total_nodes: 1000,
        rpc_nodes_available: 500,
        rpc_availability_percentage: 50,
        latest_version: '1.14.0',
        nodes_on_latest_version_percentage: 75,
        version_distribution: [
          { version: '1.14.0', count: 750, percentage: 75 },
          { version: '1.13.0', count: 250, percentage: 25 }
        ],
        total_versions_in_use: 2,
        total_feature_sets_in_use: 2
      }
    }),
    getRPCNodes: jest.fn().mockResolvedValue({
      status: 'success',
      timestamp: new Date().toISOString(),
      total_rpc_nodes: 500,
      version_distribution: [
        { version: '1.14.0', count: 375, percentage: 75 },
        { version: '1.13.0', count: 125, percentage: 25 }
      ]
    }),
    getRecentMints: jest.fn().mockResolvedValue({
      success: true,
      timestamp: new Date().toISOString(),
      block_range: { start: 100, end: 95 },
      results: [
        {
          block_number: 100,
          timestamp: new Date().toISOString(),
          mint_addresses: ['addr1', 'addr2'],
          new_mint_addresses: ['addr1'],
          pump_token_addresses: ['addr1'],
          success: true
        }
      ],
      summary: {
        total_blocks: 5,
        total_mints: 10,
        total_pump_tokens: 5
      }
    }),
    getPerformanceMetrics: jest.fn().mockResolvedValue({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      performance_samples: [
        { slot: 100, num_transactions: 1000, num_slots: 10, sample_period_secs: 10 }
      ],
      summary_stats: {
        total_transactions: 1000,
        transactions_per_second_max: 100,
        transactions_per_second_avg: 50,
        total_blocks_produced: 100,
        total_slots_skipped: 10,
        block_time_avg_ms: 500,
        slot_skip_rate: 0.1
      }
    })
  }
}));

jest.mock('../../api/pumpAnalytics', () => ({
  pumpAnalyticsApi: {
    getTrendingPumpTokens: jest.fn().mockResolvedValue({
      timestamp: new Date().toISOString(),
      tokens: [
        {
          address: 'token1',
          name: 'Token 1',
          symbol: 'TKN1',
          price: 0.1,
          price_change_24h: 5,
          volume_24h: 10000,
          holder_count: 100
        }
      ]
    })
  }
}));

describe('Dashboard Components', () => {
  test('Dashboard renders correctly', () => {
    render(createTestWrapper(Dashboard));
    expect(screen.getByText('Solana Ecosystem Dashboard')).toBeInTheDocument();
  });

  test('NetworkStatusCard renders correctly', () => {
    render(createTestWrapper(NetworkStatusCard));
    // Initial loading state should be visible
    expect(screen.getByText('Network Status')).toBeInTheDocument();
  });

  test('MintAnalyticsCard renders correctly', () => {
    render(createTestWrapper(MintAnalyticsCard));
    expect(screen.getByText('Mint Analytics')).toBeInTheDocument();
  });

  test('RPCNodesCard renders correctly', () => {
    render(createTestWrapper(RPCNodesCard));
    expect(screen.getByText('RPC Nodes')).toBeInTheDocument();
  });

  test('PumpTokensCard renders correctly', () => {
    render(createTestWrapper(PumpTokensCard));
    expect(screen.getByText('Trending Pump Tokens')).toBeInTheDocument();
  });

  test('PerformanceMetricsCard renders correctly', () => {
    render(createTestWrapper(PerformanceMetricsCard));
    expect(screen.getByText('Network Performance')).toBeInTheDocument();
  });
});
