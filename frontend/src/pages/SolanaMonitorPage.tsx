import React from 'react';
import { Box, Container, Heading } from '@chakra-ui/react';
import SolanaMonitoringDashboard from '../components/Solana/SolanaMonitoringDashboard';

/**
 * Page component for the Solana Network Monitor
 */
const SolanaMonitorPage: React.FC = () => {
  return (
    <Container maxW="container.xl" py={6}>
      <Box mb={6}>
        <Heading as="h1" size="xl">Solana Network Monitor</Heading>
      </Box>
      
      <SolanaMonitoringDashboard />
    </Container>
  );
};

export default SolanaMonitorPage;
