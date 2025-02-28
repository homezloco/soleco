import React from 'react'
import { 
  ChakraProvider, 
  Box, 
  VStack, 
  Heading, 
  Tabs, 
  TabList, 
  TabPanels, 
  Tab, 
  TabPanel 
} from '@chakra-ui/react'
import { QueryClient, QueryClientProvider } from 'react-query'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import JupiterPanel from './components/JupiterPanel'
import RaydiumPanel from './components/RaydiumPanel'
import BirdeyePanel from './components/BirdeyePanel'
import TradingModule from './components/TradingModule'
import PumpAnalytics from './components/PumpAnalytics'
import CLIDocumentation from './components/CLIDocumentation'
import DashboardContainer from './components/DashboardContainer'
import { SolanaWalletContextProvider } from './wallet/WalletContext'
import { WalletConnection } from './wallet/WalletConnection'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <SolanaWalletContextProvider>
        <ChakraProvider>
          <Router>
            <Routes>
              <Route path="/" element={
                <Box p={8}>
                  <VStack spacing={8} align="stretch">
                    <Heading as="h1" size="2xl" textAlign="center">
                      Soleco - Solana Ecosystem Explorer
                    </Heading>

                    {/* Wallet Connection Component */}
                    <Box display="flex" justifyContent="flex-end" p={4}>
                      <WalletConnection />
                    </Box>

                    <Tabs isLazy variant="enclosed">
                      <TabList>
                        <Tab>Dashboard</Tab>
                        <Tab>Jupiter</Tab>
                        <Tab>Raydium</Tab>
                        <Tab>Birdeye</Tab>
                        <Tab>Pump.fun Trading</Tab>
                        <Tab>CLI</Tab>
                      </TabList>

                      <TabPanels>
                        <TabPanel>
                          <DashboardContainer />
                        </TabPanel>
                        <TabPanel>
                          <JupiterPanel />
                        </TabPanel>
                        <TabPanel>
                          <RaydiumPanel />
                        </TabPanel>
                        <TabPanel>
                          <BirdeyePanel />
                        </TabPanel>
                        <TabPanel>
                          <TradingModule />
                        </TabPanel>
                        <TabPanel>
                          <CLIDocumentation />
                        </TabPanel>
                      </TabPanels>
                    </Tabs>
                  </VStack>
                </Box>
              } />
              <Route path="/pump-analytics" element={<PumpAnalytics />} />
              <Route path="/cli" element={<CLIDocumentation />} />
              <Route path="/dashboard" element={<DashboardContainer />} />
            </Routes>
          </Router>
        </ChakraProvider>
      </SolanaWalletContextProvider>
    </QueryClientProvider>
  )
}

export default App
