/**
 * Type declarations for the API module
 */

declare module 'api' {
  // Common API response types
  export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
  }

  // Network status types
  export interface NetworkSummary {
    total_nodes?: number;
    rpc_nodes_available?: number;
    latest_version?: string;
    nodes_on_latest_version_percentage?: number;
    version_distribution?: any[];
    rpc_availability_percentage?: number;
    total_versions_in_use?: number;
    total_feature_sets_in_use?: number;
  }

  export interface ClusterNodes {
    total_nodes?: number;
    active_nodes?: number;
    inactive_nodes?: number;
  }

  export interface NetworkStatusResponse {
    network_summary: NetworkSummary;
    cluster_nodes: ClusterNodes;
    status: string;
    timestamp: string;
  }
}
