import React from 'react';
import { 
  Box, 
  Card, 
  CardBody, 
  CardHeader, 
  Heading, 
  Text, 
  Flex, 
  Image, 
  Spinner, 
  Badge, 
  SimpleGrid, 
  Stat, 
  StatLabel, 
  StatNumber, 
  StatHelpText, 
  StatArrow, 
  useColorModeValue 
} from '@chakra-ui/react';
import { useQuery } from 'react-query';
import { pumpFunApi } from '../../api/pumpFunService';
import { getSafeImageUrl, handleImageError } from '../../utils/imageUtils';

const PumpFunMarketOverviewCard: React.FC = () => {
  const { data, isLoading, error } = useQuery(
    'pumpfun-market-overview',
    () => pumpFunApi.getMarketOverview(),
    { refetchInterval: 60000 } // Refresh every minute
  );

  const { data: solPrice } = useQuery(
    'pumpfun-sol-price',
    () => pumpFunApi.getSolPrice(),
    { refetchInterval: 60000 } // Refresh every minute
  );

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Heading size="md">Market Overview</Heading>
        </CardHeader>
        <CardBody>
          <Flex justify="center" align="center" h="300px">
            <Spinner size="xl" />
          </Flex>
        </CardBody>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <Heading size="md">Market Overview</Heading>
        </CardHeader>
        <CardBody>
          <Text>Error loading market data</Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <Heading size="md">Pump.fun Market Overview</Heading>
      </CardHeader>
      <CardBody>
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={5}>
          <Stat
            px={{ base: 4, md: 6 }}
            py="5"
            shadow="md"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={bgColor}
          >
            <StatLabel fontWeight="medium">Total Tokens</StatLabel>
            <StatNumber fontSize="2xl">
              {typeof data?.total_tokens === 'number' ? data.total_tokens.toLocaleString() : '0'}
            </StatNumber>
            <StatHelpText>
              <StatArrow type="increase" />
              {typeof data?.new_tokens_24h === 'number' ? data.new_tokens_24h.toLocaleString() : '0'} new in 24h
            </StatHelpText>
          </Stat>
          
          <Stat
            px={{ base: 4, md: 6 }}
            py="5"
            shadow="md"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={bgColor}
          >
            <StatLabel fontWeight="medium">24h Volume</StatLabel>
            <StatNumber fontSize="2xl">
              {typeof data?.total_volume_24h === 'number' ? data.total_volume_24h.toLocaleString() : '0'} SOL
            </StatNumber>
            <StatHelpText>
              <StatArrow type="increase" />
              {typeof data?.total_trades_24h === 'number' ? data.total_trades_24h.toLocaleString() : '0'} trades
            </StatHelpText>
          </Stat>
          
          <Stat
            px={{ base: 4, md: 6 }}
            py="5"
            shadow="md"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={bgColor}
          >
            <StatLabel fontWeight="medium">SOL Price</StatLabel>
            <StatNumber fontSize="2xl">
              ${solPrice?.price ? solPrice.price.toFixed(2) : '0.00'}
            </StatNumber>
            <StatHelpText>
              <StatArrow type={(solPrice?.price_change_24h || 0) > 0 ? "increase" : "decrease"} />
              {solPrice?.price_change_24h ? Math.abs(solPrice.price_change_24h).toFixed(2) : '0.00'}% in 24h
            </StatHelpText>
          </Stat>
          
          <Stat
            px={{ base: 4, md: 6 }}
            py="5"
            shadow="md"
            border="1px solid"
            borderColor={borderColor}
            rounded="lg"
            bg={bgColor}
          >
            <StatLabel fontWeight="medium">Most Active Token</StatLabel>
            <StatNumber fontSize="2xl">
              {Array.isArray(data?.most_active_tokens) && data.most_active_tokens.length > 0 
                ? data.most_active_tokens[0].name || data.most_active_tokens[0].symbol || 'Unknown'
                : 'N/A'}
            </StatNumber>
            <StatHelpText>
              {Array.isArray(data?.most_active_tokens) && data.most_active_tokens.length > 0 && 
               typeof data.most_active_tokens[0].volume_24h === 'number' ? (
                <>
                  <StatArrow type="increase" />
                  {data.most_active_tokens[0].volume_24h.toLocaleString()} SOL volume
                </>
              ) : '0 SOL volume'}
            </StatHelpText>
          </Stat>
        </SimpleGrid>
      </CardBody>
    </Card>
  );
};

export default PumpFunMarketOverviewCard;
