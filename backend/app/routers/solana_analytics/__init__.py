"""
Solana analytics routers package.
"""

from fastapi import APIRouter
from .mint_analytics import router as mint_router
from .block_analytics import router as block_router
from .defi_analytics import router as defi_router
from .programid_analytics import router as programid_router
from .account_analytics import router as account_router
from .pump_analytics import router as pump_router

router = APIRouter()

router.include_router(mint_router)
router.include_router(block_router)
router.include_router(defi_router)
router.include_router(programid_router)
router.include_router(account_router)
router.include_router(pump_router)

__all__ = [
    'router',
    'mint_router',
    'block_router',
    'defi_router',
    'programid_router',
    'account_router',
    'pump_router'
]
