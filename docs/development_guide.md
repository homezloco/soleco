# Soleco Development Guide

## Introduction

This guide is intended for developers who want to contribute to the Soleco project. It covers the development environment setup, coding standards, testing procedures, and contribution workflow.

## Development Environment Setup

### Prerequisites

- **Python**: Version 3.9 or higher
- **Git**: For version control
- **Docker** (optional): For containerized development
- **Visual Studio Code** (recommended): With Python and Solana extensions

### Setting Up Your Development Environment

1. **Clone the Repository**

```bash
git clone https://github.com/yourusername/soleco.git
cd soleco
```

2. **Create a Virtual Environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Install Development Dependencies**

```bash
pip install -r requirements-dev.txt
```

4. **Set Up Pre-commit Hooks**

```bash
pre-commit install
```

5. **Configure Environment Variables**

Create a `.env.dev` file in the `backend` directory with your development settings:

```
# API Keys
HELIUS_API_KEY=your_helius_api_key_here

# RPC Configuration
POOL_SIZE=3
DEFAULT_TIMEOUT=30
DEFAULT_MAX_RETRIES=3
DEFAULT_RETRY_DELAY=1

# Logging
LOG_LEVEL=DEBUG

# Server
PORT=8000
HOST=0.0.0.0

# Development Settings
DEBUG=True
TESTING=False
```

## Project Structure

The Soleco project follows a modular structure:

```
soleco/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── docs/
│   │   ├── models/
│   │   ├── routers/
│   │   ├── tests/
│   │   └── utils/
│   ├── config/
│   └── logs/
├── docs/
│   ├── api_reference.md
│   ├── development_guide.md
│   ├── error_handling_system.md
│   ├── installation.md
│   ├── mint_extraction_system.md
│   ├── network_status_monitoring.md
│   ├── overview.md
│   └── solana_connection_pool.md
└── frontend/ (optional)
    ├── public/
    ├── src/
    └── tests/
```

### Key Directories

- **backend/app/api**: API endpoints and controllers
- **backend/app/core**: Core functionality and application setup
- **backend/app/models**: Data models and schemas
- **backend/app/routers**: FastAPI router definitions
- **backend/app/utils**: Utility functions and helpers
- **backend/app/tests**: Test suite
- **docs**: Project documentation

## Coding Standards

### Python Style Guide

Soleco follows the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide with some additional conventions:

1. **Line Length**: Maximum line length is 100 characters
2. **Indentation**: 4 spaces (no tabs)
3. **Imports**: Grouped in the following order:
   - Standard library imports
   - Related third-party imports
   - Local application/library specific imports
