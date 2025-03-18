import React, { useState } from 'react';
import { 
  Box, 
  SimpleGrid, 
  Heading, 
  Container, 
  Tabs, 
  TabList, 
  TabPanels, 
  Tab, 
  TabPanel,
  Text,
  Flex,
  Badge,
  Tooltip
} from '@chakra-ui/react';
import NetworkStatusCard from './NetworkStatusCard';
import EnhancedNetworkStatusCard from './EnhancedNetworkStatusCard';
import PerformanceMetricsCard from './PerformanceMetricsCard';
import RpcNodesCard from './RpcNodesCard';

/**
 * Dashboard component that displays Solana network monitoring information
 */
const SolanaMonitoringDashboard: React.FC = () => {
  const [useEnhancedStatus, setUseEnhancedStatus] = useState(true);
  
  return (
    <Container maxW="container.xl" py={6}>
      <Heading as="h1" size="xl" mb={2}>Solana Network Monitor</Heading>
      <Flex mb={6} alignItems="center">
        <Text color="gray.500">Comprehensive monitoring for the Solana blockchain network</Text>
        <Tooltip label="Using enhanced error handling and reliability improvements">
          <Badge colorScheme="green" ml={2}>v2.0</Badge>
        </Tooltip>
      </Flex>
      
      <Tabs variant="enclosed" mb={6} onChange={(index) => setUseEnhancedStatus(index === 0)}>
        <TabList>
          <Tab>Enhanced Status</Tab>
          <Tab>Legacy Status</Tab>
        </TabList>
        <TabPanels>
          <TabPanel px={0}>
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6} mb={6}>
              <EnhancedNetworkStatusCard />
              <PerformanceMetricsCard />
            </SimpleGrid>
          </TabPanel>
          <TabPanel px={0}>
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6} mb={6}>
              <NetworkStatusCard />
              <PerformanceMetricsCard />
            </SimpleGrid>
          </TabPanel>
        </TabPanels>
      </Tabs>
      
      <Box mb={6}>
        <RpcNodesCard />
      </Box>
    </Container>
  );
};

export default SolanaMonitoringDashboard;
