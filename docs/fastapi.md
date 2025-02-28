# Soleco FastAPI Documentation

## Overview
Soleco's backend is built using FastAPI, providing high-performance REST APIs for Solana blockchain analytics. This document outlines the API endpoints, their functionality, and usage patterns.

## Base URL
```
http://localhost:8000/solana/analytics
```

## Endpoints

### Mint Analytics

#### 1. Analyze New Mints
```
GET /mints/new
```
Analyzes mint activities in recent blocks.

**Query Parameters:**
- `blocks` (integer, default: 1): Number of recent blocks to analyze

**Response:**
```json
{
    "mint_addresses": [...],
    "transaction_count": integer,
    "block_range": {
        "start": integer,
        "end": integer
    }
}
```

#### 2. Analyze Recent Mints
```
GET /mints/recent
```
Provides detailed analysis of recent mint activity.

**Query Parameters:**
- `limit` (integer, default: 10, max: 100): Number of blocks to analyze
- `include_transactions` (boolean, default: false): Include detailed transaction info

**Response:**
```json
{
    "mint_addresses": [...],
    "statistics": {
        "total_transactions": integer,
        "unique_mints": integer,
        "time_range": string
    }
}
```

#### 3. Analyze Specific Mint
```
GET /mints/{mint_address}
```
Analyzes activity for a specific mint address.

**Path Parameters:**
- `mint_address` (string): The Solana mint address to analyze

**Query Parameters:**
- `limit` (integer, default: 100, max: 1000): Number of transactions to analyze

## Error Handling

### Error Response Format
```json
{
    "error": {
        "code": string,
        "message": string,
        "details": object
    }
}
```

### Common Error Codes
- `400`: Bad Request
- `404`: Resource Not Found
- `429`: Rate Limit Exceeded
- `503`: Service Temporarily Unavailable

## Rate Limiting
- Default rate: 40 requests per minute per IP
- Burst limit: 100 requests per second
- Headers included: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Best Practices
1. Implement proper error handling
2. Use pagination for large datasets
3. Cache responses when appropriate
4. Monitor rate limits
5. Use appropriate timeout values

## WebSocket Support
Real-time updates available through WebSocket connections:
```
ws://localhost:8000/ws/mints
```

### WebSocket Events
- `new_mint`: New mint detected
- `mint_update`: Updates to existing mint
- `error`: Error notifications

## Security
- CORS enabled for specified origins
- API key required for sensitive endpoints
- Rate limiting per API key
- Request validation and sanitization

## Monitoring
- Prometheus metrics available at `/metrics`
- Health check endpoint at `/health`
- Detailed logging with correlation IDs

## Development Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export SOLANA_RPC_URL=your_rpc_url
export API_KEY=your_api_key
```

3. Run development server:
```bash
uvicorn app.main:app --reload
```

## Testing
Run tests with:
```bash
pytest tests/
```

## OpenAPI Documentation
Interactive API documentation available at:
```
http://localhost:8000/docs
http://localhost:8000/redoc
```
