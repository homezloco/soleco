"""
NFT handler for processing NFT-specific transactions.
"""
from typing import Dict, Any, List, Optional
from .base_handler import BaseHandler
import logging

logger = logging.getLogger(__name__)

class NFTHandler(BaseHandler):
    """Handler for NFT-specific responses"""
    
    def __init__(self):
        super().__init__()
        self.nft_stats = {
            "total_transactions": 0,
            "sales": [],
            "mints": [],
            "transfers": [],
            "listings": [],
            "delistings": [],
            "marketplace_volume": {},
            "royalty_payments": []
        }
        self.metadata_updates = []
        self._seen_signatures = set()
        
    def process_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Process an NFT transaction"""
        if not transaction or transaction.get("signature") in self._seen_signatures:
            return {}
            
        try:
            result = super().process_transaction(transaction)
            self.nft_stats["total_transactions"] += 1
            
            # Track marketplace interactions
            marketplace = self._get_marketplace(result)
            if marketplace:
                self._track_marketplace_activity(result, marketplace)
                
            # Track metadata updates
            if self._is_metadata_update(result):
                self._track_metadata_update(result)
                
            self._seen_signatures.add(transaction.get("signature"))
            return result
            
        except Exception as e:
            logger.error(f"Error processing NFT transaction: {e}")
            return {}
        
    def _get_marketplace(self, tx_details: Dict[str, Any]) -> Optional[str]:
        """Identify the marketplace from transaction details"""
        MAGIC_EDEN_V2 = "M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K"
        OPENSEA = "hausS13jsjafwWwGqZTUQRmWyvyxn9EQpqMwV1PBBmk"
        SOLANART = "CJsLwbP1iu5DuUikHEJnLfANgKy6stB2uFgvBBHoyxwz"
        
        for inst in tx_details.get("instructions", []):
            program_id = inst.get("program_id")
            if program_id:
                if program_id == MAGIC_EDEN_V2:
                    return "Magic Eden"
                elif program_id == OPENSEA:
                    return "OpenSea"
                elif program_id == SOLANART:
                    return "Solanart"
        return None
        
    def _track_marketplace_activity(
        self,
        tx_details: Dict[str, Any],
        marketplace: str
    ) -> None:
        """Track NFT marketplace activity"""
        signature = tx_details.get("signature")
        timestamp = tx_details.get("blockTime")
        
        # Detect sale
        if self._is_sale(tx_details):
            sale_info = self._extract_sale_info(tx_details)
            if sale_info:
                self.nft_stats["sales"].append({
                    "signature": signature,
                    "timestamp": timestamp,
                    "marketplace": marketplace,
                    **sale_info
                })
                
                # Track marketplace volume
                if marketplace not in self.nft_stats["marketplace_volume"]:
                    self.nft_stats["marketplace_volume"][marketplace] = 0
                self.nft_stats["marketplace_volume"][marketplace] += \
                    sale_info["price"]
                    
                # Track royalties
                if "royalty" in sale_info:
                    self.nft_stats["royalty_payments"].append({
                        "signature": signature,
                        "timestamp": timestamp,
                        "amount": sale_info["royalty"],
                        "recipient": sale_info.get("royalty_recipient")
                    })
                    
        # Detect listing/delisting
        elif self._is_listing(tx_details):
            self.nft_stats["listings"].append({
                "signature": signature,
                "timestamp": timestamp,
                "marketplace": marketplace,
                "price": self._extract_listing_price(tx_details)
            })
        elif self._is_delisting(tx_details):
            self.nft_stats["delistings"].append({
                "signature": signature,
                "timestamp": timestamp,
                "marketplace": marketplace
            })
            
    def _is_sale(self, tx_details: Dict[str, Any]) -> bool:
        """Detect if transaction is an NFT sale"""
        if not tx_details.get("meta"):
            return False
            
        # Check for token transfer and SOL transfer
        pre_balances = tx_details["meta"].get("preBalances", [])
        post_balances = tx_details["meta"].get("postBalances", [])
        
        return len(pre_balances) > 0 and len(post_balances) > 0 and \
               any(post > pre for pre, post in zip(pre_balances, post_balances))
               
    def _extract_sale_info(self, tx_details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract sale information from transaction"""
        try:
            meta = tx_details.get("meta", {})
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])
            
            if not pre_balances or not post_balances:
                return None
                
            # Find the seller (balance increased)
            for i, (pre, post) in enumerate(zip(pre_balances, post_balances)):
                if post > pre:
                    price = post - pre
                    return {
                        "price": price,
                        "seller": tx_details["message"]["accountKeys"][i],
                        "buyer": tx_details["message"]["accountKeys"][0],
                        "royalty": price * 0.05  # Assuming 5% royalty
                    }
                    
            return None
            
        except Exception as e:
            logger.error(f"Error extracting sale info: {e}")
            return None
            
    def _is_listing(self, tx_details: Dict[str, Any]) -> bool:
        """Detect if transaction is an NFT listing"""
        for inst in tx_details.get("instructions", []):
            if inst.get("data", "").startswith("list"):
                return True
        return False
        
    def _is_delisting(self, tx_details: Dict[str, Any]) -> bool:
        """Detect if transaction is an NFT delisting"""
        for inst in tx_details.get("instructions", []):
            if inst.get("data", "").startswith("delist"):
                return True
        return False
        
    def _extract_listing_price(self, tx_details: Dict[str, Any]) -> Optional[int]:
        """Extract listing price from transaction"""
        for inst in tx_details.get("instructions", []):
            if inst.get("data", "").startswith("list"):
                # Price is typically in the instruction data
                # Format depends on marketplace
                try:
                    # Basic extraction, can be enhanced based on marketplace
                    data = inst.get("data", "")
                    if len(data) > 8:  # Minimum length for price data
                        # Extract price from data based on marketplace format
                        return int(data[8:], 16)  # Example: hex to int
                except:
                    pass
        return None
        
    def _is_metadata_update(self, tx_details: Dict[str, Any]) -> bool:
        """Detect if transaction updates NFT metadata"""
        METAPLEX = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
        return any(
            inst.get("program_id") == METAPLEX
            for inst in tx_details.get("instructions", [])
        )
        
    def _track_metadata_update(self, tx_details: Dict[str, Any]) -> None:
        """Track NFT metadata updates"""
        self.metadata_updates.append({
            "signature": tx_details.get("signature"),
            "timestamp": tx_details.get("blockTime"),
            "mint": self._extract_mint_address(tx_details)
        })
        
    def _extract_mint_address(self, tx_details: Dict[str, Any]) -> Optional[str]:
        """Extract NFT mint address from transaction"""
        METAPLEX = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
        for inst in tx_details.get("instructions", []):
            if inst.get("program_id") == METAPLEX:
                # Mint address is typically the first account
                accounts = inst.get("accounts", [])
                if accounts:
                    return accounts[0]
        return None
        
    def _finalize_result(self) -> Dict[str, Any]:
        """Finalize and return the handler's results"""
        result = super()._finalize_result()
        result.update({
            "nft_types": {
                "sales": len(self.nft_stats["sales"]),
                "listings": len(self.nft_stats["listings"]),
                "delistings": len(self.nft_stats["delistings"]),
                "metadata_updates": len(self.metadata_updates)
            },
            "marketplace_volume": self.nft_stats["marketplace_volume"],
            "recent_sales": sorted(
                self.nft_stats["sales"],
                key=lambda x: x["timestamp"],
                reverse=True
            )[:10],
            "metadata_updates": self.metadata_updates
        })
        return result

    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block to analyze NFT operations.
        
        This method analyzes all transactions in a block to track NFT operations
        including sales, mints, transfers, listings, and metadata updates.
        
        Args:
            block_data: Block data from Solana RPC
            
        Returns:
            Dict containing NFT operation results and statistics
        """
        try:
            if not block_data or not isinstance(block_data, dict):
                logger.warning("Invalid block data format")
                return None
                
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.debug("No transactions in block")
                return None
                
            # Reset block-level tracking
            block_stats = {
                "total_transactions": 0,
                "sales": [],
                "mints": [],
                "transfers": [],
                "listings": [],
                "delistings": [],
                "marketplace_volume": {},
                "royalty_payments": [],
                "metadata_updates": []
            }
            
            # Process each transaction
            for tx in transactions:
                try:
                    result = await self.process(tx)
                    if not result or not isinstance(result, dict):
                        continue
                        
                    # Update block stats
                    block_stats["total_transactions"] += 1
                    
                    # Track sales
                    if result.get("sale"):
                        block_stats["sales"].append(result["sale"])
                        marketplace = result.get("marketplace")
                        if marketplace:
                            if marketplace not in block_stats["marketplace_volume"]:
                                block_stats["marketplace_volume"][marketplace] = 0
                            block_stats["marketplace_volume"][marketplace] += result["sale"].get("amount", 0)
                    
                    # Track mints
                    if result.get("mint"):
                        block_stats["mints"].append(result["mint"])
                    
                    # Track transfers
                    if result.get("transfer"):
                        block_stats["transfers"].append(result["transfer"])
                    
                    # Track listings/delistings
                    if result.get("listing"):
                        block_stats["listings"].append(result["listing"])
                    if result.get("delisting"):
                        block_stats["delistings"].append(result["delisting"])
                    
                    # Track royalties
                    if result.get("royalty"):
                        block_stats["royalty_payments"].append(result["royalty"])
                    
                    # Track metadata updates
                    if result.get("metadata_update"):
                        block_stats["metadata_updates"].append(result["metadata_update"])
                        
                except Exception as e:
                    logger.error(f"Error processing transaction: {str(e)}")
                    self.stats.update_error_count(type(e).__name__)
                    
            # Calculate summary statistics
            summary_stats = {
                "total_transactions": block_stats["total_transactions"],
                "total_sales": len(block_stats["sales"]),
                "total_mints": len(block_stats["mints"]),
                "total_transfers": len(block_stats["transfers"]),
                "total_listings": len(block_stats["listings"]),
                "total_delistings": len(block_stats["delistings"]),
                "total_metadata_updates": len(block_stats["metadata_updates"]),
                "total_volume": sum(
                    sale.get("amount", 0) 
                    for sale in block_stats["sales"]
                ),
                "marketplace_breakdown": {
                    marketplace: {
                        "volume": volume,
                        "transactions": len([
                            s for s in block_stats["sales"] 
                            if s.get("marketplace") == marketplace
                        ])
                    }
                    for marketplace, volume in block_stats["marketplace_volume"].items()
                }
            }
            
            return {
                'slot': block_data.get('slot'),
                'nft_operations': block_stats,
                'statistics': summary_stats
            }
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return {
                'error': str(e),
                'statistics': {
                    'total_transactions': 0,
                    'total_sales': 0,
                    'total_mints': 0,
                    'total_transfers': 0,
                    'total_listings': 0,
                    'total_delistings': 0,
                    'total_metadata_updates': 0,
                    'total_volume': 0,
                    'marketplace_breakdown': {}
                }
            }
