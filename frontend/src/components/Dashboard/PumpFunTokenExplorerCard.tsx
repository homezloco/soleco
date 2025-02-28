import React, { useState } from 'react';
import {
  Box,
  Card,
  CardHeader,
  CardBody,
  Heading,
  Text,
  Input,
  Button,
  Spinner,
  Flex,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  SimpleGrid,
  Image,
  Badge,
  InputGroup,
  InputRightElement,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Link,
  useColorModeValue
} from '@chakra-ui/react';
import { useQuery } from 'react-query';
import { pumpFunApi } from '../../api/pumpFunService';
import { SearchIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

const PumpFunTokenExplorerCard: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedMint, setSelectedMint] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState<'1d' | '7d' | '30d' | 'all'>('7d');

  // Search for tokens
  const { data: searchResults, isLoading: isSearching, refetch: refetchSearch } = useQuery(
    ['pumpfun-search-tokens', searchQuery],
    () => pumpFunApi.searchTokens(searchQuery),
    { 
      enabled: searchQuery.length > 2,
      staleTime: 60000
    }
  );

  // Get token details
  const { data: tokenDetails, isLoading: isLoadingDetails } = useQuery(
    ['pumpfun-token-details', selectedMint],
    () => pumpFunApi.getTokenDetails(selectedMint || ''),
    { 
      enabled: !!selectedMint,
      refetchInterval: 60000
    }
  );

  // Get token analytics
  const { data: tokenAnalytics, isLoading: isLoadingAnalytics } = useQuery(
    ['pumpfun-token-analytics', selectedMint],
    () => pumpFunApi.getTokenAnalytics(selectedMint || ''),
    { 
      enabled: !!selectedMint,
      refetchInterval: 60000
    }
  );

  // Get token history
  const { data: tokenHistory, isLoading: isLoadingHistory } = useQuery(
    ['pumpfun-token-history', selectedMint, timeframe],
    () => pumpFunApi.getTokenHistory(selectedMint || '', timeframe),
    { 
      enabled: !!selectedMint,
      refetchInterval: 60000
    }
  );

  const handleSearch = () => {
    if (searchQuery.length > 2) {
      refetchSearch();
    }
  };

  const handleSelectToken = (mint: string) => {
    setSelectedMint(mint);
    setSearchQuery(''); // Clear search after selection
  };

  const isLoading = isLoadingDetails || isLoadingAnalytics || isLoadingHistory;

  // Define interfaces for the token history data
  interface PriceHistoryItem {
    timestamp: string;
    price: number;
  }

  interface VolumeHistoryItem {
    timestamp: string;
    volume: number;
  }

  interface PumpFunToken {
    mint: string;
    name: string;
    symbol: string;
    image?: string;
    price: number;
  }

  // Format price history data for chart
  const formatPriceHistoryData = () => {
    if (!tokenHistory?.price_history) return [];
    
    return tokenHistory.price_history.map((item: PriceHistoryItem) => ({
      time: new Date(item.timestamp).toLocaleDateString(),
      price: item.price
    }));
  };

  // Format volume history data for chart
  const formatVolumeHistoryData = () => {
    if (!tokenHistory?.volume_history) return [];
    
    return tokenHistory.volume_history.map((item: VolumeHistoryItem) => ({
      time: new Date(item.timestamp).toLocaleDateString(),
      volume: item.volume
    }));
  };

  return (
    <Card>
      <CardHeader>
        <Heading size="md">Pump.fun Token Explorer</Heading>
      </CardHeader>
      <CardBody>
        {!selectedMint ? (
          <Box>
            <InputGroup mb={4}>
              <Input
                placeholder="Search for a token..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <InputRightElement>
                <Button size="sm" onClick={handleSearch}>
                  <SearchIcon />
                </Button>
              </InputRightElement>
            </InputGroup>
            
            {isSearching ? (
              <Flex justify="center" py={4}>
                <Spinner />
              </Flex>
            ) : searchResults?.length > 0 ? (
              <Box maxH="400px" overflowY="auto">
                {searchResults.map((token: PumpFunToken) => (
                  <Box
                    key={token.mint}
                    p={3}
                    mb={2}
                    borderWidth="1px"
                    borderRadius="md"
                    cursor="pointer"
                    _hover={{ bg: useColorModeValue('gray.100', 'gray.700') }}
                    onClick={() => handleSelectToken(token.mint)}
                  >
                    <Flex align="center">
                      {token.image && (
                        <Image
                          src={token.image}
                          alt={token.name || 'Token'}
                          boxSize="32px"
                          mr={3}
                          borderRadius="full"
                          fallbackSrc="https://via.placeholder.com/32"
                        />
                      )}
                      <Box>
                        <Text fontWeight="bold">{token.name || 'Unknown Token'}</Text>
                        <Flex align="center">
                          <Badge mr={2}>{token.symbol || 'N/A'}</Badge>
                          <Text fontSize="sm">{(token.price !== undefined && token.price !== null) ? token.price.toFixed(4) : '0.0000'} SOL</Text>
                        </Flex>
                      </Box>
                    </Flex>
                  </Box>
                ))}
              </Box>
            ) : searchQuery.length > 2 ? (
              <Text textAlign="center" py={4}>No tokens found</Text>
            ) : null}
          </Box>
        ) : (
          <Box>
            <Button 
              size="sm" 
              mb={4} 
              onClick={() => setSelectedMint(null)}
              variant="outline"
            >
              Back to Search
            </Button>
            
            {isLoading ? (
              <Flex justify="center" py={4}>
                <Spinner size="xl" />
              </Flex>
            ) : (
              <>
                <Flex direction={{ base: "column", md: "row" }} mb={6} align="center">
                  {tokenDetails?.image && (
                    <Image
                      src={tokenDetails.image}
                      alt={tokenDetails.name || 'Token'}
                      boxSize="64px"
                      mr={{ base: 0, md: 4 }}
                      mb={{ base: 4, md: 0 }}
                      borderRadius="full"
                      fallbackSrc="https://via.placeholder.com/64"
                    />
                  )}
                  
                  <Box flex="1" textAlign={{ base: "center", md: "left" }}>
                    <Heading size="md">{tokenDetails?.name || 'Unknown Token'}</Heading>
                    <Flex 
                      align="center" 
                      justify={{ base: "center", md: "flex-start" }}
                      mt={1}
                    >
                      <Badge mr={2}>{tokenDetails?.symbol || 'N/A'}</Badge>
                      <Link 
                        href={`https://pump.fun/token/${selectedMint}`} 
                        isExternal
                        color="blue.500"
                        fontSize="sm"
                      >
                        View on Pump.fun <ExternalLinkIcon mx="2px" />
                      </Link>
                    </Flex>
                  </Box>
                  
                  <Stat textAlign={{ base: "center", md: "right" }}>
                    <StatLabel>Current Price</StatLabel>
                    <StatNumber>{(tokenDetails?.price !== undefined && tokenDetails?.price !== null) ? tokenDetails.price.toFixed(4) : '0.0000'} SOL</StatNumber>
                    <StatHelpText>
                      {(tokenDetails?.change_percentage_24h !== undefined && tokenDetails?.change_percentage_24h !== null) && (
                        <>
                          <StatArrow type={tokenDetails.change_percentage_24h > 0 ? "increase" : "decrease"} />
                          {tokenDetails.change_percentage_24h.toFixed(2)}%
                        </>
                      )}
                    </StatHelpText>
                  </Stat>
                </Flex>
                
                <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={6}>
                  <Stat
                    p={3}
                    shadow="md"
                    border="1px solid"
                    borderColor={useColorModeValue('gray.200', 'gray.700')}
                    borderRadius="md"
                  >
                    <StatLabel>Volume (24h)</StatLabel>
                    <StatNumber>{(tokenAnalytics?.total_volume !== undefined && tokenAnalytics?.total_volume !== null) ? tokenAnalytics.total_volume.toFixed(2) : '0.00'} SOL</StatNumber>
                    {(tokenAnalytics?.volume_change_24h !== undefined && tokenAnalytics?.volume_change_24h !== null) && (
                      <StatHelpText>
                        <StatArrow type={tokenAnalytics.volume_change_24h > 0 ? "increase" : "decrease"} />
                        {tokenAnalytics.volume_change_24h.toFixed(2)}%
                      </StatHelpText>
                    )}
                  </Stat>
                  
                  <Stat
                    p={3}
                    shadow="md"
                    border="1px solid"
                    borderColor={useColorModeValue('gray.200', 'gray.700')}
                    borderRadius="md"
                  >
                    <StatLabel>Holders</StatLabel>
                    <StatNumber>{(tokenAnalytics?.holder_count !== undefined && tokenAnalytics?.holder_count !== null) ? tokenAnalytics.holder_count.toLocaleString() : '0'}</StatNumber>
                    <StatHelpText>
                      Created {(tokenAnalytics?.created_at !== undefined && tokenAnalytics?.created_at !== null) ? new Date(tokenAnalytics.created_at).toLocaleDateString() : 'Unknown'}
                    </StatHelpText>
                  </Stat>
                  
                  <Stat
                    p={3}
                    shadow="md"
                    border="1px solid"
                    borderColor={useColorModeValue('gray.200', 'gray.700')}
                    borderRadius="md"
                  >
                    <StatLabel>Trades</StatLabel>
                    <StatNumber>{(tokenAnalytics?.trade_count !== undefined && tokenAnalytics?.trade_count !== null) ? tokenAnalytics.trade_count.toLocaleString() : '0'}</StatNumber>
                    <StatHelpText>
                      All time
                    </StatHelpText>
                  </Stat>
                </SimpleGrid>
                
                <Tabs variant="enclosed" onChange={(index) => {
                  const timeframes: ('1d' | '7d' | '30d' | 'all')[] = ['1d', '7d', '30d', 'all'];
                  setTimeframe(timeframes[index]);
                }}>
                  <TabList>
                    <Tab>1D</Tab>
                    <Tab>7D</Tab>
                    <Tab>30D</Tab>
                    <Tab>All</Tab>
                  </TabList>
                  
                  <TabPanels>
                    {['1d', '7d', '30d', 'all'].map((_, index) => (
                      <TabPanel key={index} p={0} pt={4}>
                        <Box mb={6} h="250px">
                          <Heading size="sm" mb={2}>Price History</Heading>
                          <ResponsiveContainer width="100%" height="100%" minHeight={200} minWidth={300}>
                            <LineChart
                              data={formatPriceHistoryData()}
                              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="time" />
                              <YAxis />
                              <Tooltip />
                              <Legend />
                              <Line 
                                type="monotone" 
                                dataKey="price" 
                                stroke="#8884d8" 
                                activeDot={{ r: 8 }} 
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </Box>
                        
                        <Box h="250px">
                          <Heading size="sm" mb={2}>Volume History</Heading>
                          <ResponsiveContainer width="100%" height="100%" minHeight={200} minWidth={300}>
                            <LineChart
                              data={formatVolumeHistoryData()}
                              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="time" />
                              <YAxis />
                              <Tooltip />
                              <Legend />
                              <Line 
                                type="monotone" 
                                dataKey="volume" 
                                stroke="#82ca9d" 
                                activeDot={{ r: 8 }} 
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </Box>
                      </TabPanel>
                    ))}
                  </TabPanels>
                </Tabs>
              </>
            )}
          </Box>
        )}
      </CardBody>
    </Card>
  );
};

export default PumpFunTokenExplorerCard;
