"""
Solana RPC response handling and error parsing.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import Transaction
from solders.message import Message
from solders.instruction import Instruction
from solders.rpc.responses import *
from solana.rpc.async_api import AsyncClient
from .solana_errors import RetryableError, RPCError
from base58 import b58decode
from solders.pubkey import Pubkey
from solders.transaction_status import EncodedTransactionWithStatusMeta
from solders.rpc.responses import GetBlockResp
import time
import asyncio
from .logging_config import setup_logging
from collections import defaultdict

# Get logger with DEBUG level
logger = setup_logging('solana.response')

class NodeBehindError(RetryableError):
    """Exception for node behind errors"""
    pass

class SlotSkippedError(RetryableError):
    """Exception for slot skipped errors"""
    pass

class MissingBlocksError(RetryableError):
    """Exception for missing blocks errors"""
    pass

class NodeUnhealthyError(RetryableError):
    """Exception for node unhealthy errors"""
    pass

class RateLimitError(RetryableError):
    """Exception for rate limit errors"""
    pass

class RateLimitHandler:
    """Handles rate limit tracking and backoff calculations from RPC response headers"""
    
    def __init__(self):
        self.method_limit = 40  # Default method limit
        self.method_remaining = 40
        self.rps_limit = 100  # Default RPS limit
        self.rps_remaining = 100
        self.conn_limit = 40  # Default connection limit
        self.conn_remaining = 40
        self.last_update = time.time()
        self._cooldown_until = 0
        self._lock = asyncio.Lock()

    @property
    def is_rate_limited(self) -> bool:
        """Check if we're currently rate limited"""
        return time.time() < self._cooldown_until

    @property
    def cooldown_remaining(self) -> float:
        """Get remaining cooldown time in seconds"""
        if not self.is_rate_limited:
            return 0
        return self._cooldown_until - time.time()

    async def update_from_headers(self, headers: Dict[str, str]) -> None:
        """
        Update rate limit state from response headers
        
        Args:
            headers: Response headers from RPC call
        """
        async with self._lock:
            # Update method limits
            self.method_limit = int(headers.get('x-ratelimit-method-limit', self.method_limit))
            self.method_remaining = int(headers.get('x-ratelimit-method-remaining', self.method_remaining))
            
            # Update RPS limits
            self.rps_limit = int(headers.get('x-ratelimit-rps-limit', self.rps_limit))
            self.rps_remaining = int(headers.get('x-ratelimit-rps-remaining', self.rps_remaining))
            
            # Update connection limits
            self.conn_limit = int(headers.get('x-ratelimit-conn-limit', self.conn_limit))
            self.conn_remaining = int(headers.get('x-ratelimit-conn-remaining', self.conn_remaining))
            
            # Handle rate limit cooldown
            if 'retry-after' in headers:
                retry_after = float(headers['retry-after'])
                self._cooldown_until = time.time() + retry_after
            
            self.last_update = time.time()

    def should_backoff(self) -> bool:
        """
        Determine if we should back off based on current limits
        
        Returns:
            bool: True if we should back off
        """
        # If explicitly rate limited, always back off
        if self.is_rate_limited:
            return True
            
        # Back off if we're close to any limits
        return (
            self.method_remaining < 5 or  # Less than 5 method calls remaining
            self.rps_remaining < 10 or    # Less than 10 RPS remaining
            self.conn_remaining < 3       # Less than 3 connections remaining
        )

    def get_backoff_time(self) -> float:
        """
        Calculate how long to back off for
        
        Returns:
            float: Number of seconds to back off
        """
        if self.is_rate_limited:
            return self.cooldown_remaining
            
        # Calculate dynamic backoff based on remaining capacity
        backoff = 1.0  # Base backoff of 1 second
        
        # Add more backoff time if we're close to limits
        if self.method_remaining < 5:
            backoff += (5 - self.method_remaining) * 0.5
            
        if self.rps_remaining < 10:
            backoff += (10 - self.rps_remaining) * 0.2
            
        if self.conn_remaining < 3:
            backoff += (3 - self.conn_remaining) * 1.0
            
        return min(backoff, 30.0)  # Cap at 30 seconds

