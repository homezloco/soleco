"""
Solana Mint Extractor - Extracts mint addresses from Solana blockchain
Modular implementation using the MintExtractor and SolanaQueryHandler classes
"""
import time 
import logging
import asyncio
import re
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.mint_extractor import MintExtractor
from ..utils.solana_rpc import get_connection_pool

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(
    tags=["Soleco"]
)

@router.get("/extract")
async def get_mints(
    limit: int = Query(
        default=1,
        description="Number of recent blocks to scan (1-10)",
        ge=1,
        le=10
    )
) -> Dict[str, Any]:
    """
    Extract mint addresses from recent Solana blocks.
    
    Args:
        limit: Number of recent blocks to scan (1-10)
        
    Returns:
        Dictionary containing:
        - blocks: List of dictionaries with block-specific data
            - mint_addresses: List of new mint addresses found
            - pump_token_addresses: List of potential pump tokens
            - transaction_stats: Breakdown of transaction types
            - processing_time: Time taken to process the block
        - summary: Overall statistics across all blocks
            - total_blocks_scanned: Number of blocks processed
            - total_transactions: Total number of transactions
            - total_mint_addresses: Total number of mint addresses found
            - unique_mint_addresses: Number of unique mint addresses
            - total_new_mint_addresses: Total number of new mint addresses
            - total_pump_tokens: Total number of pump tokens
    
    Raises:
        HTTPException: If there's an error retrieving or processing the blocks
    """
    try:
        # Initialize handlers
        connection_pool = await get_connection_pool()
        query_handler = SolanaQueryHandler(connection_pool)
        mint_extractor = MintExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing blocks from {limit} recent blocks")
        
        try:
            blocks_data = await query_handler.process_blocks(num_blocks=limit)
        except Exception as e:
            error_str = str(e)
            # Check if this is a "block cleaned up" error
            if "cleaned up" in error_str and "First available block:" in error_str:
                # Extract the first available block number
                match = re.search(r'First available block: (\d+)', error_str)
                if match:
                    first_available = int(match.group(1))
                    logger.info(f"Switching to first available block: {first_available}")
                    
                    # Try again with the first available block
                    client = await connection_pool.get_client()
                    latest_block = await client.get_block_height()
                    
                    # Calculate how many blocks to process from the first available block
                    blocks_to_process = min(limit, latest_block - first_available + 1)
                    logger.info(f"Processing {blocks_to_process} blocks starting from {first_available}")
                    
                    # Process blocks from the first available block
                    blocks_data = await query_handler.process_blocks(
                        num_blocks=blocks_to_process,
                        start_slot=first_available
                    )
                else:
                    raise
            else:
                raise
        
        if not blocks_data:
            logger.error("No blocks_data returned from process_blocks")
            return {"success": False, "error": "Failed to get blocks data"}
            
        if not isinstance(blocks_data, dict) or not blocks_data.get("success", False):
            error = blocks_data.get("error", "Unknown error") if isinstance(blocks_data, dict) else "Invalid blocks data format"
            logger.error(f"Error in blocks_data: {error}")
            return {"success": False, "error": error}
            
        blocks_list = blocks_data.get("blocks", [])
        if not blocks_list:
            logger.warning("No blocks found in blocks_data")
            return {
                "success": True,
                "blocks": [],
                "summary": {
                    "total_blocks_scanned": 0,
                    "total_transactions": 0,
                    "total_mint_addresses": 0,
                    "unique_mint_addresses": 0,
                    "total_new_mint_addresses": 0,
                    "total_pump_tokens": 0
                }
            }
            
        # Process each block
        logger.info(f"Processing {len(blocks_list)} blocks")
        all_mint_addresses = set()
        all_pump_tokens = set()
        total_transactions = 0
        block_results = []
        
        for block in blocks_list:
            try:
                if not block:
                    logger.warning("Empty block data")
                    continue
                    
                # Log block details for debugging
                block_slot = block.get('parentSlot', 'unknown')
                tx_count = len(block.get('transactions', []))
                logger.debug(f"Processing block {block_slot} with {tx_count} transactions")
                
                # Process the block to extract mint addresses
                mint_extractor.process_block(block)
                
                # Get block-specific results
                results = mint_extractor.get_results()
                block_all_mints = results["all_mints"]
                block_new_mints = results["new_mints"]
                block_pump_tokens = results["pump_tokens"]
                
                # Log pump tokens for debugging
                if block_pump_tokens:
                    logger.debug(f"Pump tokens found in block {block_slot}: {block_pump_tokens}")
                    for token in block_pump_tokens:
                        logger.debug(f"Verified pump token: {token}")
                else:
                    logger.debug(f"No pump tokens found in block {block_slot}")
                
                # Add to overall results
                all_mint_addresses.update(block_all_mints)
                all_pump_tokens.update(block_pump_tokens)
                
                # Create block result
                block_result = {
                    "slot": block_slot,
                    "mint_addresses": list(block_all_mints),  # All mints in this block
                    "new_mint_addresses": list(block_new_mints),  # New mints in this block
                    "pump_token_addresses": list(block_pump_tokens),  # Pump tokens in this block
                    "transaction_stats": {
                        "total": tx_count,
                        "with_mints": len(block_all_mints)
                    },
                    "processing_time": blocks_data.get("statistics", {}).get("processing_time_ms", 0) / len(blocks_list)
                }
                
                block_results.append(block_result)
                total_transactions += tx_count
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}", exc_info=True)
                continue
                
        # Create summary
        summary = {
            "total_blocks_scanned": len(blocks_list),
            "total_transactions": total_transactions,
            "total_mint_addresses": len(all_mint_addresses),
            "unique_mint_addresses": len(all_mint_addresses),
            "total_new_mint_addresses": sum(len(block["new_mint_addresses"]) for block in block_results),
            "total_pump_tokens": len(all_pump_tokens),
            "processing_time_ms": blocks_data.get("statistics", {}).get("processing_time_ms", 0)
        }
        
        return {
            "success": True,
            "blocks": block_results,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error in get_mints: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Example usage
if __name__ == "__main__":
    # Set logging to DEBUG for more detailed output
    logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the main function
    async def main():
        result = await get_mints(limit=1)
        print(f"Found {len(result.get('blocks', []))} blocks with mint addresses")
    
    asyncio.run(main())
