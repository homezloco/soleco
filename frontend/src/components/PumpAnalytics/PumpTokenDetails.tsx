import React, { useEffect, useState } from 'react';
import {
  Box,
  Grid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Text,
  Select,
} from '@chakra-ui/react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { pumpAnalyticsApi } from '../../api/pumpAnalytics';
import { formatNumber, formatDate } from '../../utils/format';

interface PumpTokenDetailsProps {
  tokenAddress: string;
}

export const PumpTokenDetails: React.FC<PumpTokenDetailsProps> = ({ tokenAddress }) => {
  const [tokenData, setTokenData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d' | '30d'>('24h');

  useEffect(() => {
    const fetchTokenData = async () => {
      try {
        setLoading(true);
        const data = await pumpAnalyticsApi.getTokenAnalytics(tokenAddress, {
          time_range: timeRange,
          include_holders: true,
          include_transactions: true,
        });
        setTokenData(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch token data');
      } finally {
        setLoading(false);
      }
    };

    fetchTokenData();
  }, [tokenAddress, timeRange]);

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

  if (!tokenData) {
    return null;
  }

  const { stats, historical_data, holders, transactions } = tokenData;

  return (
    <Box>
      {/* Overview Stats */}
      <Grid templateColumns="repeat(4, 1fr)" gap={6} mb={8}>
        <Stat>
          <StatLabel>Market Cap</StatLabel>
          <StatNumber>${formatNumber(stats.market_cap)}</StatNumber>
        </Stat>
        <Stat>
          <StatLabel>24h Volume</StatLabel>
          <StatNumber>${formatNumber(stats.volume_24h)}</StatNumber>
        </Stat>
        <Stat>
          <StatLabel>Holders</StatLabel>
          <StatNumber>{formatNumber(stats.holder_count)}</StatNumber>
        </Stat>
        <Stat>
          <StatLabel>Price Change (24h)</StatLabel>
          <StatNumber>
            <StatArrow type={stats.price_change_24h >= 0 ? 'increase' : 'decrease'} />
            {stats.price_change_24h.toFixed(2)}%
          </StatNumber>
        </Stat>
      </Grid>

      {/* Time Range Selector */}
      <Select
        value={timeRange}
        onChange={(e) => setTimeRange(e.target.value as any)}
        w="200px"
        mb={4}
      >
        <option value="1h">Last Hour</option>
        <option value="24h">24 Hours</option>
        <option value="7d">7 Days</option>
        <option value="30d">30 Days</option>
      </Select>

      {/* Detailed Data Tabs */}
      <Tabs>
        <TabList>
          <Tab>Price History</Tab>
          <Tab>Holders</Tab>
          <Tab>Transactions</Tab>
        </TabList>

        <TabPanels>
          <TabPanel>
            {/* Price History Chart */}
            <Box h="400px">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={historical_data.map((d: any) => ({
                    timestamp: new Date(d.timestamp).getTime(),
                    price: d.price,
                    volume: d.volume,
                  }))}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="timestamp"
                    tickFormatter={(timestamp) => formatDate(new Date(timestamp))}
                  />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip 
                    labelFormatter={(timestamp) => formatDate(new Date(timestamp))}
                    formatter={(value) => formatNumber(value)}
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="price"
                    stroke="#8884d8"
                    name="Price"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="volume"
                    stroke="#82ca9d"
                    name="Volume"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </TabPanel>

          <TabPanel>
            {/* Holders Table */}
            <Table>
              <Thead>
                <Tr>
                  <Th>Holder</Th>
                  <Th isNumeric>Balance</Th>
                  <Th isNumeric>% of Supply</Th>
                </Tr>
              </Thead>
              <Tbody>
                {holders.map((holder: any) => (
                  <Tr key={holder.address}>
                    <Td>
                      <Text fontFamily="mono">{holder.address}</Text>
                    </Td>
                    <Td isNumeric>{formatNumber(holder.balance)}</Td>
                    <Td isNumeric>
                      {((holder.balance / stats.total_supply) * 100).toFixed(2)}%
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </TabPanel>

          <TabPanel>
            {/* Transactions Table */}
            <Table>
              <Thead>
                <Tr>
                  <Th>Time</Th>
                  <Th>Type</Th>
                  <Th isNumeric>Amount</Th>
                  <Th isNumeric>Price</Th>
                  <Th>Signature</Th>
                </Tr>
              </Thead>
              <Tbody>
                {transactions.map((tx: any) => (
                  <Tr key={tx.transaction_signature}>
                    <Td>{formatDate(tx.timestamp)}</Td>
                    <Td>{tx.transaction_type}</Td>
                    <Td isNumeric>{formatNumber(tx.amount)}</Td>
                    <Td isNumeric>
                      {tx.price ? `$${formatNumber(tx.price)}` : 'N/A'}
                    </Td>
                    <Td>
                      <Text fontFamily="mono" isTruncated>
                        {tx.transaction_signature}
                      </Text>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};
