"""
FastAPI application main module.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.routers.soleco import router as soleco_router
from app.routers.diagnostics import router as diagnostics_router
from app.routers.pump import router as pumpfun_router
from app.routers.pump_trending import router as pump_trending_router
from app.routers.jupiter import router as jupiter_router
from app.routers.dexscreener import router as dexscreener_router
from app.routers.helius import router as helius_router
from app.routers.moralis import router as moralis_router
from app.routers.raydium import router as raydium_router
from app.routers.rugcheck import router as rugcheck_router
from app.routers.shyft import router as shyft_router
from app.routers.cli import router as cli_router
from app.routers.wallet import router as wallet_router
from app.routers.analytics import router as analytics_router

from app.utils.solana_rpc import get_connection_pool
from app.dependencies.solana import get_query_handler
from app.utils.logging_config import setup_logging
from app.database.middleware import CacheMiddleware
from app.tasks.pump_data_collector import run_data_collection

# Configure logging
logger = setup_logging('app.main')

# Create a scheduler for background tasks
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting up application...")
    
    try:
        # Initialize connection pool
        pool = await get_connection_pool()
        if not pool._initialized:
            await pool.initialize()
            
        # Initialize shared query handler
        query_handler = await get_query_handler()
        await query_handler.initialize()
        
        # Test connection
        async with await pool.acquire() as client:
            logger.info("Connection pool test successful")
        
        # Schedule background tasks
        try:
            async def run_task():
                await run_data_collection()
                
            scheduler.add_job(
                run_task,
                trigger=IntervalTrigger(hours=1),  # Run every hour
                id="pump_data_collector",
                name="Pump.fun Data Collector",
                replace_existing=True
            )
            scheduler.start()
            logger.info("Scheduled background tasks started")
        except Exception as e:
            logger.error(f"Error starting scheduler: {str(e)}")
        
        yield
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise
    finally:
        # Shutdown scheduler
        try:
            if scheduler.running:
                scheduler.shutdown()
                logger.info("Background task scheduler shutdown")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {str(e)}")
        logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Soleco API",
    description="""
    Soleco API for Solana ecosystem analytics and tools.
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "Soleco",
            "description": "Core Soleco API endpoints for blockchain data extraction and analysis"
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins temporarily for debugging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add database cache middleware
app.add_middleware(CacheMiddleware)

# Add Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Create API router with prefix
api_router = APIRouter(prefix="/api")

# Include Soleco routers first
api_router.include_router(soleco_router, prefix="/soleco", tags=["Soleco"])  # Main Soleco endpoints
api_router.include_router(diagnostics_router, prefix="/soleco/diagnostics", tags=["Soleco Diagnostics"])  # Diagnostics endpoints second
api_router.include_router(pumpfun_router, prefix="/soleco/pumpfun", tags=["PumpFun"])  # PumpFun endpoints third
api_router.include_router(pump_trending_router, prefix="/soleco/pump_trending", tags=["Pump Analytics"])  # Pump Trending endpoints
api_router.include_router(cli_router, prefix="/soleco/cli", tags=["CLI"])  # CLI endpoints
api_router.include_router(wallet_router, prefix="/soleco/wallet", tags=["Wallet"])  # Wallet endpoints moved under /soleco to match frontend expectations
api_router.include_router(analytics_router, prefix="/soleco/analytics", tags=["Analytics"])  # Analytics endpoints

# Include external API routers
api_router.include_router(jupiter_router, prefix="/external/jupiter", tags=["Jupiter"])
api_router.include_router(dexscreener_router, prefix="/external/dexscreener", tags=["DexScreener"])
api_router.include_router(helius_router, prefix="/external/helius", tags=["Helius"])
api_router.include_router(moralis_router, prefix="/external/moralis", tags=["Moralis"])
api_router.include_router(raydium_router, prefix="/external/raydium", tags=["Raydium"])
api_router.include_router(rugcheck_router, prefix="/external/rugcheck", tags=["RugCheck"])
api_router.include_router(shyft_router, prefix="/external/shyft", tags=["Shyft"])

# Include API router in app with proper prefix
app.include_router(api_router)

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    """
    return {"message": "Welcome to Soleco API. Visit /docs for API documentation."}
