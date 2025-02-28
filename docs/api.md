# Soleco API Documentation

## Technical Overview

### Architecture
The Soleco API is built on a modular architecture with the following key components:

1. **Request Handlers**
   - FastAPI routers
   - Request validation
   - Response formatting
   - Error handling

2. **Core Services**
   - Solana RPC client
   - Connection pool management
   - Rate limiting
   - Caching layer

3. **Analytics Engine**
   - Transaction processing
   - Statistical analysis
   - Data aggregation
   - Real-time monitoring

4. **Enhanced Error Handling**
   - Comprehensive error classification
   - Coroutine handling with timeouts
   - Recursive response processing
   - Solana object serialization
   - Graceful degradation with fallbacks

## API Reference

### Mint Analytics API

#### Get New Mints
```python
GET /solana/analytics/mints/new
```

Retrieves information about new mint activities in recent blocks.

**Parameters:**
```python
{
    "blocks": int = Query(
        default=1,
        description="Number of recent blocks to analyze",
        ge=1,
        le=100
    )
}
```

**Response:**
```python
{
    "mint_addresses": List[str],
    "transaction_count": int,
    "block_range": {
        "start": int,
        "end": int
    },
    "statistics": {
        "total_transactions": int,
        "unique_mints": int,
        "processing_time": float
    }
}
```

#### Analyze Recent Mints
```python
GET /solana/analytics/mints/recent
```

Provides detailed analysis of recent mint activity.

**Parameters:**
```python
{
    "limit": int = Query(
        default=10,
        description="Number of blocks to analyze",
        ge=1,
        le=100
    ),
    "include_transactions": bool = Query(
        default=False,
        description="Include detailed transaction info"
    )
}
```

**Response:**
```python
{
    "mint_addresses": List[str],
    "statistics": {
        "total_transactions": int,
        "unique_mints": int,
        "time_range": str,
        "transaction_types": Dict[str, int]
    },
    "transactions": Optional[List[Dict]]  # If include_transactions=True
}
```

#### Analyze Mint Address
```python
GET /solana/analytics/mints/{mint_address}
```

Analyzes activity for a specific mint address.

**Parameters:**
```python
{
    "mint_address": str = Path(
        ...,
        description="Mint address to analyze"
    ),
    "limit": int = Query(
        default=100,
        description="Number of transactions to analyze",
        ge=1,
        le=1000
    )
}
```

**Response:**
```python
{
    "mint_info": {
        "address": str,
        "total_supply": int,
        "decimals": int,
        "authority": str,
        "freeze_authority": Optional[str]
    },
    "transactions": List[Dict],
    "statistics": {
        "holder_count": int,
        "transaction_count": int,
        "first_activity": str,
        "last_activity": str
    }
}
```

## Error Handling

### Error Response Format
```python
{
    "error": {
        "code": str,
        "message": str,
        "details": Optional[Dict]
    }
}
```

### Error Types
1. **ValidationError**
   - Invalid parameters
   - Missing required fields
   - Type mismatches

2. **RPCError**
   - Node connection issues
   - Invalid responses
   - Timeout errors

3. **RateLimitError**
   - Too many requests
   - Burst limit exceeded
   - Connection pool exhausted

4. **ProcessingError**
   - Data processing failures
   - Invalid blockchain data
   - Parsing errors

## Rate Limiting

### Configuration
```python
RATE_LIMIT_CONFIG = {
    "default": {
        "rate": 40,  # requests per minute
        "burst": 100,  # requests per second
        "timeframe": 60  # seconds
    },
    "premium": {
        "rate": 100,
        "burst": 200,
        "timeframe": 60
    }
}
```

### Headers
```python
{
    "X-RateLimit-Limit": str,
    "X-RateLimit-Remaining": str,
    "X-RateLimit-Reset": str
}
```

## WebSocket API

### Connection
```python
ws_url = "ws://localhost:8000/ws/mints"
```

### Events
```python
# New mint event
{
    "type": "new_mint",
    "data": {
        "mint_address": str,
        "timestamp": int,
        "transaction_signature": str
    }
}

# Mint update event
{
    "type": "mint_update",
    "data": {
        "mint_address": str,
        "update_type": str,
        "changes": Dict
    }
}

# Error event
{
    "type": "error",
    "data": {
        "code": str,
        "message": str
    }
}
```

## Development Guidelines

### Request Handling
```python
@router.get("/mints/{mint_address}")
async def get_mint_info(
    mint_address: str,
    limit: int = Query(default=100, ge=1, le=1000)
) -> Dict[str, Any]:
    try:
        # Validate mint address
        if not is_valid_mint_address(mint_address):
            raise ValidationError("Invalid mint address")

        # Get query handler
        query_handler = await get_query_handler()
        
        # Process request
        result = await query_handler.get_mint_info(
            mint_address=mint_address,
            limit=limit
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing mint info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
```

