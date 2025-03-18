import asyncio
import logging
from app.utils.solana_rpc import SolanaClient
from app.config import HELIUS_RPC_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_helius")

async def test_helius_connection():
    """Test connection to Helius RPC endpoint"""
    logger.info(f"Testing connection to Helius endpoint: {HELIUS_RPC_URL}")
    
    try:
        # Create client
        client = SolanaClient(HELIUS_RPC_URL)
        logger.info("Created SolanaClient instance")
        
        # Connect
        await client.connect()
        logger.info("Connected to Helius endpoint")
        
        # Test with getHealth
        response = await client._make_rpc_call("getHealth")
        logger.info(f"Health check response: {response}")
        
        # Test with getLatestBlockhash
        response = await client._make_rpc_call("getLatestBlockhash")
        logger.info(f"Latest blockhash response: {response}")
        
        # Close connection
        await client.close()
        logger.info("Connection closed")
        
        return True
    except Exception as e:
        logger.error(f"Error testing Helius connection: {str(e)}")
        logger.exception(e)
        return False

if __name__ == "__main__":
    result = asyncio.run(test_helius_connection())
    if result:
        print("Helius connection test successful!")
    else:
        print("Helius connection test failed!")
