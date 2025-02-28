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
  Select,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Link,
  useColorModeValue,
  Divider,
  Tooltip,
  HStack
} from '@chakra-ui/react';
import { ExternalLinkIcon, TriangleUpIcon, TriangleDownIcon } from '@chakra-ui/icons';
import { useQuery } from 'react-query';
import { pumpAnalyticsApi } from '../../api/pumpAnalytics';

const PumpTokensCard: React.FC = () => {
  const [timeframe, setTimeframe] = useState<'1h' | '24h' | '7d'>('24h');
  const [sortMetric, setSortMetric] = useState<'volume' | 'price_change' | 'holder_growth'>('volume');
  
  const { data, isLoading, error, refetch } = useQuery(
    ['trendingPumpTokens', timeframe, sortMetric],
    () => pumpAnalyticsApi.getTrendingPumpTokens({
      timeframe,
      sort_metric: sortMetric,
      min_market_cap: 1000 // Minimum market cap to filter out very small tokens
    }),
    {
      refetchInterval: 120000, // Refresh every 2 minutes
      staleTime: 60000, // Consider data stale after 1 minute
      retry: 3,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
      onError: (err) => {
        console.error('Pump Tokens Error:', err);
      }
    }
  );

  // Debug logging
  useEffect(() => {
    console.log('PumpTokensCard - Data:', data);
    console.log('PumpTokensCard - Loading:', isLoading);
    console.log('PumpTokensCard - Error:', error);
  }, [data, isLoading, error]);

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Check if data has a "detail" property which indicates an error
  const hasError = error || (data && data.detail);

  if (isLoading) {
    return (
      <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
        <CardHeader>
          <Heading size="md">Trending Pump Tokens</Heading>
        </CardHeader>
        <CardBody>
          <Flex justifyContent="center" alignItems="center" height="200px">
            <Spinner size="xl" />
          </Flex>
        </CardBody>
      </Card>
    );
  }

  if (hasError) {
    return (
      <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
        <CardHeader>
          <Heading size="md">Trending Pump Tokens</Heading>
        </CardHeader>
        <CardBody>
          <Flex direction="column" align="center" justify="center" minHeight="200px">
            <Text color="red.500" mb={4}>Error loading pump tokens data</Text>
            <Button colorScheme="blue" onClick={() => refetch()}>
              Retry
            </Button>
            <Text fontSize="sm" mt={4} color="gray.500">
              {data && data.detail === "Not Found" 
                ? "The pump trending endpoint is not available" 
                : "The server might be processing a large amount of data"}
            </Text>
          </Flex>
        </CardBody>
      </Card>
    );
  }

  // Mock data structure if the API doesn't return the expected format
  const tokens = data?.tokens || [];

  return (
    <Card shadow="md" borderWidth="1px" borderColor={borderColor} bg={cardBg}>
      <CardHeader>
        <Flex justify="space-between" align="center">
          <Heading size="md">Trending Pump Tokens</Heading>
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
          Last updated: {new Date(data?.timestamp || Date.now()).toLocaleString()}
        </Text>
        
        <Flex justify="space-between" mb={4}>
          <Box>
            <Text fontSize="sm" mb={1}>Timeframe:</Text>
            <Select 
              size="sm" 
              value={timeframe} 
              onChange={(e) => setTimeframe(e.target.value as '1h' | '24h' | '7d')}
              width="100px"
            >
              <option value="1h">1 Hour</option>
              <option value="24h">24 Hours</option>
              <option value="7d">7 Days</option>
            </Select>
          </Box>
          
          <Box>
            <Text fontSize="sm" mb={1}>Sort By:</Text>
            <Select 
              size="sm" 
              value={sortMetric} 
              onChange={(e) => setSortMetric(e.target.value as 'volume' | 'price_change' | 'holder_growth')}
              width="150px"
            >
              <option value="volume">Volume</option>
              <option value="price_change">Price Change</option>
              <option value="holder_growth">Holder Growth</option>
            </Select>
          </Box>
        </Flex>
        
        <Divider my={4} />
        
        <Box maxH="400px" overflowY="auto">
          <Table size="sm" variant="simple">
            <Thead position="sticky" top={0} bg={cardBg}>
              <Tr>
                <Th>Token</Th>
                <Th isNumeric>Price</Th>
                <Th isNumeric>Change</Th>
                <Th isNumeric>Volume (24h)</Th>
                <Th isNumeric>Holders</Th>
              </Tr>
            </Thead>
            <Tbody>
              {tokens.length > 0 ? (
                tokens.map((token, index) => (
                  <Tr key={index}>
                    <Td>
                      <Tooltip label={token.address}>
                        <Link href={`https://solscan.io/token/${token.address}`} isExternal>
                          {token.name || token.symbol || token.address.substring(0, 8)}
                          <ExternalLinkIcon mx="2px" />
                        </Link>
                      </Tooltip>
                    </Td>
                    <Td isNumeric>${token.price?.toFixed(6) || 'N/A'}</Td>
                    <Td isNumeric>
                      <HStack spacing={1} justify="flex-end">
                        {token.price_change_24h > 0 ? (
                          <TriangleUpIcon color="green.500" />
                        ) : token.price_change_24h < 0 ? (
                          <TriangleDownIcon color="red.500" />
                        ) : null}
                        <Text color={token.price_change_24h > 0 ? 'green.500' : token.price_change_24h < 0 ? 'red.500' : 'gray.500'}>
                          {Math.abs(token.price_change_24h || 0).toFixed(2)}%
                        </Text>
                      </HStack>
                    </Td>
                    <Td isNumeric>${token.volume_24h?.toLocaleString() || 'N/A'}</Td>
                    <Td isNumeric>{token.holder_count?.toLocaleString() || 'N/A'}</Td>
                  </Tr>
                ))
              ) : (
                <Tr>
                  <Td colSpan={5} textAlign="center">No pump tokens data available</Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        </Box>
        
        {tokens.length === 0 && (
          <Text fontSize="sm" mt={4} textAlign="center">
            No trending pump tokens found for the selected criteria.
          </Text>
        )}
        
        <Divider my={4} />
        
        <Flex justify="center">
          <Link href="/pump-analytics" color="blue.500">
            View Detailed Pump Analytics
          </Link>
        </Flex>
      </CardBody>
    </Card>
  );
};

export default PumpTokensCard;
