import React, { useState } from 'react';
import {
  Box,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Input,
  InputGroup,
  InputLeftElement,
  VStack,
  Heading,
  useToast,
} from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import { PumpTokenList } from './PumpTokenList';
import { PumpTokenDetails } from './PumpTokenDetails';
import { pumpAnalyticsApi } from '../../api/pumpAnalytics';

export const PumpAnalytics: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedToken, setSelectedToken] = useState<string | null>(null);
  const toast = useToast();

  const handleSearch = async (query: string) => {
    if (!query) {
      setSearchResults([]);
      return;
    }

    try {
      const results = await pumpAnalyticsApi.searchPumpTokens({
        query,
        match_type: 'contains',
        sort_by: 'volume'
      });
      setSearchResults(results);
    } catch (error) {
      toast({
        title: 'Search Error',
        description: 'Failed to search pump tokens',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  return (
    <Box p={6}>
      <VStack spacing={6} align="stretch">
        <Heading size="lg">Pump Token Analytics</Heading>

        <InputGroup>
          <InputLeftElement pointerEvents="none">
            <SearchIcon color="gray.300" />
          </InputLeftElement>
          <Input
            placeholder="Search pump tokens..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              handleSearch(e.target.value);
            }}
          />
        </InputGroup>

        {selectedToken ? (
          <PumpTokenDetails tokenAddress={selectedToken} />
        ) : (
          <Tabs>
            <TabList>
              <Tab>Recent</Tab>
              <Tab>New</Tab>
              <Tab>Trending</Tab>
              {searchResults.length > 0 && <Tab>Search Results</Tab>}
            </TabList>

            <TabPanels>
              <TabPanel>
                <PumpTokenList type="recent" limit={10} />
              </TabPanel>
              <TabPanel>
                <PumpTokenList type="new" limit={10} />
              </TabPanel>
              <TabPanel>
                <PumpTokenList type="trending" limit={10} />
              </TabPanel>
              {searchResults.length > 0 && (
                <TabPanel>
                  <Box>
                    {searchResults.map((token) => (
                      <Box
                        key={token.address}
                        p={4}
                        border="1px"
                        borderColor="gray.200"
                        borderRadius="md"
                        mb={2}
                        cursor="pointer"
                        onClick={() => setSelectedToken(token.address)}
                        _hover={{ bg: 'gray.50' }}
                      >
                        <VStack align="start" spacing={1}>
                          <Heading size="sm">{token.address}</Heading>
                          <Box fontSize="sm" color="gray.600">
                            Holders: {token.holder_count} | Volume: ${token.volume_24h}
                          </Box>
                        </VStack>
                      </Box>
                    ))}
                  </Box>
                </TabPanel>
              )}
            </TabPanels>
          </Tabs>
        )}
      </VStack>
    </Box>
  );
};
