// Mock data for development
const mockTokens = [
  {
    address: "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    name: "Mock Token 1",
    symbol: "MOCK1",
    holder_count: 1500,
    total_supply: 1000000,
    creation_date: "2025-02-20T00:00:00Z",
    last_activity: "2025-02-22T10:00:00Z",
    volume_24h: 50000,
    price_change_24h: 15.5,
    market_cap: 1000000
  },
  {
    address: "8xLKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    name: "Mock Token 2",
    symbol: "MOCK2",
    holder_count: 2500,
    total_supply: 2000000,
    creation_date: "2025-02-21T00:00:00Z",
    last_activity: "2025-02-22T11:00:00Z",
    volume_24h: 75000,
    price_change_24h: -5.2,
    market_cap: 2000000
  }
];

export const mockPumpAnalyticsApi = {
  getRecentPumpTokens: async () => mockTokens,
  getNewPumpTokens: async () => mockTokens,
  getTrendingPumpTokens: async () => mockTokens,
  searchPumpTokens: async () => mockTokens,
  getTokenAnalytics: async (tokenAddress: string) => ({
    token: mockTokens[0],
    analytics: {
      price_history: [],
      volume_history: [],
      holder_growth: []
    }
  })
};
