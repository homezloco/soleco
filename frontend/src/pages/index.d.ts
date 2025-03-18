/**
 * Type definitions for pages
 */

declare module 'pages/SolanaMonitorPage' {
  import React from 'react';
  
  export interface SolanaMonitorPageProps {
    // Add any props here if needed
  }
  
  const SolanaMonitorPage: React.FC<SolanaMonitorPageProps>;
  
  export default SolanaMonitorPage;
}

declare module 'pages' {
  export * from 'pages/SolanaMonitorPage';
}
