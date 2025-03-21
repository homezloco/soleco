import React, { useMemo } from 'react';
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
  Image,
  Spinner,
  Flex,
  Badge,
  Link,
  useColorModeValue,
  Button
} from '@chakra-ui/react';
import { useQuery, useQueryClient } from 'react-query';
import { pumpFunApi } from '../../api/pumpFunService';
import { ExternalLinkIcon } from '@chakra-ui/icons';
import { getSafeImageUrl, handleImageError } from '../../utils/imageUtils';
import { format } from 'date-fns';

interface PumpFunToken {
  mint: string;
  image_uri?: string;
  name?: string;
  symbol?: string;
  virtual_sol_reserves?: number;
  virtual_token_reserves?: number;
  created_timestamp?: number;
}

const PumpFunLatestTokensCard: React.FC = () => {
  const queryClient = useQueryClient();
  const { data, isLoading, error, isError } = useQuery(
    'pumpfun-latest-tokens',
    () => pumpFunApi.getLatestTokens(10, true),
    { 
      refetchInterval: 30000, // Refresh every 30 seconds
      retry: 2,
      retryDelay: 1000,
      onError: (err: any) => {
        console.error('Error fetching latest tokens:', err);
      }
    }
  );

  // Filter out any duplicate tokens by mint address
  const uniqueTokens = useMemo(() => {
    if (!Array.isArray(data)) return [];
    
    const seenMints = new Set<string>();
    return data.filter(token => {
      if (!token.mint) return false;
      if (seenMints.has(token.mint)) return false;
      seenMints.add(token.mint);
      return true;
    });
  }, [data]);

  const handleRetry = () => {
    // Force refresh by passing true as the refresh parameter
    queryClient.fetchQuery('pumpfun-latest-tokens', () => 
      pumpFunApi.getLatestTokens(10, true)
    );
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader display="flex" justifyContent="space-between" alignItems="center">
          <Heading size="md">Latest Tokens</Heading>
          <Button 
            size="sm" 
            colorScheme="blue" 
            onClick={handleRetry}
            isLoading={isLoading}
          >
            Refresh
          </Button>
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
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    const isRateLimitError = errorMessage.includes('429') || errorMessage.includes('rate limit');
    
    return (
      <Card>
        <CardHeader display="flex" justifyContent="space-between" alignItems="center">
          <Heading size="md">Latest Tokens</Heading>
          <Button 
            size="sm" 
            colorScheme="blue" 
            onClick={handleRetry}
            isLoading={isLoading}
          >
            Refresh
          </Button>
        </CardHeader>
        <CardBody>
          <Box textAlign="center" py={4}>
            <Text color="red.500" mb={3}>
              {isRateLimitError 
                ? 'Backend API rate limit exceeded. Please try again later.' 
                : 'Error loading latest tokens'}
            </Text>
            <Text fontSize="sm" color="gray.500" mb={4}>
              Our backend API may be experiencing issues or rate limiting.
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
      <CardHeader display="flex" justifyContent="space-between" alignItems="center">
        <Heading size="md">Latest Pump.fun Tokens</Heading>
        <Button 
          size="sm" 
          colorScheme="blue" 
          onClick={handleRetry}
          isLoading={isLoading}
        >
          Refresh
        </Button>
      </CardHeader>
      <CardBody overflowX="auto">
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              <Th>Token</Th>
              <Th>Price</Th>
              <Th>Created</Th>
              <Th>Actions</Th>
            </Tr>
          </Thead>
          <Tbody>
            {Array.isArray(uniqueTokens) ? uniqueTokens.map((token: PumpFunToken, index: number) => (
              <Tr key={`${token.mint}-${index}`}>
                <Td>
                  <Flex align="center">
                    {token.image_uri && (
                      <Image 
                        src={getSafeImageUrl(token.image_uri)}
                        alt={token.name || 'Token'}
                        boxSize="24px" 
                        mr={2} 
                        borderRadius="full"
                        fallbackSrc="/assets/pumpfun-logo.png"
                        onError={(e) => handleImageError(e)}
                      />
                    )}
                    <Box>
                      <Text fontWeight="bold">{token.name || 'Unknown'}</Text>
                      <Text fontSize="xs" color="gray.500">{token.symbol || 'N/A'}</Text>
                    </Box>
                  </Flex>
                </Td>
                <Td>
                  {token.virtual_sol_reserves && token.virtual_token_reserves
                    ? (token.virtual_sol_reserves / (token.virtual_token_reserves / 1000000000) / 1000000000).toFixed(4)
                    : '0.0000'} SOL
                </Td>
                <Td>
                  {token.created_timestamp ? format(new Date(token.created_timestamp), 'MMM d, HH:mm') : 'Unknown date'}
                </Td>
                <Td>
                  <Link 
                    href={`https://pump.fun/token/${token.mint}`} 
                    isExternal 
                    color="blue.500"
                  >
                    View <ExternalLinkIcon mx="2px" />
                  </Link>
                </Td>
              </Tr>
            )) : null}
          </Tbody>
        </Table>
      </CardBody>
    </Card>
  );
};

export default PumpFunLatestTokensCard;
