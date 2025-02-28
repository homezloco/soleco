/**
 * Type definitions for Pump.fun API responses
 */

export interface PumpToken {
  mint: string;
  name?: string;
  symbol?: string;
  image_uri?: string;
  price?: number;
  price_change_1h?: number;
  price_change_24h?: number;
  price_change_7d?: number;
  volume_24h?: number;
  market_cap?: number;
  liquidity?: number;
  virtual_sol_reserves?: number;
  virtual_token_reserves?: number;
  creation_time?: number;
  website?: string;
  twitter?: string;
  telegram?: string;
  discord?: string;
  description?: string;
}

export interface PumpTrade {
  signature: string;
  mint: string;
  name?: string;
  symbol?: string;
  image_uri?: string;
  price: number;
  amount: number;
  value: number;
  timestamp: number;
  block: number;
  buyer: string;
  seller: string;
  is_buy: boolean;
}

export interface PumpMarketOverview {
  total_tokens: number;
  total_volume_24h: number;
  total_trades_24h: number;
  new_tokens_24h: number;
  sol_price: number;
  sol_price_change_24h: number;
  most_active_tokens: PumpToken[];
}

export interface PumpKingOfTheHill {
  mint: string;
  name?: string;
  symbol?: string;
  image_uri?: string;
  price?: number;
  price_change_24h?: number;
  volume_24h?: number;
  market_cap?: number;
  liquidity?: number;
  creation_time?: number;
  crowned_time?: number;
  website?: string;
  twitter?: string;
  telegram?: string;
  discord?: string;
  description?: string;
}
