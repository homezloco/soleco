# Soleco Logging System

## Overview

The Soleco Logging System is a comprehensive component that provides detailed operational tracking, error reporting, and performance monitoring throughout the platform. It implements standardized logging practices to ensure consistent, structured, and informative log entries that facilitate debugging, monitoring, and analysis.

## Key Features

### 1. Standardized Logging Configuration

- **Consistent Format**: Standardized log format with timestamp, level, and message
- **Hierarchical Loggers**: Organized logger hierarchy based on module structure
- **Configurable Levels**: Adjustable logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **File and Console Output**: Logs to both files and console for comprehensive visibility

### 2. Specialized Log Categories

- **Solana RPC Logs**: Detailed logging of RPC requests, responses, and errors
- **Rate Limiting Logs**: Tracking of rate limit events and backoff strategies
- **Transaction Processing Logs**: Status updates for transaction processing
- **Batch Processing Statistics**: Summary statistics for batch operations
- **Connection Pool Logs**: Status updates for connection pool management

### 3. Statistical Logging

- **Query Tracking**: Counts of total queries, errors, and skipped queries
- **Error Type Tracking**: Categorization and counting of different error types
- **Performance Metrics**: Timing information for various operations
- **Resource Usage**: Monitoring of resource consumption

### 4. Structured Error Logging

- **Detailed Error Context**: Comprehensive context for error conditions
- **Stack Traces**: Full stack traces for unexpected errors
- **Error Classification**: Categorization of errors by type and severity
- **Recovery Actions**: Documentation of recovery attempts and outcomes

## Implementation Details

### Logging Configuration

The logging system is configured in `logging_config.py`:

```python
import logging
import os
from logging.handlers import RotatingFileHandler

def configure_logging(app_name="soleco", log_level=logging.DEBUG):
    """
    Configure the logging system.
    
    Args:
        app_name: Name of the application (used for log file names)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler
    file_handler = RotatingFileHandler(
        f"logs/{app_name}.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Create specialized loggers
    create_specialized_loggers(formatter)
    
    return logger
```

### Specialized Loggers

The system creates specialized loggers for different components:

```python
def create_specialized_loggers(formatter):
    """
    Create specialized loggers for different components.
    
    Args:
        formatter: Logging formatter to use
    """
    # RPC logger
    rpc_logger = logging.getLogger("soleco.rpc")
    rpc_file_handler = RotatingFileHandler(
        "logs/rpc.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    rpc_file_handler.setFormatter(formatter)
    rpc_logger.addHandler(rpc_file_handler)
    
    # Analytics logger
    analytics_logger = logging.getLogger("soleco.analytics")
    analytics_file_handler = RotatingFileHandler(
        "logs/analytics.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    analytics_file_handler.setFormatter(formatter)
    analytics_logger.addHandler(analytics_file_handler)
    
    # Error logger
    error_logger = logging.getLogger("soleco.error")
    error_file_handler = RotatingFileHandler(
        "logs/error.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    error_file_handler.setFormatter(formatter)
    error_logger.addHandler(error_file_handler)
```

### Log Usage Examples

#### Basic Logging

```python
import logging

logger = logging.getLogger(__name__)

def process_transaction(transaction):
    logger.debug(f"Processing transaction: {transaction.signature}")
    try:
        # Process transaction
        result = do_process(transaction)
        logger.info(f"Successfully processed transaction: {transaction.signature}")
        return result
    except Exception as e:
        logger.error(f"Error processing transaction {transaction.signature}: {str(e)}", exc_info=True)
        raise
```

#### Statistical Logging

```python
def log_batch_statistics(batch_results):
    """Log statistics for a batch of processed items."""
    total = len(batch_results)
    successful = sum(1 for r in batch_results if r.get("success"))
    failed = total - successful
    
    logger.info(
        f"Batch processing completed: {total} total, {successful} successful, {failed} failed"
    )
    
    if failed > 0:
        error_types = {}
        for result in batch_results:
            if not result.get("success"):
                error_type = result.get("error_type", "unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        logger.warning(f"Error breakdown: {error_types}")
```

#### Performance Logging

```python
import time

def log_performance(func):
    """Decorator to log function execution time."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        logger.debug(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper

@log_performance
def process_block(block_number):
    # Process block
    pass
```

## Log File Structure

The logging system creates several log files:

- **soleco.log**: Main application log with all messages
- **rpc.log**: Specialized log for RPC-related operations
- **analytics.log**: Specialized log for analytics operations
- **error.log**: Specialized log for error conditions

Each log file is configured with rotation to prevent excessive disk usage.

## Best Practices

### 1. Log Level Selection

- **DEBUG**: Detailed information for debugging purposes
- **INFO**: General operational information
- **WARNING**: Potential issues that don't prevent operation
- **ERROR**: Errors that prevent specific operations
- **CRITICAL**: Critical errors that prevent application operation

### 2. Contextual Information

- Include relevant context in log messages (e.g., transaction IDs, block numbers)
- Use structured logging where appropriate
- Include timing information for performance-sensitive operations

### 3. Error Logging

- Log full stack traces for unexpected errors
- Include error context to aid debugging
- Categorize errors by type and severity

### 4. Performance Considerations

- Avoid excessive logging in performance-critical paths
- Use appropriate log levels to control verbosity
- Consider using asynchronous logging for high-volume operations
