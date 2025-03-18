import React from 'react';
import {
  Box,
  Card,
  CardBody,
  CardHeader,
  Flex,
  Heading,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Text,
  Divider,
  SimpleGrid,
  useColorModeValue,
  Spinner,
} from '@chakra-ui/react';
import { solanaApi } from '../../api/solanaService';
import useSolanaQuery from '../../hooks/useSolanaQuery';
import RefreshButton from '../common/RefreshButton';

/**
 * Component that displays Solana performance metrics
 */
const PerformanceMetricsCard: React.FC = () => {
  // Use our custom hook to fetch performance metrics with refresh capability
  const { 
    data: performanceMetrics, 
    isLoading, 
    isError, 
    error, 
    refresh,
    isRefetching
  } = useSolanaQuery(
    ['solana', 'performance-metrics'],
    (refresh) => solanaApi.getPerformanceMetrics(refresh),
    {
      refetchInterval: 3 * 60 * 1000, // Refetch every 3 minutes
      staleTime: 1 * 60 * 1000, // Consider data stale after 1 minute
    }
  );

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  if (isLoading) {
    return (
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px" shadow="md">
        <CardHeader>
          <Flex justify="space-between" align="center">
            <Heading size="md">Solana Performance</Heading>
          </Flex>
        </CardHeader>
        <CardBody>
          <Flex justify="center" align="center" h="200px">
            <Spinner size="xl" color="blue.500" />
          </Flex>
        </CardBody>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px" shadow="md">
        <CardHeader>
          <Flex justify="space-between" align="center">
            <Heading size="md">Solana Performance</Heading>
            <RefreshButton onClick={refresh} isLoading={isRefetching} />
          </Flex>
        </CardHeader>
        <CardBody>
          <Text color="red.500">Error loading performance metrics: {(error as Error)?.message || 'Unknown error'}</Text>
        </CardBody>
      </Card>
    );
  }

  const tpsStats = performanceMetrics?.performance_samples;
  const blockStats = performanceMetrics?.block_production;
  
  return (
    <Card bg={cardBg} borderColor={borderColor} borderWidth="1px" shadow="md">
      <CardHeader>
        <Flex justify="space-between" align="center">
          <Heading size="md">Solana Performance</Heading>
          <RefreshButton onClick={refresh} isLoading={isRefetching} />
        </Flex>
      </CardHeader>
      <CardBody>
        <Flex direction="column" gap={4}>
          {/* TPS Statistics */}
          <Box>
            <Heading size="sm" mb={3}>Transaction Processing</Heading>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
              <Stat>
                <StatLabel>Average TPS</StatLabel>
                <StatNumber>{tpsStats?.mean_tps?.toFixed(2) || 'N/A'}</StatNumber>
                <StatHelpText>
                  Transactions per second
                </StatHelpText>
              </Stat>
              
              <Stat>
                <StatLabel>Peak TPS</StatLabel>
                <StatNumber>{tpsStats?.max_tps?.toFixed(2) || 'N/A'}</StatNumber>
                <StatHelpText>
                  Maximum observed
                </StatHelpText>
              </Stat>
              
              <Stat>
                <StatLabel>TPS Stability</StatLabel>
                <StatNumber>{tpsStats?.tps_std_dev?.toFixed(2) || 'N/A'}</StatNumber>
                <StatHelpText>
                  Standard deviation
                </StatHelpText>
              </Stat>
            </SimpleGrid>
          </Box>
          
          <Divider />
          
          {/* Block Production */}
          <Box>
            <Heading size="sm" mb={3}>Block Production</Heading>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
              <Stat>
                <StatLabel>Production Rate</StatLabel>
                <StatNumber>{(blockStats?.slot_production_rate * 100)?.toFixed(2) || 'N/A'}%</StatNumber>
                <StatHelpText>
                  Slots with blocks
                </StatHelpText>
              </Stat>
              
              <Stat>
                <StatLabel>Skip Rate</StatLabel>
                <StatNumber>{(blockStats?.skip_rate * 100)?.toFixed(2) || 'N/A'}%</StatNumber>
                <StatHelpText>
                  Slots without blocks
                </StatHelpText>
              </Stat>
              
              <Stat>
                <StatLabel>Total Slots</StatLabel>
                <StatNumber>{blockStats?.total_slots?.toLocaleString() || 'N/A'}</StatNumber>
                <StatHelpText>
                  {blockStats?.total_blocks_produced?.toLocaleString() || 'N/A'} blocks produced
                </StatHelpText>
              </Stat>
            </SimpleGrid>
          </Box>
          
          {/* Last Updated */}
          <Text fontSize="xs" color="gray.500" alignSelf="flex-end" mt={2}>
            Last updated: {new Date(performanceMetrics?.timestamp || '').toLocaleString()}
          </Text>
        </Flex>
      </CardBody>
    </Card>
  );
};

export default PerformanceMetricsCard;
