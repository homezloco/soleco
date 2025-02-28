import React, { useState } from 'react';
import {
  Box,
  Card,
  CardBody,
  CardHeader,
  Flex,
  Heading,
  Image,
  Select,
  Spinner,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  useColorModeValue,
  Link,
  Button,
  HStack,
  Tooltip,
  Icon
} from '@chakra-ui/react';
import { useState } from 'react';
import { useQuery } from 'react-query';
import { ExternalLinkIcon, RepeatIcon } from '@chakra-ui/icons';
import { FaTwitter, FaTelegram, FaGlobe } from 'react-icons/fa';
import { pumpFunApi } from '../../api/pumpFunService';
import { formatNumber, formatUSD, formatPercentage } from '../../utils/formatters';
import { PumpToken } from '../../types/pumpFun';

interface PumpFunTopPerformersCardProps {
  includeNsfw?: boolean;
}

const PumpFunTopPerformersCard: React.FC<PumpFunTopPerformersCardProps> = ({ includeNsfw = true }) => {
  const [metric, setMetric] = useState<string>('volume_24h');
  const [limit, setLimit] = useState<number>(10);
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryTextColor = useColorModeValue('gray.600', 'gray.400');
  
  const { data: tokens, isLoading, isError, refetch } = useQuery(
    ['topPerformers', metric, limit, includeNsfw],
    () => pumpFunApi.getTopPerformers({ 
      metric, 
      limit, 
      include_nsfw: includeNsfw 
    }),
    {
      refetchInterval: 300000, // Refetch every 5 minutes
      staleTime: 60000, // Consider data stale after 1 minute
    }
  );
  
  const handleMetricChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setMetric(e.target.value);
  };
  
  const handleLimitChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setLimit(Number(e.target.value));
  };
  
  const getMetricLabel = (metricKey: string): string => {
    const labels: Record<string, string> = {
      'volume_24h': '24h Volume',
      'price_change_1h': '1h Change',
      'price_change_24h': '24h Change',
      'price_change_7d': '7d Change',
      'market_cap': 'Market Cap'
    };
    return labels[metricKey] || metricKey;
  };
  
  const getMetricValue = (token: PumpToken, metricKey: string): string => {
    switch (metricKey) {
      case 'volume_24h':
        return formatUSD(token.volume_24h || 0);
      case 'price_change_1h':
        return formatPercentage(token.price_change_1h || 0);
      case 'price_change_24h':
        return formatPercentage(token.price_change_24h || 0);
      case 'price_change_7d':
        return formatPercentage(token.price_change_7d || 0);
      case 'market_cap':
        return formatUSD(token.market_cap || 0);
      default:
        return '—';
    }
  };
  
  const getMetricColor = (token: PumpToken, metricKey: string): string => {
    if (!metricKey.includes('price_change')) return 'inherit';
    
    const value = metricKey === 'price_change_1h' ? token.price_change_1h :
                  metricKey === 'price_change_24h' ? token.price_change_24h :
                  metricKey === 'price_change_7d' ? token.price_change_7d : 0;
                  
    return value > 0 ? 'green.500' : value < 0 ? 'red.500' : 'inherit';
  };
  
  const renderTokenImage = (token: PumpToken) => {
    if (!token.image_uri) {
      // Create an SVG with the token's initials
      const initials = (token.symbol || '??').substring(0, 2).toUpperCase();
      return (
        <Flex
          alignItems="center"
          justifyContent="center"
          bg="gray.200"
          color="gray.800"
          borderRadius="full"
          width="32px"
          height="32px"
          fontSize="xs"
          fontWeight="bold"
        >
          {initials}
        </Flex>
      );
    }
    
    return (
      <Image
        src={token.image_uri}
        alt={token.name || token.symbol || 'Token'}
        borderRadius="full"
        boxSize="32px"
        fallback={
          <Flex
            alignItems="center"
            justifyContent="center"
            bg="gray.200"
            color="gray.800"
            borderRadius="full"
            width="32px"
            height="32px"
            fontSize="xs"
            fontWeight="bold"
          >
            {(token.symbol || '??').substring(0, 2).toUpperCase()}
          </Flex>
        }
      />
    );
  };
  
  const renderSocialLinks = (token: PumpToken) => {
    return (
      <HStack spacing={2}>
        {token.website && (
          <Tooltip label={token.website}>
            <Link href={token.website} isExternal>
              <Icon as={FaGlobe} boxSize="14px" color="gray.500" />
            </Link>
          </Tooltip>
        )}
        {token.twitter && (
          <Tooltip label={`Twitter: ${token.twitter}`}>
            <Link href={`https://twitter.com/${token.twitter}`} isExternal>
              <Icon as={FaTwitter} boxSize="14px" color="twitter.500" />
            </Link>
          </Tooltip>
        )}
        {token.telegram && (
          <Tooltip label={`Telegram: ${token.telegram}`}>
            <Link href={`https://t.me/${token.telegram}`} isExternal>
              <Icon as={FaTelegram} boxSize="14px" color="telegram.500" />
            </Link>
          </Tooltip>
        )}
      </HStack>
    );
  };
  
  return (
    <Card
      bg={bgColor}
      borderColor={borderColor}
      borderWidth="1px"
      borderRadius="lg"
      boxShadow="sm"
      overflow="hidden"
      height="100%"
    >
      <CardHeader pb={0}>
        <Flex justifyContent="space-between" alignItems="center">
          <Heading size="md" color={textColor}>
            Top Performers
          </Heading>
          <HStack spacing={2}>
            <Select size="sm" value={metric} onChange={handleMetricChange} width="140px">
              <option value="volume_24h">Volume (24h)</option>
              <option value="price_change_1h">Price Change (1h)</option>
              <option value="price_change_24h">Price Change (24h)</option>
              <option value="price_change_7d">Price Change (7d)</option>
              <option value="market_cap">Market Cap</option>
            </Select>
            <Select size="sm" value={limit} onChange={handleLimitChange} width="80px">
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
            </Select>
            <Tooltip label="Refresh data">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => refetch()}
                aria-label="Refresh"
              >
                <RepeatIcon />
              </Button>
            </Tooltip>
          </HStack>
        </Flex>
      </CardHeader>
      <CardBody>
        {isLoading ? (
          <Flex justifyContent="center" alignItems="center" height="200px">
            <Spinner size="xl" color="blue.500" />
          </Flex>
        ) : isError ? (
          <Flex justifyContent="center" alignItems="center" height="200px" direction="column">
            <Text color="red.500" mb={4}>Error loading top performers</Text>
            <Button onClick={() => refetch()} colorScheme="blue" size="sm">
              Try Again
            </Button>
          </Flex>
        ) : tokens && tokens.length > 0 ? (
          <Box overflowX="auto">
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>#</Th>
                  <Th>Token</Th>
                  <Th isNumeric>Price</Th>
                  <Th isNumeric>{getMetricLabel(metric)}</Th>
                  <Th isNumeric>Liquidity</Th>
                </Tr>
              </Thead>
              <Tbody>
                {tokens.map((token, index) => (
                  <Tr key={`${token.mint}-${index}`}>
                    <Td>{index + 1}</Td>
                    <Td>
                      <Flex alignItems="center">
                        {renderTokenImage(token)}
                        <Box ml={3}>
                          <Flex alignItems="center">
                            <Text fontWeight="medium" fontSize="sm">
                              {token.symbol || '—'}
                            </Text>
                            <Link 
                              href={`https://pump.fun/token/${token.mint}`} 
                              isExternal 
                              ml={1}
                            >
                              <ExternalLinkIcon boxSize="12px" color="gray.500" />
                            </Link>
                          </Flex>
                          <Flex alignItems="center">
                            <Text fontSize="xs" color={secondaryTextColor} noOfLines={1} maxWidth="120px">
                              {token.name || '—'}
                            </Text>
                            {renderSocialLinks(token)}
                          </Flex>
                        </Box>
                      </Flex>
                    </Td>
                    <Td isNumeric>
                      <Text fontSize="sm">
                        {formatUSD(token.price || 0)}
                      </Text>
                    </Td>
                    <Td isNumeric>
                      <Text 
                        fontSize="sm" 
                        color={getMetricColor(token, metric)}
                        fontWeight="medium"
                      >
                        {getMetricValue(token, metric)}
                      </Text>
                    </Td>
                    <Td isNumeric>
                      <Text fontSize="sm">
                        {formatUSD(token.virtual_sol_reserves ? token.virtual_sol_reserves * 2 : 0)}
                      </Text>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        ) : (
          <Flex justifyContent="center" alignItems="center" height="200px">
            <Text color={secondaryTextColor}>No top performers found</Text>
          </Flex>
        )}
      </CardBody>
    </Card>
  );
};

export default PumpFunTopPerformersCard;
