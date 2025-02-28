import axios from 'axios';

// Use the environment variable for the API base URL
const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || '/api';

// Log the API base URL for debugging
console.log('API Base URL:', API_BASE_URL);

// Create Axios instance with base configuration
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 second default timeout
  headers: {
    'Content-Type': 'application/json'
  },
  // Add validation
  validateStatus: (status) => status >= 200 && status < 500,
});

// Add a request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    // Log the request for debugging
    if (import.meta.env.DEV) {
      console.log(`API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`, config.params || {});
    }
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add a response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    // Log successful responses in development
    if (import.meta.env.DEV) {
      console.log(`API Response: ${response.status} ${response.config.url}`, 
        response.data ? '[Data received]' : '[No data]');
    }
    return response;
  },
  (error) => {
    // Handle and log errors
    if (error.response) {
      console.error(`API Error ${error.response.status}:`, error.response.data);
    } else if (error.request) {
      console.error('API Request failed (no response):', error.request);
    } else {
      console.error('API Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// Add types for API responses
export interface TokenInfo {
  address: string;
  symbol: string;
  name: string;
  price: number;
  volume_24h: number;
}

export interface SwapRoute {
  route_id: string;
  in_amount: number;
  out_amount: number;
  price_impact_pct: number;
}

export interface PoolInfo {
  id: string;
  name: string;
  token_a_symbol: string;
  token_b_symbol: string;
  liquidity: number;
  volume_24h: number;
}

// Helper function to handle API timeouts more gracefully
export const withTimeout = async <T>(
  promise: Promise<T>,
  timeoutMs: number = 60000,
  errorMessage: string = 'Request timed out'
): Promise<T> => {
  let timeoutId: NodeJS.Timeout | undefined;
  
  const timeoutPromise = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new Error(errorMessage));
    }, timeoutMs);
  });
  
  try {
    const result = await Promise.race([promise, timeoutPromise]);
    if (timeoutId) clearTimeout(timeoutId);
    return result as T;
  } catch (error) {
    if (timeoutId) clearTimeout(timeoutId);
    throw error;
  }
};

// API functions
export const jupiterApi = {
  getRoutes: async (params: { 
    input_mint: string; 
    output_mint: string; 
    amount: number; 
    slippage_bps?: number; 
  }) => {
    const response = await apiClient.get<SwapRoute[]>('/external/jupiter/routes', { params });
    return response.data;
  },
  
  getTokens: async () => {
    const response = await apiClient.get('/external/jupiter/tokens');
    return response.data;
  },
};

export const raydiumApi = {
  getPools: async () => {
    const response = await apiClient.get<PoolInfo[]>('/external/raydium/pools');
    return response.data;
  },
  
  getTokenPrice: async (tokenMint: string) => {
    const response = await apiClient.get(`/external/raydium/price/${tokenMint}`);
    return response.data;
  },
};

export const birdeyeApi = {
  getTokenInfo: async (tokenAddress: string, apiKey: string) => {
    const response = await apiClient.get<TokenInfo>(`/external/birdeye/token/${tokenAddress}`, {
      headers: {
        'X-API-KEY': apiKey,
      },
    });
    return response.data;
  },
  
  getTokenPairs: async (tokenAddress: string, apiKey: string) => {
    const response = await apiClient.get(`/external/birdeye/pairs/${tokenAddress}`, {
      headers: {
        'X-API-KEY': apiKey,
      },
    });
    return response.data;
  },
};
