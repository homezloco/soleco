import React, { useState } from 'react';
import {
  Box,
  Card,
  CardBody,
  CardHeader,
  Flex,
  Heading,
  Text,
  Divider,
  Badge,
  SimpleGrid,
  useColorModeValue,
  Spinner,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Switch,
  FormControl,
  FormLabel,
  Tooltip,
  HStack,
  Tag,
} from '@chakra-ui/react';
import { solanaApi } from '../../api/solanaService';
import useSolanaQuery from '../../hooks/useSolanaQuery';
import RefreshButton from '../common/RefreshButton';

/**
 * Component that displays information about available Solana RPC nodes
 */
const RpcNodesCard: React.FC = () => {
  const [showDetails, setShowDetails] = useState(false);
  const [performHealthCheck, setPerformHealthCheck] = useState(false);
  const [useEnhancedExtractor, setUseEnhancedExtractor] = useState(true);
  
  // Use our custom hook to fetch RPC nodes with refresh capability
  const { 
    data: rpcNodesData, 
    isLoading, 
    isError, 
    error, 
    refresh,
    isRefetching
  } = useSolanaQuery(
    ['solana', 'rpc-nodes', showDetails, performHealthCheck, useEnhancedExtractor],
    (refresh) => solanaApi.getRpcNodes(
      showDetails, 
      performHealthCheck, 
      false, 
      refresh,
      useEnhancedExtractor
    ),
    {
      refetchInterval: 10 * 60 * 1000, // Refetch every 10 minutes
      staleTime: 5 * 60 * 1000, // Consider data stale after 5 minutes
    }
  );

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  if (isLoading) {
    return (
      <Card bg={cardBg} borderColor={borderColor} borderWidth="1px" shadow="md">
        <CardHeader>
          <Flex justify="space-between" align="center">
            <Heading size="md">Solana RPC Nodes</Heading>
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
            <Heading size="md">Solana RPC Nodes</Heading>
            <RefreshButton onClick={refresh} isLoading={isRefetching} />
          </Flex>
        </CardHeader>
        <CardBody>
          <Text color="red.500">Error loading RPC nodes: {(error as Error)?.message || 'Unknown error'}</Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card bg={cardBg} borderColor={borderColor} borderWidth="1px" shadow="md">
      <CardHeader>
        <Flex justify="space-between" align="center">
          <Heading size="md">
            Solana RPC Nodes
            {useEnhancedExtractor && (
              <Tooltip label="Using enhanced RPC node extractor with improved error handling">
                <Tag size="sm" colorScheme="green" ml={2}>Enhanced</Tag>
              </Tooltip>
            )}
          </Heading>
          <RefreshButton onClick={refresh} isLoading={isRefetching} />
        </Flex>
      </CardHeader>
      <CardBody>
        <Flex direction="column" gap={4}>
          {/* Controls */}
          <Flex justify="space-between" wrap="wrap" gap={2}>
            <HStack spacing={4}>
              <FormControl display="flex" alignItems="center" width="auto">
                <FormLabel htmlFor="show-details" mb="0" mr={2}>
                  Show Details
                </FormLabel>
                <Switch 
                  id="show-details" 
                  isChecked={showDetails} 
                  onChange={() => setShowDetails(!showDetails)}
                />
              </FormControl>
              
              <FormControl display="flex" alignItems="center" width="auto">
                <FormLabel htmlFor="health-check" mb="0" mr={2}>
                  Health Check
                </FormLabel>
                <Switch 
                  id="health-check" 
                  isChecked={performHealthCheck} 
                  onChange={() => setPerformHealthCheck(!performHealthCheck)}
                />
              </FormControl>
              
              <FormControl display="flex" alignItems="center" width="auto">
                <Tooltip label="Use enhanced RPC node extractor with improved error handling and reliability">
                  <FormLabel htmlFor="enhanced-extractor" mb="0" mr={2}>
                    Enhanced Mode
                  </FormLabel>
                </Tooltip>
                <Switch 
                  id="enhanced-extractor" 
                  isChecked={useEnhancedExtractor} 
                  onChange={() => setUseEnhancedExtractor(!useEnhancedExtractor)}
                  colorScheme="green"
                />
              </FormControl>
            </HStack>
          </Flex>
          
          <Divider />
          
          {/* Summary Stats */}
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Box p={3} borderWidth="1px" borderRadius="md" borderColor={borderColor}>
              <Text fontSize="sm" fontWeight="bold" mb={1}>Total RPC Nodes</Text>
              <Text fontSize="2xl">{rpcNodesData?.total_rpc_nodes || 0}</Text>
              {useEnhancedExtractor && rpcNodesData?.errors && rpcNodesData.errors.length > 0 && (
                <Text fontSize="xs" color="orange.500">
                  {rpcNodesData.errors.length} error(s) handled
                </Text>
              )}
            </Box>
            
            {performHealthCheck && (
              <Box p={3} borderWidth="1px" borderRadius="md" borderColor={borderColor}>
                <Text fontSize="sm" fontWeight="bold" mb={1}>Health Check</Text>
                <Text fontSize="2xl">{rpcNodesData?.estimated_health_percentage?.toFixed(1) || 0}%</Text>
                <Text fontSize="xs" color="gray.500">Sample size: {rpcNodesData?.health_sample_size || 0}</Text>
              </Box>
            )}
            
            <Box p={3} borderWidth="1px" borderRadius="md" borderColor={borderColor}>
              <Text fontSize="sm" fontWeight="bold" mb={1}>Version Distribution</Text>
              <Flex direction="column" gap={1}>
                {rpcNodesData?.version_distribution && 
                  Object.entries(rpcNodesData.version_distribution)
                    .slice(0, 2)
                    .map(([version, count], idx) => (
                      <Flex key={idx} justify="space-between">
                        <Text fontSize="xs">{version}</Text>
                        <Badge>{count}</Badge>
                      </Flex>
                    ))
                }
              </Flex>
            </Box>
          </SimpleGrid>
          
          {/* Detailed Node List */}
          {showDetails && rpcNodesData?.rpc_nodes && rpcNodesData.rpc_nodes.length > 0 && (
            <>
              <Divider my={2} />
              <Heading size="sm" mb={2}>RPC Node Details</Heading>
              <TableContainer>
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Endpoint</Th>
                      <Th>Version</Th>
                      <Th>Feature Set</Th>
                      {performHealthCheck && <Th>Health</Th>}
                    </Tr>
                  </Thead>
                  <Tbody>
                    {rpcNodesData.rpc_nodes.slice(0, 10).map((node, idx) => (
                      <Tr key={idx}>
                        <Td fontSize="xs">{node.rpc_endpoint}</Td>
                        <Td fontSize="xs">{node.version || 'Unknown'}</Td>
                        <Td fontSize="xs">{node.feature_set || 'Unknown'}</Td>
                        {performHealthCheck && (
                          <Td>
                            {node.health ? (
                              <Badge colorScheme="green">Healthy</Badge>
                            ) : (
                              <Tooltip label={node.health_error || 'Unhealthy'}>
                                <Badge colorScheme="red">Unhealthy</Badge>
                              </Tooltip>
                            )}
                          </Td>
                        )}
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </TableContainer>
              
              {rpcNodesData.rpc_nodes.length > 10 && (
                <Text fontSize="xs" color="gray.500" mt={2}>
                  Showing 10 of {rpcNodesData.rpc_nodes.length} nodes
                </Text>
              )}
            </>
          )}
          
          {/* Errors (if using enhanced mode) */}
          {useEnhancedExtractor && rpcNodesData?.errors && rpcNodesData.errors.length > 0 && (
            <>
              <Divider my={2} />
              <Heading size="sm" mb={2}>Error Summary</Heading>
              <Text fontSize="xs" color="gray.600" mb={2}>
                The following errors were handled gracefully by the enhanced RPC node extractor:
              </Text>
              <Box 
                maxH="150px" 
                overflowY="auto" 
                p={2} 
                borderWidth="1px" 
                borderRadius="md" 
                borderColor="orange.200"
                bg="orange.50"
                _dark={{ bg: "orange.900", borderColor: "orange.700" }}
              >
                {rpcNodesData.errors.slice(0, 5).map((err, idx) => (
                  <Text key={idx} fontSize="xs" mb={1}>
                    <Text as="span" fontWeight="bold">{err.source || 'Unknown source'}</Text>: {err.message || 'Unknown error'}
                  </Text>
                ))}
                {rpcNodesData.errors.length > 5 && (
                  <Text fontSize="xs" fontStyle="italic">
                    ...and {rpcNodesData.errors.length - 5} more errors
                  </Text>
                )}
              </Box>
            </>
          )}
          
          {/* Last Updated */}
          <Text fontSize="xs" color="gray.500" alignSelf="flex-end" mt={2}>
            Last updated: {new Date(rpcNodesData?.timestamp || '').toLocaleString()}
          </Text>
        </Flex>
      </CardBody>
    </Card>
  );
};

export default RpcNodesCard;
