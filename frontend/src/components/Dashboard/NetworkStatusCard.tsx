import React, { useEffect } from 'react';
import {
  Box,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Text,
  Flex,
  Badge,
  Spinner,
  Divider,
  List,
  ListItem,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  useColorModeValue,
  SimpleGrid
} from '@chakra-ui/react';
import { useQuery } from 'react-query';
import { dashboardApi } from '../../api/dashboardService';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { NetworkSummary, ClusterNodes } from 'api';

const NetworkStatusCard: React.FC = () => {
  const { data, isLoading, error } = useQuery(
    'networkStatus',
    () => dashboardApi.getNetworkStatus(true),
    {
      refetchInterval: 60000, // Refresh every minute
      staleTime: 30000, // Consider data stale after 30 seconds
      retry: 3,
      onError: (err) => {
        console.error('Network Status Error:', err);
      }
    }
  );

  // Debug logging
  useEffect(() => {
    console.log('NetworkStatusCard - Data:', data);
    console.log('NetworkStatusCard - Loading:', isLoading);
    console.log('NetworkStatusCard - Error:', error);
  }, [data, isLoading, error]);

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  // Colors for the pie chart
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d'];

  if (isLoading) {
    return (
      <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
        <CardHeader>
          <Heading size="md">Network Status</Heading>
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
          <Heading size="md">Network Status</Heading>
        </CardHeader>
        <CardBody>
          <Text color="red.500">Error loading network status</Text>
        </CardBody>
      </Card>
    );
  }

  const network_summary: NetworkSummary = data?.network_summary || {};
  const cluster_nodes: ClusterNodes = data?.cluster_nodes || {};
  const status = data?.status || 'unknown';
  const timestamp = data?.timestamp || new Date().toISOString();
  
  // Check for missing validators data (backend warning case)
  const hasMissingValidatorsData = 
    network_summary && 
    typeof network_summary === 'object' && 
    'total_stake' in network_summary && 
    network_summary.total_stake === 0 &&
    'active_validators' in network_summary && 
    network_summary.active_validators === 0 &&
    'delinquent_validators' in network_summary && 
    network_summary.delinquent_validators === 0;
  
  // Prepare data for version distribution pie chart
  let versionData: any[] = [];
  
  if (network_summary.version_distribution) {
    try {
      if (Array.isArray(network_summary.version_distribution)) {
        // Handle array format
        versionData = network_summary.version_distribution.slice(0, 5).map((item) => ({
          name: item.version,
          value: item.count,
          percentage: typeof item.percentage === 'number' ? item.percentage.toFixed(1) : item.percentage
        }));
      } else if (typeof network_summary.version_distribution === 'object' && network_summary.version_distribution !== null) {
        // Handle object format (convert to array)
        versionData = Object.entries(network_summary.version_distribution)
          .map(([version, count]) => ({
            name: version,
            value: count,
            percentage: ((count as number) / (network_summary.total_nodes || 1) * 100).toFixed(1)
          }))
          .slice(0, 5);
      }
    } catch (error) {
      console.error('Error processing version_distribution data:', error);
      versionData = [];
    }
  }

  return (
    <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
      <CardHeader>
        <Flex justify="space-between" align="center">
          <Heading size="md">Network Status</Heading>
          <Badge 
            colorScheme={status === 'healthy' ? 'green' : status === 'degraded' ? 'yellow' : 'red'}
            fontSize="0.8em"
            px={2}
            py={1}
            borderRadius="full"
          >
            {status.toUpperCase()}
          </Badge>
        </Flex>
      </CardHeader>
      <CardBody>
        <Text fontSize="sm" color="gray.500" mb={4}>
          Last updated: {new Date(timestamp).toLocaleString()}
        </Text>
        
        {hasMissingValidatorsData && (
          <Text color="orange.500" mb={4} fontSize="sm">
            Note: Validator data is currently unavailable. Some statistics may show as zero.
          </Text>
        )}
        
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} mb={4}>
          <Stat>
            <StatLabel>Total Nodes</StatLabel>
            <StatNumber>
              {cluster_nodes.total_nodes?.toLocaleString() || 
               (network_summary && typeof network_summary === 'object' && 'total_nodes' in network_summary) ? 
                 ('total_nodes' in network_summary ? network_summary.total_nodes?.toLocaleString() : 'N/A') : 
                 'N/A'}
            </StatNumber>
            <StatHelpText>
              {network_summary && typeof network_summary === 'object' && 'rpc_nodes_available' in network_summary ? 
                `${network_summary.rpc_nodes_available} RPC nodes available` : ''}
            </StatHelpText>
          </Stat>
          
          <Stat>
            <StatLabel>Latest Version</StatLabel>
            <StatNumber>{network_summary.latest_version}</StatNumber>
            <StatHelpText>
              {network_summary && typeof network_summary === 'object' && 'nodes_on_latest_version_percentage' in network_summary ? 
                `${network_summary.nodes_on_latest_version_percentage?.toFixed(1)}% of nodes` : ''}
            </StatHelpText>
          </Stat>
        </SimpleGrid>
        
        <Divider my={4} />
        
        <Heading size="sm" mb={3}>Version Distribution</Heading>
        <Box h="200px">
          {versionData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%" minWidth={200} minHeight={200}>
              <PieChart>
                <Pie
                  data={versionData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  fill="#8884d8"
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, percentage }) => `${name}: ${percentage}%`}
                >
                  {versionData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value: number) => [`${value} nodes`, 'Count']}
                  labelFormatter={(name) => `Version: ${name}`}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <Flex justifyContent="center" alignItems="center" height="100%">
              <Text color="gray.500">No version data available</Text>
            </Flex>
          )}
        </Box>
        
        <List spacing={2} mt={4}>
          <ListItem>
            <Text fontSize="sm">
              <strong>RPC Availability:</strong> {network_summary.rpc_availability_percentage?.toFixed(1)}%
            </Text>
          </ListItem>
          <ListItem>
            <Text fontSize="sm">
              <strong>Total Versions:</strong> {network_summary.total_versions_in_use}
            </Text>
          </ListItem>
          <ListItem>
            <Text fontSize="sm">
              <strong>Feature Sets:</strong> {network_summary.total_feature_sets_in_use}
            </Text>
          </ListItem>
        </List>
      </CardBody>
    </Card>
  );
};

export default NetworkStatusCard;
