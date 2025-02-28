# Pump.fun Trading Module

## Private Key Management

### Environment Variable Method
1. Add your Base58 private key to the `.env` file:
```
PUMP_FUN_PRIVATE_KEY=your_base58_private_key_here
```

### Programmatic Key Management

#### Encrypting a Private Key
```python
from app.pumptrade.wallet_management import WalletManager

# Encrypt and save a private key
encryption_key = WalletManager.save_encrypted_key(
    key='your_base58_private_key', 
    file_path='/path/to/encrypted_key.txt'
)

# Save the encryption key securely - you'll need it for decryption
```

#### Loading an Encrypted Key
```python
from app.pumptrade.wallet_management import WalletManager

# Load keypair from encrypted file
keypair = WalletManager.from_encrypted_file(
    file_path='/path/to/encrypted_key.txt', 
    encryption_key=your_saved_encryption_key
)
```

## Trading Endpoints

### Buy Token
- **Endpoint**: `POST /api/pumpfun/buy`
- **Parameters**:
  - `mint_address`: Token mint address (required)
  - `sol_amount`: SOL amount to spend (optional, default 0.01)
  - `slippage`: Slippage percentage (optional, default 5%)

### Sell Token
- **Endpoint**: `POST /api/pumpfun/sell`
- **Parameters**:
  - `mint_address`: Token mint address (required)
  - `percentage`: Percentage of tokens to sell (optional, default 100%)
  - `slippage`: Slippage percentage (optional, default 5%)

## Configuration Validation
Use the `/api/pumpfun/config` endpoint to verify your trading setup.

## Security Considerations
- Never commit private keys to version control
- Use environment variables or encrypted storage
- Protect your encryption keys
