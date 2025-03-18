import { useQuery, UseQueryOptions, UseQueryResult } from 'react-query';
import { useApiQuery } from './useApiQuery';

/**
 * Custom hook for Solana RPC API queries with standardized caching
 * 
 * @param queryKey - The query key for React Query cache
 * @param queryFn - The function that fetches data
 * @param options - Additional React Query options
 * @param refetchInterval - Optional refetch interval in milliseconds (default: 5 minutes)
 * @returns UseQueryResult
 */
export function useSolanaRpcQuery<TData = unknown, TError = unknown>(
  queryKey: string | unknown[],
  queryFn: () => Promise<TData>,
  options?: Omit<UseQueryOptions<TData, TError, TData>, 'queryKey' | 'queryFn'>,
  refetchInterval: number = 5 * 60 * 1000 // 5 minutes default
): UseQueryResult<TData, TError> {
  return useApiQuery<TData, TError>(
    Array.isArray(queryKey) ? ['solana-rpc', ...queryKey] : ['solana-rpc', queryKey],
    queryFn,
    options,
    refetchInterval
  );
}

/**
 * Custom hook for Solana RPC API queries with forced refresh capability
 * 
 * @param queryKey - The query key for React Query cache
 * @param queryFn - The function that fetches data with refresh parameter
 * @param refreshParam - Whether to force a refresh (pass to backend)
 * @param options - Additional React Query options
 * @param refetchInterval - Optional refetch interval in milliseconds (default: 5 minutes)
 * @returns UseQueryResult
 */
export function useRefreshableSolanaRpcQuery<TData = unknown, TError = unknown>(
  queryKey: string | unknown[],
  queryFn: (refresh: boolean) => Promise<TData>,
  refreshParam: boolean = false,
  options?: Omit<UseQueryOptions<TData, TError, TData>, 'queryKey' | 'queryFn'>,
  refetchInterval: number = 5 * 60 * 1000 // 5 minutes default
): UseQueryResult<TData, TError> {
  return useQuery<TData, TError>(
    Array.isArray(queryKey) ? ['solana-rpc', ...queryKey, { refresh: refreshParam }] : ['solana-rpc', queryKey, { refresh: refreshParam }],
    () => queryFn(refreshParam),
    {
      ...options,
      refetchInterval,
      // These will use the global defaults unless overridden
      staleTime: options?.staleTime,
      cacheTime: options?.cacheTime,
      // Add error handling specific to Solana RPC
      retry: (failureCount, error: any) => {
        // Don't retry if we get a specific Solana RPC error that indicates a permanent issue
        if (error?.response?.data?.error?.code === -32000) {
          return false;
        }
        // Default React Query retry logic (3 retries)
        return failureCount < 3;
      },
      onError: (error: any) => {
        console.error('Solana RPC query error:', error);
        if (options?.onError) {
          options.onError(error);
        }
      }
    }
  );
}
