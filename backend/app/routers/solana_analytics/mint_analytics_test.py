"""
Mint Analytics Module - Handles analysis of mint activities including Token2022 program
"""
from typing import Dict, Any, List, Optional, Set
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ...dependencies.solana import get_query_handler
from ...utils.solana_query import SolanaQueryHandler
from ...utils.solana_rpc import get_connection_pool
from ...utils.solana_error import (
    RPCError,
    NodeBehindError,
    SlotSkippedError,
    MissingBlocksError,
    NodeUnhealthyError,
    RateLimitError
)
from ...utils.handlers.mint_handler import MintHandler
from ...utils.handlers.token_handler import TokenHandler
from ...utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

# Create router
router = APIRouter(
    tags=["Solana Mint Analytics"],
    responses={
        404: {"description": "Not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
        503: {"description": "Node unavailable or behind"}
    },
)

class MintAnalytics:
    """Class for handling mint analytics operations"""
    
    def __init__(self, query_handler: SolanaQueryHandler):
        """Initialize with query handler"""
        self.query_handler = query_handler
        self.mint_handler = MintHandler()
        self.token_handler = TokenHandler()
        
    async def get_mint_activity(
        self,
        start_slot: Optional[int] = None,
        end_slot: Optional[int] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get mint activity within slot range"""
        try:
            # Get block data using handlers
            results = await self.query_handler.process_blocks(
                start_slot=start_slot,
                end_slot=end_slot,
                num_blocks=limit,
                handlers=[self.mint_handler, self.token_handler],
                batch_size=10
            )
            
            if not results:
                return {
                    "success": False,
                    "error": "No results returned from block processing",
                    "data": None
                }
                
            # Extract mint and token data
            mint_data = results.get('mint_handler', {})
            token_data = results.get('token_handler', {})
            
            return {
                "success": True,
                "data": {
                    "mint_operations": mint_data.get('mint_operations', []),
                    "token_operations": token_data.get('token_operations', []),
                    "statistics": {
                        "mint_stats": mint_data.get('statistics', {}),
                        "token_stats": token_data.get('statistics', {}),
                        "processed_blocks": results.get('processed_blocks', 0),
                        "total_blocks": results.get('total_blocks', 0)
                    },
                    "errors": results.get('errors', [])
                }
            }
            
        except (NodeBehindError, NodeUnhealthyError) as e:
            logger.error(f"Node error in get_mint_activity: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Node unavailable or behind: {str(e)}"
            )
        except RPCError as e:
            logger.error(f"RPC error in get_mint_activity: {str(e)}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error in get_mint_activity: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

@router.get(
    "/activity",
    summary="Get Mint Activity",
    description="Get mint activity within a specified slot range",
    response_description="Mint activity results including operations and statistics"
)
async def get_mint_activity(
    start_slot: Optional[int] = None,
    end_slot: Optional[int] = None,
    limit: int = 100,
    query_handler: SolanaQueryHandler = Depends(get_query_handler)
) -> Dict[str, Any]:
    """
    Get mint activity within slot range.
    
    Args:
        start_slot: Optional start slot
        end_slot: Optional end slot
        limit: Maximum number of blocks to process
        
    Returns:
        Dict containing mint activity results
    """
    analytics = MintAnalytics(query_handler)
    return await analytics.get_mint_activity(start_slot, end_slot, limit)

@router.get(
    "/solana/mint/new",
    summary="Analyze New Mints",
    description="Analyze recent blocks for new token mints",
    response_description="Analysis of new token mints including statistics"
)
async def analyze_new_mints(
    blocks: int = 1,
    query_handler: SolanaQueryHandler = Depends(get_query_handler)
) -> Dict[str, Any]:
    """Analyze recent blocks for new token mints"""
    try:
        logger.debug(f"Analyzing new mints from {blocks} blocks")
        
        # Create handlers
        mint_handler = MintHandler()
        token_handler = TokenHandler()
        
        # Process blocks with handlers
        result = await query_handler.process_blocks(
            num_blocks=blocks,
            commitment="confirmed",
            handlers=[mint_handler, token_handler],
            batch_size=5
        )
        
        if not result:
            logger.error("No result returned from process_blocks")
            return {
                "success": False,
                "error": "Failed to process blocks",
                "data": None
            }

        # Get handler results
        mint_data = result.get('mint_handler', {})
        token_data = result.get('token_handler', {})
        
        # Build enhanced response
        response_data = {
            "success": True,
            "data": {
                "summary": {
                    "new_mints": mint_data.get('new_mints', 0),
                    "mint_operations": mint_data.get('mint_operations', []),
                    "token_operations": token_data.get('token_operations', []),
                    "processed_blocks": result.get('processed_blocks', 0),
                    "total_blocks": result.get('total_blocks', 0)
                },
                "statistics": {
                    "mint_stats": mint_data.get('statistics', {}),
                    "token_stats": token_data.get('statistics', {})
                },
                "errors": result.get('errors', [])
            }
        }
        
        return response_data

    except (NodeBehindError, NodeUnhealthyError) as e:
        logger.error(f"Node error in analyze_new_mints: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Node unavailable or behind: {str(e)}"
        )
    except RPCError as e:
        logger.error(f"RPC error in analyze_new_mints: {str(e)}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error in analyze_new_mints: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get(
    "/solana/mint/recent",
    summary="Analyze Recent Mints",
    description="Analyze recent mint activity from the last N blocks",
    response_description="Analysis of recent mint activity"
)
async def analyze_recent_mints(
    limit: int = 10,
    include_transactions: bool = False,
    query_handler: SolanaQueryHandler = Depends(get_query_handler)
) -> Dict[str, Any]:
    """
    Analyze recent mint activity from the last N blocks
    
    Args:
        limit: Number of recent blocks to analyze
        include_transactions: Whether to include detailed transaction info
        
    Returns:
        Dict containing analysis results
    """
    try:
        # Get latest block height
        client = await query_handler.connection_pool.get_client()
        current_block = await client.get_block_height()
        if not current_block:
            raise HTTPException(
                status_code=503,
                detail="Failed to get current block height"
            )
            
        # Calculate block range
        start_block = max(0, current_block - limit)
        
        # Create handlers
        mint_handler = MintHandler()
        token_handler = TokenHandler()
        
        # Process blocks with handlers
        results = await query_handler.process_blocks(
            start_slot=start_block,
            end_slot=current_block,
            handlers=[mint_handler, token_handler],
            batch_size=5,
            batch_delay=1.0
        )
        
        if not results:
            return {
                "success": False,
                "error": "Failed to process blocks",
                "data": None
            }
            
        # Extract handler results
        mint_data = results.get('mint_handler', {})
        token_data = results.get('token_handler', {})
        
        response_data = {
            "success": True,
            "data": {
                "summary": {
                    "new_mints": mint_data.get('new_mints', 0),
                    "mint_operations": mint_data.get('mint_operations', []),
                    "token_operations": token_data.get('token_operations', []),
                    "processed_blocks": results.get('processed_blocks', 0),
                    "total_blocks": results.get('total_blocks', 0)
                },
                "statistics": {
                    "mint_stats": mint_data.get('statistics', {}),
                    "token_stats": token_data.get('statistics', {})
                },
                "errors": results.get('errors', [])
            }
        }
        
        # Include transaction details if requested
        if include_transactions:
            response_data["data"]["transactions"] = {
                "mint_transactions": mint_data.get('transactions', []),
                "token_transactions": token_data.get('transactions', [])
            }
            
        return response_data

    except (NodeBehindError, NodeUnhealthyError) as e:
        logger.error(f"Node error in analyze_recent_mints: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Node unavailable or behind: {str(e)}"
        )
    except RPCError as e:
        logger.error(f"RPC error in analyze_recent_mints: {str(e)}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error in analyze_recent_mints: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

# Constants for token-related programs
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # Standard SPL Token
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"  # Token 2022
METAPLEX_TOKEN_METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"  # Metaplex Token Metadata
CANDY_MACHINE_CORE_ID = "CndyV3LdqHUfDLmE5naZjVN8rBZz4tqhdefbAnjHG3JR"  # Candy Machine Core v3
CANDY_MACHINE_ID = "cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ"  # Candy Machine v2
CANDY_GUARD_ID = "Guard1JwRhJkVH6XZhzoYxeBVQe872VH6QggF4BWmS9g"  # Candy Guard
MPL_TOKEN_AUTH_RULES = "auth9SigNpDKz4sJJ1DfCTuZrZNSAgh9sFD3rboVmgg"  # MPL Token Authorization Rules
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"

# Known token mints to exclude
KNOWN_TOKEN_MINTS = {
    "So11111111111111111111111111111111111111112",  # Wrapped SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "7i5KKsX2weiTkry7jA4ZwSJ4zRWqW2PPkiupCAMMQCLQ",  # PYTH
}

"""
Mint Analytics Test Module - Test endpoints for mint analytics functionality
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from ...dependencies.solana import get_query_handler
from ...utils.solana_query import SolanaQueryHandler
from ...utils.solana_error import (
    RPCError,
    NodeBehindError,
    NodeUnhealthyError
)
from ...utils.handlers.mint_handler import MintHandler
from ...utils.handlers.token_handler import TokenHandler
from ...utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

# Create router with OpenAPI documentation
router = APIRouter(
    prefix="/test",
    tags=["Solana Mint Analytics Tests"],
    responses={
        404: {"description": "Not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
        503: {"description": "Node unavailable or behind"}
    },
)

# Response Models
class MintStats(BaseModel):
    """Statistics for mint operations"""
    total_mints: int = Field(0, description="Total number of mint operations")
    unique_mints: int = Field(0, description="Number of unique mint addresses")
    token_types: Dict[str, int] = Field(default_factory=dict, description="Count of different token types")
    success_rate: float = Field(0.0, description="Percentage of successful mint operations")

class TokenOperation(BaseModel):
    """Token operation details"""
    type: str = Field(..., description="Type of token operation")
    mint_address: str = Field(..., description="Mint address of the token")
    program_id: str = Field(..., description="Program ID that processed the operation")
    slot: Optional[int] = Field(None, description="Slot number where operation occurred")
    signature: Optional[str] = Field(None, description="Transaction signature")

class MintTestResponse(BaseModel):
    """Standardized test response format"""
    success: bool = Field(..., description="Whether the operation was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data if successful")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")

@router.get(
    "/mock-mint",
    summary="Test Mint Operation",
    description="Test endpoint that simulates a mint operation with mock data",
    response_model=MintTestResponse,
    responses={
        200: {
            "description": "Successful mock mint operation",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "mint_address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                            "operation_type": "mint",
                            "timestamp": "2025-02-24T22:52:45+08:00"
                        }
                    }
                }
            }
        }
    }
)
async def test_mock_mint(
    mint_type: str = Query("standard", description="Type of mint operation to simulate (standard/token2022)"),
    query_handler: SolanaQueryHandler = Depends(get_query_handler)
) -> Dict[str, Any]:
    """
    Test endpoint that simulates a mint operation with mock data.
    Useful for testing integration with other systems.
    """
    try:
        # Create mock mint data
        mock_data = {
            "mint_address": (
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" 
                if mint_type == "standard" 
                else "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
            ),
            "operation_type": "mint",
            "timestamp": "2025-02-24T22:52:45+08:00"
        }
        
        return {
            "success": True,
            "data": mock_data
        }
        
    except Exception as e:
        logger.error(f"Error in test_mock_mint: {str(e)}")
        return {
            "success": False,
            "error": f"Test operation failed: {str(e)}"
        }

