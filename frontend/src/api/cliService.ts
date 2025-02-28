import { apiClient } from './client';

export interface CLIInfo {
  version: string;
  description: string;
  features: Record<string, string>;
  installation: Record<string, string>;
  documentation_url: string;
}

/**
 * Fetch CLI information
 * @returns CLI information
 */
export const getCliInfo = async (): Promise<CLIInfo> => {
  try {
    const response = await apiClient.get<CLIInfo>('/soleco/cli/info');
    return response.data;
  } catch (error) {
    console.error('Error fetching CLI info:', error);
    throw error;
  }
};

/**
 * Get CLI download URL
 * @returns CLI download URL
 */
export const getCliDownloadUrl = (): string => {
  return '/api/soleco/cli/download';
};

/**
 * Get CLI documentation URL
 * @returns CLI documentation URL
 */
export const getCliDocsUrl = (): string => {
  return '/api/soleco/cli/docs';
};
