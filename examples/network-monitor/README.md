# Soleco Network Monitor

A real-time dashboard for monitoring the Solana network status using the Soleco API.

![Dashboard Screenshot](screenshots/dashboard.png)

## Features

- **Real-time Network Status**: Live monitoring of Solana network health
- **Performance Metrics**: TPS, block time, and confirmation time visualization
- **Validator Overview**: Distribution of validators by stake and status
- **RPC Node Health**: Status of RPC nodes with performance metrics
- **Alert System**: Configurable alerts for network events
- **Historical Data**: View and compare historical performance data

## Technologies

- **React**: Frontend library for building the user interface
- **TypeScript**: Type-safe JavaScript
- **Chart.js**: Data visualization library
- **Material-UI**: React component library
- **Soleco SDK**: JavaScript SDK for the Soleco API
- **WebSockets**: For real-time data updates

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Access to a Soleco API instance

### Installation

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/yourusername/soleco.git
cd soleco/examples/network-monitor

# Install dependencies
npm install

# Configure the application
cp .env.example .env
# Edit .env to set your Soleco API URL
```

### Running the Application

```bash
# Start the development server
npm start
```

Open your browser and navigate to `http://localhost:3000`.

## Usage

### Dashboard Overview

The main dashboard provides a comprehensive overview of the Solana network status:

- **Network Health Indicator**: Shows the overall health status of the network
- **Key Metrics**: Displays TPS, block time, and confirmation time
- **Performance Charts**: Shows historical performance data
- **Validator Distribution**: Visualizes validator distribution by stake and status
- **RPC Node Status**: Shows the status of RPC nodes with performance metrics

### Real-time Monitoring

The dashboard updates in real-time to show the current state of the network:

- **Live TPS Counter**: Shows the current transactions per second
- **Block Production**: Displays information about recent blocks
- **Validator Status**: Shows the status of validators (active, delinquent)
- **Alert Panel**: Displays alerts for network events

### Historical Data Analysis

You can view and analyze historical data:

- **Time Range Selection**: Select a time range to view historical data
- **Metric Comparison**: Compare different metrics over time
- **Anomaly Detection**: Highlights anomalies in the data
- **Export Data**: Export data for further analysis

## Configuration

You can configure the dashboard by editing the `.env` file:

```
# Soleco API URL
REACT_APP_SOLECO_API_URL=https://your-soleco-instance.com/api

# Update interval in milliseconds
REACT_APP_UPDATE_INTERVAL=5000

# Enable/disable features
REACT_APP_ENABLE_ALERTS=true
REACT_APP_ENABLE_WEBSOCKETS=true

# Theme
REACT_APP_THEME=dark
```

## Project Structure

```
network-monitor/
├── public/                # Static assets
├── src/
│   ├── components/        # React components
│   │   ├── Dashboard/     # Dashboard components
│   │   ├── Charts/        # Chart components
│   │   ├── Alerts/        # Alert components
│   │   └── common/        # Common components
│   ├── hooks/             # Custom React hooks
│   ├── services/          # API services
│   ├── store/             # State management
│   ├── types/             # TypeScript types
│   ├── utils/             # Utility functions
│   ├── App.tsx            # Main application component
│   └── index.tsx          # Application entry point
├── .env.example           # Example environment variables
├── package.json           # Project dependencies
└── tsconfig.json          # TypeScript configuration
```

## Key Components

### NetworkStatusCard

Displays the current network status with a health indicator.

```tsx
import React from 'react';
import { Card, CardContent, Typography, Box, Chip } from '@mui/material';
import { useNetworkStatus } from '../../hooks/useNetworkStatus';

export const NetworkStatusCard: React.FC = () => {
  const { status, isLoading, error } = useNetworkStatus();

  if (isLoading) return <Card><CardContent>Loading...</CardContent></Card>;
  if (error) return <Card><CardContent>Error: {error.message}</CardContent></Card>;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>Network Status</Typography>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="body1">Status:</Typography>
          <Chip 
            label={status.network_status} 
            color={status.network_status === 'healthy' ? 'success' : 'error'} 
          />
        </Box>
        <Box mt={2}>
          <Typography variant="body2">
            Current Slot: {status.performance.current_slot}
          </Typography>
          <Typography variant="body2">
            Block Height: {status.performance.current_block_height}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};
```

### PerformanceChart

Displays a chart of performance metrics over time.

```tsx
import React from 'react';
import { Card, CardContent, Typography } from '@mui/material';
import { Line } from 'react-chartjs-2';
import { usePerformanceHistory } from '../../hooks/usePerformanceHistory';

export const PerformanceChart: React.FC = () => {
  const { data, isLoading, error } = usePerformanceHistory();

  if (isLoading) return <Card><CardContent>Loading...</CardContent></Card>;
  if (error) return <Card><CardContent>Error: {error.message}</CardContent></Card>;

  const chartData = {
    labels: data.timestamps,
    datasets: [
      {
        label: 'TPS',
        data: data.tps,
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Transactions Per Second',
      },
    },
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>Performance</Typography>
        <Line data={chartData} options={options} />
      </CardContent>
    </Card>
  );
};
```

### ValidatorDistribution

Displays a pie chart of validator distribution by stake.

```tsx
import React from 'react';
import { Card, CardContent, Typography } from '@mui/material';
import { Pie } from 'react-chartjs-2';
import { useValidators } from '../../hooks/useValidators';

export const ValidatorDistribution: React.FC = () => {
  const { data, isLoading, error } = useValidators();

  if (isLoading) return <Card><CardContent>Loading...</CardContent></Card>;
  if (error) return <Card><CardContent>Error: {error.message}</CardContent></Card>;

  const chartData = {
    labels: ['Top 10%', 'Next 15%', 'Next 25%', 'Remaining 50%'],
    datasets: [
      {
        data: [
          data.stake_distribution.top_10_percent,
          data.stake_distribution.top_25_percent - data.stake_distribution.top_10_percent,
          data.stake_distribution.top_50_percent - data.stake_distribution.top_25_percent,
          100 - data.stake_distribution.top_50_percent,
        ],
        backgroundColor: [
          'rgba(255, 99, 132, 0.6)',
          'rgba(54, 162, 235, 0.6)',
          'rgba(255, 206, 86, 0.6)',
          'rgba(75, 192, 192, 0.6)',
        ],
        borderWidth: 1,
      },
    ],
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>Validator Stake Distribution</Typography>
        <Pie data={chartData} />
      </CardContent>
    </Card>
  );
};
```

## Custom Hooks

### useNetworkStatus

Hook for fetching the current network status.

```tsx
import { useState, useEffect } from 'react';
import { SolecoClient } from 'soleco-js';

const client = new SolecoClient({
  baseUrl: process.env.REACT_APP_SOLECO_API_URL,
});

export const useNetworkStatus = () => {
  const [status, setStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const result = await client.network.getStatus({
          includeValidators: true,
          includePerformance: true,
        });
        setStatus(result.data);
        setError(null);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return { status, isLoading, error };
};
```

## Contributing

Contributions are welcome! Please see the [Development Guide](../../docs/development_guide.md) for information on how to contribute.

## License

This example is licensed under the [MIT License](../../LICENSE).
