from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ..utils.solana_query import SolanaQueryHandler
from ..utils.solana_response import SolanaResponseManager, EndpointConfig
from ..utils.solana_rpc import SolanaConnectionPool, get_connection_pool
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/program_analytics.log'
)
logger = logging.getLogger(__name__)

router = APIRouter()

class ProgramResponseHandler(SolanaResponseManager):
    """Handler for program-specific transaction responses"""
    
    def __init__(self):
        config = EndpointConfig(
            url="https://api.mainnet-beta.solana.com",
            requests_per_second=40.0,
            burst_limit=80,
            max_retries=3,
            retry_delay=1.0
        )
        super().__init__(config)
        self.activity_stats = {
            "total_transactions": 0,
            "unique_callers": set(),
            "instruction_counts": {},
            "compute_budget_usage": [],
            "error_rate": 0,
            "success_rate": 0
        }

    def process_transaction(self, transaction: Dict) -> Dict:
        """Process a single transaction"""
        self.activity_stats["total_transactions"] += 1
        
        tx_details = super().process_transaction(transaction)
        
        # Track unique callers
        if "signers" in transaction:
            self.activity_stats["unique_callers"].update(transaction["signers"])
        
        # Track instruction types and compute budget
        for inst in tx_details.get("instructions", []):
            inst_type = inst.get("type", "unknown")
            self.activity_stats["instruction_counts"][inst_type] = \
                self.activity_stats["instruction_counts"].get(inst_type, 0) + 1
            
            if "computeUnitsConsumed" in inst:
                self.activity_stats["compute_budget_usage"].append(
                    inst["computeUnitsConsumed"]
                )

        return tx_details

class ProgramAnalytics:
    def __init__(self):
        self.connection_pool = get_connection_pool()
        self.query_handler = SolanaQueryHandler(self.connection_pool)
        self.response_handler = ProgramResponseHandler()

    async def analyze_program_activity(
        self,
        program_id: str,
        start_slot: Optional[int] = None,
        end_slot: Optional[int] = None
    ) -> Dict:
        """Analyze program activity within specified slot range."""
        try:
            # Get transactions for the program
            txs = await self.query_handler.get_program_transactions(
                program_id,
                start_slot,
                end_slot,
                batch_size=20
            )
            
            for tx in txs:
                self.response_handler.process_transaction(tx)
            
            # Prepare stats for return
            stats = self.response_handler.activity_stats.copy()
            stats["unique_callers"] = list(stats["unique_callers"])
            
            if stats["compute_budget_usage"]:
                stats["avg_compute_units"] = sum(stats["compute_budget_usage"]) / len(stats["compute_budget_usage"])
            else:
                stats["avg_compute_units"] = 0
                
            return stats

        except Exception as e:
            logger.error(f"Error analyzing program activity: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_program_dependencies(self, program_id: str) -> Dict:
        """Analyze program dependencies and interactions."""
        try:
            # Get recent program transactions
            txs = await self.query_handler.get_program_transactions(
                program_id,
                batch_size=20
            )
            
            dependencies = {
                "called_by": set(),
                "calls_to": set(),
                "token_programs": set(),
                "system_interactions": False
            }

            for tx in txs:
                tx_details = self.response_handler.process_transaction(tx)
                
                # Analyze instruction flow
                for inst in tx_details.get("instructions", []):
                    program = inst.get("program_id")
                    if program != program_id:
                        if program == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                            dependencies["token_programs"].add("Token Program")
                        elif program == "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL":
                            dependencies["token_programs"].add("Associated Token Program")
                        elif program == "11111111111111111111111111111111":
                            dependencies["system_interactions"] = True
                        else:
                            dependencies["calls_to"].add(program)

            # Convert sets to lists for JSON serialization
            dependencies["called_by"] = list(dependencies["called_by"])
            dependencies["calls_to"] = list(dependencies["calls_to"])
            dependencies["token_programs"] = list(dependencies["token_programs"])

            return dependencies

        except Exception as e:
            logger.error(f"Error analyzing program dependencies: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

program_analytics = ProgramAnalytics()

@router.get("/analyze/{program_id}")
async def analyze_program(
    program_id: str,
    start_slot: Optional[int] = None,
    end_slot: Optional[int] = None
):
    """
    Analyze program activity and dependencies.
    
    Parameters:
    - program_id: The program ID to analyze
    - start_slot: Optional starting slot for analysis
    - end_slot: Optional ending slot for analysis
    """
    activity = await program_analytics.analyze_program_activity(
        program_id,
        start_slot,
        end_slot
    )
    dependencies = await program_analytics.get_program_dependencies(program_id)
    
    return {
        "program_id": program_id,
        "activity_stats": activity,
        "dependencies": dependencies,
        "analysis_time": datetime.utcnow().isoformat()
    }

@router.get("/trending")
async def get_trending_programs(
    timeframe: int = Query(24, description="Timeframe in hours to analyze")
):
    """Get trending programs based on transaction volume."""
    try:
        # Get latest block for time range calculation
        latest_block = await program_analytics.query_handler.get_latest_block()
        blocks_per_hour = 60 * 60 * 2  # Approximate Solana blocks per hour
        start_slot = latest_block - (timeframe * blocks_per_hour)
        
        program_activity = {}
        handler = ProgramResponseHandler()
        
        # Process blocks in batches
        await program_analytics.query_handler.process_blocks(
            start_slot,
            latest_block,
            handler=handler,
            batch_size=50,
            batch_delay=1.0
        )
        
        # Get program activity from handler stats
        program_activity = handler.activity_stats["instruction_counts"]
        
        # Sort by activity
        trending = sorted(
            program_activity.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "timeframe_hours": timeframe,
            "trending_programs": [
                {"program_id": p[0], "transaction_count": p[1]}
                for p in trending
            ],
            "analysis_time": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting trending programs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
