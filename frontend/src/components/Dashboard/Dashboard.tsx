import React from 'react';
import { 
  Box, 
  Grid, 
  Heading, 
  Text, 
  Flex, 
  Stat, 
  StatLabel, 
  StatNumber, 
  StatHelpText, 
  StatArrow, 
  SimpleGrid,
  Card,
  CardHeader,
  CardBody,
  Divider,
  Spinner,
  useColorModeValue
} from '@chakra-ui/react';
import { useQuery } from 'react-query';
import NetworkStatusCard from './NetworkStatusCard';
import MintAnalyticsCard from './MintAnalyticsCard';
import RPCNodesCard from './RPCNodesCard';
import PumpTokensCard from './PumpTokensCard';
import PerformanceMetricsCard from './PerformanceMetricsCard';
import HistoricalDataCard from './HistoricalDataCard';
import PumpFunTopPerformersCard from './PumpFunTopPerformersCard';
import PumpFunKingOfTheHillCard from './PumpFunKingOfTheHillCard';

const Dashboard: React.FC = () => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Box p={5}>
      <Heading as="h1" size="xl" mb={6}>
        Solana Ecosystem Dashboard
      </Heading>
      
      <Text mb={6}>
        Real-time analytics and insights into the Solana blockchain ecosystem
      </Text>
      
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={5} mb={8}>
        <Stat
          px={{ base: 4, md: 6 }}
          py="5"
          shadow="md"
          border="1px solid"
          borderColor={borderColor}
          rounded="lg"
          bg={bgColor}
        >
          <StatLabel fontWeight="medium">Network Status</StatLabel>
          <StatNumber fontSize="2xl">Healthy</StatNumber>
          <StatHelpText>
            <StatArrow type="increase" />
            99.8% Uptime
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
          <StatLabel fontWeight="medium">Active RPC Nodes</StatLabel>
          <StatNumber fontSize="2xl">2,456</StatNumber>
          <StatHelpText>
            <StatArrow type="increase" />
            +12 in last 24h
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
          <StatLabel fontWeight="medium">New Mint Addresses</StatLabel>
          <StatNumber fontSize="2xl">583</StatNumber>
          <StatHelpText>
            <StatArrow type="increase" />
            Last 24 hours
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
          <StatLabel fontWeight="medium">New Pump Tokens</StatLabel>
          <StatNumber fontSize="2xl">127</StatNumber>
          <StatHelpText>
            <StatArrow type="increase" />
            Last 24 hours
          </StatHelpText>
        </Stat>
      </SimpleGrid>
      
      <Grid 
        templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} 
        gap={6}
        sx={{
          "& > *": {
            minHeight: "450px",
            width: "100%",
            height: "100%"
          }
        }}
      >
        <NetworkStatusCard />
        <MintAnalyticsCard />
        <RPCNodesCard />
        <PumpTokensCard />
        <PerformanceMetricsCard />
        <HistoricalDataCard />
        <PumpFunTopPerformersCard />
        <PumpFunKingOfTheHillCard includeNsfw={true} />
      </Grid>
    </Box>
  );
};

export default Dashboard;
