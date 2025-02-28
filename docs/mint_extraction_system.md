# Solana Mint Extraction System

## Overview

The Solana Mint Extraction System is a specialized component of the Soleco platform that identifies, tracks, and analyzes mint addresses on the Solana blockchain. It provides comprehensive information about all mint addresses, newly created mints, and special "pump" tokens.

## Key Features

### 1. Comprehensive Mint Tracking

- **All Mint Addresses**: Tracks all mint addresses found in transactions, including from token balances
- **New Mint Detection**: Identifies newly created mint addresses
- **Pump Token Tracking**: Specifically tracks addresses ending with 'pump'

### 2. Transaction Analysis

- **Deep Transaction Parsing**: Analyzes transaction instructions to extract mint addresses
- **Token Balance Analysis**: Extracts mint addresses from token balances
- **Program ID Recognition**: Identifies token program interactions (both standard and Token2022)

### 3. Analytics and Reporting

- **Statistical Summaries**: Provides summary statistics about mint activity
- **Historical Tracking**: Maintains historical data about mint addresses
- **Detailed Transaction Information**: Links mint addresses to their originating transactions

### 4. Pump Token Identification

- **Case-Insensitive Detection**: Uses case-insensitive checks for 'pump' suffix
- **Dedicated Tracking**: Stores pump tokens in a dedicated set
- **Detailed Logging**: Provides detailed logging for pump token identification

## Usage

### API Endpoints

The Mint Extraction System is exposed through several API endpoints:

1. **`/api/soleco/solana/mints/extract`**
   - Extracts mint addresses from a specific block
   - Returns all mint addresses, new mint addresses, and pump tokens

2. **`/api/soleco/solana/mints/new/recent`**
   - Returns recently created mint addresses
   - Includes pump tokens in a separate array

### Example Response

```json
{
  "block_number": 123456789,
  "mint_addresses": [
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "So11111111111111111111111111111111111111112"
  ],
  "new_mint_addresses": [
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
  ],
  "pump_token_addresses": [
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
  ],
  "stats": {
    "total_mint_addresses": 3,
    "total_new_mint_addresses": 1,
    "total_pump_tokens": 1
  },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

## Implementation Details

### Mint Detection Process

1. **Transaction Retrieval**: Retrieves transactions from a specific block
2. **Instruction Parsing**: Parses transaction instructions to identify token program calls
3. **Mint Address Extraction**: Extracts mint addresses from token program instructions
4. **Token Balance Analysis**: Extracts mint addresses from token balances
5. **New Mint Identification**: Determines if a mint is newly created based on instruction patterns
6. **Pump Token Detection**: Checks if addresses end with 'pump' (case-insensitive)

### MintExtractor Class

The core of the system is the `MintExtractor` class, which:

- Tracks three types of mint addresses:
  - `mint_addresses`: All mint addresses found in transactions
  - `new_mint_addresses`: Only newly created mint addresses
  - `pump_tokens`: Addresses ending with 'pump'
- Provides methods for processing transactions and extracting mint addresses
- Implements logic to determine if a mint is new
- Provides results with comprehensive statistics

### Token Program Support

The system supports both standard Token Program and Token2022 Program:

- Standard Token Program: `TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA`
- Token2022 Program: `TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`

### Pump Token Identification

Pump tokens are identified using a case-insensitive check for addresses ending with 'pump':

```python
if address.lower().endswith('pump'):
    self.pump_tokens.add(address)
```

## Performance Considerations

- **Efficient Data Structures**: Uses sets for fast membership testing and deduplication
- **Optimized Transaction Processing**: Processes transactions efficiently to minimize resource usage
- **Selective Analysis**: Only analyzes relevant instructions to improve performance
- **Batch Processing**: Supports processing multiple blocks in batch for better throughput

## Logging and Debugging

- **Detailed Logging**: Comprehensive logging for all mint extraction activities
- **Debug Messages**: Specific debug messages for pump token identification
- **Statistical Tracking**: Tracks and logs summary statistics for each processed block
- **Error Handling**: Robust error handling with detailed error messages

## Testing

The Mint Extraction System includes comprehensive testing:

- **Unit Tests**: Tests for individual components like mint address extraction
- **Integration Tests**: Tests for the complete extraction process
- **Edge Case Tests**: Tests for unusual transaction patterns
- **Performance Tests**: Tests to ensure optimal performance under load
