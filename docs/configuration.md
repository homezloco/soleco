# Soleco Configuration Guide

## Overview

This document provides a comprehensive guide to configuring the Soleco platform. Soleco offers various configuration options to customize its behavior, performance, and functionality to suit your specific needs.

## Configuration Methods

Soleco supports multiple configuration methods, listed in order of precedence:

1. **Environment Variables**: Highest precedence, overrides all other settings
2. **Configuration Files**: `.env` files for environment-specific settings
3. **Default Values**: Built-in defaults used when no configuration is provided

## Environment Variables

### Core Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PORT` | Port for the API server | `8000` | `8080` |
| `HOST` | Host for the API server | `0.0.0.0` | `127.0.0.1` |
| `DEBUG` | Enable debug mode | `False` | `True` |
| `TESTING` | Enable testing mode | `False` | `True` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `ENVIRONMENT` | Environment (development, staging, production) | `development` | `production` |

### Solana RPC Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `HELIUS_API_KEY` | API key for Helius RPC endpoint | None | `your_api_key_here` |
| `POOL_SIZE` | Size of the connection pool | `5` | `10` |
| `DEFAULT_TIMEOUT` | Default timeout for RPC requests (seconds) | `30` | `60` |
| `DEFAULT_MAX_RETRIES` | Default maximum retries for RPC requests | `3` | `5` |
| `DEFAULT_RETRY_DELAY` | Default delay between retries (seconds) | `1.0` | `2.0` |
| `RATE_LIMIT_REQUESTS` | Maximum requests per minute | `100` | `200` |
| `RATE_LIMIT_PERIOD` | Rate limit period (seconds) | `60` | `120` |

### RPC Node Extractor Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DNS_RESOLVER_TIMEOUT` | Timeout for DNS resolution (seconds) | `0.5` | `1.0` |
| `DNS_RESOLVER_LIFETIME` | Lifetime of DNS resolver (seconds) | `1.0` | `2.0` |
| `MAX_CONCURRENT_DNS_LOOKUPS` | Maximum concurrent DNS lookups | `10` | `20` |
| `URL_CACHE_TTL` | Time-to-live for URL cache (seconds) | `3600` | `7200` |
| `MAX_IP_CONVERSIONS` | Maximum IP addresses to convert | `30` | `50` |

### Mint Extraction Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MINT_CACHE_SIZE` | Size of mint address cache | `10000` | `20000` |
| `PUMP_TOKEN_THRESHOLD` | Threshold for pump token detection | `1000` | `2000` |
| `MINT_EXTRACTION_BATCH_SIZE` | Batch size for mint extraction | `100` | `200` |
| `MINT_EXTRACTION_CONCURRENCY` | Concurrency level for mint extraction | `5` | `10` |

### Network Status Monitoring Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `STATUS_CACHE_TTL` | Time-to-live for status cache (seconds) | `60` | `120` |
| `VALIDATOR_SAMPLE_SIZE` | Sample size for validator monitoring | `100` | `200` |
| `PERFORMANCE_METRICS_WINDOW` | Window for performance metrics (slots) | `1000` | `2000` |
| `HEALTH_CHECK_INTERVAL` | Interval for health checks (seconds) | `300` | `600` |

### Database Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DATABASE_URL` | URL for the database | `sqlite:///./soleco.db` | `postgresql://user:pass@localhost/soleco` |
| `DATABASE_POOL_SIZE` | Connection pool size for the database | `5` | `10` |
| `DATABASE_MAX_OVERFLOW` | Maximum overflow connections | `10` | `20` |
| `DATABASE_POOL_RECYCLE` | Connection recycle time (seconds) | `3600` | `7200` |

### Caching Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `CACHE_TYPE` | Type of cache to use | `memory` | `redis` |
| `CACHE_REDIS_URL` | URL for Redis cache | None | `redis://localhost:6379/0` |
| `CACHE_DEFAULT_TIMEOUT` | Default cache timeout (seconds) | `300` | `600` |
| `CACHE_KEY_PREFIX` | Prefix for cache keys | `soleco:` | `myapp:soleco:` |

### Security Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SECRET_KEY` | Secret key for security features | Random | `your-secret-key` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` | `https://example.com,https://api.example.com` |
| `CORS_METHODS` | Allowed CORS methods | `GET,POST,PUT,DELETE` | `GET,POST` |
| `CORS_HEADERS` | Allowed CORS headers | `*` | `Content-Type,Authorization` |
| `API_KEY_HEADER` | Header name for API key | `X-API-Key` | `Authorization` |

## Configuration Files

### .env File

Create a `.env` file in the root directory of the project to set environment variables:

