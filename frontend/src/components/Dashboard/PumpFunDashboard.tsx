import React from 'react';
import { Grid, GridItem, Box } from '@chakra-ui/react';
import PumpFunMarketOverviewCard from './PumpFunMarketOverviewCard';
import PumpFunLatestTokensCard from './PumpFunLatestTokensCard';
import PumpFunTopPerformersCard from './PumpFunTopPerformersCard';
import PumpFunKingOfTheHillCard from './PumpFunKingOfTheHillCard';
import PumpFunLatestTradesCard from './PumpFunLatestTradesCard';
import PumpFunTokenExplorerCard from './PumpFunTokenExplorerCard';

const PumpFunDashboard: React.FC = () => {
  return (
    <Box>
      <Grid
        templateColumns={{ base: 'repeat(1, 1fr)', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }}
        gap={6}
        mb={6}
      >
        <GridItem>
          <PumpFunMarketOverviewCard />
        </GridItem>
        <GridItem>
          <PumpFunKingOfTheHillCard />
        </GridItem>
        <GridItem>
          <PumpFunTopPerformersCard />
        </GridItem>
      </Grid>

      <Grid
        templateColumns={{ base: 'repeat(1, 1fr)', lg: 'repeat(2, 1fr)' }}
        gap={6}
        mb={6}
      >
        <GridItem>
          <PumpFunLatestTokensCard />
        </GridItem>
        <GridItem>
          <PumpFunLatestTradesCard />
        </GridItem>
      </Grid>

      <Grid mb={6}>
        <GridItem>
          <PumpFunTokenExplorerCard />
        </GridItem>
      </Grid>
    </Box>
  );
};

export default PumpFunDashboard;
