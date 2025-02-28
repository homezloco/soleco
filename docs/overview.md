# Soleco Project Overview

## Introduction

Soleco is a comprehensive Solana blockchain analytics platform designed to provide real-time insights, monitoring, and analytics for the Solana ecosystem. The platform offers a variety of features including RPC node discovery and health monitoring, mint token tracking, pump token identification, and network status monitoring.

## Key Features

### 1. Solana RPC Node Management
- Discovery and tracking of all available Solana RPC nodes
- Health monitoring and performance metrics for RPC nodes
- Dynamic connection pooling with automatic fallback to healthy nodes
- Optimized DNS lookups and hostname resolution for RPC endpoints

### 2. Mint Token Analytics
- Tracking of all mint addresses in transactions
- Identification of newly created mint tokens
- Special tracking for "pump" tokens (addresses ending with 'pump')
- Historical analytics for mint token activity

### 3. Network Status Monitoring
- Comprehensive Solana network status reporting
- Performance metrics collection and analysis
- Validator information and vote account tracking
- Block production and transaction statistics

### 4. Robust Error Handling
- Enhanced error handling for Solana RPC interactions
- Coroutine handling and proper async/await patterns
- Structured error responses and detailed logging
- Rate limiting with automatic backoff

## Architecture

The Soleco platform is built with a modern, scalable architecture:

- **Backend**: FastAPI-based Python application
- **Frontend**: Modern web interface (details to be expanded)
- **Data Processing**: Asynchronous processing for high throughput
- **Connection Management**: Advanced connection pooling for reliability

## Technical Stack

- **Language**: Python 3.9+
- **Web Framework**: FastAPI
- **Async Framework**: asyncio
- **Solana Interaction**: Custom Solana RPC client with enhanced features
- **HTTP Client**: httpx for async HTTP requests
- **DNS Resolution**: dnspython for optimized DNS lookups

## Project Structure

```
soleco/
├── backend/
│   ├── app/
│   │   ├── config.py           # Configuration settings
│   │   ├── main.py             # FastAPI application entry point
│   │   ├── dependencies/       # Dependency injection components
│   │   ├── docs/               # API documentation
│   │   ├── models/             # Data models
│   │   ├── routers/            # API route definitions
│   │   ├── tests/              # Test suite
│   │   └── utils/              # Utility functions and classes
│   │       ├── handlers/       # Specialized handlers for different data types
│   │       └── solana_*.py     # Solana-specific utilities
│   ├── logs/                   # Application logs
│   └── requirements.txt        # Python dependencies
├── docs/                       # Project documentation
└── frontend/                   # Frontend application
```

## Getting Started

See the [Installation Guide](installation.md) for setup instructions and the [API Documentation](api.md) for details on available endpoints.

## Next Steps

See the [Roadmap](../ROADMAP.md) for planned features and enhancements.
