import React from 'react';
import { 
  Box, 
  Tabs, 
  TabList, 
  TabPanels, 
  Tab, 
  TabPanel,
  useColorModeValue
} from '@chakra-ui/react';
import Dashboard from './Dashboard/Dashboard'; // Original dashboard
import PumpFunDashboard from './Dashboard/PumpFunDashboard'; // New PumpFun dashboard

const DashboardContainer: React.FC = () => {
  return (
    <Box>
      <Tabs variant="enclosed" colorScheme="blue">
        <TabList>
          <Tab>Solana Ecosystem</Tab>
          <Tab>Pump.fun Analytics</Tab>
        </TabList>
        
        <TabPanels>
          <TabPanel p={0} pt={5}>
            <Dashboard />
          </TabPanel>
          <TabPanel p={0} pt={5}>
            <PumpFunDashboard />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default DashboardContainer;
