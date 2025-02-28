/**
 * Global type declarations for the Soleco project
 */

// Declare module for API types
declare module 'api' {
  // Common API response types
  export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
  }

  // Re-export types from dashboardService
  export * from '../api/dashboardService';
}

// Declare module for component types
declare module 'components' {
  // Common component props
  export interface CardProps {
    title?: string;
    subtitle?: string;
    isLoading?: boolean;
    error?: Error | null;
    onRefresh?: () => void;
  }
}

// Declare module for mock data
declare module 'mocks' {
  // Mock data types
  export interface MockData<T> {
    data: T;
    delay?: number;
    error?: boolean;
    errorMessage?: string;
  }
}

// Declare module for utility functions
declare module 'utils' {
  // Common utility types
  export interface FormatOptions {
    locale?: string;
    currency?: string;
    decimals?: number;
  }
}

// Declare module for wallet integration
declare module 'wallet' {
  // Wallet types
  export interface WalletInfo {
    address: string;
    balance: number;
    isConnected: boolean;
  }
}
