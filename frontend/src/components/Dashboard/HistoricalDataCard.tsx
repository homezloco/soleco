import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Text,
  Select,
  Flex,
  Spinner,
  Button,
  useColorModeValue,
  Tabs, 
  TabList, 
  TabPanels, 
  Tab, 
  TabPanel
} from '@chakra-ui/react';
import { useQuery } from 'react-query';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';
import { format } from 'date-fns';

import { dashboardApi } from '../../api/dashboardService';

// Types for historical data
interface NetworkStatusHistoryItem {
  status: string;
  timestamp: string;
  data: any;
  active_stake?: number;
  total_nodes?: number;
  active_nodes?: number;
  inactive_nodes?: number;
}

interface MintAnalyticsHistoryItem {
  blocks: number;
  new_mints_count: number;
  pump_tokens_count: number;
  timestamp: string;
  data: any;
  new_mints?: number;
  total_mints?: number;
  active_mints?: number;
}

interface PumpTokensHistoryItem {
  timestamp?: string;
  token_count?: number;
  tokens_count?: number;
  volume_change?: number;
  price_change?: number;
  volume?: number;
  holder_growth?: number;
  data?: {
    timestamp?: string;
    token_count?: number;
    tokens_count?: number;
    volume_change?: number;
    price_change?: number;
    volume?: number;
    holder_growth?: number;
  };
}

interface HistoricalDataProps {
  data: any;
  timeRange: any;
}

// API functions to fetch historical data
const fetchNetworkStatusHistory = async (hours: number) => {
  try {
    const limit = 24; // Set a reasonable limit for data points
    console.log(`Fetching network status history for the past ${hours} hours with limit ${limit}...`);
    const response = await dashboardApi.getNetworkStatusHistory(hours, limit);
    console.log('Network Status History raw response:', response);
    
    // Check if response is an array or an object with a data property
    if (Array.isArray(response)) {
      console.log('Network Status History API response:', response);
      console.log('Network Status History: Using response directly');
      console.log('Network Status History sample item:', response.length > 0 ? response[0] : 'No items');
      console.log('Network Status History sample item keys:', response.length > 0 ? Object.keys(response[0]) : 'No items');
      return response;
    } else if (response && typeof response === 'object' && response.data) {
      console.log('Network Status History API response:', response.data);
      console.log('Network Status History: Using response.data');
      console.log('Network Status History sample item:', response.data.length > 0 ? response.data[0] : 'No items');
      console.log('Network Status History sample item keys:', response.data.length > 0 ? Object.keys(response.data[0]) : 'No items');
      return response.data;
    } else {
      console.warn('Network Status History: Unexpected response format', response);
      return [];
    }
  } catch (error) {
    console.error('Error fetching network status history:', error);
    return [];
  }
};

const fetchMintAnalyticsHistory = async (blocks: number, hours: number) => {
  try {
    const limit = 24; // Set a reasonable limit for data points
    console.log(`Fetching mint analytics history for ${blocks} blocks over the past ${hours} hours with limit ${limit}...`);
    const response = await dashboardApi.getMintAnalyticsHistory(blocks, hours, limit);
    console.log('Mint Analytics History raw response:', response);
    
    // Check if response is an array or an object with a data property
    if (Array.isArray(response)) {
      console.log('Mint Analytics History API response:', response);
      console.log('Mint Analytics History: Using response directly');
      console.log('Mint Analytics History sample item:', response.length > 0 ? response[0] : 'No items');
      console.log('Mint Analytics History sample item keys:', response.length > 0 ? Object.keys(response[0]) : 'No items');
      return response;
    } else if (response && typeof response === 'object' && response.data) {
      console.log('Mint Analytics History API response:', response.data);
      console.log('Mint Analytics History: Using response.data');
      console.log('Mint Analytics History sample item:', response.data.length > 0 ? response.data[0] : 'No items');
      console.log('Mint Analytics History sample item keys:', response.data.length > 0 ? Object.keys(response.data[0]) : 'No items');
      return response.data;
    } else {
      console.warn('Mint Analytics History: Unexpected response format', response);
      return [];
    }
  } catch (error) {
    console.error('Error fetching mint analytics history:', error);
    return [];
  }
};

