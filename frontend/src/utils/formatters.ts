/**
 * Utility functions for formatting numbers, currencies, and percentages
 */

/**
 * Format a number with commas as thousands separators
 * @param value The number to format
 * @param decimals Number of decimal places to include
 * @returns Formatted number string
 */
export const formatNumber = (value: number | undefined | null, decimals: number = 0): string => {
  if (value === undefined || value === null) return '—';
  
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value);
};

/**
 * Format a number as USD currency
 * @param value The number to format as currency
 * @param decimals Number of decimal places to include
 * @returns Formatted currency string
 */
export const formatUSD = (value: number | undefined | null, decimals?: number): string => {
  if (value === undefined || value === null) return '$0.00';
  
  // Determine appropriate number of decimal places based on value
  let decimalPlaces = decimals;
  if (decimalPlaces === undefined) {
    if (value < 0.01) decimalPlaces = 6;
    else if (value < 1) decimalPlaces = 4;
    else if (value < 1000) decimalPlaces = 2;
    else decimalPlaces = 2;
  }
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimalPlaces,
    maximumFractionDigits: decimalPlaces
  }).format(value);
};

/**
 * Format a number as a percentage
 * @param value The number to format as percentage (e.g., 0.15 for 15%)
 * @param decimals Number of decimal places to include
 * @returns Formatted percentage string
 */
export const formatPercentage = (value: number | undefined | null, decimals: number = 2): string => {
  if (value === undefined || value === null) return '0.00%';
  
  // Convert to percentage (multiply by 100)
  const percentage = value * 100;
  
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
    signDisplay: 'exceptZero'
  }).format(value);
};

/**
 * Format a timestamp as a date string
 * @param timestamp Unix timestamp in seconds or milliseconds
 * @param format Format type ('date', 'datetime', 'time', 'relative')
 * @returns Formatted date string
 */
export const formatTimestamp = (
  timestamp: number | undefined | null, 
  format: 'date' | 'datetime' | 'time' | 'relative' = 'datetime'
): string => {
  if (!timestamp) return '—';
  
  // Convert to milliseconds if in seconds
  const ms = timestamp > 1000000000000 ? timestamp : timestamp * 1000;
  const date = new Date(ms);
  
  if (format === 'date') {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } else if (format === 'time') {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  } else if (format === 'relative') {
    const now = Date.now();
    const diff = now - ms;
    
    // Convert to appropriate time unit
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return `${seconds}s ago`;
  } else {
    // datetime format
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
};

/**
 * Format a number of bytes into a human-readable string
 * @param bytes Number of bytes
 * @param decimals Number of decimal places to include
 * @returns Formatted size string (e.g., "1.5 MB")
 */
export const formatBytes = (bytes: number | undefined | null, decimals: number = 2): string => {
  if (bytes === undefined || bytes === null || bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
};
