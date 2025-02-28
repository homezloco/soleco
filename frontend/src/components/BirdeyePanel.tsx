import {
  VStack,
  HStack,
  Input,
  Button,
  Text,
  Box,
  useToast,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
} from '@chakra-ui/react'
import { useState } from 'react'
import { useQuery } from 'react-query'
import { birdeyeApi, TokenInfo } from '../api/client'

export default function BirdeyePanel() {
  const [tokenAddress, setTokenAddress] = useState('')
  const [apiKey, setApiKey] = useState('')
  const toast = useToast()

  const { data: tokenInfo, isLoading, error, refetch } = useQuery<TokenInfo>(
    ['birdeyeToken', tokenAddress],
    () => birdeyeApi.getTokenInfo(tokenAddress, apiKey),
    {
      enabled: false,
      retry: 1,
    }
  )

  const handleSearch = () => {
    if (!tokenAddress || !apiKey) {
      toast({
        title: 'Error',
        description: 'Please provide both token address and API key',
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
      <Text fontSize="2xl" fontWeight="bold">
        Birdeye Token Info
      </Text>

      <VStack spacing={4}>
        <Input
          placeholder="Token Address"
          value={tokenAddress}
          onChange={(e) => setTokenAddress(e.target.value)}
        />
        <Input
          placeholder="Birdeye API Key"
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
        <Button
          colorScheme="blue"
          onClick={handleSearch}
          isLoading={isLoading}
          width="full"
        >
          Search Token
        </Button>
      </VStack>

      {error ? (
        <Text color="red.500">Error: {(error as Error).message}</Text>
      ) : null}

      {tokenInfo && (
        <Box p={5} shadow="md" borderWidth="1px" borderRadius="lg">
          <VStack spacing={4} align="stretch">
            <Stat>
              <StatLabel>Token Name</StatLabel>
              <StatNumber>{tokenInfo.name}</StatNumber>
              <StatHelpText>{tokenInfo.symbol}</StatHelpText>
            </Stat>

            <Stat>
              <StatLabel>Price</StatLabel>
              <StatNumber>${tokenInfo.price.toLocaleString()}</StatNumber>
            </Stat>

            <Stat>
              <StatLabel>24h Volume</StatLabel>
              <StatNumber>${tokenInfo.volume_24h.toLocaleString()}</StatNumber>
            </Stat>
          </VStack>
        </Box>
      )}
    </VStack>
  )
}