### Response Processing
```python
class MintResponseHandler:
    def process_result(self, result: Any) -> Dict[str, Any]:
        try:
            # Validate result
            if not self._is_valid_result(result):
                raise ValidationError("Invalid result format")
                
            # Process data
            processed_data = self._process_mint_data(result)
            
            # Format response
            return {
                "success": True,
                "data": processed_data,
                "timestamp": int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Error processing result: {str(e)}")
            raise ProcessingError("Failed to process result")
```

## Testing

### Unit Tests
```python
def test_mint_analysis():
    # Setup
    handler = MintResponseHandler()
    test_data = load_test_data()
    
    # Execute
    result = handler.process_result(test_data)
    
    # Assert
    assert "mint_addresses" in result
    assert "statistics" in result
    assert result["success"] is True
```

### Integration Tests
```python
async def test_mint_endpoint():
    # Setup
    client = TestClient(app)
    mint_address = "test_mint_address"
    
    # Execute
    response = await client.get(f"/mints/{mint_address}")
    
    # Assert
    assert response.status_code == 200
    assert "mint_info" in response.json()
```

## Security

### Request Validation
```python
def validate_request(request: Dict[str, Any]) -> bool:
    required_fields = ["api_key", "timestamp", "signature"]
    
    # Check required fields
    if not all(field in request for field in required_fields):
        return False
        
    # Validate timestamp
    if abs(time.time() - request["timestamp"]) > MAX_TIMESTAMP_DIFF:
        return False
        
    # Validate signature
    return verify_signature(request)
```

### API Key Validation
```python
async def validate_api_key(api_key: str) -> bool:
    # Check cache first
    if cached_result := await cache.get(f"api_key:{api_key}"):
        return cached_result
        
    # Validate with database
    is_valid = await db.validate_api_key(api_key)
    
    # Cache result
    await cache.set(f"api_key:{api_key}", is_valid, expire=3600)
    
    return is_valid
```

## Enhanced RPC Error Handling

The API implements sophisticated error handling for Solana RPC interactions:

1. **Automatic Retries**: Automatically retries failed RPC calls with exponential backoff
2. **Fallback Mechanisms**: Falls back to alternative RPC nodes when primary node fails
3. **Coroutine Management**: Properly handles asynchronous operations with timeouts
4. **Response Validation**: Validates RPC responses before processing
5. **Graceful Degradation**: Returns partial data when complete data is unavailable

Example implementation:

```python
@app.get("/solana/analytics/mints/{mint_address}")
async def get_mint_info(
    mint_address: str = Path(description="The mint address to get information for")
) -> Dict[str, Any]:
    try:
        # Validate mint address
        if not is_valid_mint_address(mint_address):
            raise ValidationError("Invalid mint address")
            
        # Get mint info with enhanced error handling
        mint_info = await safe_rpc_call_async(
            lambda: solana_client.get_account_info(mint_address),
            method_name="get_account_info",
            timeout=10.0
        )
        
        # Process and return the result
        return {
            "status": "success",
            "data": process_mint_info(mint_info),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except ValidationError as e:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": str(e),
                "error_code": "INVALID_REQUEST",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except RateLimitError as e:
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "error": str(e),
                "error_code": "RATE_LIMITED",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except NodeUnhealthyError as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(e),
                "error_code": "NODE_UNHEALTHY",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=504,
            content={
                "status": "error",
                "error": "Request timed out",
                "error_code": "TIMEOUT",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except RPCError as e:
        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "error": str(e),
                "error_code": "RPC_ERROR",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except Exception as e:
        logger.exception(f"Unexpected error in get_mint_info: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
```

## Client Usage

### Python Client

```python
import requests
import json

def get_mint_info(mint_address):
    response = requests.get(f"https://api.soleco.io/solana/analytics/mints/{mint_address}")
    if response.status_code == 200:
        return response.json()["data"]
    else:
        error_data = response.json()
        print(f"Error: {error_data['error']} (Code: {error_data['error_code']})")
        return None
```

### JavaScript Client

```javascript
async function getMintInfo(mintAddress) {
    try {
        const response = await fetch(`https://api.soleco.io/solana/analytics/mints/${mintAddress}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            return data.data;
        } else {
            console.error(`Error: ${data.error} (Code: ${data.error_code})`);
            return null;
        }
    } catch (error) {
        console.error('Failed to fetch mint info:', error);
        return null;
    }
}
