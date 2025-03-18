# 🚀 Soleco: Solana Blockchain Analytics Platform

## 📖 Overview

A comprehensive API aggregator for the Solana ecosystem, integrating multiple protocols including Jupiter, Raydium, Birdeye, Meteora, and more.

## Project Structure

```
soleco/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── jupiter.py
│   │   │   ├── raydium.py
│   │   │   ├── birdeye.py
│   │   │   └── ...
│   │   └── main.py
│   └── requirements.txt
├── cli/
│   ├── soleco_cli/
│   │   ├── api.py
│   │   ├── config.py
│   │   ├── utils.py
│   │   └── ...
│   ├── tests/
│   └── README.md
└── frontend/
    ├── src/
    │   ├── api/
    │   │   └── client.ts
    │   ├── components/
    │   │   ├── JupiterPanel.tsx
    │   │   ├── RaydiumPanel.tsx
    │   │   └── BirdeyePanel.tsx
    │   └── App.tsx
    └── package.json
```

## Setup

### Backend

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the application
```bash
uvicorn app.main:app --reload
```

### CLI

1. Install the CLI tool:
```bash
cd cli
pip install -e .
```

2. Use the CLI:
```bash
soleco --help
```

For detailed CLI documentation, see [CLI README](cli/README.md)

## 📄 Documentation

Full API documentation available at `/docs` when the server is running.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md)

## 💡 Support & Community

- [Discord Community](https://discord.gg/your-discord)
- [Twitter](https://twitter.com/soleco)
- [GitHub Discussions](https://github.com/yourusername/soleco/discussions)

## 📊 Roadmap

- [ ] Implement more API integrations
- [ ] Develop frontend dashboard
- [ ] Add advanced analytics features
- [ ] Implement user authentication

## 📝 License

MIT License

## 💖 Sponsors

[Your sponsorship information]

## 🔄 Solana RPC Caching System

The Solana RPC caching system is designed to:

1. **Reduce load on Solana RPC nodes** - By caching responses, we minimize the number of direct RPC calls
2. **Improve application performance** - Cached responses are served much faster than making new RPC calls
3. **Provide consistent user experience** - Even when RPC nodes are experiencing issues, cached data ensures the application remains functional
4. **Allow for forced refresh** - When needed, users can manually refresh data to get the latest information

### Backend Caching

The backend implements SQLite-based caching for all Solana RPC endpoints:

- **Network Status** - Comprehensive network status information (TTL: 5 minutes)
- **Performance Metrics** - TPS and block production statistics (TTL: 3 minutes)
- **RPC Nodes** - Available RPC nodes with version distribution (TTL: 10 minutes)
- **Token Information** - Token metadata and details (TTL: 15 minutes)

All cache TTL values are centralized in `backend/app/constants/cache.py` for easy management.

### Frontend Integration

The frontend uses React Query with custom hooks for data fetching:

- **useSolanaQuery** - Custom hook for Solana API queries
- **useRefreshablePumpFunQuery** - Hook with manual refresh capability

### Components

- **NetworkStatusCard** - Displays network status information
- **PerformanceMetricsCard** - Shows performance metrics
- **RpcNodesCard** - Lists available RPC nodes
- **SolanaMonitoringDashboard** - Combines all components

### Error Handling

The caching system includes robust error handling:

- **Coroutine Handling** - Properly awaits coroutines in the NetworkStatusHandler
- **Response Processing** - Better handling of nested structures in RPC responses
- **Error Logging** - Enhanced logging with detailed error information
- **Graceful Degradation** - Returns cached data when available, even if current API calls fail

For more details, see the [Solana RPC Caching Documentation](./docs/solana_rpc_caching.md).

---

**Disclaimer**: This project is community-driven and not affiliated with Solana Foundation.

# Soleco - Solana Ecosystem Monitoring

## Overview
Soleco is a comprehensive monitoring and analytics platform for the Solana blockchain ecosystem, providing real-time insights into network health, RPC node performance, and validator statistics.

## Features
- Real-time Solana network status monitoring
- RPC node performance tracking
- Validator health and stake distribution analysis
- Historical performance metrics

## Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/soleco.git
cd soleco

# Install backend dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
cd frontend
npm install
```

## Contributing
We welcome contributions! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
