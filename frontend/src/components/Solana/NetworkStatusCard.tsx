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
  Progress,
  Badge,
  SimpleGrid,
  useColorModeValue,
  Spinner,
} from '@chakra-ui/react';
import { solanaApi } from '../../api/solanaService';
import useSolanaQuery from '../../hooks/useSolanaQuery';
import RefreshButton from '../common/RefreshButton';

/**
 * Component that displays the current Solana network status
 */
const NetworkStatusCard: React.FC = () => {
  // Use our custom hook to fetch network status with refresh capability
  const { 
    data: networkStatus, 
    isLoading, 
    isError, 
    error, 
    refresh,
    isRefetching
  } = useSolanaQuery(
    ['solana', 'network-status'],
    (refresh) => solanaApi.getNetworkStatus(true, refresh),
    {
      refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
      staleTime: 2 * 60 * 1000, // Consider data stale after 2 minutes
    }
  );

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  // Helper function to determine status color
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'success':
        return 'green';
      case 'degraded':
      case 'warning':
        return 'yellow';
      case 'error':
      case 'down':
        return 'red';
      default:
        return 'gray';
    }
  };

  if (isLoading) {
    return (
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px" shadow="md">
        <CardHeader>
          <Flex justify="space-between" align="center">
            <Heading size="md">Solana Network Status</Heading>
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
            <Heading size="md">Solana Network Status</Heading>
            <RefreshButton onClick={refresh} isLoading={isRefetching} />
          </Flex>
        </CardHeader>
        <CardBody>
          <Text color="red.500">Error loading network status: {(error as Error)?.message || 'Unknown error'}</Text>
        </CardBody>
      </Card>
    );
  }

  const summary = networkStatus?.network_summary;
  
  return (
    <Card bg={cardBg} borderColor={borderColor} borderWidth="1px" shadow="md">
      <CardHeader>
        <Flex justify="space-between" align="center">
          <Heading size="md">Solana Network Status</Heading>
          <RefreshButton onClick={refresh} isLoading={isRefetching} />
        </Flex>
      </CardHeader>
      <CardBody>
        <Flex direction="column" gap={4}>
          {/* Overall Status */}
          <Flex justify="space-between" align="center">
            <Text fontWeight="bold">Status:</Text>
            <Badge colorScheme={getStatusColor(networkStatus?.status || 'unknown')} px={2} py={1} borderRadius="full">
              {networkStatus?.status || 'Unknown'}
            </Badge>
          </Flex>
          
          <Divider />
          
          {/* Network Summary */}
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            <Stat>
              <StatLabel>Total Nodes</StatLabel>
              <StatNumber>{summary?.total_nodes || 0}</StatNumber>
              <StatHelpText>
                {summary?.rpc_nodes_available || 0} RPC nodes available
              </StatHelpText>
            </Stat>
            
            <Stat>
              <StatLabel>Latest Version</StatLabel>
              <StatNumber>{summary?.latest_version || 'Unknown'}</StatNumber>
              <StatHelpText>
                {summary?.nodes_on_latest_version_percentage || 0}% of nodes on latest
              </StatHelpText>
            </Stat>
          </SimpleGrid>
          
          <Divider />
          
          {/* RPC Availability */}
          <Box>
            <Flex justify="space-between" mb={1}>
              <Text fontSize="sm">RPC Availability</Text>
              <Text fontSize="sm" fontWeight="bold">
                {summary?.rpc_availability_percentage || 0}%
              </Text>
            </Flex>
            <Progress 
              value={summary?.rpc_availability_percentage || 0} 
              colorScheme={
                (summary?.rpc_availability_percentage || 0) > 80 ? 'green' : 
                (summary?.rpc_availability_percentage || 0) > 50 ? 'yellow' : 'red'
              }
              borderRadius="full"
              size="sm"
            />
          </Box>
          
          {/* Version Distribution */}
          {summary?.version_distribution && Object.keys(summary.version_distribution).length > 0 && (
            <Box mt={2}>
              <Text fontSize="sm" mb={2}>Version Distribution</Text>
              {Object.entries(summary.version_distribution).map(([version, count], index) => (
                <Flex key={index} justify="space-between" mb={1}>
                  <Text fontSize="xs">{version}</Text>
                  <Text fontSize="xs" fontWeight="bold">{count} nodes</Text>
                </Flex>
              ))}
            </Box>
          )}
          
          {/* Last Updated */}
          <Text fontSize="xs" color="gray.500" alignSelf="flex-end" mt={2}>
            Last updated: {new Date(networkStatus?.timestamp || '').toLocaleString()}
          </Text>
        </Flex>
      </CardBody>
    </Card>
  );
};

export default NetworkStatusCard;