const fetchPumpTokensHistory = async (timeframe: '1h' | '24h' | '7d', sortMetric: 'volume' | 'price_change' | 'holder_growth', hours: number, limit: number = 24) => {
  try {
    console.log(`Fetching pump tokens history for ${timeframe} timeframe, ${sortMetric} metric over the past ${hours} hours...`);
    console.log(`Getting pump tokens history: timeframe=${timeframe}, sortMetric=${sortMetric}, hours=${hours}, limit=${limit}`);
    
    const response = await dashboardApi.getPumpTokensHistory(timeframe, sortMetric, hours, limit);
    console.log('Pump tokens history response:', response);
    
    // Check if response is an array or an object with a data property
    if (Array.isArray(response)) {
      console.log('Pump Tokens History API response:', response);
      console.log('Pump Tokens History: Using response directly');
      console.log('Pump Tokens History sample item:', response.length > 0 ? response[0] : 'No items');
      console.log('Pump Tokens History sample item keys:', response.length > 0 ? Object.keys(response[0]) : 'No items');
      return response;
    } else if (response && typeof response === 'object' && response.data) {
      console.log('Pump Tokens History API response:', response.data);
      console.log('Pump Tokens History: Using response.data');
      console.log('Pump Tokens History sample item:', response.data.length > 0 ? response.data[0] : 'No items');
      console.log('Pump Tokens History sample item keys:', response.data.length > 0 ? Object.keys(response.data[0]) : 'No items');
      return response.data;
    } else {
      console.warn('Pump Tokens History: Unexpected response format', response);
      return [];
    }
  } catch (error) {
    console.error('Error fetching pump tokens history:', error);
    return [];
  }
};

// Format timestamp for display
const formatTimestamp = (timestamp: string | undefined) => {
  if (!timestamp) {
    return 'Unknown Date';
  }
  
  try {
    return format(new Date(timestamp), 'MM/dd/yyyy HH:mm');
  } catch (error) {
    return timestamp;
  }
};

// Add CSS styles
const styles = {
  chartContainer: {
    position: 'relative' as const,
    width: '100%',
    height: '400px',
    minHeight: '400px',
    minWidth: '300px',
    marginTop: '20px',
    marginBottom: '20px',
    display: 'flex',
    flexDirection: 'column' as const,
  },
  noDataMessage: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '300px',
    width: '100%',
    fontSize: '16px',
    color: 'gray',
  }
};

