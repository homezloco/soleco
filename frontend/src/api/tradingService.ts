import { apiClient } from './client';

// Define interfaces for trading-related data
export interface CoinData {
  mint: string;
  name?: string;
  symbol?: string;
  bonding_curve: string;
  associated_bonding_curve: string;
  virtual_sol_reserves: number;
  virtual_token_reserves: number;
  complete: boolean;
}

export interface TradeResponse {
  success: boolean;
  transaction_signature?: string;
  error?: string;
}

export interface TokenBalance {
  mint: string;
  balance: number;
}

export interface NetworkDiagnostics {
  rpc_status: string;
  connection_latency_ms: number;
  block_height: number;
  slot: number;
}

/**
 * Get coin data for a specific mint address
 * @param mintAddress The mint address to get data for
 * @returns Coin data or null if not found
 */
export const getCoinData = async (mintAddress: string): Promise<CoinData | null> => {
  try {
    const response = await apiClient.get<CoinData>(`/soleco/trade/coin-data/${mintAddress}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching coin data:', error);
    return null;
  }
};

/**
 * Buy a token
 * @param mintAddress The mint address of the token to buy
 * @param solAmount Amount of SOL to spend
 * @param slippage Slippage tolerance percentage
 * @returns Trade response
 */
export const buyToken = async (
  mintAddress: string, 
  solAmount: number, 
  slippage: number = 5
): Promise<TradeResponse> => {
  try {
    const response = await apiClient.post<TradeResponse>('/soleco/trade/buy', {
      mint: mintAddress,
      sol_amount: solAmount,
      slippage_percentage: slippage
    });
    return response.data;
  } catch (error) {
    console.error('Error buying token:', error);
    return {
      success: false,
      error: 'Failed to complete transaction'
    };
  }
};

/**
 * Sell a token
 * @param mintAddress The mint address of the token to sell
 * @param tokenAmount Amount of tokens to sell
 * @param slippage Slippage tolerance percentage
 * @returns Trade response
 */
export const sellToken = async (
  mintAddress: string, 
  tokenAmount: number, 
  slippage: number = 5
): Promise<TradeResponse> => {
  try {
    const response = await apiClient.post<TradeResponse>('/soleco/trade/sell', {
      mint: mintAddress,
      token_amount: tokenAmount,
      slippage_percentage: slippage
    });
    return response.data;
  } catch (error) {
    console.error('Error selling token:', error);
    return {
      success: false,
      error: 'Failed to complete transaction'
    };
  }
};

/**
 * Get token balances for the connected wallet
 * @returns Array of token balances
 */
export const getTokenBalances = async (): Promise<TokenBalance[]> => {
  try {
    const response = await apiClient.get<TokenBalance[]>('/soleco/trade/balances');
    return response.data;
  } catch (error) {
    console.error('Error fetching token balances:', error);
    return [];
  }
};

/**
 * Get network diagnostics
 * @returns Network diagnostics information
 */
export const getNetworkDiagnostics = async (): Promise<NetworkDiagnostics | null> => {
  try {
    const response = await apiClient.get<NetworkDiagnostics>('/soleco/trade/network-diagnostics');
    return response.data;
  } catch (error) {
    console.error('Error fetching network diagnostics:', error);
    return null;
  }
};
