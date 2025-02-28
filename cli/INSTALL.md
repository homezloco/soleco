# Installing the Soleco CLI

This guide provides instructions for installing and setting up the Soleco CLI tool.

## Prerequisites

Before installing the Soleco CLI, ensure you have the following:

- Python 3.8 or higher
- pip (Python package installer)
- Access to a Soleco backend API (for full functionality)

## Installation Methods

### Method 1: Install from Source (Development)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/soleco.git
   cd soleco/cli
   ```

2. Install the package in development mode:
   ```bash
   pip install -e .
   ```

   This will install the CLI in development mode, allowing you to make changes to the code and see them reflected immediately.

3. Verify the installation:
   ```bash
   soleco --version
   ```

### Method 2: Install from PyPI (Coming Soon)

Once the package is published to PyPI, you can install it directly:

```bash
pip install soleco-cli
```

## Configuration

After installation, you'll need to configure the CLI to connect to your Soleco backend:

```bash
# Set the API URL
soleco set-config api_url http://your-soleco-backend:8000

# View current configuration
soleco config
```

## Troubleshooting

### Common Issues

1. **Command not found**: If the `soleco` command is not found, ensure that Python's bin directory is in your PATH. You can also try running:
   ```bash
   python -m soleco_cli.cli
   ```

2. **Connection errors**: If you see connection errors, verify that:
   - The API URL is correct
   - The Soleco backend is running
   - There are no network issues or firewalls blocking the connection

3. **Import errors**: If you see import errors, ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

### Getting Help

If you encounter any issues, you can:

1. Run with debug logging:
   ```bash
   soleco --debug <command>
   ```

2. Check the CLI help:
   ```bash
   soleco --help
   ```

3. Contact the Soleco team for support

## Next Steps

Once installed, you can:

- Explore the CLI commands using `soleco --help`
- Try the interactive shell with `soleco shell`
- Check out the examples in the `examples` directory
- Read the full documentation in the README.md file
