/**
 * Type declarations for the mocks module
 */

declare module 'mocks' {
  // Mock data types
  export interface MockData<T> {
    data: T;
    delay?: number;
    error?: boolean;
    errorMessage?: string;
  }
}
