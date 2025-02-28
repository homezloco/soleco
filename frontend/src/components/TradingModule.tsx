import React, { useState, useEffect } from 'react';
import { 
  Box, 
  VStack, 
  HStack, 
  Input, 
  Button, 
  Text, 
  Select, 
  useToast 
} from '@chakra-ui/react';
import { 
  CoinData, 
  getCoinData, 
  buyToken, 
  sellToken, 
  getTokenBalances, 
  getNetworkDiagnostics 
} from '../api/tradingService';

const TradingModule: React.FC = () => {
  const [mintAddress, setMintAddress] = useState<string>('');
  const [solAmount, setSolAmount] = useState<string>('');
  const [slippage, setSlippage] = useState<number>(5);
  const [coinData, setCoinData] = useState<CoinData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const toast = useToast();

  const fetchCoinData = async () => {
    if (!mintAddress) return;
    
    setLoading(true);
    try {
      const data = await getCoinData(mintAddress);
      setCoinData(data);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch coin data",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleBuy = async () => {
    if (!mintAddress || !solAmount) return;
    
    setLoading(true);
    try {
      const amount = parseFloat(solAmount);
      if (isNaN(amount)) {
        throw new Error("Invalid SOL amount");
      }
      
      const response = await buyToken(mintAddress, amount, slippage);
      
      if (response.success) {
        toast({
          title: "Success",
          description: `Transaction successful: ${response.transaction_signature?.substring(0, 8)}...`,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        // Refresh data
        fetchCoinData();
      } else {
        throw new Error(response.error || "Transaction failed");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to complete transaction",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSell = async () => {
    if (!mintAddress) return;
    
    setLoading(true);
    try {
      // For simplicity, we're selling 100% of tokens
      const response = await sellToken(mintAddress, 0, slippage); // 0 means sell all
      
      if (response.success) {
        toast({
          title: "Success",
          description: `Transaction successful: ${response.transaction_signature?.substring(0, 8)}...`,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        // Refresh data
        fetchCoinData();
      } else {
        throw new Error(response.error || "Transaction failed");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to complete transaction",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box p={6} borderWidth={1} borderRadius="lg">
      <VStack spacing={4}>
        <Text fontSize="2xl" fontWeight="bold">Pump.fun Trading Module</Text>
        
        <Input 
          placeholder="Enter Token Mint Address" 
          value={mintAddress}
          onChange={(e) => setMintAddress(e.target.value)}
        />
        
        <Button 
          onClick={fetchCoinData}
          isLoading={loading}
          colorScheme="blue"
        >
          Fetch Coin Data
        </Button>

        {coinData && (
          <Box>
            <Text>Token Name: {coinData.name || 'N/A'}</Text>
            <Text>Virtual SOL Reserves: {coinData.virtual_sol_reserves}</Text>
            <Text>Virtual Token Reserves: {coinData.virtual_token_reserves}</Text>
          </Box>
        )}

        <HStack width="full">
          <Input 
            placeholder="SOL Amount" 
            type="number"
            value={solAmount}
            onChange={(e) => setSolAmount(e.target.value)}
          />
          <Select 
            value={slippage} 
            onChange={(e) => setSlippage(parseInt(e.target.value))}
            width="150px"
          >
            <option value={1}>1% Slippage</option>
            <option value={5}>5% Slippage</option>
            <option value={10}>10% Slippage</option>
          </Select>
        </HStack>

        <HStack>
          <Button 
            onClick={handleBuy}
            isLoading={loading}
            colorScheme="green"
          >
            Buy Token
          </Button>
          <Button 
            onClick={handleSell}
            isLoading={loading}
            colorScheme="red"
          >
            Sell Token
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
};

export default TradingModule;
