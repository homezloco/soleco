/**
 * Type declarations for the utils module
 */

declare module 'utils' {
  // Common utility types
  export interface FormatOptions {
    locale?: string;
    currency?: string;
    decimals?: number;
  }

  // Date formatting options
  export interface DateFormatOptions {
    format?: string;
    timezone?: string;
  }

  // Number formatting options
  export interface NumberFormatOptions {
    prefix?: string;
    suffix?: string;
    decimals?: number;
    groupSeparator?: string;
    decimalSeparator?: string;
  }
}
