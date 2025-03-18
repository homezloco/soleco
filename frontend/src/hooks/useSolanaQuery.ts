import { useQuery, UseQueryOptions, UseQueryResult } from 'react-query';
import React from 'react';

/**
 * Custom hook for making Solana API queries with refresh capability
 * 
 * @param queryKey - Unique key for React Query cache
 * @param queryFn - Function that makes the API call
 * @param options - Additional React Query options
 * @param refetchInterval - Optional refetch interval in milliseconds (default: 5 minutes)
 * @returns UseQueryResult with additional refresh function
 */
export function useSolanaQuery<TData, TError = unknown>(
  queryKey: string | readonly unknown[],
  queryFn: (refresh?: boolean) => Promise<TData>,
  options?: Omit<UseQueryOptions<TData, TError, TData>, 'queryKey' | 'queryFn'>,
  refetchInterval: number = 5 * 60 * 1000 // 5 minutes default
) {
  const formattedQueryKey = Array.isArray(queryKey) 
    ? ['solana', ...queryKey] 
    : ['solana', queryKey];
  
  const [refreshParam, setRefreshParam] = React.useState(false);
  
  // Reset refresh param after query completes
  React.useEffect(() => {
    if (refreshParam) {
      const timer = setTimeout(() => {
        setRefreshParam(false);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [refreshParam]);
  
  const queryResult = useQuery<TData, TError>(
    [...formattedQueryKey, { refresh: refreshParam }],
    () => queryFn(refreshParam),
    {
      ...options,
      refetchInterval,
      // These will use the global defaults unless overridden
      staleTime: options?.staleTime,
      cacheTime: options?.cacheTime,
    }
  );
  
  // Add a refresh function that triggers a refetch with refresh=true
  const refresh = React.useCallback(() => {
    setRefreshParam(true);
    return queryResult.refetch();
  }, [queryResult.refetch]);
  
  return {
    ...queryResult,
    refresh,
    isRefetching: queryResult.isRefetching || refreshParam,
  };
}

export default useSolanaQuery;
