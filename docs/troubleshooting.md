# Soleco Troubleshooting Guide

## Overview

This guide provides solutions for common issues you might encounter when using the Soleco platform. It covers installation problems, runtime errors, performance issues, and connectivity problems.

## Installation Issues

### Python Version Compatibility

**Issue**: Error messages related to Python version incompatibility.

**Solution**:
1. Verify your Python version:
   ```bash
   python --version
   ```
2. Ensure you're using Python 3.9 or higher.
3. If necessary, install a compatible Python version:
   ```bash
   # Windows
   # Download from https://www.python.org/downloads/
   
   # macOS
   brew install python@3.9
   
   # Linux
   sudo apt-get install python3.9
   ```

### Dependency Installation Failures

**Issue**: Errors when installing dependencies with pip.

**Solution**:
1. Update pip:
   ```bash
   python -m pip install --upgrade pip
   ```
2. Install dependencies with verbose output:
   ```bash
   pip install -r requirements.txt -v
   ```
3. For specific package errors, try installing them individually:
   ```bash
   pip install package-name
   ```
4. If you encounter C extension compilation errors, install the required development tools:
   ```bash
   # Windows
   # Install Visual C++ Build Tools
   
   # macOS
   xcode-select --install
   
   # Linux
   sudo apt-get install python3-dev build-essential
   ```

### Environment Variable Configuration

**Issue**: Application fails to start due to missing environment variables.

**Solution**:
1. Verify your `.env` file exists and contains all required variables.
2. Check for typos in variable names.
3. Ensure the `.env` file is in the correct location (root of the project).
4. Verify environment variables are loaded:
   ```bash
   # Windows
   set
   
   # macOS/Linux
   printenv
   ```

## Runtime Errors

### Solana RPC Connection Errors

**Issue**: Errors connecting to Solana RPC endpoints.

**Error Messages**:
- `ConnectionError: Connection refused`
- `TimeoutError: Connection timed out`
- `SolanaRPCError: Failed to connect to RPC endpoint`

**Solution**:
1. Verify your internet connection.
2. Check if the Helius API key is valid:
   ```bash
   curl -X POST https://mainnet.helius-rpc.com/ \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"getHealth","params":[],"api_key":"YOUR_HELIUS_API_KEY"}'
   ```
3. Try increasing the connection timeout:
   ```
   DEFAULT_TIMEOUT=60
   ```
4. Increase the number of retries:
   ```
   DEFAULT_MAX_RETRIES=5
   ```
