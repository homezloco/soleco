/**
 * Type definitions for hooks
 */

declare module 'hooks/useApiQuery' {
  export function useApiQuery<T>(url: string, options?: any): {
    data: T | undefined;
    isLoading: boolean;
    isError: boolean;
    error: any;
    refetch: () => void;
  };
  export default useApiQuery;
}

declare module 'hooks/usePumpFunQuery' {
  export function usePumpFunQuery<T>(url: string, options?: any): {
    data: T | undefined;
    isLoading: boolean;
    isError: boolean;
    error: any;
    refetch: () => void;
  };
  export default usePumpFunQuery;
}

declare module 'hooks/useSolanaQuery' {
  export function useSolanaQuery<T>(url: string, options?: any): {
    data: T | undefined;
    isLoading: boolean;
    isError: boolean;
    error: any;
    refetch: () => void;
  };
  export default useSolanaQuery;
}

declare module 'hooks/useSolanaRpcQuery' {
  export function useSolanaRpcQuery<T>(url: string, options?: any): {
    data: T | undefined;
    isLoading: boolean;
    isError: boolean;
    error: any;
    refetch: () => void;
  };
  export default useSolanaRpcQuery;
}

declare module 'hooks' {
  export * from 'hooks/useApiQuery';
  export * from 'hooks/usePumpFunQuery';
  export * from 'hooks/useSolanaQuery';
  export * from 'hooks/useSolanaRpcQuery';
}