class SolanaResponseHandler:
    """Handles parsing and validation of Solana RPC responses"""
    
    # Define standard RPC error codes
    RPC_ERROR_CODES = {
        -32002: {
            "name": "Transaction simulation failed",
            "retry": True,
            "description": "Transaction simulation failed due to preflight check or blockhash issues"
        },
        -32003: {
            "name": "Transaction signature verification failure",
            "retry": False,
            "description": "Invalid signature or key pair"
        },
        -32004: {
            "name": "Block not available",
            "retry": True,
            "description": "Requested block is not available, likely due to timeout"
        },
        -32005: {
            "name": "Node is unhealthy",
            "retry": True,
            "description": "Node is behind by slots and needs to catch up"
        },
        -32007: {
            "name": "Slot skipped",
            "retry": False,
            "description": "Slot was skipped or missing due to ledger jump"
        },
        -32009: {
            "name": "Slot missing",
            "retry": False,
            "description": "Slot was skipped or missing in long-term storage"
        },
        -32010: {
            "name": "Account index missing",
            "retry": False,
            "description": "Account excluded from secondary indexes"
        },
        -32013: {
            "name": "Invalid signature length",
            "retry": False,
            "description": "Transaction signature length mismatch"
        },
        -32014: {
            "name": "Block status unavailable",
            "retry": True,
            "description": "Block status not yet available"
        },
        -32015: {
            "name": "Unsupported transaction version",
            "retry": False,
            "description": "Transaction version not supported by client"
        },
        -32016: {
            "name": "Minimum context slot not reached",
            "retry": True,
            "description": "Required minimum context slot has not been reached"
        },
        -32602: {
            "name": "Invalid parameters",
            "retry": False,
            "description": "Invalid parameters in request"
        }
    }
    
    # Define program-specific error codes
    PROGRAM_ERROR_CODES = {
        # Token program errors
        3: {
            "name": "InvalidAccountData",
            "retry": False,
            "description": "Invalid account data format"
        },
        18: {
            "name": "InvalidMintAuthority",
            "retry": False,
            "description": "Invalid mint authority"
        },
        24: {
            "name": "InvalidFreezeAuthority",
            "retry": False,
            "description": "Invalid freeze authority"
        },
        30: {
            "name": "AccountInUse",
            "retry": False,
            "description": "Account already in use"
        },
        40: {
            "name": "InvalidProgramAuthority",
            "retry": False,
            "description": "Invalid program authority"
        },
        1009: {
            "name": "InvalidAccountOwner",
            "retry": False,
            "description": "Invalid account owner"
        },
        4369: {
            "name": "AccountNotInitialized",
            "retry": False,
            "description": "Account not initialized"
        },
        6000: {
            "name": "InvalidAccountData",
            "retry": False,
            "description": "Invalid account data"
        },
        6001: {
            "name": "InvalidTokenAccount",
            "retry": False,
            "description": "Invalid token account"
        },
        6028: {
            "name": "InvalidTokenAccount",
            "retry": False,
            "description": "Invalid token account"
        }
    }
    
    # Define transaction-specific error types
    TRANSACTION_ERROR_TYPES = {
        "InsufficientFundsForRent": {
            "name": "InsufficientFundsForRent",
            "retry": False,
            "description": "Insufficient funds for account rent"
        },
        "ProgramFailedToComplete": {
            "name": "ProgramFailedToComplete",
            "retry": True,
            "description": "Program failed to complete execution"
        }
    }

    def handle_response(self, response: Any) -> Dict[str, Any]:
        """Handle a response from the RPC client"""
        try:
            if isinstance(response, dict):
                # Handle error responses
                if "error" in response:
                    error_info = self.parse_error(response["error"])
                    if error_info["retry"]:
                        raise RetryableError(error_info["message"])
                    raise RPCError(error_info["message"])
                    
                # Handle successful responses
                if "result" in response:
                    return response["result"]
                    
                # Provide more context for invalid format
                raise RPCError(f"Invalid RPC response format. Expected 'result' or 'error' field. Got: {list(response.keys())}")
                
            # Handle solders response objects
            if hasattr(response, "to_json"):
                try:
                    return response.to_json()
                except Exception as e:
                    raise RPCError(f"Failed to serialize solders response: {str(e)}")
            elif hasattr(response, "result"):
                return response.result
                
            # Handle primitive responses
            if isinstance(response, (int, str, bool)):
                return response
                
            raise RPCError(f"Unexpected response type: {type(response)}. Response: {str(response)[:200]}")
            
        except Exception as e:
            if not isinstance(e, (RetryableError, RPCError)):
                logger.error(f"Unexpected error handling response: {str(e)}")
                raise RPCError(f"Failed to handle response: {str(e)}")
            raise

    def handle_native_response(self, response: Any, context: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Handle responses from the native Solana client"""
        try:
            # Handle strongly-typed responses from solders
            if isinstance(response, (GetTransactionResp, GetBlockResp)):
                return response.value
                
            # Handle RpcResult responses
            if hasattr(response, "result"):
                return response.result
                
            # Fall back to general response handling
            return self.handle_response(response)
            
        except Exception as e:
            error_msg = f"Error handling native response: {str(e)}"
            if context:
                error_msg = f"{error_msg} (Context: {context})"
            logger.error(error_msg)
            raise RetryableError(error_msg)

    async def handle_transaction(
        self,
        client: AsyncClient,
        signature: Union[str, Signature],
        encoding: Optional[str] = None,
        commitment: Optional[str] = None,
        max_supported_transaction_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Handle transaction fetching with the native client"""
        try:
            response = await client.get_transaction(
                signature,
                encoding=encoding or "jsonParsed",
                commitment=commitment,
                max_supported_transaction_version=max_supported_transaction_version or 0
            )
            return self.handle_native_response(response, f"Transaction {signature}")
            
        except Exception as e:
            logger.error(f"Error fetching transaction {signature}: {str(e)}")
            raise RetryableError(f"Failed to fetch transaction: {str(e)}")

    async def handle_block(
        self,
        client: AsyncClient,
        slot: int,
        encoding: Optional[str] = None,
        commitment: Optional[str] = None,
        max_supported_transaction_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Handle block fetching with the native client"""
        try:
            response = await client.get_block(
                slot,
                encoding=encoding or "jsonParsed",
                commitment=commitment,
                max_supported_transaction_version=max_supported_transaction_version or 0
            )
            return self.handle_native_response(response, f"Block {slot}")
            
        except Exception as e:
            logger.error(f"Error fetching block {slot}: {str(e)}")
            raise RetryableError(f"Failed to fetch block: {str(e)}")

    def handle_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process block data and extract relevant information"""
        try:
            transactions = block_data.get("transactions", [])
            block_time = block_data.get("blockTime")
            block_height = block_data.get("blockHeight")
            parent_slot = block_data.get("parentSlot")
            
            results = {
                "success": True,
                "slot": block_data.get("slot"),
                "block_time": block_time,
                "block_height": block_height,
                "parent_slot": parent_slot,
                "transaction_count": len(transactions),
                "transactions": []
            }
            
            for tx in transactions:
                try:
                    tx_result = self.handle_transaction(tx)
                    if tx_result:
                        results["transactions"].append(tx_result)
                except Exception as e:
                    logger.warning(f"Error processing transaction in block: {str(e)}")
                    continue
                    
            return results
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "slot": block_data.get("slot")
            }

    def validate_transaction_response(self, response: Optional[Dict[str, Any]], signature: str) -> Optional[Dict[str, Any]]:
        """Validate and process a transaction response"""
        if not response:
            logger.warning(f"No response data for transaction {signature}")
            return None
            
        try:
            # Handle error responses
            if "error" in response:
                error_info = self.parse_error(response["error"])
                if error_info["retry"]:
                    raise RetryableError(error_info["message"])
                logger.error(f"Non-retryable error for transaction {signature}: {error_info['message']}")
                return None
                
            # Handle successful responses
            if not isinstance(response, dict):
                logger.error(f"Invalid response type for transaction {signature}: {type(response)}")
                return None
                
            if "result" not in response:
                logger.error(f"Invalid response format for transaction {signature}. Keys: {list(response.keys())}")
                return None
                
            result = response["result"]
            if not result:
                logger.warning(f"Transaction {signature} not found")
                return None
                
            # Validate transaction data structure
            if isinstance(result, dict):
                if "transaction" not in result and "message" not in result:
                    logger.error(f"Missing transaction data for {signature}. Available keys: {list(result.keys())}")
                    return None
            else:
                logger.error(f"Unexpected result type for transaction {signature}: {type(result)}")
                return None
                
            return result
            
        except Exception as e:
            logger.error(f"Error validating transaction {signature}: {str(e)}")
            raise RetryableError(f"Failed to validate transaction response: {str(e)}")

    @staticmethod
    def validate_block_response(response: Dict[str, Any], slot: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Validate and process a block response"""
        if not response:
            return None
            
        if isinstance(response, dict) and "error" in response:
            error_info = SolanaResponseHandler.parse_error(response["error"])
            logger.debug(f"Block request for slot {slot} failed: {error_info['message']}")
            if error_info["retry"]:
                raise RetryableError(error_info["message"])
            raise RPCError(error_info["message"])
            
        return response

    @staticmethod
    def validate_slot_response(response: Any) -> int:
        """Validate and process a slot response"""
        if response is None:
            raise RPCError("No result in slot response")
            
        # Handle dictionary responses
        if isinstance(response, dict):
            if "error" in response:
                error_info = SolanaResponseHandler.parse_error(response["error"])
                logger.debug(f"Slot request failed: {error_info['message']}")
                if error_info["retry"]:
                    raise RetryableError(error_info["message"])
                raise RPCError(error_info["message"])
                
            if "result" in response:
                return int(response["result"])
                
        # Handle primitive responses
        if isinstance(response, (int, str)):
            return int(response)
            
        raise RPCError(f"Invalid slot response type: {type(response)}")

    @staticmethod
    def validate_blocks_response(response: Dict[str, Any]) -> list:
        """Validate and process a blocks response"""
        blocks = response.get("result", [])
        if not isinstance(blocks, list):
            raise ValueError(f"Invalid blocks response: {blocks}")
        return blocks

    @staticmethod
    def format_params(method: str, *args, **kwargs) -> Dict[str, Any]:
        """Format parameters for RPC request"""
        # Get commitment and encoding config
        commitment = kwargs.get('commitment')
        config = {
            "commitment": commitment if commitment else "finalized",
            "encoding": "jsonParsed"
        }
        
        # Format parameters based on method
        if method == "getTransaction":
            signature = args[0]
            return {
                "method": method,
                "params": [
                    str(signature) if isinstance(signature, Signature) else signature,
                    config
                ]
            }
        elif method == "getBlock":
            slot = args[0]
            return {
                "method": method,
                "params": [slot, config]
            }
        elif method == "getBlocks":
            start_slot = args[0]
            end_slot = args[1] if len(args) > 1 else None
            params = [start_slot]
            if end_slot is not None:
                params.append(end_slot)
            params.append(config)
            return {
                "method": method,
                "params": params
            }
        elif method == "getSlot":
            return {
                "method": method,
                "params": [config]
            }
        else:
            raise ValueError(f"Unknown method: {method}")

    @staticmethod
    def create_request(method: str, *args, **kwargs) -> Dict[str, Any]:
        """Create a complete RPC request"""
        params = SolanaResponseHandler.format_params(method, *args, **kwargs)
        return {
            "jsonrpc": "2.0",
            "id": 1,
            **params
        }

    def handle_transaction(self, tx: Any) -> Dict[str, Any]:
        """Process a transaction to extract relevant information"""
        if not tx or not tx.transaction or not tx.meta:
            return {}
            
        try:
            # Process pre and post token balances
            pre_token_balances = getattr(tx.meta, 'pre_token_balances', []) or []
            post_token_balances = getattr(tx.meta, 'post_token_balances', []) or []
            
            # Process instructions
            message = tx.transaction.message
            if message:
                account_keys = [str(key) for key in (getattr(message, 'account_keys', []) or [])]
                instructions = getattr(message, 'instructions', []) or []
                
                results = {
                    "slot": tx.slot,
                    "transaction": tx.transaction,
                    "pre_token_balances": pre_token_balances,
                    "post_token_balances": post_token_balances,
                    "instructions": []
                }
                
                for instruction in instructions:
                    try:
                        instruction_result = self._process_instruction(instruction, account_keys)
                        if instruction_result:
                            results["instructions"].append(instruction_result)
                    except Exception as e:
                        logger.warning(f"Error processing instruction: {str(e)}")
                        continue
                        
                return results
                
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            raise RetryableError(f"Failed to process transaction: {str(e)}")

    def _process_instruction(self, instruction: Any, account_keys: List[str]) -> Dict[str, Any]:
        """Process a single instruction to extract relevant information"""
        try:
            if not instruction or not account_keys:
                logger.debug("Skipping instruction processing - missing instruction or account keys")
                return
                
            # Get program ID using multiple methods
            program_id = None
            instruction_data = {}
            
            logger.debug("Starting program ID extraction...")
            logger.debug(f"Instruction type: {type(instruction)}")
            
            # Method 1: Handle dictionary-type instructions with programIdIndex
            if isinstance(instruction, dict):
                try:
                    if 'programIdIndex' in instruction:
                        program_idx = instruction['programIdIndex']
                        if isinstance(program_idx, int) and program_idx < len(account_keys):
                            program_id = str(account_keys[program_idx])
                            logger.debug(f"Method 1 - Program ID from index: {program_id}")
                except Exception as e:
                    logger.debug(f"Error getting program_id from programIdIndex: {e}")
            
            # Method 2: Check message header
            if not program_id and hasattr(instruction, 'message') and hasattr(instruction.message, 'header'):
                try:
                    header = instruction.message.header
                    if hasattr(header, 'program_ids') and header.program_ids:
                        program_id = str(header.program_ids[0])
                        logger.debug(f"Method 2 - Message header: {program_id}")
                except Exception as e:
                    logger.debug(f"Error getting program_id from message header: {e}")
            
            # Method 3: Direct program_id attribute
            if not program_id and hasattr(instruction, 'program_id'):
                try:
                    program_id = str(instruction.program_id)
                    logger.debug(f"Method 3 - Direct attribute: {program_id}")
                except Exception as e:
                    logger.debug(f"Error getting direct program_id: {e}")
            
            # Method 4: Program ID from parsed data
            if not program_id and hasattr(instruction, 'parsed'):
                try:
                    parsed = instruction.parsed
                    if isinstance(parsed, dict):
                        # Check direct program field
                        if 'program' in parsed:
                            program_id = str(parsed['program'])
                            logger.debug(f"Method 4a - Parsed program field: {program_id}")
                        # Check nested info.program field
                        elif 'info' in parsed and isinstance(parsed['info'], dict):
                            info = parsed['info']
                            if 'program' in info:
                                program_id = str(info['program'])
                                logger.debug(f"Method 4b - Parsed info program field: {program_id}")
                except Exception as e:
                    logger.debug(f"Error parsing instruction data: {e}")
            
            # Method 5: Program ID from program index
            if not program_id and hasattr(instruction, 'program'):
                try:
                    program_idx = getattr(instruction, 'program')
                    if isinstance(program_idx, int) and program_idx < len(account_keys):
                        program_id = str(account_keys[program_idx])
                        logger.debug(f"Method 5 - Program index: {program_id}")
                except Exception as e:
                    logger.debug(f"Error getting program_id from index: {e}")
            
            # Method 6: Check inner instructions
            if not program_id and hasattr(instruction, 'inner_instructions'):
                try:
                    inner_instructions = instruction.inner_instructions
                    if inner_instructions and len(inner_instructions) > 0:
                        for inner in inner_instructions:
                            if hasattr(inner, 'program_id'):
                                program_id = str(inner.program_id)
                                logger.debug(f"Method 6 - Inner instruction: {program_id}")
                                break
                except Exception as e:
                    logger.debug(f"Error checking inner instructions: {e}")

            if not program_id:
                logger.warning("Could not determine program ID for instruction")
                # Log detailed instruction data for debugging
                try:
                    logger.debug(f"Instruction type: {type(instruction)}")
                    logger.debug(f"Instruction data: {instruction}")
                    if isinstance(instruction, dict):
                        logger.debug(f"Available instruction keys: {list(instruction.keys())}")
                        if 'accounts' in instruction:
                            logger.debug(f"Instruction accounts: {instruction['accounts']}")
                    if hasattr(instruction, '__dict__'):
                        logger.debug(f"Instruction attributes: {instruction.__dict__}")
                    if hasattr(instruction, 'data'):
                        logger.debug(f"Raw instruction data: {instruction.data}")
                except Exception as e:
                    logger.debug(f"Error logging instruction details: {e}")
            
            # Validate program ID format
            if program_id:
                try:
                    # Convert to string if needed
                    if not isinstance(program_id, str):
                        logger.warning(f"Program ID is not a string: {type(program_id)}")
                        program_id = str(program_id)
                    
                    # Basic format validation
                    if len(program_id) < 32 or len(program_id) > 44:
                        logger.warning(f"Program ID has invalid length: {len(program_id)}")
                        program_id = None
                    elif not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in program_id):
                        logger.warning(f"Program ID contains invalid characters")
                        program_id = None
                except Exception as e:
                    logger.warning(f"Error validating program ID: {e}")
                    program_id = None
            
            # Process token program instructions
            if program_id in ['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb']:
                logger.debug(f"Found token program instruction: {program_id}")
                # Check instruction accounts
                if hasattr(instruction, 'accounts') and instruction.accounts:
                    # For token programs, the mint address can be in different positions
                    # depending on the instruction type
                    for account_idx in instruction.accounts:
                        if isinstance(account_idx, int) and account_idx < len(account_keys):
                            addr = str(account_keys[account_idx])
                            self._add_mint_address(addr, 'token_program')
                
                # Check parsed data for mint addresses
                if hasattr(instruction, 'parsed'):
                    parsed = instruction.parsed
                    if isinstance(parsed, dict):
                        info = parsed.get('info', {})
                        # Check common fields that might contain mint addresses
                        mint_fields = ['mint', 'mintAuthority', 'tokenMint', 'mintAccount']
                        for field in mint_fields:
                            if field in info:
                                addr = str(info[field])
                                self._add_mint_address(addr, 'token_program_parsed')

            # Process associated token program instructions
            elif program_id == 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL':
                logger.debug("Found associated token program instruction")
                if hasattr(instruction, 'accounts'):
                    # Check all accounts as potential mint addresses
                    for account_idx in instruction.accounts:
                        if isinstance(account_idx, int) and account_idx < len(account_keys):
                            addr = str(account_keys[account_idx])
                            self._add_mint_address(addr, 'associated_token_program')

            # Process metadata program instructions
            elif program_id == 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s':
                logger.debug("Found metadata program instruction")
                if hasattr(instruction, 'accounts'):
                    # Check all accounts as potential mint addresses
                    for account_idx in instruction.accounts:
                        if isinstance(account_idx, int) and account_idx < len(account_keys):
                            addr = str(account_keys[account_idx])
                            self._add_mint_address(addr, 'metadata_program')
                    
            # Process Jupiter program instructions
            elif program_id == 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4':
                logger.debug("Found Jupiter program instruction")
                # Check instruction data for route information
                if hasattr(instruction, 'data'):
                    data = instruction.data
                    if isinstance(data, dict):
                        # Check for route info which contains mint addresses
                        route = data.get('route', {})
                        if isinstance(route, dict):
                            # Check input and output token mints
                            input_mint = route.get('inputMint')
                            output_mint = route.get('outputMint')
                            if input_mint:
                                self._add_mint_address(str(input_mint), 'jupiter_input')
                            if output_mint:
                                self._add_mint_address(str(output_mint), 'jupiter_output')
                            
                            # Check route markets for additional mints
                            markets = route.get('markets', [])
                            for market in markets:
                                if isinstance(market, dict):
                                    mint_a = market.get('mintA')
                                    mint_b = market.get('mintB')
                                    if mint_a:
                                        self._add_mint_address(str(mint_a), 'jupiter_market')
                                    if mint_b:
                                        self._add_mint_address(str(mint_b), 'jupiter_market')

                # Process all accounts as they may contain mint addresses
                if hasattr(instruction, 'accounts'):
                    for account_idx in instruction.accounts:
                        if isinstance(account_idx, int) and account_idx < len(account_keys):
                            addr = str(account_keys[account_idx])
                            self._add_mint_address(addr, 'jupiter_account')

            # Process all instruction data for potential mint addresses
            if hasattr(instruction, 'data'):
                data = instruction.data
                if isinstance(data, dict):
                    # Recursively search through all dictionary values for potential mint addresses
                    def search_dict_for_mints(d, path=''):
                        if not isinstance(d, dict):
                            return
                        for k, v in d.items():
                            if isinstance(v, str) and len(v) >= 32 and len(v) <= 44:
                                self._add_mint_address(v, f'instruction_data_{path}{k}')
                            elif isinstance(v, dict):
                                search_dict_for_mints(v, f'{path}{k}.')
                            elif isinstance(v, list):
                                for i, item in enumerate(v):
                                    if isinstance(item, dict):
                                        search_dict_for_mints(item, f'{path}{k}[{i}].')
                    
                    search_dict_for_mints(data)
                    
            # Process all accounts in the instruction
            accounts = getattr(instruction, 'accounts', []) or []
            for i, account_index in enumerate(accounts):
                if isinstance(account_index, int) and account_index < len(account_keys):
                    addr = str(account_keys[account_index])
                    # Only process accounts that look like they could be mint addresses
                    if len(addr) >= 32 and len(addr) <= 44 and not addr.startswith('1111'):
                        logger.debug(f"Checking account {i}: {addr}")
                        self._add_mint_address(addr, 'instruction_accounts')
                    
            # Check instruction data for potential mint references
            if hasattr(instruction, 'data'):
                data = instruction.data
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, str) and len(value) >= 32 and len(value) <= 44:
                            logger.debug(f"Checking data field {key}: {value}")
                            self._add_mint_address(str(value), 'instruction_data')
                            
            return {
                "program_id": program_id,
                "accounts": account_keys,
                "data": data
            }
            
        except Exception as e:
            logger.warning(f"Error processing instruction: {str(e)}")
            return {}

    def _add_mint_address(self, address: str, source: str) -> bool:
        """Add a mint address if it's valid and not already processed"""
        try:
            if not address:
                logger.debug(f"Skipping empty address from {source}")
                return False
                
            if address in self.processed_addresses:
                logger.debug(f"Already processed address {address} from {source}")
                return False
                
            self.processed_addresses.add(address)
            
            # Validate the address
            if not self._is_valid_mint_address(address):
                logger.debug(f"Invalid mint address {address} from {source}")
                return False
                
            # Check for pump tokens
            if address.lower().endswith('pump'):
                logger.info(f"Found pump token: {address} from {source}")
                self.pump_tokens.add(address)
            else:
                logger.info(f"Found mint address: {address} from {source}")
                self.mint_addresses.add(address)
                
            return True
            
        except Exception as e:
            logger.warning(f"Error adding mint address {address} from {source}: {str(e)}")
            return False

    def _is_valid_mint_address(self, address: str) -> bool:
        """Validate if an address is likely to be a mint address"""
        if not address:
            return False
            
        # Filter out known system addresses and program addresses
        if address in self.SYSTEM_ADDRESSES or address in self.PROGRAM_ADDRESSES:
            return False
            
        try:
            # Check length (should be 32-44 characters)
            if len(address) < 32 or len(address) > 44:
                return False
                
            # Should not contain special characters except base58 alphabet
            if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):
                return False
                
            # Additional heuristics for pump tokens
            if 'pump' in address.lower() and not address.endswith('pump'):
                return False
                
            return True
            
        except:
            return False

    @staticmethod
    def parse_error(error: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Solana error into a structured response with retry information"""
        if not error:
            return {
                "message": "Unknown error",
                "retry": False,
                "code": None,
                "description": "No error details available"
            }
            
        # Handle transaction-specific errors
        if isinstance(error, dict):
            for error_type, info in SolanaResponseHandler.TRANSACTION_ERROR_TYPES.items():
                if error_type in error:
                    return {
                        "code": error_type,
                        "message": f"{info['name']}: {info['description']}",
                        "retry": info['retry'],
                        "description": info['description'],
                        "details": error[error_type]
                    }
            
        # Handle RPC errors
        if isinstance(error, dict) and 'code' in error:
            code = error['code']
            error_info = SolanaResponseHandler.RPC_ERROR_CODES.get(code, {
                "name": "Unknown RPC error",
                "retry": False,
                "description": "Unrecognized error code"
            })
            
            return {
                "message": f"{error_info['name']}: {error.get('message', error_info['description'])}",
                "retry": error_info['retry'],
                "code": code,
                "description": error_info['description']
            }
            
        # Handle instruction errors
        if isinstance(error, dict) and 'InstructionError' in error:
            instruction_idx, err_detail = error['InstructionError']
            
            # Handle custom program errors
            if isinstance(err_detail, dict) and 'Custom' in err_detail:
                custom_code = err_detail['Custom']
                error_info = SolanaResponseHandler.PROGRAM_ERROR_CODES.get(custom_code, {
                    "name": f"CustomError{custom_code}",
                    "retry": False,
                    "description": f"Custom program error code {custom_code}"
                })
                
                return {
                    "code": custom_code,
                    "message": f"Program error in instruction {instruction_idx}: {error_info['name']}",
                    "retry": error_info['retry'],
                    "description": error_info['description']
                }
            
            # Handle string error codes
            if isinstance(err_detail, str):
                error_info = SolanaResponseHandler.TRANSACTION_ERROR_TYPES.get(err_detail, {
                    "name": err_detail,
                    "retry": False,
                    "description": f"Program error: {err_detail}"
                })
                
                return {
                    "code": err_detail,
                    "message": f"Error in instruction {instruction_idx}: {error_info['description']}",
                    "retry": error_info['retry'],
                    "description": error_info['description']
                }
            
        return {
            "message": str(error),
            "retry": False,
            "code": None,
            "description": "Unstructured error"
        }

    @staticmethod
    def validate_rpc_response(response_json: Any) -> Any:
        """
        Validate and parse a JSON RPC response
        
        Args:
            response_json: The JSON response from the RPC endpoint
            
        Returns:
            The validated result from the response
            
        Raises:
            RPCError: If the response is invalid or contains an error
            Various RetryableError subclasses for specific error conditions
        """
        if not isinstance(response_json, dict):
            raise RPCError(f"Invalid JSON response format: {response_json}")
            
        if "error" in response_json:
            error = response_json["error"]
            if isinstance(error, dict):
                error_code = error.get("code", 0)
                error_message = error.get("message", str(error))
                
                # Map error codes to specific exceptions
                error_mapping = {
                    -32005: NodeBehindError,
                    -32007: SlotSkippedError,
                    -32008: MissingBlocksError,
                    -32009: NodeUnhealthyError
                }
                
                error_class = error_mapping.get(error_code)
                if error_class:
                    raise error_class(error_message)
                    
            raise RPCError(f"RPC error: {error}")
            
        if "result" not in response_json:
            raise RPCError(f"Missing 'result' in response: {response_json}")
            
        return response_json["result"]

    @staticmethod
    def handle_http_response(response, endpoint: str) -> Dict:
        """
        Handle HTTP response and check for rate limits
        
        Args:
            response: The HTTP response object
            endpoint: The RPC endpoint URL
            
        Returns:
            The parsed JSON response
            
        Raises:
            RateLimitError: If the request was rate limited
            RPCError: For other HTTP errors
        """
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 1))
            raise RateLimitError(f"Rate limited by {endpoint}, retry after {retry_after}s")
            
        response.raise_for_status()
        return response.json()

class MintResponseHandler(SolanaResponseHandler):
    """Handler for processing mint-related responses from Solana transactions"""
    
    def __init__(self):
        """Initialize the MintResponseHandler"""
        super().__init__()
        
        # Initialize sets for tracking addresses
        self.mint_addresses: set[str] = set()
        self.pump_tokens: set[str] = set()
        self.processed_addresses: set[str] = set()
        self.errors: list[str] = []
        
        # Configure logging
        self.logger = logging.getLogger("solana.response")
        
        # Known program IDs for different transaction types
        self.PROGRAM_TYPES: dict[str, str] = {
            'Vote111111111111111111111111111111111111111': 'vote',
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'token',
            'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb': 'token2022',
            'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s': 'metadata',
            'p1exdMJcjVao65QdewkaZRUnU6VPSXhus9n2GzWfh98': 'metaplex',
            'vau1zxA2LbssAUEF7Gpw91zMM1LvXrvpzJtmZ58rPsn': 'metaplex',
            'cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ': 'candy_machine',
            'CndyV3LdqHUfDLmE5naZjVN8rBZz4tqhdefbAnjHG3JR': 'candy_machine',
            'ComputeBudget111111111111111111111111111111': 'compute_budget',
            'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 'associated_token',
            'hausS13jsjafwWwGqZTUQRmWyvyxn9EQpqMwV1PBBmk': 'marketplace',
            'M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K': 'marketplace',
            'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4': 'jupiter',
        }
        
        # Program IDs for NFT-related programs
        self.NFT_PROGRAM_IDS: set[str] = {
            'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s',  # Metadata
            'p1exdMJcjVao65QdewkaZRUnU6VPSXhus9n2GzWfh98',  # Metaplex
            'cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ',  # Candy Machine v2
            'CndyV3LdqHUfDLmE5naZjVN8rBZz4tqhdefbAnjHG3JR',  # Candy Machine v3
        }
        
        # Token program IDs
        self.TOKEN_PROGRAM_ID = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
        self.TOKEN_2022_PROGRAM_ID = 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'
        self.ASSOCIATED_TOKEN_PROGRAM_ID = 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'
        
        # Set of known system addresses to filter out
        self.SYSTEM_ADDRESSES: set[str] = {
            'So11111111111111111111111111111111111111112',  # Wrapped SOL
            self.TOKEN_PROGRAM_ID,  # Token Program
            self.ASSOCIATED_TOKEN_PROGRAM_ID,  # Associated Token Program
            self.TOKEN_2022_PROGRAM_ID,  # Token Program 2022
            '11111111111111111111111111111111',  # System Program
            'ComputeBudget111111111111111111111111111111',  # Compute Budget
            'Vote111111111111111111111111111111111111111',  # Vote Program
            'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr',  # Memo Program
        }
        
        # Set of known program IDs to filter out
        self.PROGRAM_ADDRESSES: set[str] = {
            'DCA265Vj8a9CEuX1eb1LWRnDT7uK6q1xMipnNyatn23M',  # DCA Program
            'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4',  # Jupiter Program
            'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc',  # Whirlpool Program
            'SoLFiHG9TfgtdUXUjWAxi3LtvYuFyDLVhBWxdMZxyCe',  # SolFi Program
            '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',  # Raydium Program
            'AzHrwdCsEZotAjr7sjenHrHpf1ZKYoGBP6N7HVhEsyen',  # Azuro Program
            'M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K',  # Magic Eden Program
            'HYPERfwdTjyJ2SCaKHmpF2MtrXqWxrsotYDsTrshHWq8',  # Hyperspace Program
            'mmm3XBJg5gk8XJxEKBvdgptZz6SgK4tXvn36sodowMc',  # Metamask Program
            'So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo',  # Solend Program
            'DjVE6JNiYqPL2QXyCUUh8rNjHrbz9hXHNYt99MQ59qw1',  # Orca Program
        }
        
    def handle_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a raw RPC response"""
        if not response or "result" not in response:
            return self._create_response()
            
        result = response["result"]
        return self.handle_block(result)

    def handle_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process block data and extract mint information"""
        if not block_data:
            return self._create_response()

        # Extract transactions from block
        transactions = block_data.get("transactions", [])
        if transactions:
            for tx_data in transactions:
                self.handle_transaction(tx_data)

        return self._create_response()

    def handle_transaction(self, tx_data: Any) -> Dict[str, Any]:
        """Process a transaction to extract mint addresses and related info
        
        Args:
            tx_data: Transaction data from RPC response
            
        Returns:
            Dict containing mint addresses and transaction details
        """
        # Initialize/reset state for this transaction
        self._init_response_data()
        
        try:
            logger.debug("Starting transaction processing")
            
            # Get message data - it should already be properly structured from extract_mints_from_block
            message = None
            meta = {}
            
            if isinstance(tx_data, dict):
                # Try to get message from various locations in dict
                message = tx_data.get("message")
                meta = tx_data.get("meta", {})
                
                if not message and "transaction" in tx_data:
                    # Try to get message from transaction object if it exists
                    transaction = tx_data.get("transaction", {})
                    if isinstance(transaction, dict):
                        message = transaction.get("message")
                        meta = transaction.get("meta", {})
                        logger.debug(f"Found message in transaction object, meta keys: {meta.keys() if meta else 'None'}")
            elif isinstance(tx_data, (list, tuple)):
                # Handle list/tuple format - assume first element is the message
                message = tx_data[0] if tx_data else None
                logger.debug("Processing list/tuple format transaction")
            else:
                # Handle non-dict objects (e.g. Solders objects)
                message = getattr(tx_data, "message", None)
                meta = getattr(tx_data, "meta", None)
                logger.debug(f"Processing non-dict transaction, type: {type(tx_data)}")
        
            if not message:
                logger.debug(f"No message data found in handle_transaction. Data type: {type(tx_data)}")
                return
                
            logger.debug(f"Transaction message type: {type(message)}")
            
            # Get account keys
            account_keys = []
            if isinstance(message, dict):
                account_keys = message.get("accountKeys", [])
                if not account_keys and 'accounts' in message:
                    # Some formats use 'accounts' instead of 'accountKeys'
                    account_keys = message.get("accounts", [])
            elif isinstance(message, (list, tuple)):
                # Handle list/tuple format - assume these are the account keys
                account_keys = message
            else:
                # Handle non-dict message (e.g. Solders objects)
                account_keys = getattr(message, "account_keys", [])
                if not account_keys:
                    # Try alternate attribute names
                    account_keys = getattr(message, "accounts", [])
        
            if not account_keys:
                logger.debug("No account keys found in message")
                return
                
            logger.debug(f"Found {len(account_keys)} account keys")
            
            # Process instructions
            instructions = []
            if isinstance(message, dict):
                instructions = message.get("instructions", [])
            elif isinstance(message, (list, tuple)):
                # Handle list/tuple format - assume second element contains instructions
                instructions = message[1] if len(message) > 1 else []
            else:
                # Handle non-dict message
                instructions = getattr(message, "instructions", [])
        
            if not instructions:
                logger.debug("No instructions found in message")
                return
                
            logger.debug(f"Processing {len(instructions)} instructions")
            
            # Process each instruction
            for idx, instruction in enumerate(instructions):
                logger.debug(f"Processing instruction {idx+1}/{len(instructions)}")
                self._process_instruction(instruction, account_keys)
        
            # Process token balances if available
            if isinstance(meta, dict):
                pre_token_balances = meta.get("preTokenBalances", [])
                post_token_balances = meta.get("postTokenBalances", [])
                
                if pre_token_balances:
                    logger.debug(f"Processing {len(pre_token_balances)} pre-token balances")
                    self._process_token_balances(pre_token_balances, 'pre')
                if post_token_balances:
                    logger.debug(f"Processing {len(post_token_balances)} post-token balances")
                    self._process_token_balances(post_token_balances, 'post')
        
            result = self._create_response()
            logger.debug(f"Transaction processing complete. Found mint addresses: {result.get('mint_addresses', [])}")
            return result
        
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}", exc_info=True)
            return self._create_response()

    def _process_instruction(self, instruction: Any, account_keys: List[str]) -> None:
        """Process a single instruction to extract mint addresses"""
        try:
            if not instruction or not account_keys:
                logger.debug("Skipping instruction processing - missing instruction or account keys")
                return
                
            # Get program ID using multiple methods
            program_id = None
            instruction_data = {}
            
            logger.debug("Starting program ID extraction...")
            logger.debug(f"Instruction type: {type(instruction)}")
            
            # Method 1: Handle dictionary-type instructions with programIdIndex
            if isinstance(instruction, dict):
                try:
                    if 'programIdIndex' in instruction:
                        program_idx = instruction['programIdIndex']
                        if isinstance(program_idx, int) and program_idx < len(account_keys):
                            program_id = str(account_keys[program_idx])
                            logger.debug(f"Method 1 - Program ID from index: {program_id}")
                except Exception as e:
                    logger.debug(f"Error getting program_id from programIdIndex: {e}")
            
            # Method 2: Check message header
            if not program_id and hasattr(instruction, 'message') and hasattr(instruction.message, 'header'):
                try:
                    header = instruction.message.header
                    if hasattr(header, 'program_ids') and header.program_ids:
                        program_id = str(header.program_ids[0])
                        logger.debug(f"Method 2 - Message header: {program_id}")
                except Exception as e:
                    logger.debug(f"Error getting program_id from message header: {e}")
            
            # Method 3: Direct program_id attribute
            if not program_id and hasattr(instruction, 'program_id'):
                try:
                    program_id = str(instruction.program_id)
                    logger.debug(f"Method 3 - Direct attribute: {program_id}")
                except Exception as e:
                    logger.debug(f"Error getting direct program_id: {e}")
            
            # Method 4: Program ID from parsed data
            if not program_id and hasattr(instruction, 'parsed'):
                try:
                    parsed = instruction.parsed
                    if isinstance(parsed, dict):
                        # Check direct program field
                        if 'program' in parsed:
                            program_id = str(parsed['program'])
                            logger.debug(f"Method 4a - Parsed program field: {program_id}")
                        # Check nested info.program field
                        elif 'info' in parsed and isinstance(parsed['info'], dict):
                            info = parsed['info']
                            if 'program' in info:
                                program_id = str(info['program'])
                                logger.debug(f"Method 4b - Parsed info program field: {program_id}")
                except Exception as e:
                    logger.debug(f"Error parsing instruction data: {e}")
            
            # Method 5: Program ID from program index
            if not program_id and hasattr(instruction, 'program'):
                try:
                    program_idx = getattr(instruction, 'program')
                    if isinstance(program_idx, int) and program_idx < len(account_keys):
                        program_id = str(account_keys[program_idx])
                        logger.debug(f"Method 5 - Program index: {program_id}")
                except Exception as e:
                    logger.debug(f"Error getting program_id from index: {e}")
            
            # Method 6: Check inner instructions
            if not program_id and hasattr(instruction, 'inner_instructions'):
                try:
                    inner_instructions = instruction.inner_instructions
                    if inner_instructions and len(inner_instructions) > 0:
                        for inner in inner_instructions:
                            if hasattr(inner, 'program_id'):
                                program_id = str(inner.program_id)
                                logger.debug(f"Method 6 - Inner instruction: {program_id}")
                                break
                except Exception as e:
                    logger.debug(f"Error checking inner instructions: {e}")

            if not program_id:
                logger.warning("Could not determine program ID for instruction")
                return
                
            # Validate program ID format
            if program_id:
                try:
                    # Convert to string if needed
                    if not isinstance(program_id, str):
                        logger.warning(f"Program ID is not a string: {type(program_id)}")
                        program_id = str(program_id)
                    
                    # Basic format validation
                    if len(program_id) < 32 or len(program_id) > 44:
                        logger.warning(f"Program ID has invalid length: {len(program_id)}")
                        program_id = None
                    elif not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in program_id):
                        logger.warning(f"Program ID contains invalid characters")
                        program_id = None
                except Exception as e:
                    logger.warning(f"Error validating program ID: {e}")
                    program_id = None
            
            # Process token program instructions
            if program_id in ['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb']:
                logger.debug(f"Found token program instruction: {program_id}")
                self._process_token_instruction(instruction, account_keys)

            # Process associated token program instructions
            elif program_id == 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL':
                logger.debug("Found associated token program instruction")
                self._process_associated_token_instruction(instruction, account_keys)

            # Process metadata program instructions
            elif program_id == 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s':
                logger.debug("Found metadata program instruction")
                self._process_metadata_instruction(instruction, account_keys)
                    
            # Process Jupiter program instructions
            elif program_id == 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4':
                logger.debug("Found Jupiter program instruction")
                self._process_jupiter_instruction(instruction, account_keys)
            else:
                # For unknown programs, try to extract mints from instruction data
                self._process_unknown_instruction(instruction, account_keys)
                            
        except Exception as e:
            logger.error(f"Error processing instruction: {str(e)}", exc_info=True)
            self.errors.append(f"Error processing instruction: {str(e)}")

    def _process_token_instruction(self, instruction: Any, account_keys: List[str]) -> None:
        """Process a token program instruction"""
        try:
            # Get program ID and data
            program_id = self._get_program_id_from_instruction(instruction, account_keys)
            if not program_id:
                return

            # Skip if not a token program
            if program_id not in [
                'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
                'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',  # Token-2022
            ]:
                return

            # Extract accounts from instruction
            accounts = instruction.get('accounts', [])
            if not accounts:
                return

            # Check instruction data for potential mint operations
            instruction_data = instruction.get('data')
            if not instruction_data:
                return

            # Process mint-related accounts
            for idx, account in enumerate(accounts):
                if not isinstance(account, int):
                    continue
                    
                address = account_keys[account] if account < len(account_keys) else None
                if not address:
                    continue

                # Check if this could be a mint address
                if self._is_valid_mint_address(address):
                    # Look for mint initialization or token creation patterns
                    if idx == 0 and len(accounts) >= 2:  # First account in mint instructions is often the mint
                        self._add_mint_address(address, f"token_program_mint_{program_id}")
                        self.logger.debug(f"Found potential mint address from token program: {address}")

        except Exception as e:
            self.logger.error(f"Error processing token instruction: {str(e)}")
            self.errors.append(f"Error processing token instruction: {str(e)}")

    def _process_instruction(self, instruction: Any, account_keys: List[str]) -> None:
        """Process a single instruction to extract mint addresses"""
        try:
            if not isinstance(instruction, dict):
                return

            program_id = self._get_program_id_from_instruction(instruction, account_keys)
            if not program_id:
                return

            self.logger.debug(f"Processing instruction with program ID: {program_id}")

            # Skip system programs
            if self._is_system_program(program_id):
                self.logger.debug(f"Skipping mint detection for system program: {program_id}")
                return

            # Process token program instructions
            if program_id in [
                'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
                'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',  # Token-2022
            ]:
                self.logger.debug(f"Found token program instruction: {program_id}")
                self._process_token_instruction(instruction, account_keys)
                return

            # Process associated token program instructions
            if program_id == 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL':
                self.logger.debug("Found associated token program instruction")
                accounts = instruction.get('accounts', [])
                if accounts and len(accounts) >= 3:  # ATA instructions typically have mint as 3rd account
                    mint_idx = accounts[2] if isinstance(accounts[2], int) else None
                    if mint_idx is not None and mint_idx < len(account_keys):
                        mint_address = account_keys[mint_idx]
                        if self._is_valid_mint_address(mint_address):
                            self._add_mint_address(mint_address, "associated_token_program")
                            self.logger.debug(f"Found potential mint address from ATA program: {mint_address}")
                return

            # Check all accounts in the instruction for potential mint addresses
            accounts = instruction.get('accounts', [])
            for account in accounts:
                if not isinstance(account, int) or account >= len(account_keys):
                    continue
                    
                address = account_keys[account]
                if self._is_valid_mint_address(address):
                    self._add_mint_address(address, f"instruction_{program_id}")
                    self.logger.debug(f"Found potential mint address from instruction: {address}")

        except Exception as e:
            self.logger.error(f"Error processing instruction: {str(e)}")
            self.errors.append(f"Error processing instruction: {str(e)}")

    def _process_associated_token_instruction(self, instruction: Any, account_keys: List[str]) -> None:
        """Process an associated token program instruction"""
        try:
            # Check all accounts as potential mint addresses
            if hasattr(instruction, 'accounts'):
                for account_idx in instruction.accounts:
                    if isinstance(account_idx, int) and account_idx < len(account_keys):
                        addr = str(account_keys[account_idx])
                        self._add_mint_address(addr, 'associated_token_program')

        except Exception as e:
            self.logger.error(f"Error processing associated token instruction: {str(e)}")
            self.errors.append(f"Error processing associated token instruction: {str(e)}")

    def _process_metadata_instruction(self, instruction: Any, account_keys: List[str]) -> None:
        """Process a metadata program instruction"""
        try:
            # Check all accounts as potential mint addresses
            if hasattr(instruction, 'accounts'):
                for account_idx in instruction.accounts:
                    if isinstance(account_idx, int) and account_idx < len(account_keys):
                        addr = str(account_keys[account_idx])
                        self._add_mint_address(addr, 'metadata_program')

        except Exception as e:
            self.logger.error(f"Error processing metadata instruction: {str(e)}")
            self.errors.append(f"Error processing metadata instruction: {str(e)}")

    def _process_jupiter_instruction(self, instruction: Any, account_keys: List[str]) -> None:
        """Process a Jupiter program instruction"""
        try:
            # Check instruction data for route information
            if hasattr(instruction, 'data'):
                data = instruction.data
                if isinstance(data, dict):
                    # Check for route info which contains mint addresses
                    route = data.get('route', {})
                    if isinstance(route, dict):
                        # Check input and output token mints
                        input_mint = route.get('inputMint')
                        output_mint = route.get('outputMint')
                        if input_mint:
                            self._add_mint_address(str(input_mint), 'jupiter_input')
                        if output_mint:
                            self._add_mint_address(str(output_mint), 'jupiter_output')
                        
                        # Check route markets for additional mints
                        markets = route.get('markets', [])
                        for market in markets:
                            if isinstance(market, dict):
                                mint_a = market.get('mintA')
                                mint_b = market.get('mintB')
                                if mint_a:
                                    self._add_mint_address(str(mint_a), 'jupiter_market')
                                if mint_b:
                                    self._add_mint_address(str(mint_b), 'jupiter_market')

            # Process all accounts as they may contain mint addresses
            if hasattr(instruction, 'accounts'):
                for account_idx in instruction.accounts:
                    if isinstance(account_idx, int) and account_idx < len(account_keys):
                        addr = str(account_keys[account_idx])
                        self._add_mint_address(addr, 'jupiter_account')

        except Exception as e:
            self.logger.error(f"Error processing Jupiter instruction: {str(e)}")
            self.errors.append(f"Error processing Jupiter instruction: {str(e)}")

    def _process_unknown_instruction(self, instruction: Any, account_keys: List[str]) -> None:
        """Process an unknown program instruction"""
        try:
            # Process all instruction data for potential mint addresses
            if hasattr(instruction, 'data'):
                data = instruction.data
                if isinstance(data, dict):
                    # Recursively search through all dictionary values for potential mint addresses
                    def search_dict_for_mints(d, path=''):
                        if not isinstance(d, dict):
                            return
                        for k, v in d.items():
                            if isinstance(v, str) and len(v) >= 32 and len(v) <= 44:
                                self._add_mint_address(v, f'instruction_data_{path}{k}')
                            elif isinstance(v, dict):
                                search_dict_for_mints(v, f'{path}{k}.')
                            elif isinstance(v, list):
                                for i, item in enumerate(v):
                                    if isinstance(item, dict):
                                        search_dict_for_mints(item, f'{path}{k}[{i}].')
                    
                    search_dict_for_mints(data)
                    
            # Process all accounts in the instruction
            accounts = getattr(instruction, 'accounts', []) or []
            for i, account_index in enumerate(accounts):
                if isinstance(account_index, int) and account_index < len(account_keys):
                    addr = str(account_keys[account_index])
                    # Only process accounts that look like they could be mint addresses
                    if len(addr) >= 32 and len(addr) <= 44 and not addr.startswith('1111'):
                        self.logger.debug(f"Checking account {i}: {addr}")
                        self._add_mint_address(addr, 'instruction_accounts')
                    
            # Check instruction data for potential mint references
            if hasattr(instruction, 'data'):
                data = instruction.data
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, str) and len(value) >= 32 and len(value) <= 44:
                            self.logger.debug(f"Checking data field {key}: {value}")
                            self._add_mint_address(str(value), 'instruction_data')
                            
        except Exception as e:
            self.logger.error(f"Error processing unknown instruction: {str(e)}")
            self.errors.append(f"Error processing unknown instruction: {str(e)}")

    def _add_mint_address(self, address: str, source: str) -> bool:
        """Add a mint address if it's valid and not already processed"""
        try:
            if not address:
                self.logger.debug(f"Skipping empty address from {source}")
                return False
                
            if address in self.processed_addresses:
                self.logger.debug(f"Already processed address {address} from {source}")
                return False
                
            self.processed_addresses.add(address)
            
            # Validate the address
            if not self._is_valid_mint_address(address):
                self.logger.debug(f"Invalid mint address {address} from {source}")
                return False
                
            # Check for pump tokens
            if address.lower().endswith('pump'):
                self.logger.info(f"Found pump token: {address} from {source}")
                self.pump_tokens.add(address)
            else:
                self.logger.info(f"Found mint address: {address} from {source}")
                self.mint_addresses.add(address)
                
            return True
            
        except Exception as e:
            self.logger.warning(f"Error adding mint address from {source}: {str(e)}")
            return False

    def _is_valid_mint_address(self, address: str) -> bool:
        """Validate if an address is likely to be a mint address"""
        if not address:
            return False
            
        # Filter out known system addresses and program addresses
        if address in self.SYSTEM_ADDRESSES or address in self.PROGRAM_ADDRESSES:
            return False
            
        try:
            # Check length (should be 32-44 characters)
            if len(address) < 32 or len(address) > 44:
                return False
                
            # Should not contain special characters except base58 alphabet
            if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):
                return False
                
            # Additional heuristics for pump tokens
            if 'pump' in address.lower() and not address.endswith('pump'):
                return False
                
            return True
            
        except Exception:
            return False

    def _create_response(self) -> Dict[str, Any]:
        """Create the response dictionary"""
        response = {
            'mint_addresses': list(self.mint_addresses),
            'pump_tokens': list(self.pump_tokens),
            'errors': self.errors
        }
        
        # Log summary
        self.logger.info(f"Found {len(response['mint_addresses'])} mint addresses and {len(response['pump_tokens'])} pump tokens")
        if response['errors']:
            self.logger.warning(f"Encountered {len(response['errors'])} errors during processing")
            
        return response

    def get_transaction_type(self, program_id: str) -> Optional[str]:
        """Get the transaction type for a program ID"""
        return self.PROGRAM_TYPES.get(program_id)

    def parse_transaction_for_mints(self, tx_data: Any) -> Dict[str, Any]:
        """Parse a transaction to find mint addresses and related information
        
        Args:
            tx_data: Transaction data from RPC response
            
        Returns:
            Dict containing mint addresses and transaction details
        """
        result = {
            'mint_addresses': set(),
            'transaction_type': None,
            'program_id': None,
            'errors': []
        }
        
        try:
            # Handle both Solders objects and dictionaries
            if isinstance(tx_data, dict):
                transaction = tx_data.get('transaction', {})
                meta = tx_data.get('meta', {})
            else:
                transaction = getattr(tx_data, 'transaction', None)
                meta = getattr(tx_data, 'meta', None)
                
            if not transaction:
                return result
                
            # Get message data
            if isinstance(transaction, dict):
                message = transaction.get('message', {})
            else:
                message = getattr(transaction, 'message', None)
                
            if not message:
                return result
                
            # Get account keys
            account_keys = []
            if isinstance(message, dict):
                account_keys = message.get('accountKeys', [])
                if not account_keys and 'accounts' in message:
                    # Some formats use 'accounts' instead of 'accountKeys'
                    account_keys = message.get('accounts', [])
            else:
                account_keys = getattr(message, 'account_keys', [])
                if not account_keys:
                    # Try alternate attribute names
                    account_keys = getattr(message, 'accounts', [])
            
            if not account_keys:
                return result
                
            # Process instructions
            if isinstance(message, dict):
                instructions = message.get('instructions', [])
            else:
                instructions = getattr(message, 'instructions', [])
            
            if not instructions:
                return result
                
            # Process each instruction
            for instruction in instructions:
                self._process_instruction(instruction, account_keys)
            
            # Process token balances if available
            if meta:
                pre_token_balances = meta.get('preTokenBalances', []) if isinstance(meta, dict) else getattr(meta, 'pre_token_balances', [])
                post_token_balances = meta.get('postTokenBalances', []) if isinstance(meta, dict) else getattr(meta, 'post_token_balances', [])
                
                if pre_token_balances:
                    self._process_token_balances(pre_token_balances, 'pre')
                if post_token_balances:
                    self._process_token_balances(post_token_balances, 'post')
                    
            # Add results
            result['mint_addresses'] = list(self.mint_addresses)
            result['errors'] = self.errors
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing transaction for mints: {str(e)}")
            result['errors'].append(str(e))
            return result

    def extract_mints_from_block(self, block_data: Union[Dict[str, Any], GetBlockResp], include_transactions: bool = False) -> List[Dict[str, Any]]:
        """Extract mint addresses from a block
        
        Args:
            block_data: Block data from RPC response
            include_transactions: Whether to include transaction details in response
            
        Returns:
            List of dicts containing mint addresses and optional transaction details
        """
        mints = []
        
        try:
            # Initialize response
            self._init_response_data()
            
            # Handle both Solders objects and dictionaries
            if isinstance(block_data, GetBlockResp):
                transactions = getattr(block_data, 'transactions', []) or []
            elif isinstance(block_data, dict):
                transactions = block_data.get('transactions', [])
            elif isinstance(block_data, list):
                transactions = block_data  # Direct list of transactions
            else:
                self.logger.error(f"Unsupported block data type: {type(block_data)}")
                return []

            if not transactions:
                self.logger.debug("No transactions found in block")
                return []

            # Process each transaction
            for tx_index, tx in enumerate(transactions):
                try:
                    # For dictionary format, we need to ensure we have the right structure
                    if isinstance(tx, dict):
                        # RPC responses can have different structures:
                        # 1. {transaction: {message: {...}}, meta: {...}}
                        # 2. {message: {...}, meta: {...}}
                        # 3. {transaction: {...}, meta: {...}}
                        # 4. Direct transaction object
                        
                        if 'message' in tx:
                            # Structure 2
                            tx_obj = {
                                'transaction': {
                                    'message': tx['message']
                                },
                                'meta': tx.get('meta', {})
                            }
                        elif tx.get('transaction', {}).get('message'):
                            # Structure 1
                            tx_obj = tx
                        elif isinstance(tx.get('transaction'), dict):
                            # Structure 3
                            tx_obj = {
                                'transaction': {
                                    'message': tx['transaction']
                                },
                                'meta': tx.get('meta', {})
                            }
                        else:
                            # Structure 4 - Direct transaction object
                            tx_obj = tx
                    else:
                        # Solders object - use as is
                        tx_obj = tx

                    # Process the transaction
                    tx_result = self.handle_transaction(tx_obj)

                    # Add transaction details if requested
                    if tx_result.get('mint_addresses') and include_transactions:
                        # Extract signature based on data type
                        sig = None
                        if isinstance(tx_obj, dict):
                            # Try different paths to find signature
                            if 'transaction' in tx_obj and isinstance(tx_obj['transaction'], dict):
                                sig = tx_obj['transaction'].get('signatures', [None])[0]
                            if not sig and 'signatures' in tx_obj:
                                sig = tx_obj['signatures'][0]
                        else:
                            # Handle non-dict objects
                            signatures = getattr(tx_obj, 'signatures', [])
                            sig = str(signatures[0]) if signatures else None

                        tx_result['transaction_details'] = {
                            'signature': str(sig) if sig else '',
                            'slot': block_data.get('slot') if isinstance(block_data, dict) else getattr(block_data, 'slot', None),
                            'timestamp': block_data.get('blockTime') if isinstance(block_data, dict) else getattr(block_data, 'block_time', None)
                        }
                        
                    if tx_result.get('mint_addresses'):
                        mints.append(tx_result)

                except Exception as e:
                    self.logger.error(f"Error processing transaction in block: {str(e)}")
                    continue

            return mints

        except Exception as e:
            self.logger.error(f"Error processing block: {str(e)}")
            return []

    def handle_block(self, block_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process block data and extract mint information
        
        Args:
            block_data: Block data from RPC response
            
        Returns:
            List of dicts containing mint addresses and transaction details
        """
        try:
            return self.extract_mints_from_block(block_data, include_transactions=True)
        except Exception as e:
            self.logger.error(f"Error in handle_block: {str(e)}")
            return []

    def _init_response_data(self) -> None:
        """Initialize response data"""
        self.processed_addresses = set()
        self.mint_addresses = set()
        self.pump_tokens = set()
        self.errors = []

    def is_valid_program_id(self, program_id: str) -> bool:
        """
        Validate program ID format and characteristics
        
        Args:
            program_id: The program ID to validate
            
        Returns:
            bool: True if the program ID is valid, False otherwise
        """
        # Base58 character set
        BASE58_CHARS = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
        
        try:
            # Basic format checks
            if not isinstance(program_id, str):
                self.logger.debug(f"Program ID is not a string: {type(program_id)}")
                return False
            if len(program_id) < 32 or len(program_id) > 44:
                self.logger.debug(f"Program ID has invalid length: {len(program_id)}")
                return False
            if not all(c in BASE58_CHARS for c in program_id):
                self.logger.debug(f"Program ID contains invalid characters: {program_id}")
                return False
                
            # Check against known system and program addresses
            if program_id in self.SYSTEM_ADDRESSES:
                self.logger.debug(f"Program ID is a known system address: {program_id}")
                return False
            if program_id in self.PROGRAM_ADDRESSES:
                self.logger.debug(f"Program ID is a known program address: {program_id}")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error validating program ID: {e}")
            return False

    def extract_mint_from_instruction(self, instruction: Any, account_keys: List[str]) -> Optional[str]:
        """
        Extract mint address from instruction with validation
        
        Args:
            instruction: The instruction to extract from
            account_keys: List of account keys
            
        Returns:
            Optional[str]: The mint address if found and valid, None otherwise
        """
        try:
            # Check parsed data first
            if hasattr(instruction, 'parsed'):
                parsed = instruction.parsed
                if isinstance(parsed, dict):
                    info = parsed.get('info', {})
                    mint_fields = ['mint', 'mintAuthority', 'tokenMint', 'mintAccount']
                    for field in mint_fields:
                        if field in info:
                            mint = str(info[field])
                            if self.is_valid_program_id(mint):
                                self.logger.debug(f"Found mint address in parsed data: {mint}")
                                return mint
            
            # Check accounts
            if hasattr(instruction, 'accounts'):
                for account_idx in instruction.accounts:
                    if isinstance(account_idx, int) and account_idx < len(account_keys):
                        addr = str(account_keys[account_idx])
                        if self.is_valid_program_id(addr):
                            self.logger.debug(f"Found mint address in accounts: {addr}")
                            return addr
                            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting mint from instruction: {e}")
            return None

    def is_token_mint_instruction(self, instruction: Any) -> bool:
        """
        Check if instruction is a token mint operation
        
        Args:
            instruction: The instruction to check
            
        Returns:
            bool: True if the instruction is a mint operation, False otherwise
        """
        try:
            if hasattr(instruction, 'parsed'):
                parsed = instruction.parsed
                if isinstance(parsed, dict):
                    # Check for mint-related operations
                    if parsed.get('type') in ['mintTo', 'initializeMint', 'createMint']:
                        self.logger.debug(f"Found mint operation: {parsed.get('type')}")
                        return True
                    
                    # Check for mint authority
                    info = parsed.get('info', {})
                    if 'mintAuthority' in info:
                        self.logger.debug("Found mint authority in instruction")
                        return True
                        
                    # Check for mint-related accounts
                    accounts = info.get('accounts', {})
                    mint_related = ['mint', 'tokenMint', 'mintAccount']
                    if any(acc in accounts for acc in mint_related):
                        self.logger.debug("Found mint-related accounts")
                        return True
            return False
        except Exception as e:
            self.logger.error(f"Error checking token mint instruction: {e}")
            return False

    def _add_mint_address(self, address: str, source: str) -> bool:
        """Add a mint address if it's valid and not already processed"""
        try:
            if not address:
                self.logger.debug(f"Skipping empty address from {source}")
                return False
                
            if address in self.processed_addresses:
                self.logger.debug(f"Already processed address {address} from {source}")
                return False
                
            self.processed_addresses.add(address)
            
            # Validate the address
            if not self._is_valid_mint_address(address):
                self.logger.debug(f"Invalid mint address {address} from {source}")
                return False
                
            # Check for pump tokens
            if address.lower().endswith('pump'):
                self.logger.info(f"Found pump token: {address} from {source}")
                self.pump_tokens.add(address)
            else:
                self.logger.info(f"Found mint address: {address} from {source}")
                self.mint_addresses.add(address)
                
            return True
            
        except Exception as e:
            self.logger.warning(f"Error adding mint address {address} from {source}: {str(e)}")
            return False

    def _is_valid_mint_address(self, address: str) -> bool:
        """Validate if an address is likely to be a mint address"""
        if not address:
            return False
            
        # Filter out known system addresses and program addresses
        if address in self.SYSTEM_ADDRESSES or address in self.PROGRAM_ADDRESSES:
            return False
            
        try:
            # Check length (should be 32-44 characters)
            if len(address) < 32 or len(address) > 44:
                return False
                
            # Should not contain special characters except base58 alphabet
            if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):
                return False
                
            # Additional heuristics for pump tokens
            if 'pump' in address.lower() and not address.endswith('pump'):
                return False
                
            return True
            
        except:
            return False

    def _get_program_id_from_instruction(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """Extract program ID from instruction using multiple methods"""
        try:
            # Method 1: Direct program_id field
            if 'programId' in instruction:
                return str(instruction['programId'])
                
            # Method 2: Program ID index
            if 'programIdIndex' in instruction:
                idx = instruction['programIdIndex']
                if isinstance(idx, int) and idx < len(account_keys):
                    return str(account_keys[idx])
                    
            # Method 3: Last account in accounts array
            if 'accounts' in instruction:
                accounts = instruction['accounts']
                if accounts and isinstance(accounts[-1], int) and accounts[-1] < len(account_keys):
                    return str(account_keys[accounts[-1]])
                    
            # Method 4: Parsed data program field
            if 'parsed' in instruction:
                parsed = instruction['parsed']
                if isinstance(parsed, dict):
                    if 'program' in parsed:
                        return str(parsed['program'])
                    if 'info' in parsed and isinstance(parsed['info'], dict):
                        info = parsed['info']
                        if 'program' in info:
                            return str(info['program'])
                            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting program ID: {str(e)}")
            return None

    def _is_system_program(self, program_id: str) -> bool:
        """Check if a program ID is a known system program"""
        if not program_id:
            return False
            
        try:
            # Check if program is in our known system programs list
            if program_id in self.SYSTEM_ADDRESSES:
                return True
                
            # Check if program is in our program types mapping
            program_type = self.PROGRAM_TYPES.get(program_id)
            if program_type in ['system', 'compute_budget', 'vote', 'stake', 'loader', 'config']:
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking system program: {str(e)}")
            return False

    def handle_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block response to extract mint information"""
        start_time = time.time()
        
        if not block_data or not isinstance(block_data, dict):
            logger.error("Invalid block data format")
            return self._create_response(errors=["Invalid block data format"])

        try:
            # Extract transactions safely
            transactions = block_data.get("transactions", [])
            if transactions:
                for tx_data in transactions:
                    self.handle_transaction(tx_data)

            return self._create_response()

        except Exception as e:
            error_msg = f"Error processing block: {str(e)}"
            logger.error(error_msg)
            return self._create_response(errors=[error_msg])

    def _process_token_balances(self, balances: List[Dict], tx_index: int, balance_type: str,
                              processed_addresses: Set[str], mint_addresses: Set[str], 
                              pump_tokens: Set[str]) -> bool:
        """Process token balances to extract mint addresses"""
        found_mints = False
        
        for balance in balances:
            if not isinstance(balance, dict):
                continue
                
            try:
                mint = balance.get('mint')
                if not mint or mint in processed_addresses:
                    continue
                    
                processed_addresses.add(mint)
                
                if self._is_valid_mint_address(mint):
                    if mint.lower().endswith('pump'):
                        pump_tokens.add(mint)
                        logger.info(f"Found pump token: {mint} in {balance_type} balance (tx {tx_index})")
                    else:
                        mint_addresses.add(mint)
                        logger.info(f"Found mint in {balance_type} balance: {mint} (tx {tx_index})")
                    found_mints = True
                    
            except Exception as e:
                logger.error(f"Error processing token balance: {str(e)}")
                
        return found_mints

    def _process_instructions(self, instructions: List[Dict], account_keys: List[str], tx_index: int,
                            processed_addresses: Set[str], mint_addresses: Set[str], 
                            pump_tokens: Set[str]) -> bool:
        """Process transaction instructions to extract mint addresses"""
        found_mints = False
        
        for instr_index, instr in enumerate(instructions):
            if not isinstance(instr, dict):
                continue
                
            try:
                program_id = self._extract_program_id(instr, account_keys)
                if not program_id:
                    continue

                # Process token program instructions
                if program_id in [self.TOKEN_PROGRAM_ID, self.TOKEN_2022_PROGRAM_ID]:
                    # Check first few accounts for mint
                    for i in range(min(3, len(account_keys))):
                        account = account_keys[i]
                        if account not in processed_addresses and self._is_valid_mint_address(account):
                            processed_addresses.add(account)
                            if account.lower().endswith('pump'):
                                pump_tokens.add(account)
                                logger.info(f"Found pump token in token program: {account} (tx {tx_index})")
                            else:
                                mint_addresses.add(account)
                                logger.info(f"Found mint in token program: {account} (tx {tx_index})")
                            found_mints = True

                # Process associated token program
                elif program_id == self.ASSOCIATED_TOKEN_PROGRAM_ID:
                    accounts = instr.get('accounts', [])
                    if len(accounts) >= 3:
                        mint_index = accounts[2]
                        if isinstance(mint_index, int) and mint_index < len(account_keys):
                            mint = account_keys[mint_index]
                            if mint not in processed_addresses and self._is_valid_mint_address(mint):
                                processed_addresses.add(mint)
                                if mint.lower().endswith('pump'):
                                    pump_tokens.add(mint)
                                    logger.info(f"Found pump token in ATA: {mint} (tx {tx_index})")
                                else:
                                    mint_addresses.add(mint)
                                    logger.info(f"Found mint in ATA: {mint} (tx {tx_index})")
                                found_mints = True
            except Exception as e:
                logger.error(f"Error processing instruction {instr_index} in tx {tx_index}: {str(e)}")
                continue
                
        return found_mints

    def _extract_program_id(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """Extract program ID from instruction using multiple methods"""
        try:
            # Method 1: Direct program_id field
            if 'programId' in instruction:
                return str(instruction['programId'])
                
            # Method 2: Program ID index
            if 'programIdIndex' in instruction:
                idx = instruction['programIdIndex']
                if isinstance(idx, int) and idx < len(account_keys):
                    return str(account_keys[idx])
                    
            # Method 3: Last account in accounts array
            if 'accounts' in instruction:
                accounts = instruction['accounts']
                if accounts and isinstance(accounts[-1], int) and accounts[-1] < len(account_keys):
                    return str(account_keys[accounts[-1]])
                    
            # Method 4: Parsed data program field
            if 'parsed' in instruction:
                parsed = instruction['parsed']
                if isinstance(parsed, dict):
                    if 'program' in parsed:
                        return str(parsed['program'])
                    if 'info' in parsed and isinstance(parsed['info'], dict):
                        info = parsed['info']
                        if 'program' in info:
                            return str(info['program'])
                            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting program ID: {str(e)}")
            return None

    def _is_valid_mint_address(self, address: str) -> bool:
        """Validate if an address is likely to be a mint address"""
        if not address:
            return False
            
        # Filter out known system/program addresses
        if address in self.SYSTEM_ADDRESSES:
            return False
            
        try:
            # Check length (should be 32-44 characters)
            if len(address) < 32 or len(address) > 44:
                return False
                
            # Should only contain base58 characters
            if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):
                return False
                
            # Additional validation for pump tokens
            if 'pump' in address.lower() and not address.endswith('pump'):
                return False
                
            return True
            
        except Exception:
            return False

    def _categorize_transaction(self, tx: Dict[str, Any]) -> List[str]:
        """Categorize a transaction based on its contents"""
        tx_types = set()
        
        try:
            message = tx.get('transaction', {}).get('message', {})
            if not message:
                return ['other']
                
            # Get program IDs from instructions
            instructions = message.get('instructions', [])
            for instr in instructions:
                if not isinstance(instr, dict):
                    continue
                    
                program_id = self._extract_program_id(instr, message.get('accountKeys', []))
                if program_id:
                    if program_id in self.PROGRAM_TYPES:
                        tx_types.add(self.PROGRAM_TYPES[program_id])
                        
            # Add NFT type if metadata programs found
            if any(pid in self.NFT_PROGRAM_IDS for pid in 
                  [self._extract_program_id(i, message.get('accountKeys', [])) for i in instructions 
                   if isinstance(i, dict)]):
                tx_types.add('nft')
                
            # Default to other if no types found
            if not tx_types:
                tx_types.add('other')
                
        except Exception as e:
            logger.error(f"Error categorizing transaction: {str(e)}")
            tx_types.add('other')
            
        return list(tx_types)
