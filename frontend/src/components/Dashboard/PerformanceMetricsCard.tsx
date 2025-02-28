import React, { useEffect } from 'react';
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
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  useColorModeValue,
  Divider,
  Tooltip
} from '@chakra-ui/react';
import { useQuery } from 'react-query';
import { dashboardApi } from '../../api/dashboardService';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from 'recharts';

// Add CSS styles
const styles = {
  chartContainer: {
    position: 'relative' as const,
    width: '100%',
    height: '200px',
    minHeight: '200px',
    minWidth: '300px',
    marginBottom: '24px',
    display: 'flex',
    flexDirection: 'column' as const,
  }
};

const PerformanceMetricsCard: React.FC = () => {
  const { data, isLoading, error } = useQuery(
    'performanceMetrics',
    () => dashboardApi.getPerformanceMetrics(),
    {
      refetchInterval: 60000, // Refresh every minute
      staleTime: 30000, // Consider data stale after 30 seconds,
      retry: 3,
      onError: (err) => {
        console.error('Performance Metrics Error:', err);
      }
    }
  );

  // Debug logging
  useEffect(() => {
    console.log('PerformanceMetricsCard - Data:', data);
    console.log('PerformanceMetricsCard - Loading:', isLoading);
    console.log('PerformanceMetricsCard - Error:', error);
  }, [data, isLoading, error]);

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  if (isLoading) {
    return (
      <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
        <CardHeader>
          <Heading size="md">Network Performance</Heading>
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
          <Heading size="md">Network Performance</Heading>
        </CardHeader>
        <CardBody>
          <Text color="red.500">Error loading performance metrics</Text>
        </CardBody>
      </Card>
    );
  }

  // Prepare data for the TPS chart
  const tpsChartData = data?.performance_samples?.map(sample => ({
    slot: sample.slot,
    tps: sample.numTransactions / sample.samplePeriodSecs
  })) || [];

  return (
    <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
      <CardHeader>
        <Flex justify="space-between" align="center">
          <Heading size="md">Network Performance</Heading>
          <Badge 
            colorScheme={data?.status === 'healthy' ? 'green' : data?.status === 'degraded' ? 'yellow' : 'red'}
            fontSize="0.8em"
            px={2}
            py={1}
            borderRadius="full"
          >
            {data?.status?.toUpperCase() || 'UNKNOWN'}
          </Badge>
        </Flex>
      </CardHeader>
      <CardBody>
        <Text fontSize="sm" color="gray.500" mb={4}>
          Last updated: {new Date(data?.timestamp || Date.now()).toLocaleString()}
        </Text>
        
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} mb={6}>
          <Stat
            px={{ base: 2, md: 4 }}
            py="3"
            shadow="sm"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={cardBg}
          >
            <StatLabel fontSize="xs">Max TPS</StatLabel>
            <StatNumber fontSize="lg">{data?.tps_statistics?.max_tps?.toFixed(1) || 'N/A'}</StatNumber>
            <StatHelpText fontSize="xs">Transactions per second</StatHelpText>
          </Stat>
          
          <Stat
            px={{ base: 2, md: 4 }}
            py="3"
            shadow="sm"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={cardBg}
          >
            <StatLabel fontSize="xs">Avg TPS</StatLabel>
            <StatNumber fontSize="lg">{data?.tps_statistics?.average_tps?.toFixed(1) || 'N/A'}</StatNumber>
            <StatHelpText fontSize="xs">Transactions per second</StatHelpText>
          </Stat>
          
          <Stat
            px={{ base: 2, md: 4 }}
            py="3"
            shadow="sm"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={cardBg}
          >
            <StatLabel fontSize="xs">Avg Block Time</StatLabel>
            <StatNumber fontSize="lg">400</StatNumber>
            <StatHelpText fontSize="xs">Milliseconds</StatHelpText>
          </Stat>
          
          <Stat
            px={{ base: 2, md: 4 }}
            py="3"
            shadow="sm"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={cardBg}
          >
            <StatLabel fontSize="xs">Slot Skip Rate</StatLabel>
            <StatNumber fontSize="lg">{(data?.block_production_statistics?.skipped_slot_percentage)?.toFixed(2) || 'N/A'}%</StatNumber>
            <StatHelpText fontSize="xs">Lower is better</StatHelpText>
          </Stat>
        </SimpleGrid>
        
        <Heading size="sm" mb={3}>Transactions Per Second (TPS)</Heading>
        <Box sx={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%" minWidth={300} minHeight={200}>
            <LineChart
              data={tpsChartData}
              margin={{
                top: 5,
                right: 30,
                left: 20,
                bottom: 5,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="slot" />
              <YAxis />
              <RechartsTooltip 
                formatter={(value: number) => [`${value.toFixed(2)} TPS`, 'Transactions Per Second']}
                labelFormatter={(slot) => `Slot: ${slot}`}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="tps" 
                stroke="#8884d8" 
                activeDot={{ r: 8 }} 
                name="TPS"
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
        
        <Divider my={4} />
        
        <Heading size="sm" mb={3}>Block Production Summary</Heading>
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          <Stat
            px={{ base: 2, md: 4 }}
            py="3"
            shadow="sm"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={cardBg}
          >
            <StatLabel fontSize="xs">Total Blocks Produced</StatLabel>
            <StatNumber fontSize="lg">{data?.block_production_statistics?.total_blocks?.toLocaleString() || 'N/A'}</StatNumber>
          </Stat>
          
          <Stat
            px={{ base: 2, md: 4 }}
            py="3"
            shadow="sm"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={cardBg}
          >
            <StatLabel fontSize="xs">Total Slots Skipped</StatLabel>
            <StatNumber fontSize="lg">{data?.block_production_statistics?.skipped_slots?.toLocaleString() || 'N/A'}</StatNumber>
          </Stat>
          
          <Stat
            px={{ base: 2, md: 4 }}
            py="3"
            shadow="sm"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={cardBg}
          >
            <StatLabel fontSize="xs">Total Transactions</StatLabel>
            <StatNumber fontSize="lg">{data?.tps_statistics?.average_tps ? Math.round(data.tps_statistics.average_tps * 60).toLocaleString() : 'N/A'}</StatNumber>
          </Stat>
        </SimpleGrid>
      </CardBody>
    </Card>
  );
};

export default PerformanceMetricsCard;
