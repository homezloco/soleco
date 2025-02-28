# Soleco SDK

Official Software Development Kits for interacting with the Soleco API in multiple programming languages.

## Available SDKs

- [JavaScript/TypeScript](#javascripttypescript)
- [Python](#python)
- [Rust](#rust)

## JavaScript/TypeScript

### Features

- Full TypeScript support with comprehensive type definitions
- Promise-based API with async/await support
- Browser and Node.js compatibility
- Automatic retries and error handling
- Comprehensive documentation and examples

### Installation

```bash
# npm
npm install soleco-js

# yarn
yarn add soleco-js

# pnpm
pnpm add soleco-js
```

### Usage

```typescript
import { SolecoClient } from 'soleco-js';

// Initialize client
const soleco = new SolecoClient({
  baseUrl: 'https://your-soleco-instance.com/api',
  apiKey: 'your_api_key_here', // Optional
  timeout: 30000, // 30 seconds
  retries: 3
});

// Get network status
async function getNetworkStatus() {
  try {
    const status = await soleco.network.getStatus({
      includeValidators: true,
      includePerformance: true
    });
    console.log('Network status:', status);
  } catch (error) {
    console.error('Error getting network status:', error);
  }
}

// List RPC nodes
async function listRpcNodes() {
  try {
    const nodes = await soleco.rpc.listNodes({
      includeDetails: true,
      healthCheck: true
    });
    console.log('RPC nodes:', nodes);
  } catch (error) {
    console.error('Error listing RPC nodes:', error);
  }
}

// Extract mint addresses
async function extractMintAddresses(blockNumber) {
  try {
    const mints = await soleco.mint.extractFromBlock(blockNumber);
    console.log('Mint addresses:', mints);
  } catch (error) {
    console.error('Error extracting mint addresses:', error);
  }
}

// Get recent new mints
async function getRecentMints() {
  try {
    const recentMints = await soleco.mint.getRecent({
      limit: 10,
      includePumpTokens: true
    });
    console.log('Recent mints:', recentMints);
  } catch (error) {
    console.error('Error getting recent mints:', error);
  }
}
```

### Advanced Usage

```typescript
// Using the WebSocket API for real-time updates
const subscription = soleco.network.subscribeToStatus({
  includeValidators: true,
  updateInterval: 5000 // 5 seconds
});

subscription.on('update', (status) => {
  console.log('Network status updated:', status);
});

subscription.on('error', (error) => {
  console.error('Subscription error:', error);
});

// Unsubscribe when done
subscription.unsubscribe();

// Batch operations
const batchResults = await soleco.batch([
  soleco.network.getStatus(),
  soleco.rpc.listNodes(),
  soleco.mint.getRecent({ limit: 5 })
]);

// Custom request
const customResult = await soleco.request({
  method: 'GET',
  path: '/custom/endpoint',
  params: { foo: 'bar' }
});
```

## Python

### Features

- Async and sync API support
- Type hints for better IDE integration
- Automatic retries and error handling
- Context manager support
- Comprehensive documentation and examples

### Installation

```bash
pip install soleco-py
```

### Usage

```python
from soleco import SolecoClient

# Initialize client
soleco = SolecoClient(
    base_url="https://your-soleco-instance.com/api",
    api_key="your_api_key_here",  # Optional
    timeout=30,  # 30 seconds
    retries=3
)

# Get network status
def get_network_status():
    try:
        status = soleco.network.get_status(
            include_validators=True,
            include_performance=True
        )
        print("Network status:", status)
    except Exception as e:
        print("Error getting network status:", e)

# List RPC nodes
def list_rpc_nodes():
    try:
        nodes = soleco.rpc.list_nodes(
            include_details=True,
            health_check=True
        )
        print("RPC nodes:", nodes)
    except Exception as e:
        print("Error listing RPC nodes:", e)

# Extract mint addresses
def extract_mint_addresses(block_number):
    try:
        mints = soleco.mint.extract_from_block(block_number)
        print("Mint addresses:", mints)
    except Exception as e:
        print("Error extracting mint addresses:", e)

# Get recent new mints
def get_recent_mints():
    try:
        recent_mints = soleco.mint.get_recent(
            limit=10,
            include_pump_tokens=True
        )
        print("Recent mints:", recent_mints)
    except Exception as e:
        print("Error getting recent mints:", e)
```

### Async Usage

```python
import asyncio
from soleco import AsyncSolecoClient

async def main():
    # Initialize async client
    async with AsyncSolecoClient(
        base_url="https://your-soleco-instance.com/api",
        api_key="your_api_key_here"
    ) as soleco:
        # Get network status
        status = await soleco.network.get_status()
        print("Network status:", status)
        
        # List RPC nodes
        nodes = await soleco.rpc.list_nodes()
        print("RPC nodes:", nodes)
        
        # Parallel requests
        status, nodes, mints = await asyncio.gather(
            soleco.network.get_status(),
            soleco.rpc.list_nodes(),
            soleco.mint.get_recent(limit=5)
        )

# Run the async function
asyncio.run(main())
```

### Advanced Usage

```python
# Context manager for automatic cleanup
with SolecoClient(base_url="https://your-soleco-instance.com/api") as soleco:
    # Use the client
    status = soleco.network.get_status()

# Custom request
custom_result = soleco.request(
    method="GET",
    path="/custom/endpoint",
    params={"foo": "bar"}
)

# Streaming responses
for item in soleco.mint.stream_recent(limit=100, batch_size=10):
    print("Mint:", item)
```

## Rust

### Features

- Strong type safety and performance
- Async/await support
- Error handling with custom error types
- Serialization/deserialization with serde
- Comprehensive documentation and examples

### Installation

Add to your `Cargo.toml`:

```toml
[dependencies]
soleco = "0.1.0"
```

### Usage

```rust
use soleco::{SolecoClient, SolecoConfig};
use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize client
    let config = SolecoConfig::new()
        .with_base_url("https://your-soleco-instance.com/api")
        .with_api_key("your_api_key_here") // Optional
        .with_timeout(std::time::Duration::from_secs(30))
        .with_retries(3);
    
    let client = SolecoClient::new(config);
    
    // Get network status
    let status = client.network().get_status()
        .include_validators(true)
        .include_performance(true)
        .send()
        .await?;
    
    println!("Network status: {:?}", status);
    
    // List RPC nodes
    let nodes = client.rpc().list_nodes()
        .include_details(true)
        .health_check(true)
        .send()
        .await?;
    
    println!("RPC nodes: {:?}", nodes);
    
    // Extract mint addresses
    let block_number = 123456789;
    let mints = client.mint().extract_from_block(block_number)
        .send()
        .await?;
    
    println!("Mint addresses: {:?}", mints);
    
    // Get recent new mints
    let recent_mints = client.mint().get_recent()
        .limit(10)
        .include_pump_tokens(true)
        .send()
        .await?;
    
    println!("Recent mints: {:?}", recent_mints);
    
    Ok(())
}
```

### Advanced Usage

```rust
use soleco::{SolecoClient, SolecoConfig};
use futures::future;
use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    let client = SolecoClient::new(SolecoConfig::new()
        .with_base_url("https://your-soleco-instance.com/api"));
    
    // Parallel requests
    let (status, nodes, mints) = future::join3(
        client.network().get_status().send(),
        client.rpc().list_nodes().send(),
        client.mint().get_recent().limit(5).send()
    ).await;
    
    println!("Status: {:?}", status?);
    println!("Nodes: {:?}", nodes?);
    println!("Mints: {:?}", mints?);
    
    // Custom request
    let custom_result: serde_json::Value = client.request()
        .method("GET")
        .path("/custom/endpoint")
        .query_param("foo", "bar")
        .send()
        .await?;
    
    println!("Custom result: {:?}", custom_result);
    
    Ok(())
}
```

## SDK Development

### Project Structure

```
sdk/
├── js/                  # JavaScript/TypeScript SDK
│   ├── src/
│   ├── tests/
│   ├── package.json
│   └── README.md
├── python/              # Python SDK
│   ├── soleco/
│   ├── tests/
│   ├── setup.py
│   └── README.md
├── rust/                # Rust SDK
│   ├── src/
│   ├── tests/
│   ├── Cargo.toml
│   └── README.md
└── README.md            # Main SDK documentation
```

### Building and Testing

Each SDK has its own build and test process. See the README in each SDK directory for specific instructions.

## Contributing

Please see the [Development Guide](../docs/development_guide.md) for information on how to contribute to the Soleco SDKs.

## License

Soleco SDKs are licensed under the [MIT License](../LICENSE).
