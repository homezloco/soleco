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
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Tooltip,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Code,
  Button,
  Collapse,
} from '@chakra-ui/react';
import { solanaApi } from '../../api/solanaService';
import useSolanaQuery from '../../hooks/useSolanaQuery';
import RefreshButton from '../common/RefreshButton';
import { InfoIcon } from '@chakra-ui/icons';

// Define the enhanced network status interface
interface EnhancedNetworkStatus {
  node_count: number;
  active_nodes: number;
  delinquent_nodes: number;
  version_distribution: {
    [version: string]: {
      count: number;
      percentage: number;
    };
  };
  feature_set_distribution: {
    [featureSet: string]: {
      count: number;
      percentage: number;
    };
  };
  stake_distribution: {
    [group: string]: {
      count: number;
      stake: number;
      stake_percentage: number;
    };
  };
  average_tps?: number;
  errors: Array<{
    source: string;
    error: string;
    type?: string;
    timestamp: string;
  }>;
  status: string;
  data_source?: string;
  execution_time?: number;
  timestamp: string;
}

/**
 * Component that displays enhanced Solana network status with comprehensive metrics
 */
const EnhancedNetworkStatusCard: React.FC = () => {
  // State for showing/hiding error details
  const [showErrorDetails, setShowErrorDetails] = React.useState(false);
  
  // Use our custom hook to fetch enhanced network status with refresh capability
  const { 
    data: networkStatus, 
    isLoading, 
    isError, 
    error, 
    refresh,
    isRefetching
  } = useSolanaQuery<EnhancedNetworkStatus>(
    ['solana', 'enhanced-network-status'],
    (refresh) => solanaApi.getEnhancedNetworkStatus(refresh),
    {
      refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
      staleTime: 2 * 60 * 1000, // Consider data stale after 2 minutes
    }
  );

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const accordionBg = useColorModeValue('gray.50', 'gray.700');
  const errorBg = useColorModeValue('red.50', 'red.900');
  const warningBg = useColorModeValue('yellow.50', 'yellow.900');
  
  // Helper function to determine status color
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'success':
        return 'green';
      case 'degraded':
      case 'warning':
      case 'partial_success':
        return 'yellow';
      case 'unhealthy':
      case 'error':
      case 'down':
        return 'red';
      default:
        return 'gray';
    }
  };

  // Helper function to format large numbers
  const formatNumber = (num: number): string => {
    if (!num && num !== 0) return 'N/A';
    
    if (num >= 1000000000) {
      return (num / 1000000000).toFixed(2) + 'B';
    }
    if (num >= 1000000) {
      return (num / 1000000).toFixed(2) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(2) + 'K';
    }
    return num.toString();
  };

  // Format date for display
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch (e) {
      return dateString || 'Unknown';
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
          <Alert status="error" variant="left-accent" borderRadius="md">
            <AlertIcon />
            <Box>
              <AlertTitle>Error loading network status</AlertTitle>
              <AlertDescription>
                {(error as Error)?.message || 'Unknown error'}
              </AlertDescription>
            </Box>
          </Alert>
        </CardBody>
      </Card>
    );
  }

  // Check if we have errors in the response
  const hasErrors = networkStatus?.errors && networkStatus.errors.length > 0;
  
  return (
    <Card bg={cardBg} borderColor={borderColor} borderWidth="1px" shadow="md">
      <CardHeader>
        <Flex justify="space-between" align="center">
          <Heading size="md">Solana Network Status</Heading>
          <Flex align="center" gap={2}>
            {networkStatus?.data_source && (
              <Tooltip label={`Data source: ${networkStatus.data_source}`}>
                <Badge colorScheme={networkStatus.data_source === 'primary' ? 'blue' : 'purple'}>
                  {networkStatus.data_source === 'primary' ? 'Primary' : 'Fallback'}
                </Badge>
              </Tooltip>
            )}
            <RefreshButton onClick={refresh} isLoading={isRefetching} />
          </Flex>
        </Flex>
      </CardHeader>
      <CardBody>
        <Flex direction="column" gap={4}>
          {/* Error Alert */}
          {hasErrors && (
            <Alert 
              status={networkStatus.status === 'error' ? 'error' : 'warning'} 
              variant="left-accent" 
              borderRadius="md"
            >
              <AlertIcon />
              <Box flex="1">
                <AlertTitle>
                  {networkStatus.status === 'error' 
                    ? 'Error retrieving network status' 
                    : 'Partial data available'}
                </AlertTitle>
                <AlertDescription display="block">
                  {networkStatus.errors.length} error(s) occurred during data collection
                  <Button 
                    size="sm" 
                    variant="link" 
                    colorScheme="blue" 
                    onClick={() => setShowErrorDetails(!showErrorDetails)}
                    ml={2}
                  >
                    {showErrorDetails ? 'Hide Details' : 'Show Details'}
                  </Button>
                </AlertDescription>
                
                <Collapse in={showErrorDetails} animateOpacity>
                  <Box mt={2} p={2} bg={useColorModeValue('blackAlpha.50', 'whiteAlpha.50')} borderRadius="md">
                    {networkStatus.errors.map((err, idx) => (
                      <Box key={idx} mb={2} fontSize="sm">
                        <Text fontWeight="bold">
                          Source: {err.source} {err.type ? `(${err.type})` : ''}
                        </Text>
                        <Text>{err.error}</Text>
                        <Text fontSize="xs" color="gray.500">
                          {formatDate(err.timestamp)}
                        </Text>
                      </Box>
                    ))}
                  </Box>
                </Collapse>
              </Box>
            </Alert>
          )}
          
          {/* Overall Status */}
          <Flex justify="space-between" align="center">
            <Text fontWeight="bold">Status:</Text>
            <Badge 
              colorScheme={getStatusColor(networkStatus?.status || 'unknown')} 
              px={2} 
              py={1} 
              borderRadius="full"
              fontSize="md"
            >
              {networkStatus?.status || 'Unknown'}
            </Badge>
          </Flex>
          
          <Divider />
          
          {/* Network Summary */}
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Stat>
              <StatLabel>Total Nodes</StatLabel>
              <StatNumber>{networkStatus?.node_count || 0}</StatNumber>
              <StatHelpText>
                {networkStatus?.active_nodes || 0} active / {networkStatus?.delinquent_nodes || 0} delinquent
              </StatHelpText>
            </Stat>
            
            <Stat>
              <StatLabel>Active Nodes</StatLabel>
              <StatNumber>
                {networkStatus?.node_count ? 
                  `${Math.round((networkStatus.active_nodes / networkStatus.node_count) * 100)}%` : 
                  '0%'
                }
              </StatNumber>
              <StatHelpText>
                {networkStatus?.active_nodes || 0} of {networkStatus?.node_count || 0} nodes
              </StatHelpText>
            </Stat>
            
            <Stat>
              <StatLabel>Average TPS</StatLabel>
              <StatNumber>{networkStatus?.average_tps?.toFixed(2) || 'N/A'}</StatNumber>
              <StatHelpText>
                Transactions per second
              </StatHelpText>
            </Stat>
          </SimpleGrid>
          
          <Divider />
          
          {/* Node Health */}
          <Box>
            <Flex justify="space-between" mb={1}>
              <Text fontWeight="bold">Node Health</Text>
              <Text fontSize="sm">
                {networkStatus?.active_nodes || 0} active / {networkStatus?.delinquent_nodes || 0} delinquent
              </Text>
            </Flex>
            <Progress 
              value={networkStatus?.node_count ? (networkStatus.active_nodes / networkStatus.node_count) * 100 : 0} 
              colorScheme={getStatusColor(networkStatus?.status || 'unknown')}
              borderRadius="full"
              size="md"
            />
          </Box>
          
          <Divider />
          
          {/* Detailed Information */}
          <Accordion allowToggle defaultIndex={[]} bg={accordionBg} borderRadius="md">
            {/* Version Distribution */}
            <AccordionItem border="none">
              <AccordionButton py={2}>
                <Box flex="1" textAlign="left" fontWeight="medium">
                  Version Distribution
                </Box>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                {networkStatus?.version_distribution && 
                 Object.keys(networkStatus.version_distribution).length > 0 ? (
                  <TableContainer>
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th>Version</Th>
                          <Th isNumeric>Count</Th>
                          <Th isNumeric>Percentage</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {Object.entries(networkStatus.version_distribution)
                          .sort(([, a], [, b]) => b.count - a.count)
                          .map(([version, data]) => (
                            <Tr key={version}>
                              <Td>{version}</Td>
                              <Td isNumeric>{data.count}</Td>
                              <Td isNumeric>{data.percentage}%</Td>
                            </Tr>
                          ))}
                      </Tbody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Text>No version distribution data available</Text>
                )}
              </AccordionPanel>
            </AccordionItem>
            
            {/* Feature Set Distribution */}
            <AccordionItem border="none">
              <AccordionButton py={2}>
                <Box flex="1" textAlign="left" fontWeight="medium">
                  Feature Set Distribution
                </Box>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                {networkStatus?.feature_set_distribution && 
                 Object.keys(networkStatus.feature_set_distribution).length > 0 ? (
                  <TableContainer>
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th>Feature Set</Th>
                          <Th isNumeric>Count</Th>
                          <Th isNumeric>Percentage</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {Object.entries(networkStatus.feature_set_distribution)
                          .sort(([, a], [, b]) => b.count - a.count)
                          .map(([featureSet, data]) => (
                            <Tr key={featureSet}>
                              <Td>{featureSet}</Td>
                              <Td isNumeric>{data.count}</Td>
                              <Td isNumeric>{data.percentage}%</Td>
                            </Tr>
                          ))}
                      </Tbody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Text>No feature set distribution data available</Text>
                )}
              </AccordionPanel>
            </AccordionItem>
            
            {/* Stake Distribution */}
            <AccordionItem border="none">
              <AccordionButton py={2}>
                <Box flex="1" textAlign="left" fontWeight="medium">
                  Stake Distribution
                </Box>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                {networkStatus?.stake_distribution && 
                 Object.keys(networkStatus.stake_distribution).length > 0 ? (
                  <TableContainer>
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th>Group</Th>
                          <Th isNumeric>Validators</Th>
                          <Th isNumeric>Stake %</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {Object.entries(networkStatus.stake_distribution)
                          .sort(([group, ]) => group === 'delinquent' ? 1 : -1) // Put delinquent at the bottom
                          .map(([group, data]) => (
                            <Tr key={group}>
                              <Td>
                                <Badge 
                                  colorScheme={
                                    group === 'high' ? 'green' : 
                                    group === 'medium' ? 'blue' : 
                                    group === 'low' ? 'yellow' : 
                                    'red'
                                  }
                                >
                                  {group.charAt(0).toUpperCase() + group.slice(1)}
                                </Badge>
                              </Td>
                              <Td isNumeric>{data.count}</Td>
                              <Td isNumeric>{data.stake_percentage}%</Td>
                            </Tr>
                          ))}
                      </Tbody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Text>No stake distribution data available</Text>
                )}
              </AccordionPanel>
            </AccordionItem>
          </Accordion>
          
          {/* Metadata */}
          <Flex justify="space-between" fontSize="xs" color="gray.500" mt={2}>
            <Text>Last updated: {formatDate(networkStatus?.timestamp || '')}</Text>
            {networkStatus?.execution_time && (
              <Text>Retrieved in {networkStatus.execution_time}s</Text>
            )}
          </Flex>
        </Flex>
      </CardBody>
    </Card>
  );
};

export default EnhancedNetworkStatusCard;
