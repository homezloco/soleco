import React from 'react';
import {
  Box,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Text,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Flex,
  Badge,
  Link,
  useColorModeValue,
  Button,
  Image
} from '@chakra-ui/react';
import { useQuery, useQueryClient } from 'react-query';
import { pumpFunApi, PumpFunTrade } from '../../api/pumpFunService';
import { ExternalLinkIcon } from '@chakra-ui/icons';
import { getSafeImageUrl, handleImageError } from '../../utils/imageUtils';
import { format } from 'date-fns';
import { formatDistanceToNow } from 'date-fns';

const PumpFunLatestTradesCard: React.FC = () => {
  const queryClient = useQueryClient();
  const { data, isLoading, error, isError } = useQuery(
    'pumpfun-latest-trades',
    () => pumpFunApi.getLatestTrades(15),
    { 
      refetchInterval: 30000, // Refresh every 30 seconds
      retry: 2,
      retryDelay: 1000,
      onError: (err: any) => {
        console.error('Error fetching latest trades:', err);
      }
    }
  );

  const handleRetry = () => {
    queryClient.invalidateQueries('pumpfun-latest-trades');
  };

  // Helper function to format timestamp
  const formatRelativeTime = (timestamp: string | number): string => {
    if (!timestamp) return 'Unknown';
    
    try {
      const date = new Date(typeof timestamp === 'string' ? parseInt(timestamp) : timestamp);
      if (isNaN(date.getTime())) return 'Invalid date';
      
      return formatDistanceToNow(date, { addSuffix: true });
    } catch (e) {
      console.error('Error formatting date:', e);
      return 'Unknown';
    }
  };

  // Format wallet address to shortened form (e.g., "Ax12...3Bcd")
  const formatAddress = (address: string): string => {
    if (!address) return 'Unknown';
    return `${address.substring(0, 4)}...${address.substring(address.length - 4)}`;
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Heading size="md">Latest Trades</Heading>
        </CardHeader>
        <CardBody>
          <Flex justify="center" align="center" h="300px">
            <Spinner size="xl" />
          </Flex>
        </CardBody>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <Heading size="md">Latest Trades</Heading>
        </CardHeader>
        <CardBody>
          <Box textAlign="center" py={4}>
            <Text color="red.500" mb={3}>
              Error loading latest trades
            </Text>
            <Text fontSize="sm" color="gray.500" mb={4}>
              Please try again later.
            </Text>
            <Button 
              colorScheme="blue" 
              size="sm"
              onClick={handleRetry}
            >
              Retry
            </Button>
          </Box>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <Heading size="md">Latest Pump.fun Trades</Heading>
      </CardHeader>
      <CardBody overflowX="auto">
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              <Th>Token</Th>
              <Th>Type</Th>
              <Th>Price</Th>
              <Th>Amount</Th>
              <Th>Total</Th>
              <Th>Time</Th>
            </Tr>
          </Thead>
          <Tbody>
            {Array.isArray(data) ? data.map((trade: PumpFunTrade, index: number) => (
              <Tr key={index}>
                <Td>
                  <Flex align="center">
                    {trade.image_uri ? (
                      <Image 
                        src={getSafeImageUrl(trade.image_uri)}
                        alt={trade.symbol || 'Token'}
                        boxSize="24px" 
                        mr={2} 
                        borderRadius="full"
                        fallbackSrc="/assets/pumpfun-logo.png"
                        onError={(e) => handleImageError(e)}
                      />
                    ) : (
                      <Box 
                        w="24px" 
                        h="24px" 
                        mr={2} 
                        borderRadius="full" 
                        bg="gray.200" 
                        display="flex" 
                        alignItems="center" 
                        justifyContent="center"
                      >
                        <Text fontSize="xs">{trade.symbol?.charAt(0) || '?'}</Text>
                      </Box>
                    )}
                    <Link
                      href={`https://pump.fun/token/${trade.mint}`}
                      isExternal
                      color="blue.500"
                    >
                      {trade.symbol || 'unknown'}
                    </Link>
                  </Flex>
                </Td>
                <Td>
                  <Badge colorScheme={trade.is_buy ? 'green' : 'red'}>
                    {trade.is_buy ? 'buy' : 'sell'}
                  </Badge>
                </Td>
                <Td>
                  {trade.sol_amount !== undefined 
                    ? (trade.sol_amount / 1000000000).toFixed(4) 
                    : '0.0000'} SOL
                </Td>
                <Td>
                  {trade.token_amount !== undefined 
                    ? (trade.token_amount / 1000000000).toFixed(2) 
                    : '0.00'}
                </Td>
                <Td>
                  {(trade.sol_amount !== undefined && trade.is_buy) 
                    ? (trade.sol_amount / 1000000000).toFixed(4) 
                    : '0.0000'} SOL
                </Td>
                <Td>{formatRelativeTime(trade.timestamp)}</Td>
              </Tr>
            )) : null}
          </Tbody>
        </Table>
      </CardBody>
    </Card>
  );
};

export default PumpFunLatestTradesCard;
