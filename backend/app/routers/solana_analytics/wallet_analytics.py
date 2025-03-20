from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Path
from solana.rpc.commitment import Commitment

from app.utils.solana_query import SolanaQueryHandler
from app.utils.solana_rpc import get_connection_pool
from app.utils.handlers.wallet_response_handler import WalletResponseHandler
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/wallet",
    tags=["Soleco"]
)

class WalletExtractor:
    """Handles extraction and processing of wallet-related data from the Solana blockchain."""
    
    def __init__(self, solana_query: SolanaQueryHandler):
        self.solana_query = solana_query
        self.response_handler = WalletResponseHandler()
        
    async def get_wallet_transactions(
        self,
        wallet_address: str,
        before: Optional[str] = None,
        limit: int = 100,
        commitment: str = "confirmed"
    ) -> List[Dict]:
        """
        Retrieve transactions for a specific wallet address.
        
        Args:
            wallet_address: The wallet address to query
            before: Optional signature to start query from
            limit: Maximum number of transactions to return
            commitment: The commitment level to use
            
        Returns:
            List of processed transaction data
        """
        try:
            logger.debug(f"Fetching transactions for wallet {wallet_address}")
            
            signatures = await self.solana_query.get_signatures_for_address(
                wallet_address,
                before=before,
                limit=limit,
                commitment=commitment
            )
            
            if not signatures:
                logger.info(f"No transactions found for wallet {wallet_address}")
                return []
                
            transactions = []
            for sig in signatures:
                tx = await self.solana_query.get_transaction(
                    sig.signature,
                    commitment=commitment
                )
                if tx:
                    processed_tx = self.response_handler.process_transaction(tx)
                    transactions.append(processed_tx)
                    
            logger.debug(f"Successfully processed {len(transactions)} transactions for {wallet_address}")
            return transactions
            
        except Exception as e:
            logger.error(f"Error fetching wallet transactions: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch wallet transactions: {str(e)}"
            )
            
    async def analyze_activity_range(
        self,
        wallet_address: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """
        Analyze wallet activity over a specific time range.
        
        Args:
            wallet_address: The wallet address to analyze
            start_time: Start of the analysis period
            end_time: End of the analysis period
            
        Returns:
            Dictionary containing activity analysis results
        """
        try:
            logger.debug(f"Analyzing activity range for wallet {wallet_address}")
            
            transactions = await self.get_wallet_transactions(
                wallet_address,
                limit=1000  # Increased limit for range analysis
            )
            
            # Filter transactions within time range
            filtered_txs = [
                tx for tx in transactions
                if start_time <= datetime.fromtimestamp(tx['blockTime']) <= end_time
            ]
            
            # Analyze activity patterns
            analysis = {
                'total_transactions': len(filtered_txs),
                'unique_programs': len(set(tx['program'] for tx in filtered_txs)),
                'total_sol_transferred': sum(tx['sol_transfer'] for tx in filtered_txs if 'sol_transfer' in tx),
                'gas_usage': sum(tx['gas_used'] for tx in filtered_txs if 'gas_used' in tx),
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
            }
            
            logger.debug(f"Completed activity range analysis for {wallet_address}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing activity range: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to analyze activity range: {str(e)}"
            )
            
    async def get_wallet_portfolio(self, wallet_address: str) -> Dict:
        """
        Get current token portfolio for a wallet address.
        
        Args:
            wallet_address: The wallet address to query
            
        Returns:
            Dictionary containing token balances and metadata
        """
        try:
            logger.debug(f"Fetching portfolio for wallet {wallet_address}")
            
            token_accounts = await self.solana_query.get_token_accounts_by_owner(
                wallet_address
            )
            
            portfolio = {
                'tokens': [],
                'total_value_usd': 0.0
            }
            
            for account in token_accounts:
                token_data = await self.solana_query.get_token_data(
                    account.mint
                )
                if token_data:
                    portfolio['tokens'].append({
                        'mint': account.mint,
                        'balance': account.balance,
                        'decimals': token_data.decimals,
                        'symbol': token_data.symbol
                    })
                    
            logger.debug(f"Successfully retrieved portfolio for {wallet_address}")
            return portfolio
            
        except Exception as e:
            logger.error(f"Error fetching wallet portfolio: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch wallet portfolio: {str(e)}"
            )

class WalletAnalytics:
    """Handles wallet analytics and activity tracking."""
    
    def __init__(self, solana_query: SolanaQueryHandler):
        self.wallet_extractor = WalletExtractor(solana_query)
        
    async def analyze_wallet_activity(
        self,
        wallet_address: str,
        timeframe: int = 24
    ) -> Dict:
        """
        Analyze recent wallet activity and portfolio.
        
        Args:
            wallet_address: The wallet address to analyze
            timeframe: Hours of activity to analyze
            
        Returns:
            Dictionary containing activity analysis and portfolio data
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=timeframe)
            
            # Get activity analysis
            activity = await self.wallet_extractor.analyze_activity_range(
                wallet_address,
                start_time,
                end_time
            )
            
            # Get current portfolio
            portfolio = await self.wallet_extractor.get_wallet_portfolio(
                wallet_address
            )
            
            return {
                'activity': activity,
                'portfolio': portfolio,
                'timeframe_hours': timeframe
            }
            
        except Exception as e:
            logger.error(f"Error analyzing wallet activity: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to analyze wallet activity: {str(e)}"
            )

wallet_analytics = None

@router.on_event("startup")
async def startup_event():
    global wallet_analytics
    connection_pool = await get_connection_pool()
    wallet_analytics = WalletAnalytics(SolanaQueryHandler(connection_pool))

@router.get("/activity/{wallet_address}")
async def get_wallet_activity(
    wallet_address: str = Path(..., description="Wallet address to analyze"),
    timeframe: int = Query(
        24,
        description="Timeframe in hours to analyze",
        ge=1,
        le=168
    )
):
    """
    Get comprehensive wallet activity analysis.
    
    Parameters:
    - wallet_address: The wallet address to analyze
    - timeframe: Analysis timeframe in hours
    """
    return await wallet_analytics.analyze_wallet_activity(wallet_address, timeframe)

@router.get("/frequency/{wallet_address}")
async def get_transaction_frequency(
    wallet_address: str = Path(..., description="Wallet address to analyze"),
    timeframe: int = Query(
        168,
        description="Timeframe in hours to analyze",
        ge=1,
        le=720
    )
):
    """
    Analyze transaction frequency patterns.
    
    Parameters:
    - wallet_address: The wallet address to analyze
    - timeframe: Analysis timeframe in hours
    """
    # TODO: Implement transaction frequency analysis

@router.get("/gas/{wallet_address}")
async def get_gas_patterns(
    wallet_address: str = Path(..., description="Wallet address to analyze"),
    timeframe: int = Query(
        24,
        description="Timeframe in hours to analyze",
        ge=1,
        le=168
    )
):
    """
    Analyze gas usage patterns.
    
    Parameters:
    - wallet_address: The wallet address to analyze
    - timeframe: Analysis timeframe in hours
    """
    # TODO: Implement gas pattern analysis
