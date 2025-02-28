# Soleco CLI Examples

This directory contains example scripts demonstrating how to use the Soleco CLI tool in different scenarios.

## Available Examples

### 1. Python API Usage Example

**File:** `cli_usage_example.py`

This example demonstrates how to use the Soleco CLI programmatically from Python code. It shows:

- How to configure the Soleco CLI
- How to initialize and use the API client
- How to fetch network status, RPC nodes, and mint information
- How to format and export data to different formats

To run this example:

```bash
python cli_usage_example.py
```

### 2. PowerShell Script Example

**File:** `cli_shell_example.ps1`

This example demonstrates how to use the Soleco CLI from PowerShell scripts. It shows:

- How to execute CLI commands from PowerShell
- How to process JSON and CSV output
- How to extract and analyze data from command results

To run this example:

```powershell
.\cli_shell_example.ps1
```

### 3. Bash Script Example

**File:** `cli_shell_example.sh`

This example demonstrates how to use the Soleco CLI from Bash scripts on Unix/Linux systems. It shows:

- How to execute CLI commands from Bash
- How to process JSON output using jq
- How to extract and analyze data from command results

To run this example:

```bash
chmod +x cli_shell_example.sh
./cli_shell_example.sh
```

### 4. Custom Commands Extension Example

**File:** `custom_commands_example.py`

This advanced example demonstrates how to extend the Soleco CLI with custom commands. It shows:

- How to create custom Click commands that build on Soleco functionality
- How to integrate with the Soleco API client
- How to implement specialized commands for specific use cases
- How to generate custom reports and analyses

The example includes these custom commands:
- `find-pump-tokens`: Find and filter pump tokens in recent blocks
- `compare-rpc-nodes`: Compare and rank RPC nodes by performance
- `daily-report`: Generate a daily report of Solana network activity

To run this example:

```bash
# Show help
python custom_commands_example.py --help

# Find pump tokens
python custom_commands_example.py find-pump-tokens --blocks 10

# Compare RPC nodes
python custom_commands_example.py compare-rpc-nodes --health-check

# Generate a daily report
python custom_commands_example.py daily-report --days 3 --output report.md
```

## Prerequisites

Before running these examples, make sure:

1. The Soleco CLI is installed:
   ```bash
   cd ../
   pip install -e .
   ```

2. The Soleco backend API is running and accessible (default: http://localhost:8000)

## Expected Output

Each example script will:

1. Configure the Soleco CLI
2. Fetch network status information
3. List RPC nodes
4. Analyze recent mints
5. Generate output files (JSON, CSV)

The scripts will create the following files:
- `network_status.json`: Contains Solana network status information
- `rpc_nodes.csv`: List of RPC nodes in CSV format
- `recent_mints.json`: Recent mint information in JSON format

## Customization

You can modify these examples to:

- Change the API endpoint
- Add additional commands
- Implement custom data processing logic
- Integrate with other tools and workflows

Feel free to use these examples as a starting point for your own scripts and applications.
