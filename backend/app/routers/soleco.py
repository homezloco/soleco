from fastapi import APIRouter
from .solana_mint_extractor_modular import router as mint_extractor_router
from .solana_new_mints_extractor import router as new_mints_router
from .solana_analytics.mint_analytics import router as mint_analytics_router
from .solana_analytics.wallet_analytics import router as wallet_analytics_router
from .solana import router as solana_router
from .solana_rpc_nodes import router as rpc_nodes_router
from .solana_network import router as network_router

router = APIRouter(
    prefix="",  # Remove prefix since it's added in main.py
    tags=["Soleco"],  # Use consistent tag for all Soleco endpoints
    responses={404: {"description": "Not found"}},
)

# Core Solana endpoints
router.include_router(solana_router, prefix="/solana", tags=["Soleco"])  # Include solana router with solana prefix
router.include_router(rpc_nodes_router, prefix="/solana", tags=["Soleco"])  # Include rpc_nodes_router with solana prefix
router.include_router(network_router, prefix="/solana", tags=["Soleco"])  # Add /solana prefix to network router

# Mint analysis endpoints
router.include_router(mint_extractor_router, prefix="/mints", tags=["Soleco"])
router.include_router(new_mints_router, prefix="/mints/new", tags=["Soleco"])

# Analytics endpoints
router.include_router(mint_analytics_router, prefix="/analytics/mints", tags=["Soleco"])
router.include_router(wallet_analytics_router, prefix="/analytics/wallets", tags=["Soleco"])
