# Soleco Web Dashboard

A modern, responsive web interface for visualizing and interacting with Soleco API data.

## Features

- **Network Status Dashboard**: Real-time visualization of Solana network health and performance
- **RPC Node Explorer**: Interactive explorer for Solana RPC nodes with filtering and sorting
- **Mint Analytics**: Visual representation of mint activity and pump token detection
- **Performance Metrics**: Charts and graphs showing historical performance data
- **Admin Panel**: Configuration and management interface for Soleco settings

## Technology Stack

- **React**: Frontend library for building user interfaces
- **TypeScript**: Type-safe JavaScript
- **Vite**: Next-generation frontend tooling
- **Tailwind CSS**: Utility-first CSS framework
- **Chart.js**: Data visualization library
- **React Query**: Data fetching and caching library
- **React Router**: Routing library for React
- **Axios**: HTTP client for API requests

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── api/             # API client and request handlers
│   ├── components/      # Reusable UI components
│   ├── context/         # React context providers
│   ├── hooks/           # Custom React hooks
│   ├── layouts/         # Page layout components
│   ├── pages/           # Page components
│   ├── store/           # State management
│   ├── styles/          # Global styles and themes
│   ├── types/           # TypeScript type definitions
│   ├── utils/           # Utility functions
│   ├── App.tsx          # Main application component
│   ├── main.tsx         # Application entry point
│   └── vite-env.d.ts    # Vite environment types
├── .eslintrc.js         # ESLint configuration
├── .prettierrc          # Prettier configuration
├── index.html           # HTML template
├── package.json         # Project dependencies and scripts
├── tailwind.config.js   # Tailwind CSS configuration
├── tsconfig.json        # TypeScript configuration
└── vite.config.ts       # Vite configuration
```

## Development

### Running the Development Server

```bash
npm run dev
```

### Building for Production

```bash
npm run build
```

### Running Tests

```bash
npm run test
```

## Dashboard Pages

### Network Status

The Network Status dashboard provides a real-time overview of the Solana network's health and performance. It includes:

- Current network status indicator
- Transaction per second (TPS) metrics
- Block production statistics
- Validator distribution map
- Recent performance history charts

### RPC Node Explorer

The RPC Node Explorer allows users to browse, search, and filter Solana RPC nodes. Features include:

- Searchable node list with filtering options
- Performance metrics for each node
- Health status indicators
- Version distribution charts
- Detailed node information views

### Mint Analytics

The Mint Analytics dashboard visualizes data related to token mints on Solana:

- Recent mint activity timeline
- Pump token detection alerts
- Token creation statistics
- Interactive mint explorer
- Token volume and activity charts

### Configuration

The Configuration page provides an interface for managing Soleco settings:

- RPC endpoint configuration
- Performance tuning options
- Logging level controls
- Feature toggles
- User preference settings

## Customization

### Themes

The dashboard supports light and dark themes, which can be customized in the `tailwind.config.js` file.

### Branding

To customize branding elements:

1. Replace logo files in the `public/` directory
2. Update color schemes in the `tailwind.config.js` file
3. Modify the `src/styles/variables.css` file for global style variables

## Contributing

Please see the [Development Guide](../docs/development_guide.md) for information on how to contribute to the Soleco Web Dashboard.
