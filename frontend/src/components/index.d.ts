/**
 * Type declarations for the components module
 */

declare module 'components' {
  // Common component props
  export interface CardProps {
    title?: string;
    subtitle?: string;
    isLoading?: boolean;
    error?: Error | null;
    onRefresh?: () => void;
  }

  // Chart component props
  export interface ChartProps {
    data: any[];
    width?: number;
    height?: number;
    margin?: {
      top: number;
      right: number;
      bottom: number;
      left: number;
    };
  }
}