```
# Server Configuration
PORT=8000
HOST=0.0.0.0
DEBUG=True
LOG_LEVEL=DEBUG

# Solana RPC Configuration
HELIUS_API_KEY=your_helius_api_key_here
POOL_SIZE=5
DEFAULT_TIMEOUT=30
DEFAULT_MAX_RETRIES=3
DEFAULT_RETRY_DELAY=1.0

# RPC Node Extractor Configuration
DNS_RESOLVER_TIMEOUT=0.5
DNS_RESOLVER_LIFETIME=1.0
MAX_CONCURRENT_DNS_LOOKUPS=10
URL_CACHE_TTL=3600
MAX_IP_CONVERSIONS=30

# Mint Extraction Configuration
MINT_CACHE_SIZE=10000
PUMP_TOKEN_THRESHOLD=1000
MINT_EXTRACTION_BATCH_SIZE=100
MINT_EXTRACTION_CONCURRENCY=5

# Network Status Monitoring Configuration
STATUS_CACHE_TTL=60
VALIDATOR_SAMPLE_SIZE=100
PERFORMANCE_METRICS_WINDOW=1000
HEALTH_CHECK_INTERVAL=300

# Database Configuration
DATABASE_URL=sqlite:///./soleco.db
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_RECYCLE=3600

# Caching Configuration
CACHE_TYPE=memory
CACHE_DEFAULT_TIMEOUT=300
CACHE_KEY_PREFIX=soleco:

# Security Configuration
SECRET_KEY=your-secret-key
CORS_ORIGINS=*
CORS_METHODS=GET,POST,PUT,DELETE
CORS_HEADERS=*
API_KEY_HEADER=X-API-Key
```

### Environment-Specific Configuration

You can create environment-specific configuration files:

- `.env.development`: Development environment configuration
- `.env.staging`: Staging environment configuration
- `.env.production`: Production environment configuration

To use a specific environment configuration:

```bash
# Linux/macOS
export ENVIRONMENT=production
python run.py

# Windows
set ENVIRONMENT=production
python run.py
```

## Programmatic Configuration

You can also configure Soleco programmatically:

```python
from app.core.config import settings

# Override settings
settings.POOL_SIZE = 10
settings.DEFAULT_TIMEOUT = 60
```

## Configuration Validation

Soleco validates configuration values at startup. If any configuration values are invalid, the application will log an error and use default values or exit if the configuration is critical.

## Advanced Configuration

### Custom RPC Endpoints

You can configure custom RPC endpoints:

```python
# config.py
CUSTOM_RPC_ENDPOINTS = [
    "https://my-custom-rpc-endpoint.com",
    "https://another-custom-endpoint.com"
]
```

### Custom Error Handlers

You can configure custom error handlers:

```python
# config.py
from app.utils.errors import default_error_handler

ERROR_HANDLERS = {
    "SolanaRPCError": default_error_handler,
    "ConnectionError": custom_connection_error_handler
}
```

### Custom Logging Configuration

You can configure custom logging:

```python
# logging_config.py
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filename": "logs/soleco.log",
            "maxBytes": 10485760,
            "backupCount": 5
        }
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": True
        }
    }
}
```

## Performance Tuning

### Connection Pool Tuning

Adjust the connection pool size based on your workload:

- For low-traffic applications: `POOL_SIZE=3`
- For medium-traffic applications: `POOL_SIZE=5`
- For high-traffic applications: `POOL_SIZE=10` or higher

### Timeout and Retry Tuning

Adjust timeouts and retries based on your network conditions:

- For stable networks: `DEFAULT_TIMEOUT=30`, `DEFAULT_MAX_RETRIES=3`
- For unstable networks: `DEFAULT_TIMEOUT=60`, `DEFAULT_MAX_RETRIES=5`

### Caching Tuning

Adjust caching parameters based on your data freshness requirements:

- For real-time data: `STATUS_CACHE_TTL=30`
- For near-real-time data: `STATUS_CACHE_TTL=60`
- For less time-sensitive data: `STATUS_CACHE_TTL=300`

## Environment-Specific Recommendations

### Development Environment

```
DEBUG=True
LOG_LEVEL=DEBUG
POOL_SIZE=3
DEFAULT_TIMEOUT=30
DEFAULT_MAX_RETRIES=3
```

### Staging Environment

```
DEBUG=False
LOG_LEVEL=INFO
POOL_SIZE=5
DEFAULT_TIMEOUT=30
DEFAULT_MAX_RETRIES=3
```

### Production Environment

```
DEBUG=False
LOG_LEVEL=WARNING
POOL_SIZE=10
DEFAULT_TIMEOUT=30
DEFAULT_MAX_RETRIES=3
```

## Troubleshooting Configuration Issues

### Common Issues

1. **Missing API Keys**: Ensure `HELIUS_API_KEY` is set correctly
2. **Connection Pool Exhaustion**: Increase `POOL_SIZE` if you see connection errors
3. **Timeout Errors**: Increase `DEFAULT_TIMEOUT` if you experience timeout errors
4. **Rate Limiting**: Adjust `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_PERIOD` if you're being rate limited

### Debugging Configuration

To debug configuration issues, set `DEBUG=True` and `LOG_LEVEL=DEBUG` to get more detailed logging.

### Configuration Validation

Soleco validates configuration at startup. Check the logs for configuration validation errors:

```
ERROR - app.core.config - Invalid value for POOL_SIZE: expected integer, got string
```

## Security Considerations

### API Key Security

- Store API keys in environment variables, not in code
- Use different API keys for different environments
- Rotate API keys regularly

### CORS Configuration

- Restrict `CORS_ORIGINS` to only the domains that need access
- Limit `CORS_METHODS` to only the methods you need
- Limit `CORS_HEADERS` to only the headers you need

### Rate Limiting

- Set appropriate rate limits to prevent abuse
- Monitor rate limit usage and adjust as needed

## Conclusion

Proper configuration is essential for optimal performance and security of the Soleco platform. Use this guide to configure Soleco according to your specific requirements and environment.

For further assistance, refer to the [Troubleshooting Guide](troubleshooting.md) or contact the Soleco support team.