4. **Docstrings**: Follow [Google style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
5. **Type Hints**: Use type hints for function parameters and return values

### Code Formatting

We use the following tools for code formatting and linting:

- **Black**: For code formatting
- **isort**: For import sorting
- **flake8**: For linting
- **mypy**: For type checking

Run the formatting tools:

```bash
# Format code
black backend/

# Sort imports
isort backend/

# Lint code
flake8 backend/

# Type check
mypy backend/
```

## Testing

### Test Framework

Soleco uses pytest for testing. Tests are located in the `backend/app/tests` directory.

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest backend/app/tests/test_solana_rpc.py

# Run tests with coverage report
pytest --cov=backend/app
```

### Test Categories

1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test interactions between components
3. **API Tests**: Test API endpoints
4. **Performance Tests**: Test performance under load

### Writing Tests

Follow these guidelines when writing tests:

1. Use descriptive test names that explain what is being tested
2. Use fixtures for common setup and teardown
3. Use parametrized tests for testing multiple inputs
4. Mock external dependencies
5. Include both positive and negative test cases

Example test:

```python
import pytest
from app.utils.solana_rpc import safe_rpc_call_async

@pytest.mark.asyncio
async def test_safe_rpc_call_async_success(mock_client):
    # Arrange
    mock_client.call.return_value = {"result": "success"}
    
    # Act
    result = await safe_rpc_call_async(mock_client, "getBalance", ["address"])
    
    # Assert
    assert result == {"result": "success"}
    mock_client.call.assert_called_once_with("getBalance", ["address"])

@pytest.mark.asyncio
async def test_safe_rpc_call_async_retry_on_error(mock_client):
    # Arrange
    mock_client.call.side_effect = [
        Exception("Connection error"),
        {"result": "success"}
    ]
    
    # Act
    result = await safe_rpc_call_async(
        mock_client, "getBalance", ["address"], max_retries=1
    )
    
    # Assert
    assert result == {"result": "success"}
    assert mock_client.call.call_count == 2
```

## Debugging

### Logging

Use the built-in logging system for debugging:

```python
import logging

logger = logging.getLogger(__name__)

def process_data(data):
    logger.debug(f"Processing data: {data}")
    # Process data
    logger.info("Data processing complete")
```

### Debug Mode

Run the application in debug mode:

```bash
python run.py --debug
```

### Using pdb

You can use Python's built-in debugger:

```python
import pdb

def complex_function():
    # Some code
    pdb.set_trace()  # Debugger will stop here
    # More code
```

## Contribution Workflow

### Branching Strategy

We follow the [GitHub Flow](https://guides.github.com/introduction/flow/) branching strategy:

1. Create a branch from `main` for your feature or bugfix
2. Make your changes in the branch
3. Create a pull request to merge your branch into `main`
4. After review, merge your pull request

### Branch Naming Convention

Use the following format for branch names:

- Feature: `feature/short-description`
- Bugfix: `bugfix/short-description`
- Hotfix: `hotfix/short-description`
- Release: `release/version-number`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code changes that neither fix bugs nor add features
- `perf`: Performance improvements
- `test`: Adding or modifying tests
- `chore`: Changes to the build process or auxiliary tools

Example:

```
feat(connection-pool): add support for prioritized endpoints

- Add priority queue for endpoints
- Implement performance tracking
- Update documentation

Closes #123
```

### Pull Request Process

1. Ensure your code passes all tests and linting
2. Update documentation if necessary
3. Create a pull request with a clear description of the changes
4. Request review from at least one team member
5. Address any feedback from the review
6. Once approved, merge the pull request

## Performance Considerations

### Asynchronous Programming

Soleco makes heavy use of asynchronous programming with `asyncio`:

1. Use `async`/`await` for I/O-bound operations
2. Avoid blocking the event loop with CPU-intensive tasks
3. Use `asyncio.gather` for concurrent tasks
4. Be mindful of exception handling in asynchronous code

Example:

```python
import asyncio

async def fetch_data(client, address):
    return await client.get_balance(address)

async def fetch_multiple_balances(client, addresses):
    tasks = [fetch_data(client, address) for address in addresses]
    return await asyncio.gather(*tasks)
```

### Caching

Implement caching for expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_calculation(param1, param2):
    # Expensive calculation
    return result
```

### Connection Pooling

Use the connection pool for efficient resource management:

```python
async with connection_pool.get_client() as client:
    result = await client.get_balance(address)
```

## Deployment

### Staging Environment

Before deploying to production, test changes in the staging environment:

```bash
# Deploy to staging
./deploy.sh staging
```

### Production Deployment

Deploy to production after successful staging tests:

```bash
# Deploy to production
./deploy.sh production
```

### Monitoring

Monitor the application after deployment:

1. Check logs for errors
2. Monitor performance metrics
3. Set up alerts for critical issues

## Documentation

### Code Documentation

Document your code with docstrings:

```python
def calculate_priority(endpoint_stats):
    """
    Calculate the priority score for an endpoint based on its performance stats.
    
    Args:
        endpoint_stats (dict): Dictionary containing endpoint performance statistics
            with keys 'success_rate', 'avg_latency', and 'failure_count'.
    
    Returns:
        float: Priority score between 0 and 1, where higher is better.
    
    Raises:
        ValueError: If endpoint_stats is missing required keys.
    """
    # Implementation
```

### API Documentation

Update API documentation when adding or modifying endpoints:

1. Update the OpenAPI schema
2. Update the API reference documentation
3. Include example requests and responses

### Markdown Documentation

Update markdown documentation in the `docs` directory:

1. Keep documentation up-to-date with code changes
2. Use clear, concise language
3. Include examples and diagrams where appropriate

## Security Best Practices

### API Keys and Secrets

1. Never commit API keys or secrets to the repository
2. Use environment variables for sensitive information
3. Rotate API keys regularly

### Input Validation

Validate all user input:

```python
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    address: str
    
    @validator('address')
    def validate_address(cls, v):
        if not v.startswith('0x'):
            raise ValueError('Address must start with 0x')
        if len(v) != 42:
            raise ValueError('Address must be 42 characters long')
        return v
```

### Rate Limiting

Implement rate limiting for API endpoints:

```python
from fastapi import Depends, HTTPException
from app.utils.rate_limit import RateLimiter

rate_limiter = RateLimiter(requests_per_minute=60)

@app.get("/api/endpoint")
async def endpoint(rate_limit: bool = Depends(rate_limiter)):
    # Endpoint implementation
```

## Troubleshooting Common Issues

### Connection Issues

If you're experiencing connection issues with Solana RPC:

1. Check your internet connection
2. Verify your API keys
3. Try using a different RPC endpoint
4. Check the Solana network status

### Performance Issues

If you're experiencing performance issues:

1. Check for blocking operations in asynchronous code
2. Look for memory leaks
3. Optimize database queries
4. Implement caching for expensive operations

### Dependency Issues

If you're experiencing dependency issues:

1. Ensure your virtual environment is activated
2. Update your dependencies
3. Check for conflicting dependencies
4. Use a specific version of a dependency if needed

## Additional Resources

- [Solana Documentation](https://docs.solana.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