@router.get(
    "/instruction-types",
    summary="Test Instruction Types",
    description="Test endpoint that returns all supported instruction types",
    response_model=MintTestResponse,
    responses={
        200: {
            "description": "List of supported instruction types",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "instruction_types": ["mint", "mintTo", "createMint"],
                            "program_types": ["spl_token", "token2022"]
                        }
                    }
                }
            }
        }
    }
)
async def test_instruction_types() -> Dict[str, Any]:
    """
    Test endpoint that returns all supported instruction types.
    Useful for validating instruction handling logic.
    """
    try:
        return {
            "success": True,
            "data": {
                "instruction_types": ["mint", "mintTo", "createMint", "MintTo", "mint_to"],
                "program_types": ["spl_token", "token2022", "metadata", "ata"],
                "supported_programs": {
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "spl_token",
                    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb": "token2022",
                    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s": "metadata"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error in test_instruction_types: {str(e)}")
        return {
            "success": False,
            "error": f"Test operation failed: {str(e)}"
        }

@router.get(
    "/error-simulation",
    summary="Test Error Handling",
    description="Test endpoint that simulates various error conditions",
    response_model=MintTestResponse,
    responses={
        200: {"description": "Error simulation successful"},
        429: {"description": "Rate limit simulation"},
        503: {"description": "Node unavailable simulation"}
    }
)
async def test_error_handling(
    error_type: str = Query("rate_limit", description="Type of error to simulate (rate_limit/node_error/validation)")
) -> Dict[str, Any]:
    """
    Test endpoint that simulates various error conditions.
    Useful for testing error handling and recovery logic.
    """
    try:
        if error_type == "rate_limit":
            raise RPCError("Rate limit exceeded")
        elif error_type == "node_error":
            raise NodeUnhealthyError("Node is behind")
        elif error_type == "validation":
            raise ValueError("Invalid instruction format")
            
        return {
            "success": True,
            "data": {"message": "No error simulated"}
        }
        
    except RPCError as e:
        logger.error(f"RPC error in test_error_handling: {str(e)}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit simulation: {str(e)}"
        )
    except NodeUnhealthyError as e:
        logger.error(f"Node error in test_error_handling: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Node error simulation: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error in test_error_handling: {str(e)}")
        return {
            "success": False,
            "error": f"Error simulation: {str(e)}"
        }

# Constants for token-related programs
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # Standard SPL Token
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"  # Token 2022
METAPLEX_TOKEN_METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"  # Metaplex Token Metadata