5. Check if the Solana network is experiencing issues: [Solana Status](https://status.solana.com/)

### Rate Limiting Errors

**Issue**: Receiving rate limit errors from RPC endpoints.

**Error Messages**:
- `SolanaRPCError: 429 Too Many Requests`
- `RateLimitExceeded: Rate limit exceeded`

**Solution**:
1. Reduce the frequency of requests.
2. Implement exponential backoff in your application code:
   ```python
   import time
   import random
   
   def exponential_backoff(retry_count, base_delay=1):
       return base_delay * (2 ** retry_count) + random.uniform(0, 0.5)
   
   retry_count = 0
   max_retries = 5
   
   while retry_count < max_retries:
       try:
           # Make RPC request
           break
       except RateLimitExceeded:
           retry_count += 1
           if retry_count >= max_retries:
               raise
           delay = exponential_backoff(retry_count)
           time.sleep(delay)
   ```
3. Consider upgrading to a paid API plan with higher rate limits.
4. Use multiple API keys and rotate between them.

### Data Parsing Errors

**Issue**: Errors parsing data from Solana RPC responses.

**Error Messages**:
- `KeyError: 'result'`
- `TypeError: 'NoneType' object is not subscriptable`
- `JSONDecodeError: Expecting value`

**Solution**:
1. Add more robust error handling:
   ```python
   try:
       result = response.get('result')
       if result is None:
           # Handle missing result
           return None
       
       # Process result
       return process_result(result)
   except (KeyError, TypeError, json.JSONDecodeError) as e:
       logger.error(f"Error parsing response: {e}")
       return None
   ```
2. Log the full response for debugging:
   ```python
   logger.debug(f"Full response: {response}")
   ```
3. Update your code to handle changes in the RPC response format.

### Memory Errors

**Issue**: Application crashes with memory errors.

**Error Messages**:
- `MemoryError`
- `OSError: [Errno 12] Cannot allocate memory`

**Solution**:
1. Reduce batch sizes for processing:
   ```
   MINT_EXTRACTION_BATCH_SIZE=50
   ```
2. Implement pagination for large data sets.
3. Use generators instead of loading all data into memory:
   ```python
   def process_large_dataset(data_source):
       for chunk in data_source.iter_chunks(100):
           yield process_chunk(chunk)
   ```
4. Increase system memory or use a machine with more RAM.
5. Monitor memory usage with tools like `psutil`:
   ```python
   import psutil
   
   def log_memory_usage():
       process = psutil.Process()
       memory_info = process.memory_info()
       logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
   ```

## Performance Issues

### Slow Response Times

**Issue**: API endpoints respond slowly.

**Solution**:
1. Implement caching for frequently accessed data:
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_validator_info(validator_identity):
       # Fetch validator info
       return info
   ```
2. Optimize database queries:
   - Add indexes for frequently queried fields
   - Use batch processing instead of individual queries
3. Increase connection pool size:
   ```
   POOL_SIZE=10
   ```
4. Use asynchronous processing for non-blocking operations:
   ```python
   import asyncio
   
   async def process_multiple_items(items):
       tasks = [process_item(item) for item in items]
       return await asyncio.gather(*tasks)
   ```
5. Profile your code to identify bottlenecks:
   ```python
   import cProfile
   
   cProfile.run('function_to_profile()', 'profile_output')
   ```

### High CPU Usage

**Issue**: Application consumes excessive CPU resources.

**Solution**:
1. Identify CPU-intensive operations using profiling tools.
2. Optimize algorithms and data structures.
3. Use multiprocessing for CPU-bound tasks:
   ```python
   from multiprocessing import Pool
   
   def process_data_parallel(data_chunks):
       with Pool(processes=4) as pool:
           results = pool.map(process_chunk, data_chunks)
       return results
   ```
4. Reduce polling frequency for status checks.
5. Implement rate limiting for resource-intensive operations.

### Database Performance Issues

**Issue**: Slow database operations.

**Solution**:
1. Add indexes for frequently queried fields:
   ```sql
   CREATE INDEX idx_transaction_signature ON transactions(signature);
   ```
2. Optimize queries:
   - Use specific column names instead of SELECT *
   - Add LIMIT clauses to queries
   - Use JOINs efficiently
3. Implement connection pooling:
   ```
   DATABASE_POOL_SIZE=10
   ```
4. Consider using a more powerful database server.
5. Implement database sharding for large datasets.

## Connectivity Issues

### DNS Resolution Problems

**Issue**: Slow or failing DNS resolution for RPC nodes.

**Solution**:
1. Reduce DNS resolver timeout:
   ```
   DNS_RESOLVER_TIMEOUT=0.5
   DNS_RESOLVER_LIFETIME=1.0
   ```
2. Implement DNS caching:
   ```python
   dns_cache = {}
   
   def resolve_hostname(hostname):
       if hostname in dns_cache:
           if time.time() - dns_cache[hostname]['timestamp'] < 3600:
               return dns_cache[hostname]['addresses']
       
       addresses = dns.resolver.resolve(hostname, 'A')
       dns_cache[hostname] = {
           'addresses': [str(addr) for addr in addresses],
           'timestamp': time.time()
       }
       return dns_cache[hostname]['addresses']
   ```
3. Use IP addresses directly instead of hostnames when possible.
4. Configure a local DNS cache server.

### Firewall and Network Issues

**Issue**: Connections blocked by firewalls or network restrictions.

**Solution**:
1. Check if outbound connections to Solana RPC ports (typically 8899) are allowed.
2. Verify network proxy settings if applicable.
3. Test connectivity with curl:
   ```bash
   curl -X POST https://api.mainnet-beta.solana.com -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}'
   ```
4. If behind a corporate firewall, request exceptions for required endpoints.
5. Consider using a VPN or proxy service if necessary.

## Logging and Debugging

### Enabling Debug Logging

To get more detailed logs for troubleshooting:

1. Set the log level to DEBUG:
   ```
   LOG_LEVEL=DEBUG
   ```
2. Check the logs for detailed information:
   ```bash
   # View the last 100 lines of the log
   tail -n 100 logs/soleco.log
   
   # Follow the log in real-time
   tail -f logs/soleco.log
   
   # Search for specific error messages
   grep "ERROR" logs/soleco.log
   ```

### Debugging API Requests

To debug API requests:

1. Use tools like [Postman](https://www.postman.com/) or [curl](https://curl.se/) to make requests directly to the API.
2. Examine the request and response headers.
3. Add request IDs for tracing:
   ```python
   import uuid
   
   @app.middleware("http")
   async def add_request_id(request, call_next):
       request_id = str(uuid.uuid4())
       request.state.request_id = request_id
       response = await call_next(request)
       response.headers["X-Request-ID"] = request_id
       return response
   ```
4. Log request and response details:
   ```python
   @app.middleware("http")
   async def log_requests(request, call_next):
       logger.debug(f"Request: {request.method} {request.url}")
       start_time = time.time()
       response = await call_next(request)
       process_time = time.time() - start_time
       logger.debug(f"Response: {response.status_code} ({process_time:.4f}s)")
       return response
   ```

## Common Error Messages and Solutions

### "No healthy RPC endpoints available"

**Issue**: All RPC endpoints in the connection pool are unhealthy.

**Solution**:
1. Check your internet connection.
2. Verify your Helius API key is valid.
3. Add more RPC endpoints to the pool:
   ```python
   # In your configuration
   ADDITIONAL_RPC_ENDPOINTS = [
       "https://api.mainnet-beta.solana.com",
       "https://solana-api.projectserum.com"
   ]
   ```
4. Increase health check timeouts:
   ```
   HEALTH_CHECK_TIMEOUT=10
   ```
5. Restart the application to reset the connection pool.

### "Transaction simulation failed"

**Issue**: Solana transaction simulation failed.

**Solution**:
1. Check if the transaction is valid.
2. Ensure account balances are sufficient for the transaction.
3. Verify the transaction is properly signed.
4. Check for program errors in the simulation result:
   ```python
   try:
       result = await client.simulate_transaction(transaction)
       if "err" in result.get("result", {}):
           error = result["result"]["err"]
           logger.error(f"Transaction simulation error: {error}")
           # Handle specific error types
   except Exception as e:
       logger.error(f"Simulation failed: {e}")
   ```

### "Invalid Solana address"

**Issue**: The provided Solana address is invalid.

**Solution**:
1. Verify the address format (base58-encoded string).
2. Check for typos or truncation.
3. Implement address validation:
   ```python
   import base58
   
   def is_valid_solana_address(address):
       try:
           decoded = base58.b58decode(address)
           return len(decoded) == 32
       except Exception:
           return False
   ```

### "Error parsing account data"

**Issue**: Failed to parse account data from Solana.

**Solution**:
1. Check if the account exists.
2. Verify the account data format matches your expectations.
3. Implement more robust parsing logic:
   ```python
   try:
       account_info = await client.get_account_info(address)
       if "result" not in account_info or account_info["result"] is None:
           logger.error(f"Account not found: {address}")
           return None
       
       data = account_info["result"]["value"]["data"]
       if not data or len(data) < 2:
           logger.error(f"Invalid account data format: {data}")
           return None
       
       # Parse data based on expected format
       return parse_account_data(data)
   except Exception as e:
       logger.error(f"Error parsing account data: {e}")
       return None
   ```

## Advanced Troubleshooting

### Using Diagnostic Endpoints

Soleco provides diagnostic endpoints for troubleshooting:

```
GET /api/soleco/diagnostics
```

This endpoint returns information about:
- Application version
- System information
- Connection pool status
- RPC endpoint health
- Memory usage

### Monitoring Tools

Consider using monitoring tools to track application health:

1. **Prometheus and Grafana** for metrics collection and visualization
2. **ELK Stack** (Elasticsearch, Logstash, Kibana) for log analysis
3. **Sentry** for error tracking
4. **New Relic** or **Datadog** for application performance monitoring

### Generating Support Information

To generate a support bundle for troubleshooting:

```bash
python scripts/generate_support_bundle.py
```

This creates a ZIP file containing:
- Application logs
- Configuration (with sensitive information redacted)
- System information
- Diagnostic reports

## Getting Help

If you're still experiencing issues after trying the solutions in this guide:

1. Check the [GitHub Issues](https://github.com/yourusername/soleco/issues) for similar problems and solutions.
2. Search the [Solana Developer Forum](https://forums.solana.com/) for related discussions.
3. Join the [Solana Discord](https://discord.com/invite/solana) for community support.
4. Contact the Soleco support team with detailed information about your issue:
   - Error messages and stack traces
   - Steps to reproduce the issue
   - Environment information (OS, Python version, etc.)
   - Relevant configuration settings
