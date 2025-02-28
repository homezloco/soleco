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
  Select,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Button,
  useColorModeValue,
  Tooltip,
  Divider
} from '@chakra-ui/react';
import { useQuery } from 'react-query';
import { dashboardApi } from '../../api/dashboardService';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from 'recharts';

const styles = {
  chartContainer: {
    position: 'relative' as const,
    width: '100%',
    height: '250px',
    minHeight: '250px',
    minWidth: '300px',
    marginBottom: '20px',
    display: 'flex',
    flexDirection: 'column' as const,
  }
};

const MintAnalyticsCard: React.FC = () => {
  const [blocks, setBlocks] = useState(2);
  
  const { data, isLoading, error, refetch } = useQuery(
    ['recentMints', blocks],
    () => dashboardApi.getRecentMints(blocks),
    {
      refetchInterval: 180000, // Refresh every 3 minutes
      staleTime: 120000, // Consider data stale after 2 minutes
      retry: 2,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
      onError: (err) => {
        console.error('Mint Analytics Error:', err);
      }
    }
  );

  // Debug logging
  useEffect(() => {
    console.log('MintAnalyticsCard - Data:', data);
    console.log('MintAnalyticsCard - Loading:', isLoading);
    console.log('MintAnalyticsCard - Error:', error);
  }, [data, isLoading, error]);

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  if (isLoading) {
    return (
      <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
        <CardHeader>
          <Heading size="md">Mint Analytics</Heading>
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
          <Heading size="md">Mint Analytics</Heading>
        </CardHeader>
        <CardBody>
          <Flex direction="column" align="center" justify="center" minHeight="200px">
            <Text color="red.500" mb={4}>Error loading mint analytics</Text>
            <Button colorScheme="blue" onClick={() => refetch()}>
              Retry
            </Button>
            <Text fontSize="sm" mt={4} color="gray.500">
              Try reducing the number of blocks to analyze
            </Text>
          </Flex>
        </CardBody>
      </Card>
    );
  }

  // Prepare data for the chart - only if data exists
  const chartData = data?.results 
    ? data.results.map(result => ({
        block: result.block_number,
        'All Mints': result.mint_addresses.length,
        'New Mints': result.new_mint_addresses.length,
        'Pump Tokens': result.pump_token_addresses.length
      })).reverse() 
    : [
        {
          block: 1,
          'All Mints': data?.stats?.total_all_mints || 0,
          'New Mints': data?.stats?.total_new_mints || data?.new_mints?.length || 0,
          'Pump Tokens': data?.stats?.total_pump_tokens || data?.pump_tokens?.length || 0
        }
      ]; // Fallback to summary data if results not available

  return (
    <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
      <CardHeader>
        <Flex justify="space-between" align="center">
          <Heading size="md">Mint Analytics</Heading>
          <Flex align="center">
            <Text fontSize="sm" mr={2}>Blocks:</Text>
            <Select 
              size="sm" 
              value={blocks} 
              onChange={(e) => setBlocks(Number(e.target.value))}
              width="80px"
            >
              <option value={2}>2</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={15}>15</option>
              <option value={20}>20</option>
            </Select>
            <Button 
              size="sm" 
              ml={2} 
              onClick={() => refetch()}
              colorScheme="blue"
              variant="outline"
            >
              Refresh
            </Button>
          </Flex>
        </Flex>
      </CardHeader>
      <CardBody>
        <Text fontSize="sm" color="gray.500" mb={4}>
          Last updated: {data?.timestamp ? new Date(data.timestamp).toLocaleString() : new Date().toLocaleString()}
        </Text>
        
        <Box sx={styles.chartContainer}>
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
              <XAxis dataKey="block" />
              <YAxis />
              <RechartsTooltip />
              <Legend />
              <Bar dataKey="All Mints" fill="#8884d8" />
              <Bar dataKey="New Mints" fill="#82ca9d" />
              <Bar dataKey="Pump Tokens" fill="#ffc658" />
            </BarChart>
          </ResponsiveContainer>
        </Box>
        
        <Divider my={4} />
        
        <Heading size="sm" mb={3}>Summary</Heading>
        <Flex justify="space-between" mb={4}>
          <Box textAlign="center" p={3} shadow="sm" borderWidth="1px" borderRadius="md">
            <Text fontWeight="bold" fontSize="lg">{data?.stats?.total_all_mints || 0}</Text>
            <Text fontSize="sm">Total Mint Addresses</Text>
          </Box>
          <Box textAlign="center" p={3} shadow="sm" borderWidth="1px" borderRadius="md">
            <Text fontWeight="bold" fontSize="lg">
              {data?.stats?.total_new_mints || data?.new_mints?.length || 0}
            </Text>
            <Text fontSize="sm">New Mint Addresses</Text>
          </Box>
          <Box textAlign="center" p={3} shadow="sm" borderWidth="1px" borderRadius="md">
            <Text fontWeight="bold" fontSize="lg">{data?.stats?.total_pump_tokens || data?.pump_tokens?.length || 0}</Text>
            <Text fontSize="sm">Pump Tokens</Text>
          </Box>
        </Flex>
        
        <Heading size="sm" mb={3}>Latest Block Details</Heading>
        {data?.results && data.results.length > 0 ? (
          <Table size="sm" variant="simple">
            <Thead>
              <Tr>
                <Th>Block</Th>
                <Th isNumeric>All Mints</Th>
                <Th isNumeric>New Mints</Th>
                <Th isNumeric>Pump Tokens</Th>
              </Tr>
            </Thead>
            <Tbody>
              {data.results.slice(0, 5).map((result) => (
                <Tr key={result.block_number}>
                  <Td>{result.block_number}</Td>
                  <Td isNumeric>{result.mint_addresses?.length || 0}</Td>
                  <Td isNumeric>{result.new_mint_addresses?.length || 0}</Td>
                  <Td isNumeric>
                    <Badge colorScheme="purple">
                      {result.pump_token_addresses?.length || 0}
                    </Badge>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        ) : null}
      </CardBody>
    </Card>
  );
};

export default MintAnalyticsCard;
