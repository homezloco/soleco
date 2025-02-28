# This file makes the routers directory a Python package

from .soleco import router as soleco_router
from .diagnostics import router as diagnostics_router
from .pump import router as pumpfun_router
from .jupiter import router as jupiter_router
from .raydium import router as raydium_router
from .helius import router as helius_router
from .shyft import router as shyft_router
from .moralis import router as moralis_router
from .rugcheck import router as rugcheck_router
from .dexscreener import router as dexscreener_router

routers = [
    soleco_router,  # Soleco router first
    diagnostics_router,  # Soleco Diagnostics second
    pumpfun_router,  # PumpFun third
    jupiter_router,
    raydium_router,
    helius_router,
    shyft_router,
    moralis_router,
    rugcheck_router,
    dexscreener_router
]
