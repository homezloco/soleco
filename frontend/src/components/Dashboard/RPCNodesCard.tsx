import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Text,
  Flex,
  Spinner,
  Badge,
  Button,
  Switch,
  FormControl,
  FormLabel,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  useColorModeValue,
  Divider,
  Link,
  Tooltip
} from '@chakra-ui/react';
import { ExternalLinkIcon } from '@chakra-ui/icons';
import { useQuery } from 'react-query';
import { dashboardApi } from '../../api/dashboardService';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from 'recharts';

const RPCNodesCard: React.FC = () => {
  const [includeDetails, setIncludeDetails] = useState(false);
  const [healthCheck, setHealthCheck] = useState(false);
  
  const { data, isLoading, error, refetch } = useQuery(
    ['rpcNodes', includeDetails, healthCheck],
    () => dashboardApi.getRPCNodes(includeDetails, healthCheck),
    {
      refetchInterval: 300000, // Refresh every 5 minutes
      staleTime: 240000, // Consider data stale after 4 minutes
      retry: 3,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
      onError: (err) => {
        console.error('RPC Nodes Error:', err);
      }
    }
  );

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Debug logging
  useEffect(() => {
    console.log('RPCNodesCard - Data:', data);
    console.log('RPCNodesCard - Loading:', isLoading);
    console.log('RPCNodesCard - Error:', error);
  }, [data, isLoading, error]);

  if (isLoading) {
    return (
      <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
        <CardHeader>
          <Heading size="md">RPC Nodes</Heading>
        </CardHeader>
        <CardBody>
          <Flex justifyContent="center" alignItems="center" height="200px">
            <Spinner size="xl" />
          </Flex>
        </CardBody>
      </Card>
    );
  }

  if (error) {
    return (
      <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
        <CardHeader>
          <Heading size="md">RPC Nodes</Heading>
        </CardHeader>
        <CardBody>
          <Text color="red.500">Error loading RPC nodes data</Text>
        </CardBody>
      </Card>
    );
  }

  // Prepare data for the version distribution chart
  let chartData: any[] = [];
  
  if (data?.version_distribution) {
    console.log('RPC Nodes version_distribution data:', data.version_distribution);
    console.log('RPC Nodes version_distribution type:', typeof data.version_distribution);
    console.log('RPC Nodes is Array:', Array.isArray(data.version_distribution));
    
    try {
      if (Array.isArray(data.version_distribution)) {
        // Handle array format
        chartData = data.version_distribution.slice(0, 5).map(item => ({
          name: item.version,
          value: item.count,
          percentage: typeof item.percentage === 'number' ? item.percentage.toFixed(1) : item.percentage
        }));
      } else if (typeof data.version_distribution === 'object' && data.version_distribution !== null) {
        // Handle object format (convert to array)
        chartData = Object.entries(data.version_distribution)
          .map(([version, count]) => ({
            name: version,
            value: count,
            percentage: ((count as number) / (data.total_nodes || 1) * 100).toFixed(1)
          }))
          .slice(0, 5);
      } else {
        console.error('Unexpected version_distribution format:', data.version_distribution);
        chartData = [];
      }
    } catch (error) {
      console.error('Error processing version_distribution data:', error);
      chartData = [];
    }
  }

  return (
    <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
      <CardHeader>
        <Flex justify="space-between" align="center">
          <Heading size="md">RPC Nodes</Heading>
          <Button 
            size="sm" 
            onClick={() => refetch()}
            colorScheme="blue"
            variant="outline"
          >
            Refresh
          </Button>
        </Flex>
      </CardHeader>
      <CardBody>
        <Text fontSize="sm" color="gray.500" mb={4}>
          Last updated: {new Date(data?.timestamp).toLocaleString()}
        </Text>
        
        <Flex justify="space-between" mb={4}>
          <Box textAlign="center" p={3} shadow="sm" borderWidth="1px" borderRadius="md" flex="1" mr={2}>
            <Text fontWeight="bold" fontSize="lg">{(data?.total_nodes || 0).toLocaleString()}</Text>
            <Text fontSize="sm">Total RPC Nodes</Text>
          </Box>
          
          <Box textAlign="center" p={3} shadow="sm" borderWidth="1px" borderRadius="md" flex="1" ml={2}>
            <Text fontWeight="bold" fontSize="lg">{data?.conversion_stats?.successful || 0}</Text>
            <Text fontSize="sm">Converted URLs</Text>
          </Box>
        </Flex>
        
        <Box h="250px" mb={4}>
          <ResponsiveContainer width="100%" height="100%" minWidth={300} minHeight={200}>
            <BarChart
              data={chartData}
              margin={{
                top: 5,
                right: 30,
                left: 20,
                bottom: 5,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <RechartsTooltip 
                formatter={(value: number, name: string) => [value, name === 'value' ? 'Nodes' : 'Percentage']}
                labelFormatter={(name) => `Version: ${name}`}
              />
              <Legend />
              <Bar dataKey="value" fill="#8884d8" name="Node Count" />
            </BarChart>
          </ResponsiveContainer>
        </Box>
        
        <Divider my={4} />
        
        <Flex justify="space-between" mb={4}>
          <FormControl display="flex" alignItems="center" maxW="200px">
            <FormLabel htmlFor="include-details" mb="0" fontSize="sm">
              Show Details
            </FormLabel>
            <Switch 
              id="include-details" 
              isChecked={includeDetails}
              onChange={() => setIncludeDetails(!includeDetails)}
            />
          </FormControl>
          
          <FormControl display="flex" alignItems="center" maxW="200px">
            <FormLabel htmlFor="health-check" mb="0" fontSize="sm">
              Health Check
            </FormLabel>
            <Switch 
              id="health-check" 
              isChecked={healthCheck}
              onChange={() => setHealthCheck(!healthCheck)}
            />
          </FormControl>
        </Flex>
        
        {includeDetails && data?.rpc_nodes && (
          <>
            <Heading size="sm" mb={3}>RPC Node Details</Heading>
            <Box maxH="300px" overflowY="auto">
              <Table size="sm" variant="simple">
                <Thead position="sticky" top={0} bg={cardBg}>
                  <Tr>
                    <Th>Endpoint</Th>
                    <Th>Version</Th>
                    <Th>Feature Set</Th>
                    {healthCheck && <Th>Health</Th>}
                  </Tr>
                </Thead>
                <Tbody>
                  {data.rpc_nodes.slice(0, 20).map((node, index) => (
                    <Tr key={index}>
                      <Td>
                        <Tooltip label={node.rpc_endpoint}>
                          <Link href={`https://${node.rpc_endpoint.replace(/^https?:\/\//, '')}`} isExternal>
                            {node.rpc_endpoint.replace(/^https?:\/\//, '').substring(0, 20)}...
                            <ExternalLinkIcon mx="2px" />
                          </Link>
                        </Tooltip>
                      </Td>
                      <Td>{node.version}</Td>
                      <Td>{node.feature_set}</Td>
                      {healthCheck && (
                        <Td>
                          {node.is_healthy !== undefined ? (
                            <Badge colorScheme={node.is_healthy ? 'green' : 'red'}>
                              {node.is_healthy ? 'Healthy' : 'Unhealthy'}
                            </Badge>
                          ) : (
                            <Badge colorScheme="gray">Unknown</Badge>
                          )}
                        </Td>
                      )}
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
            {data.rpc_nodes.length > 20 && (
              <Text fontSize="sm" mt={2} textAlign="center" color="gray.500">
                Showing 20 of {data.rpc_nodes.length} nodes
              </Text>
            )}
          </>
        )}
      </CardBody>
    </Card>
  );
};

export default RPCNodesCard;
