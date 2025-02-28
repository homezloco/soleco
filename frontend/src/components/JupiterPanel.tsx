import { useState, useEffect } from 'react'
import {
  VStack,
  HStack,
  Input,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  useToast,
  Box,
  Select,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  SimpleGrid,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  Badge,
} from '@chakra-ui/react'
import { useQuery } from 'react-query'
import { jupiterApi, SwapRoute } from '../api/client'

interface PopularToken {
  id: string;
  symbol: string;
  mint: string;
  price: number;
  price_24h_change?: number;
}

export default function JupiterPanel() {
  const [inputMint, setInputMint] = useState('')
  const [outputMint, setOutputMint] = useState('')
  const [amount, setAmount] = useState('')
  const [slippageBps, setSlippageBps] = useState('50')
  const toast = useToast()

  // Fetch popular tokens
  const { data: popularTokens, isLoading: loadingTokens } = useQuery<PopularToken[]>(
    'popularTokens',
    () => jupiterApi.getPopularTokens()
  )

  // Fetch routes
  const { data: routes, isLoading: loadingRoutes, error, refetch } = useQuery<SwapRoute[]>(
    ['jupiterRoutes', inputMint, outputMint, amount],
    () => jupiterApi.getRoutes({
      input_mint: inputMint,
      output_mint: outputMint,
      amount: Number(amount),
      slippage_bps: Number(slippageBps)
    }),
    {
      enabled: false,
      retry: 1,
    }
  )

  // Fetch market depth
  const { data: marketDepth, isLoading: loadingDepth } = useQuery(
    ['marketDepth', inputMint, outputMint],
    () => jupiterApi.getMarketDepth(inputMint, outputMint),
    {
      enabled: !!inputMint && !!outputMint,
    }
  )

  const handleSearch = () => {
    if (!inputMint || !outputMint || !amount) {
      toast({
        title: 'Error',
        description: 'Please fill in all fields',
        status: 'error',
        duration: 3000,
        isClosable: true,
      })
      return
    }
    refetch()
  }

  return (
    <VStack spacing={6} align="stretch">
      <Tabs isFitted variant="enclosed">
        <TabList mb="1em">
          <Tab>Swap</Tab>
          <Tab>Popular Tokens</Tab>
          <Tab>Market Depth</Tab>
        </TabList>

        <TabPanels>
          <TabPanel>
            <VStack spacing={4}>
              <HStack spacing={4} width="full">
                <Select
                  placeholder="Select Input Token"
                  value={inputMint}
                  onChange={(e) => setInputMint(e.target.value)}
                >
                  {popularTokens?.map((token) => (
                    <option key={token.mint} value={token.mint}>
                      {token.symbol} - {token.price.toFixed(2)} USD
                    </option>
                  ))}
                </Select>
                <Select
                  placeholder="Select Output Token"
                  value={outputMint}
                  onChange={(e) => setOutputMint(e.target.value)}
                >
                  {popularTokens?.map((token) => (
                    <option key={token.mint} value={token.mint}>
                      {token.symbol} - {token.price.toFixed(2)} USD
                    </option>
                  ))}
                </Select>
              </HStack>

              <HStack spacing={4} width="full">
                <Input
                  placeholder="Amount"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  type="number"
                />
                <Input
                  placeholder="Slippage (BPS)"
                  value={slippageBps}
                  onChange={(e) => setSlippageBps(e.target.value)}
                  type="number"
                  width="200px"
                />
                <Button
                  colorScheme="blue"
                  onClick={handleSearch}
                  isLoading={loadingRoutes}
                >
                  Find Routes
                </Button>
              </HStack>

              {error ? (
                <Text color="red.500">Error: {(error as Error).message}</Text>
              ) : null}

              {routes && routes.length > 0 ? (
                <Table variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Route ID</Th>
                      <Th isNumeric>Input Amount</Th>
                      <Th isNumeric>Output Amount</Th>
                      <Th isNumeric>Price Impact</Th>
                      <Th>Markets Used</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {routes.map((route) => (
                      <Tr key={route.route_id}>
                        <Td>{route.route_id.slice(0, 8)}...</Td>
                        <Td isNumeric>{route.in_amount}</Td>
                        <Td isNumeric>{route.out_amount}</Td>
                        <Td isNumeric>
                          <Badge
                            colorScheme={route.price_impact_pct < 1 ? 'green' : 'red'}
                          >
                            {route.price_impact_pct.toFixed(2)}%
                          </Badge>
                        </Td>
                        <Td>{route.market_infos.length} markets</Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              ) : null}
            </VStack>
          </TabPanel>

          <TabPanel>
            <SimpleGrid columns={3} spacing={4}>
              {loadingTokens ? (
                <Spinner />
              ) : (
                popularTokens?.map((token) => (
                  <Box
                    key={token.mint}
                    p={5}
                    shadow="md"
                    borderWidth="1px"
                    borderRadius="lg"
                  >
                    <Stat>
                      <StatLabel>{token.symbol}</StatLabel>
                      <StatNumber>${token.price.toFixed(2)}</StatNumber>
                      {token.price_24h_change && (
                        <StatHelpText>
                          <StatArrow
                            type={token.price_24h_change > 0 ? 'increase' : 'decrease'}
                          />
                          {Math.abs(token.price_24h_change).toFixed(2)}%
                        </StatHelpText>
                      )}
                    </Stat>
                  </Box>
                ))
              )}
            </SimpleGrid>
          </TabPanel>

          <TabPanel>
            {loadingDepth ? (
              <Spinner />
            ) : marketDepth ? (
              <VStack spacing={4}>
                <Text fontSize="xl">Market Depth Analysis</Text>
                {/* Add market depth visualization here */}
                <Box p={4} borderWidth="1px" borderRadius="lg">
                  <pre>{JSON.stringify(marketDepth, null, 2)}</pre>
                </Box>
              </VStack>
            ) : (
              <Text>Select tokens to view market depth</Text>
            )}
          </TabPanel>
        </TabPanels>
      </Tabs>
    </VStack>
  )
}
