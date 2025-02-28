# Soleco Documentation

## Introduction

Welcome to the Soleco documentation! This comprehensive documentation covers all aspects of the Soleco platform, from installation and configuration to advanced usage and troubleshooting.

## Table of Contents

### Getting Started
- [Overview](overview.md) - Introduction to Soleco, its purpose, features, and architecture
- [Installation Guide](installation.md) - Step-by-step installation instructions
- [Configuration Guide](configuration.md) - Detailed configuration options and best practices

### Core Components
- [Solana Connection Pool](solana_connection_pool.md) - Documentation for the Solana RPC Connection Pool
- [Solana RPC Node Extractor](solana_rpc_node_extractor.md) - Documentation for the RPC Node Extractor
- [Mint Extraction System](mint_extraction_system.md) - Documentation for the Mint Extraction System
- [Error Handling System](error_handling_system.md) - Documentation for the Error Handling System
- [Network Status Monitoring](network_status_monitoring.md) - Documentation for the Network Status Monitoring
- [Logging System](logging_system.md) - Documentation for the Logging System

### API Reference
- [API Reference](api_reference.md) - Comprehensive API endpoint documentation

### Developer Resources
- [Development Guide](development_guide.md) - Guide for developers contributing to Soleco
- [Troubleshooting Guide](troubleshooting.md) - Solutions for common issues

## Quick Start

To get started with Soleco quickly:

1. **Install Soleco**:
   ```bash
   git clone https://github.com/yourusername/soleco.git
   cd soleco
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the root directory with:
   ```
   HELIUS_API_KEY=your_helius_api_key_here
   POOL_SIZE=5
   DEFAULT_TIMEOUT=30
   DEFAULT_MAX_RETRIES=3
   DEFAULT_RETRY_DELAY=1
   ```

3. **Run Soleco**:
   ```bash
   cd backend
   python run.py
   ```

4. **Access the API**:
   Open your browser and navigate to `http://localhost:8000/docs` to see the API documentation.

## Key Features

- **Enhanced Solana RPC Connection Pool**: Reliable and efficient connection management with prioritized endpoints and performance tracking
- **Comprehensive RPC Node Extractor**: Discover and analyze available RPC nodes on the Solana network
- **Advanced Mint Extraction System**: Track mint addresses and identify pump tokens
- **Robust Error Handling**: Structured error hierarchy and comprehensive logging
- **Real-time Network Status Monitoring**: Monitor the health and performance of the Solana network
- **Detailed Logging System**: Comprehensive logging for debugging and analysis

## Support

If you encounter any issues or have questions:

- Check the [Troubleshooting Guide](troubleshooting.md)
- Open an issue on GitHub
- Contact the Soleco support team

## Contributing

We welcome contributions to Soleco! Please see the [Development Guide](development_guide.md) for information on how to contribute.

## License

Soleco is licensed under the [MIT License](../LICENSE).
