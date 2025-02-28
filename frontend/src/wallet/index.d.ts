/**
 * Type declarations for the wallet module
 */

declare module 'wallet' {
  // Wallet types
  export interface WalletInfo {
    address: string;
    balance: number;
    isConnected: boolean;
  }

  // Transaction types
  export interface Transaction {
    id: string;
    amount: number;
    timestamp: string;
    status: 'pending' | 'confirmed' | 'failed';
  }

  // Wallet provider types
  export interface WalletProvider {
    name: string;
    icon: string;
    isInstalled: boolean;
  }
}
