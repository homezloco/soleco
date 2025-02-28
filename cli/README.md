# Soleco CLI

A powerful command-line interface for interacting with the Soleco Solana blockchain analytics platform.

## Features

- **Network Analytics**: Access Solana network status and performance metrics
- **RPC Node Management**: List, analyze, and check health of Solana RPC nodes
- **Mint Analytics**: Track and analyze token mints, including pump tokens
- **Interactive Shell**: User-friendly shell for interactive exploration
- **Multiple Output Formats**: Export data as JSON, CSV, or formatted tables
- **Configuration Management**: Easily configure API endpoints and preferences

## Installation

### Using pip

```bash
pip install -e .
```

### From Source

```bash
git clone https://github.com/yourusername/soleco.git
cd soleco/cli
pip install -e .
```

## Usage

### Basic Commands

```bash
# Get help
soleco --help

# Check version
soleco --version

# Start interactive shell
soleco shell

# Enable debug logging
soleco --debug <command>
```

### Configuration

```bash
# View all configuration settings
soleco config

# Get a specific configuration value
soleco config --key api_url

# Set a configuration value
soleco set-config api_url http://localhost:8000

# Reset configuration to defaults
soleco reset-config
```

### Network Commands

```bash
# Get Solana network status
soleco network status

# Get summary only
soleco network status --summary

# Export as JSON
soleco network status --format json

# Save to file
soleco network status --output network_status.json

# Get performance metrics
soleco network performance
```

### RPC Node Commands

```bash
# List RPC nodes
soleco rpc list

# List with detailed information
soleco rpc list --details

# Perform health checks
soleco rpc list --health-check

# Filter by version
soleco rpc list --version 1.14.17

# Sort by latency
soleco rpc list --health-check --sort latency

# Get RPC statistics
soleco rpc stats

# Get filtered RPC statistics (excluding private endpoints)
soleco rpc stats --filtered
```

### Mint Commands

```bash
# Get recent mints
soleco mint recent

# Analyze more blocks
soleco mint recent --blocks 10

# Show only pump tokens
soleco mint recent --pump-only

# Show only new mint addresses
soleco mint recent --new-only

# Analyze a specific mint address
soleco mint analyze <MINT_ADDRESS>

# Include transaction history
soleco mint analyze <MINT_ADDRESS> --history

# Get mint statistics
soleco mint stats

# Get statistics for a different timeframe
soleco mint stats --timeframe 7d

# Extract mints from recent blocks
soleco mint extract

# Extract from more blocks
soleco mint extract --limit 5
```

### Diagnostics Commands

```bash
# Get system diagnostic information
soleco diagnostics info

# Export as JSON
soleco diagnostics info --format json
```

### Interactive Shell

The interactive shell provides a user-friendly interface for exploring Soleco functionality:

```bash
# Start the shell
soleco shell

# Inside the shell
> help                 # Display help
> config               # Show configuration
> set api_url <url>    # Set configuration
> status               # Show network status
> rpc                  # List RPC nodes
> mints                # Show recent mints
> diagnostics          # Show system diagnostics
> exit                 # Exit the shell
```

## Output Formats

Most commands support multiple output formats:

```bash
# Default table format
soleco network status

# JSON format
soleco network status --format json

# CSV format
soleco network status --format csv

# Save to file
soleco network status --format json --output result.json
```

## Development

### Setting Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

[MIT License](LICENSE)
