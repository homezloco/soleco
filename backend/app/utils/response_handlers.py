from typing import Optional, Dict, Any, TYPE_CHECKING, TypeVar
import logging
import time
from collections import defaultdict

from .solana_types import (
    EndpointConfig,
    RPCError,
    NodeBehindError,
    SlotSkippedError,
    MissingBlocksError,
    SimulationError,
    NodeUnhealthyError,
    RateLimitError
)
from .handlers.base_handler import BaseHandler
from .handlers.token_handler import TokenHandler
from .handlers.program_handler import ProgramHandler
from .handlers.mint_handler import MintHandler

T = TypeVar('T')

if TYPE_CHECKING:
    from .response_handlers import SolanaResponseManager

logger = logging.getLogger(__name__)

class QueryBatchStats:
    def __init__(self):
        self.total = 0
        self.success = 0
        self.failure = 0
        self.errors = defaultdict(int)

    def increment_total(self):
        self.total += 1

    def increment_success(self):
        self.success += 1

    def increment_failure(self):
        self.failure += 1

    def record_error(self, error):
        self.errors[error] += 1

    def get_current(self):
        return {
            "total": self.total,
            "success": self.success,
            "failure": self.failure,
            "errors": dict(self.errors)
        }


class ResponseHandler:
    """Base class for handling Solana RPC responses"""
    
    def __init__(self, response_manager: Optional['SolanaResponseManager'] = None):
        self.response_manager = response_manager
        self.stats = QueryBatchStats()
        
    async def handle_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a raw RPC response
        
        Args:
            response: The raw RPC response
            
        Returns:
            Processed result
        """
        try:
            if not response or not isinstance(response, dict):
                logger.warning("Invalid response format")
                self.stats.increment_failure()
                return {
                    "success": False,
                    "error": "Invalid response format",
                    "data": None,
                    "statistics": self.stats.get_current()
                }

            # Process the result
            result = await self.process_result(response)
            
            # Update statistics
            if result.get("success", False):
                self.stats.increment_success()
            else:
                self.stats.increment_failure()
                if result.get("error"):
                    self.stats.record_error(result["error"])

            return result

        except Exception as e:
            error_msg = f"Error in handle_response: {str(e)}"
            logger.error(error_msg)
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            return {
                "success": False,
                "error": error_msg,
                "data": None,
                "statistics": self.stats.get_current()
            }

    async def process_result(self, result: Any) -> Dict[str, Any]:
        """
        Process the result portion of the response.
        
        Args:
            result: The result to process
            
        Returns:
            Processed result
        """
        try:
            # Validate result format
            if not result or not isinstance(result, dict):
                logger.warning("Invalid result format")
                return {
                    "success": False,
                    "error": "Invalid result format",
                    "data": None,
                    "statistics": self.stats.get_current()
                }

            # Extract block data
            block_data = result.get('result', {})
            if not isinstance(block_data, dict):
                logger.warning("Invalid block data format")
                return {
                    "success": False,
                    "error": "Invalid block data format",
                    "data": None,
                    "statistics": self.stats.get_current()
                }

            # Update statistics
            self.stats.increment_total()
            self.stats.increment_success()
            
            # Process block data
            return {
                "success": True,
                "slot": block_data.get('slot', 0),
                "timestamp": block_data.get('blockTime', int(time.time())),
                "data": block_data,
                "statistics": self.stats.get_current()
            }

        except Exception as e:
            error_msg = f"Error processing result: {str(e)}"
            logger.error(error_msg)
            self.stats.increment_failure()
            self.stats.record_error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "data": None,
                "statistics": self.stats.get_current()
            }

class SolanaResponseManager:
    """Manager for handling Solana RPC responses with comprehensive error handling."""
    
    def __init__(self, config: EndpointConfig):
        self.config = config
        self.stats = QueryBatchStats()
        
        # Initialize handlers
        self.base_handler = BaseHandler()
        self.token_handler = TokenHandler()
        self.program_handler = ProgramHandler()
        self.mint_handler = MintHandler()
    
    async def handle_response(self, response: Dict[str, Any]) -> Any:
        """
        Handle a raw RPC response with error checking
        
        Args:
            response: Raw RPC response
            
        Returns:
            Processed response data
            
        Raises:
            RPCError: If response contains an error
        """
        if not response:
            raise RPCError("Empty response")
            
        if "error" in response:
            error = response["error"]
            error_code = error.get("code", -1)
            error_message = error.get("message", "Unknown error")
            
            if error_code == -32007:  # Slot skipped
                raise SlotSkippedError(f"Slot was skipped: {error_message}")
            elif error_code == -32004:  # Node is behind
                raise NodeBehindError(f"Node is behind: {error_message}")
            elif error_code == -32009:  # Transaction simulation failed
                raise SimulationError(f"Transaction simulation failed: {error_message}")
            elif error_code == -32008:  # Missing blocks
                raise MissingBlocksError(f"Missing blocks: {error_message}")
            else:
                raise RPCError(f"RPC error {error_code}: {error_message}")
                
        if "result" not in response:
            # Handle raw response format
            if isinstance(response, (dict, list)):
                return await self.process_result(response)
            raise RPCError("Invalid response format")
            
        return await self.process_result(response["result"])
        
    async def process_result(self, result: Any) -> Any:
        """Process the result portion of the response"""
        if result is None:
            return None
            
        # Handle list results
        if isinstance(result, list):
            processed = []
            for item in result:
                processed.append(await self.process_result(item))
            return processed
            
        # For block data, use base handler
        if isinstance(result, dict) and ("transactions" in result or "blockhash" in result):
            return await self.base_handler.process_result(result)
            
        # Delegate to appropriate handler based on result type
        if isinstance(result, dict):
            if "mint" in result:
                return await self.mint_handler.process_result(result)
            elif "token" in result:
                return await self.token_handler.process_result(result)
            elif "program" in result:
                return await self.program_handler.process_result(result)
                
        # Return raw result if no handler matches
        return result
