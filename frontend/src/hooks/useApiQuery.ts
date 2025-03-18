import { useQuery, UseQueryOptions, UseQueryResult } from 'react-query';

/**
 * Custom hook for API queries with standardized caching
 * 
 * @param queryKey - The query key for React Query cache
 * @param queryFn - The function that fetches data
 * @param options - Additional React Query options
 * @param refetchInterval - Optional refetch interval in milliseconds (default: 5 minutes)
 * @returns UseQueryResult
 */
export function useApiQuery<TData = unknown, TError = unknown>(
  queryKey: string | unknown[],
  queryFn: () => Promise<TData>,
  options?: Omit<UseQueryOptions<TData, TError, TData>, 'queryKey' | 'queryFn'>,
  refetchInterval: number = 5 * 60 * 1000 // 5 minutes default
): UseQueryResult<TData, TError> {
  return useQuery<TData, TError>(
    queryKey,
    queryFn,
    {
      ...options,
      refetchInterval,
      // These will use the global defaults unless overridden
      staleTime: options?.staleTime,
      cacheTime: options?.cacheTime,
    }
  );
}

/**
 * Custom hook for API queries with forced refresh capability
 * 
 * @param queryKey - The query key for React Query cache
 * @param queryFn - The function that fetches data
 * @param refreshParam - Whether to force a refresh (pass to backend)
 * @param options - Additional React Query options
 * @param refetchInterval - Optional refetch interval in milliseconds (default: 5 minutes)
 * @returns UseQueryResult
 */
export function useRefreshableApiQuery<TData = unknown, TError = unknown>(
  queryKey: string | unknown[],
  queryFn: (refresh: boolean) => Promise<TData>,
  refreshParam: boolean = false,
  options?: Omit<UseQueryOptions<TData, TError, TData>, 'queryKey' | 'queryFn'>,
  refetchInterval: number = 5 * 60 * 1000 // 5 minutes default
): UseQueryResult<TData, TError> {
  return useQuery<TData, TError>(
    Array.isArray(queryKey) ? [...queryKey, { refresh: refreshParam }] : [queryKey, { refresh: refreshParam }],
    () => queryFn(refreshParam),
    {
      ...options,
      refetchInterval,
      // These will use the global defaults unless overridden
      staleTime: options?.staleTime,
      cacheTime: options?.cacheTime,
    }
  );
}
