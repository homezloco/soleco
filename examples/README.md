# Soleco Example Applications

This directory contains example applications that demonstrate how to use the Soleco API in real-world scenarios.

## Available Examples

1. [Network Monitor](#network-monitor) - A real-time Solana network monitoring dashboard
2. [RPC Node Explorer](#rpc-node-explorer) - An interactive tool for exploring and testing Solana RPC nodes
3. [Mint Tracker](#mint-tracker) - A tool for tracking new mint addresses and pump tokens
4. [Performance Analyzer](#performance-analyzer) - A utility for analyzing Solana network performance
5. [CLI Demo](#cli-demo) - Demonstration of the Soleco CLI tool
6. [SDK Examples](#sdk-examples) - Code examples for using the Soleco SDKs

## Network Monitor

A real-time dashboard for monitoring the Solana network status.

### Features

- Real-time TPS (Transactions Per Second) monitoring
- Validator health and stake distribution visualization
- Block production statistics
- Network performance metrics
- Configurable alerts for network events

### Technologies

- React.js with TypeScript
- Chart.js for data visualization
- WebSockets for real-time updates
- Soleco JavaScript SDK

### Running the Example

```bash
cd examples/network-monitor
npm install
npm start
```

Then open your browser to `http://localhost:3000`.

## RPC Node Explorer

An interactive tool for exploring and testing Solana RPC nodes.

### Features

- Browse and search available RPC nodes
- Test node performance and reliability
- Compare response times across different nodes
- View node version distribution
- Export node lists in various formats

### Technologies

- Vue.js with TypeScript
- Axios for HTTP requests
- D3.js for advanced visualizations
- Soleco JavaScript SDK

### Running the Example

```bash
cd examples/rpc-explorer
npm install
npm run serve
```

Then open your browser to `http://localhost:8080`.

## Mint Tracker

A tool for tracking new mint addresses and pump tokens on the Solana blockchain.

### Features

- Real-time notifications for new mint addresses
- Pump token detection and alerts
- Historical mint activity visualization
- Token metadata lookup
- Export data to CSV or JSON

### Technologies

- Python with FastAPI
- SQLite for data storage
- Plotly for data visualization
- Soleco Python SDK

### Running the Example

```bash
cd examples/mint-tracker
pip install -r requirements.txt
python app.py
```

Then open your browser to `http://localhost:5000`.

## Performance Analyzer

A utility for analyzing Solana network performance.

### Features

- Historical performance data analysis
- Comparison of different time periods
- Correlation analysis between metrics
- Performance prediction
- Anomaly detection

### Technologies

- Python with Pandas and NumPy
- Jupyter Notebook
- Matplotlib and Seaborn for visualization
- Scikit-learn for predictions
- Soleco Python SDK

### Running the Example

```bash
cd examples/performance-analyzer
pip install -r requirements.txt
jupyter notebook
```

Then open the `Performance_Analysis.ipynb` notebook.

## CLI Demo

Demonstration of the Soleco CLI tool with example scripts and workflows.

### Features

- Example shell scripts for common tasks
- Automated data collection and analysis
- Integration with system monitoring tools
- Batch processing examples
- Data export and visualization

### Technologies

- Bash scripts
- Python scripts
- Soleco CLI
- GNU tools (awk, sed, grep, etc.)

### Running the Example

```bash
cd examples/cli-demo
chmod +x *.sh
./demo.sh
```

## SDK Examples

Code examples for using the Soleco SDKs in different programming languages.

### JavaScript/TypeScript Examples

```bash
cd examples/sdk/javascript
npm install
node network-status.js
```

### Python Examples

```bash
cd examples/sdk/python
pip install -r requirements.txt
python network_status.py
```

### Rust Examples

```bash
cd examples/sdk/rust
cargo run --example network-status
```

## Example Structure

Each example follows a similar structure:

```
example-name/
├── README.md           # Specific documentation for this example
├── src/                # Source code
├── tests/              # Tests
├── package.json        # For JavaScript/TypeScript examples
├── requirements.txt    # For Python examples
├── Cargo.toml          # For Rust examples
└── screenshots/        # Screenshots and images
```

## Contributing

We welcome contributions to these examples! Please see the [Development Guide](../docs/development_guide.md) for information on how to contribute.

## License

These examples are licensed under the [MIT License](../LICENSE).