// Component for displaying network status history
const NetworkStatusHistory: React.FC<HistoricalDataProps> = ({ data, timeRange }) => {
  // Format data for chart
  const chartData = React.useMemo(() => {
    if (!data) {
      console.log('Network Status History: Invalid data format', data);
      return [];
    }
    
    if (!Array.isArray(data)) {
      console.log('Network Status History: Data is not an array', data);
      return [];
    }
    
    if (data.length === 0) {
      console.log('Network Status History: Empty data array');
      return [];
    }
    
    console.log('Network Status History: Processing data', data);
    console.log('Network Status History: Data type', typeof data);
    console.log('Network Status History: Is array', Array.isArray(data));
    console.log('Network Status History: Length', data.length);
    
    try {
      return data.map((item: NetworkStatusHistoryItem, index: number) => {
        // Extract values from item or nested data object
        const networkData = item.data || {};
        console.log(`Network Status History item ${index}:`, item);
        console.log(`Network Status History item ${index} structure:`, {
          hasTimestamp: !!item.timestamp,
          timestampValue: item.timestamp,
          hasActiveStake: !!item.active_stake,
          activeStakeValue: item.active_stake,
          hasTotalNodes: !!item.total_nodes,
          totalNodesValue: item.total_nodes,
          hasActiveNodes: !!item.active_nodes,
          activeNodesValue: item.active_nodes,
          hasInactiveNodes: !!item.inactive_nodes,
          inactiveNodesValue: item.inactive_nodes,
          nestedDataKeys: Object.keys(networkData)
        });
        
        // Check if we have the expected properties
        if (!item.timestamp) {
          console.warn(`Network Status History item ${index} missing timestamp`);
        }
        
        // Extract metrics from the nested data object
        console.log(`Network Status History item ${index} nested data:`, networkData);
        
        // Extract validator data from the nested structure
        const validators = networkData.validators || {};
        console.log(`Network Status History item ${index} validators data:`, validators);
        
        const result = {
          timestamp: formatTimestamp(item.timestamp),
          active_stake: parseFloat(String(validators.active_stake || 0)),
          total_nodes: parseFloat(String(validators.total_nodes || validators.total || 0)),
          active_nodes: parseFloat(String(validators.active_nodes || validators.active || 0)),
          inactive_nodes: parseFloat(String(validators.inactive_nodes || validators.inactive || 0))
        };
        
        console.log(`Network Status History item ${index} processed result:`, result);
        
        return result;
      });
    } catch (error) {
      console.error('Error processing Network Status History data:', error);
      return [];
    }
  }, [data]);

  useEffect(() => {
    if (chartData && chartData.length > 0) {
      console.log('Network Status History: Processed chart data', chartData);
      console.log('Network Status History: First data point', chartData[0]);
    } else {
      console.warn('Network Status History: No chart data available after processing');
    }
  }, [chartData]);

  if (!chartData || chartData.length === 0) {
    return (
      <div style={styles.noDataMessage}>
        <div>No historical data available</div>
      </div>
    );
  }

  return (
    <div style={styles.chartContainer}>
      <ResponsiveContainer width="100%" height={400} minWidth={300} minHeight={300} aspect={2}>
        <LineChart
          data={chartData}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="timestamp" 
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => {
              if (!value || value === 'Unknown Date') return value;
              try {
                const date = new Date(value);
                if (isNaN(date.getTime())) {
                  return value;
                }
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
              } catch (error) {
                console.warn('Error formatting timestamp:', value, error);
                return value;
              }
            }}
          />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value, name) => {
              const formattedName = name === 'active_stake' ? 'Active Stake'
                : name === 'total_nodes' ? 'Total Nodes'
                : name === 'active_nodes' ? 'Active Nodes'
                : name === 'inactive_nodes' ? 'Inactive Nodes'
                : name;
              return [value, formattedName];
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="total_nodes"
            name="Total Nodes"
            stroke="#8884d8"
            activeDot={{ r: 8 }}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="active_nodes"
            name="Active Nodes"
            stroke="#82ca9d"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="inactive_nodes"
            name="Inactive Nodes"
            stroke="#ff7300"
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// Component for displaying mint analytics history
const MintAnalyticsHistory: React.FC<HistoricalDataProps> = ({ data, timeRange }) => {
  // Format data for chart
  const chartData = React.useMemo(() => {
    if (!data) {
      console.log('Mint Analytics History: Invalid data format', data);
      return [];
    }
    
    if (!Array.isArray(data)) {
      console.log('Mint Analytics History: Data is not an array', data);
      return [];
    }
    
    if (data.length === 0) {
      console.log('Mint Analytics History: Empty data array');
      return [];
    }
    
    console.log('Mint Analytics History: Processing data', data);
    console.log('Mint Analytics History: Data type', typeof data);
    console.log('Mint Analytics History: Is array', Array.isArray(data));
    console.log('Mint Analytics History: Length', data.length);
    
    try {
      return data.map((item: MintAnalyticsHistoryItem, index: number) => {
        // Extract values from item or nested data object
        const mintData = item.data || {};
        console.log(`Mint Analytics History item ${index}:`, item);
        console.log(`Mint Analytics History item ${index} structure:`, {
          hasTimestamp: !!item.timestamp,
          timestampValue: item.timestamp,
          hasNewMints: !!item.new_mints,
          newMintsValue: item.new_mints,
          hasNewMintsCount: !!item.new_mints_count,
          newMintsCountValue: item.new_mints_count,
          hasTotalMints: !!item.total_mints,
          totalMintsValue: item.total_mints,
          hasActiveMints: !!item.active_mints,
          activeMintsValue: item.active_mints,
          nestedDataKeys: Object.keys(mintData)
        });
        
        // Check if we have the expected properties
        if (!item.timestamp) {
          console.warn(`Mint Analytics History item ${index} missing timestamp`);
        }
        
        // Log the nested data structure
        console.log(`Mint Analytics History item ${index} nested data:`, mintData);
        
        const result = {
          timestamp: formatTimestamp(item.timestamp),
          new_mints: parseFloat(String(item.new_mints_count || mintData.new_mints_count || mintData.new_mints || 0)),
          total_mints: parseFloat(String(mintData.total_mints || 0)),
          active_mints: parseFloat(String(mintData.active_mints || 0))
        };
        
        console.log(`Mint Analytics History item ${index} processed result:`, result);
        console.log(`Mint Analytics History item ${index} processed result keys:`, Object.keys(result));
        console.log(`Mint Analytics History item ${index} processed result values:`, Object.values(result));
        
        return result;
      });
    } catch (error) {
      console.error('Error processing Mint Analytics History data:', error);
      return [];
    }
  }, [data]);

  useEffect(() => {
    if (chartData && chartData.length > 0) {
      console.log('Mint Analytics History: Processed chart data', chartData);
      console.log('Mint Analytics History: First data point', chartData[0]);
      console.log('Mint Analytics History: Processed chart data keys:', chartData.map(item => Object.keys(item)));
      console.log('Mint Analytics History: Processed chart data values:', chartData.map(item => Object.values(item)));
    } else {
      console.warn('Mint Analytics History: No chart data available after processing');
    }
  }, [chartData]);

  if (!chartData || chartData.length === 0) {
    return (
      <div style={styles.noDataMessage}>
        <div>No historical data available</div>
      </div>
    );
  }

  return (
    <div style={styles.chartContainer}>
      <ResponsiveContainer width="100%" height={400} minWidth={300} minHeight={300} aspect={2}>
        <LineChart
          data={chartData}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="timestamp" 
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => {
              if (!value || value === 'Unknown Date') return value;
              try {
                const date = new Date(value);
                if (isNaN(date.getTime())) {
                  return value;
                }
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
              } catch (error) {
                console.warn('Error formatting timestamp:', value, error);
                return value;
              }
            }}
          />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value, name) => {
              const formattedName = name === 'new_mints' ? 'New Mints'
                : name === 'total_mints' ? 'Total Mints'
                : name === 'active_mints' ? 'Active Mints'
                : name;
              return [value, formattedName];
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="new_mints"
            name="New Mints"
            stroke="#8884d8"
            activeDot={{ r: 8 }}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="total_mints"
            name="Total Mints"
            stroke="#82ca9d"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="active_mints"
            name="Active Mints"
            stroke="#ff7300"
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// Component for displaying pump tokens history
const PumpTokensHistory: React.FC<HistoricalDataProps> = ({ data, timeRange }) => {
  // Format data for chart
  const chartData = React.useMemo(() => {
    if (!data) {
      console.log('Pump Tokens History: Invalid data format', data);
      return [];
    }
    
    if (!Array.isArray(data)) {
      console.log('Pump Tokens History: Data is not an array', data);
      return [];
    }
    
    if (data.length === 0) {
      console.log('Pump Tokens History: Empty data array');
      return [];
    }
    
    console.log('Pump Tokens History: Processing data', data);
    console.log('Pump Tokens History: Data type', typeof data);
    console.log('Pump Tokens History: Is array', Array.isArray(data));
    console.log('Pump Tokens History: Length', data.length);
    
    try {
      return data.map((item: PumpTokensHistoryItem, index: number) => {
        // Extract values from item or nested data object
        const pumpData = item.data || {};
        console.log(`Pump Tokens History item ${index}:`, item);
        
        // Check if we have the expected properties
        if (!item.timestamp) {
          console.warn(`Pump Tokens History item ${index} missing timestamp`);
        }
        
        // Log the nested data structure
        console.log(`Pump Tokens History item ${index} nested data:`, pumpData);
        
        const result = {
          timestamp: formatTimestamp(item.timestamp),
          volume: parseFloat(String(pumpData.volume || 0)),
          price_change: parseFloat(String(pumpData.price_change || 0)),
          holder_growth: parseFloat(String(pumpData.holder_growth || 0)),
          tokens_count: parseFloat(String(item.tokens_count || 0))
        };
        
        console.log(`Pump Tokens History item ${index} processed result:`, result);
        console.log(`Pump Tokens History item ${index} processed result keys:`, Object.keys(result));
        console.log(`Pump Tokens History item ${index} processed result values:`, Object.values(result));
        console.log(`Pump Tokens History item ${index} processed result timestamp:`, result.timestamp);
        console.log(`Pump Tokens History item ${index} processed result volume:`, result.volume);
        console.log(`Pump Tokens History item ${index} processed result price_change:`, result.price_change);
        console.log(`Pump Tokens History item ${index} processed result holder_growth:`, result.holder_growth);
        console.log(`Pump Tokens History item ${index} processed result tokens_count:`, result.tokens_count);
        
        return result;
      });
    } catch (error) {
      console.error('Error processing Pump Tokens History data:', error);
      return [];
    }
  }, [data]);

  useEffect(() => {
    if (chartData && chartData.length > 0) {
      console.log('Pump Tokens History: Processed chart data', chartData);
      console.log('Pump Tokens History: First data point', chartData[0]);
      console.log('Pump Tokens History: Processed chart data keys:', chartData.map(item => Object.keys(item)));
      console.log('Pump Tokens History: Processed chart data values:', chartData.map(item => Object.values(item)));
    } else {
      console.warn('Pump Tokens History: No chart data available after processing');
    }
  }, [chartData]);

  if (!chartData || chartData.length === 0) {
    return (
      <div style={styles.noDataMessage}>
        <div>No historical data available</div>
      </div>
    );
  }

  return (
    <div style={styles.chartContainer}>
      <ResponsiveContainer width="100%" height={400} minWidth={300} minHeight={300} aspect={2}>
        <LineChart
          data={chartData}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="timestamp" 
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => {
              if (!value || value === 'Unknown Date') return value;
              try {
                const date = new Date(value);
                if (isNaN(date.getTime())) {
                  return value;
                }
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
              } catch (error) {
                console.warn('Error formatting timestamp:', value, error);
                return value;
              }
            }}
          />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value, name) => {
              const formattedName = name === 'volume' ? 'Volume'
                : name === 'price_change' ? 'Price Change'
                : name === 'holder_growth' ? 'Holder Growth'
                : name === 'tokens_count' ? 'Tokens Count'
                : name;
              return [value, formattedName];
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="volume"
            name="Volume"
            stroke="#8884d8"
            activeDot={{ r: 8 }}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="price_change"
            name="Price Change"
            stroke="#82ca9d"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="holder_growth"
            name="Holder Growth"
            stroke="#ff7300"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="tokens_count"
            name="Tokens Count"
            stroke="#34A85A"
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// Main component for historical data card
const HistoricalDataCard: React.FC = () => {
  const [timeRange, setTimeRange] = useState(24);
  const [blocksRange, setBlocksRange] = useState(2);
  const [timeframe, setTimeframe] = useState<'1h' | '24h' | '7d'>('24h');
  const [sortMetric, setSortMetric] = useState<'volume' | 'price_change' | 'holder_growth'>('volume');
  
  // Network Status History
  const { 
    data: networkStatusHistory, 
    isLoading: isLoadingNetworkStatus, 
    error: networkStatusError,
    refetch: refetchNetworkStatus 
  } = useQuery(
    ['networkStatusHistory', timeRange],
    () => fetchNetworkStatusHistory(timeRange),
    {
      refetchInterval: 300000, // 5 minutes
      staleTime: 60000, // 1 minute
      retry: 2,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
      onError: (err) => {
        console.error('Network Status History Error:', err);
      }
    }
  );
  
  // Mint Analytics History
  const { 
    data: mintAnalyticsHistory, 
    isLoading: isLoadingMintAnalytics, 
    error: mintAnalyticsError,
    refetch: refetchMintAnalytics 
  } = useQuery(
    ['mintAnalyticsHistory', blocksRange, timeRange],
    () => fetchMintAnalyticsHistory(blocksRange, timeRange),
    {
      refetchInterval: 300000, // 5 minutes
      staleTime: 60000, // 1 minute
      retry: 2,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
      onError: (err) => {
        console.error('Mint Analytics History Error:', err);
      }
    }
  );
  
  // Pump Tokens History
  const { 
    data: pumpTokensHistory, 
    isLoading: isLoadingPumpTokens, 
    error: pumpTokensError,
    refetch: refetchPumpTokens 
  } = useQuery(
    ['pumpTokensHistory', timeframe, sortMetric, timeRange],
    () => fetchPumpTokensHistory(timeframe, sortMetric, timeRange, 24),
    {
      refetchInterval: 300000, // 5 minutes
      staleTime: 60000, // 1 minute
      retry: 2,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
      onError: (err) => {
        console.error('Pump Tokens History Error:', err);
      }
    }
  );
  
  const handleTimeRangeChange = (value: number) => {
    setTimeRange(value);
  };
  
  const handleBlocksRangeChange = (value: number) => {
    setBlocksRange(value);
  };
  
  const handleTimeframeChange = (value: '1h' | '24h' | '7d') => {
    setTimeframe(value);
  };
  
  const handleSortMetricChange = (value: 'volume' | 'price_change' | 'holder_growth') => {
    setSortMetric(value);
  };
  
  return (
    <Card width="100%">
      <CardHeader>
        <Heading size="md">Historical Analytics</Heading>
      </CardHeader>
      <CardBody minHeight="500px">
        <Box width="100%" minHeight="450px">
          <Flex justify="flex-end" mb={4}>
            <Flex align="center">
              <Text fontWeight="bold" mr={2}>Time Range:</Text>
              <Select
                value={timeRange}
                onChange={(e) => handleTimeRangeChange(Number(e.target.value))}
                width="150px"
              >
                <option value={6}>Last 6 hours</option>
                <option value={12}>Last 12 hours</option>
                <option value={24}>Last 24 hours</option>
                <option value={48}>Last 48 hours</option>
              </Select>
            </Flex>
          </Flex>
          
          <Tabs isFitted variant="enclosed">
            <TabList mb="1em">
              <Tab>Network Status</Tab>
              <Tab>Mint Analytics</Tab>
              <Tab>Pump Tokens</Tab>
            </TabList>
            <TabPanels>
              <TabPanel minHeight="450px" height="450px" width="100%">
                {isLoadingNetworkStatus ? (
                  <Flex direction="column" align="center" justify="center" minHeight="300px">
                    <Spinner size="xl" />
                    <Text mt={4}>Loading network status history...</Text>
                  </Flex>
                ) : networkStatusError ? (
                  <Flex direction="column" align="center" justify="center" minHeight="300px">
                    <Text color="red.500" mb={4}>Error loading network status history</Text>
                    <Button colorScheme="blue" onClick={() => refetchNetworkStatus()}>
                      Retry
                    </Button>
                  </Flex>
                ) : (
                  <NetworkStatusHistory 
                    data={networkStatusHistory} 
                    timeRange={timeRange} 
                  />
                )}
              </TabPanel>
              <TabPanel minHeight="450px" height="450px" width="100%">
                {isLoadingMintAnalytics ? (
                  <Flex direction="column" align="center" justify="center" minHeight="300px">
                    <Spinner size="xl" />
                    <Text mt={4}>Loading mint analytics history...</Text>
                  </Flex>
                ) : mintAnalyticsError ? (
                  <Flex direction="column" align="center" justify="center" minHeight="300px">
                    <Text color="red.500" mb={4}>Error loading mint analytics history</Text>
                    <Button colorScheme="blue" onClick={() => refetchMintAnalytics()}>
                      Retry
                    </Button>
                  </Flex>
                ) : (
                  <MintAnalyticsHistory 
                    data={mintAnalyticsHistory} 
                    timeRange={timeRange} 
                  />
                )}
              </TabPanel>
              <TabPanel minHeight="450px" height="450px" width="100%">
                {isLoadingPumpTokens ? (
                  <Flex direction="column" align="center" justify="center" minHeight="300px">
                    <Spinner size="xl" />
                    <Text mt={4}>Loading pump tokens history...</Text>
                  </Flex>
                ) : pumpTokensError ? (
                  <Flex direction="column" align="center" justify="center" minHeight="300px">
                    <Text color="red.500" mb={4}>Error loading pump tokens history</Text>
                    <Button colorScheme="blue" onClick={() => refetchPumpTokens()}>
                      Retry
                    </Button>
                  </Flex>
                ) : (
                  <PumpTokensHistory 
                    data={pumpTokensHistory} 
                    timeRange={timeRange} 
                  />
                )}
              </TabPanel>
            </TabPanels>
          </Tabs>
        </Box>
      </CardBody>
    </Card>
  );
};

export default HistoricalDataCard;
