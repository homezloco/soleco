import React, { useEffect, useState } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Text,
  Select,
  NumberInput,
  NumberInputField,
  Stack,
  Flex,
  Badge,
} from '@chakra-ui/react';
import { pumpAnalyticsApi, PumpTokenStats } from '../../api/pumpAnalytics';
import { formatNumber, formatDate } from '../../utils/format';

interface PumpTokenListProps {
  type: 'recent' | 'new' | 'trending';
  limit?: number;
}

export const PumpTokenList: React.FC<PumpTokenListProps> = ({ type, limit = 10 }) => {
  const [tokens, setTokens] = useState<PumpTokenStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<string>('volume');
  const [minHolders, setMinHolders] = useState<number | null>(null);

  useEffect(() => {
    const fetchTokens = async () => {
      try {
        setLoading(true);
        let data;

        switch (type) {
          case 'recent':
            data = await pumpAnalyticsApi.getRecentPumpTokens({
              limit,
              include_stats: true,
              min_holder_count: minHolders || undefined,
            });
            break;
          case 'new':
            data = await pumpAnalyticsApi.getNewPumpTokens({
              time_window: 24,
              min_holder_count: minHolders || undefined,
            });
            break;
          case 'trending':
            data = await pumpAnalyticsApi.getTrendingPumpTokens({
              timeframe: '24h',
              sort_metric: sortBy as any,
            });
            break;
        }

        setTokens(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch tokens');
      } finally {
        setLoading(false);
      }
    };

    fetchTokens();
  }, [type, limit, sortBy, minHolders]);

  if (loading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
      </Box>
    );
  }

  if (error) {
    return (
      <Box textAlign="center" py={10} color="red.500">
        <Text>{error}</Text>
      </Box>
    );
  }

  return (
    <Box>
      <Flex justify="space-between" mb={4}>
        <Stack direction="row" spacing={4} align="center">
          <Select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            w="200px"
          >
            <option value="volume">Volume</option>
            <option value="holders">Holders</option>
            <option value="market_cap">Market Cap</option>
            <option value="price_change">Price Change</option>
          </Select>
          <NumberInput
            value={minHolders || ''}
            onChange={(_, value) => setMinHolders(value || null)}
            min={0}
            max={1000000}
            w="150px"
          >
            <NumberInputField placeholder="Min Holders" />
          </NumberInput>
        </Stack>
      </Flex>

      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>Token</Th>
            <Th isNumeric>Holders</Th>
            <Th isNumeric>Volume (24h)</Th>
            <Th isNumeric>Price Change</Th>
            <Th isNumeric>Market Cap</Th>
            <Th>Last Activity</Th>
          </Tr>
        </Thead>
        <Tbody>
          {tokens.map((token) => (
            <Tr key={token.address}>
              <Td>
                <Text fontFamily="mono">{token.address}</Text>
              </Td>
              <Td isNumeric>{formatNumber(token.holder_count)}</Td>
              <Td isNumeric>${formatNumber(token.volume_24h)}</Td>
              <Td isNumeric>
                <Badge
                  colorScheme={token.price_change_24h >= 0 ? 'green' : 'red'}
                >
                  {token.price_change_24h.toFixed(2)}%
                </Badge>
              </Td>
              <Td isNumeric>${formatNumber(token.market_cap)}</Td>
              <Td>{token.last_activity ? formatDate(token.last_activity) : 'N/A'}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};
