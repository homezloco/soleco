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
  Divider,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription
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
  const [isBackgroundProcessing, setIsBackgroundProcessing] = useState(false);
  
  const { data, isLoading, error, refetch } = useQuery(
    ['recentMints', blocks],
    () => dashboardApi.getRecentMints(blocks),
    {
      refetchInterval: 180000, // Refresh every 3 minutes
      staleTime: 120000, // Consider data stale after 2 minutes
      retry: 3,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
      onError: (err) => {
        console.error('Mint Analytics Error:', err);
      },
      onSuccess: (data) => {
        // Check if data contains a message indicating background processing
        if (data?.message && data.message.includes('background')) {
          setIsBackgroundProcessing(true);
          // Schedule a refetch after a short delay
          setTimeout(() => refetch(), 5000);
        } else {
          setIsBackgroundProcessing(false);
        }
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

  if (isLoading && !data) {
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
            <Alert status="error" variant="subtle" flexDirection="column" alignItems="center" justifyContent="center" textAlign="center" borderRadius="md" mb={4}>
              <AlertIcon boxSize="40px" mr={0} />
              <AlertTitle mt={4} mb={1} fontSize="lg">Error Loading Data</AlertTitle>
              <AlertDescription maxWidth="sm">
                {error instanceof Error ? error.message : 'Failed to load mint analytics'}
              </AlertDescription>
            </Alert>
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
        <Flex justifyContent="space-between" alignItems="center">
          <Heading size="md">Mint Analytics</Heading>
          <Select 
            value={blocks} 
            onChange={(e) => setBlocks(Number(e.target.value))}
            width="120px"
            size="sm"
          >
            <option value={1}>1 Block</option>
            <option value={2}>2 Blocks</option>
            <option value={5}>5 Blocks</option>
            <option value={10}>10 Blocks</option>
          </Select>
        </Flex>
      </CardHeader>
      <CardBody>
        {isBackgroundProcessing && (
          <Alert status="info" mb={4} borderRadius="md">
            <AlertIcon />
            <Flex align="center" justify="space-between" width="100%">
              <Text>Processing data in background...</Text>
              <Spinner size="sm" ml={2} />
            </Flex>
          </Alert>
        )}
        
        <Box sx={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="block" />
              <YAxis />
              <RechartsTooltip />
              <Legend />
              <Bar dataKey="All Mints" fill="#8884d8" />
              <Bar dataKey="New Mints" fill="#82ca9d" />
              <Bar dataKey="Pump Tokens" fill="#ff7300" />
            </BarChart>
          </ResponsiveContainer>
        </Box>
        
        <Divider my={4} />
        
        <Box>
          <Heading size="sm" mb={3}>Summary</Heading>
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>Metric</Th>
                <Th isNumeric>Count</Th>
              </Tr>
            </Thead>
            <Tbody>
              <Tr>
                <Td>New Mint Addresses</Td>
                <Td isNumeric>
                  <Badge colorScheme="green" fontSize="0.9em">
                    {data?.summary?.total_new_mints || data?.new_mints?.length || 0}
                  </Badge>
                </Td>
              </Tr>
              <Tr>
                <Td>Pump Tokens</Td>
                <Td isNumeric>
                  <Badge colorScheme="orange" fontSize="0.9em">
                    {data?.summary?.total_pump_tokens || data?.pump_tokens?.length || 0}
                  </Badge>
                </Td>
              </Tr>
              <Tr>
                <Td>Blocks Processed</Td>
                <Td isNumeric>
                  <Badge colorScheme="blue" fontSize="0.9em">
                    {data?.summary?.blocks_processed || data?.blocks_processed || 0}
                  </Badge>
                </Td>
              </Tr>
            </Tbody>
          </Table>
        </Box>
      </CardBody>
    </Card>
  );
};

export default MintAnalyticsCard;
