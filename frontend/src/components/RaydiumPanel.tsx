import {
  VStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  Spinner,
} from '@chakra-ui/react'
import { useQuery } from 'react-query'
import { raydiumApi, PoolInfo } from '../api/client'

export default function RaydiumPanel() {
  const { data: pools, isLoading, error } = useQuery<PoolInfo[]>(
    'raydiumPools',
    () => raydiumApi.getPools()
  )

  if (isLoading) {
    return (
      <VStack spacing={4} align="center" p={4}>
        <Spinner size="xl" />
        <Text>Loading Raydium pools...</Text>
      </VStack>
    )
  }

  if (error) {
    return (
      <VStack spacing={4} align="center" p={4}>
        <Text color="red.500">Error: {(error as Error).message}</Text>
      </VStack>
    )
  }

  return (
    <VStack spacing={6} align="stretch">
      <Text fontSize="2xl" fontWeight="bold">
        Raydium Liquidity Pools
      </Text>

      {pools && pools.length > 0 ? (
        <Table variant="simple">
          <Thead>
            <Tr>
              <Th>Pool Name</Th>
              <Th>Token Pair</Th>
              <Th isNumeric>Liquidity</Th>
              <Th isNumeric>24h Volume</Th>
            </Tr>
          </Thead>
          <Tbody>
            {pools.map((pool) => (
              <Tr key={pool.id}>
                <Td>{pool.name}</Td>
                <Td>{pool.token_a_symbol}/{pool.token_b_symbol}</Td>
                <Td isNumeric>${pool.liquidity.toLocaleString()}</Td>
                <Td isNumeric>${pool.volume_24h.toLocaleString()}</Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      ) : (
        <Text>No pools available</Text>
      )}
    </VStack>
  )
}
