# Solana RPC Endpoint Health Monitor

This script monitors the health of Solana RPC endpoints in the connection pool and updates their performance metrics. It helps ensure that the connection pool always uses the most reliable and performant endpoints.

## Features

- Periodically checks the health of all endpoints in the connection pool
- Updates performance metrics (success rate, latency, failure count)
- Re-sorts endpoints based on performance metrics
- Logs detailed statistics about endpoint performance
- Can run as a daemon process with graceful shutdown handling

## Usage

### Running Manually

```bash
# Run once with default settings (5-minute interval)
python -m app.scripts.monitor_rpc_health

# Run with a custom interval (e.g., 60 seconds)
python -m app.scripts.monitor_rpc_health --interval 60

# Run continuously as a daemon process
python -m app.scripts.monitor_rpc_health --daemon --interval 300
```

### Running as a Service

1. Edit the `solana_rpc_monitor.service` file to set the correct paths for your environment:

```
WorkingDirectory=/path/to/soleco/backend
ExecStart=/path/to/soleco/backend/venv/bin/python -m app.scripts.monitor_rpc_health --interval 300 --daemon
```

2. Copy the service file to the systemd directory:

```bash
sudo cp solana_rpc_monitor.service /etc/systemd/system/
```

3. Reload systemd, enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable solana_rpc_monitor
sudo systemctl start solana_rpc_monitor
```

4. Check the status of the service:

```bash
sudo systemctl status solana_rpc_monitor
```

5. View logs:

```bash
sudo journalctl -u solana_rpc_monitor -f
```

## Output

The script logs detailed information about the connection pool and endpoint performance:

- Current endpoints in the pool
- Health check results
- Top performing endpoints based on success rate and latency
- Connection pool statistics

## Integration with Connection Pool

The monitoring script integrates with the `SolanaConnectionPool` class to:

1. Check the health of all endpoints using a lightweight RPC call
2. Update performance metrics for each endpoint
3. Re-sort endpoints based on performance
4. Ensure the connection pool prioritizes the most reliable endpoints

This helps maintain optimal performance and reliability for Solana RPC connections.
