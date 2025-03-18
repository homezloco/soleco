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
from datetime import datetime
import logging
import os

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

from app.utils.solana_rpc import get_connection_pool, DEFAULT_RPC_ENDPOINTS
from app.dependencies.solana import get_query_handler
from app.utils.logging_config import setup_logging
from app.database.middleware import CacheMiddleware
from app.tasks.pump_data_collector import run_data_collection
from app.scripts.schedule_rpc_pool_update import start_scheduler as start_rpc_pool_scheduler

# Configure logging
logger = setup_logging('app.main')

# Create a scheduler for background tasks
scheduler = AsyncIOScheduler()

# Store background tasks
background_tasks = []

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
            await pool.initialize(DEFAULT_RPC_ENDPOINTS)
            
        # Initialize shared query handler
        query_handler = await get_query_handler()
        await query_handler.initialize()
        
        # Test connection
        async with await pool.acquire() as client:
            logger.info("Connection pool test successful")
        
        # Schedule background tasks
        try:
            # Schedule pump data collection
            async def run_task():
                await run_data_collection()
                
            scheduler.add_job(
                run_task,
                trigger=IntervalTrigger(hours=1),  # Run every hour
                id="pump_data_collector",
                name="Pump.fun Data Collector",
                replace_existing=True
            )
            
            # Start the scheduler
            scheduler.start()
            logger.info("Scheduled background tasks started")
            
            # Start RPC pool update scheduler
            logger.info("Starting RPC pool update scheduler")
            try:
                # Configure scheduler logging
                scheduler_logger = logging.getLogger('app.scripts.schedule_rpc_pool_update')
                scheduler_logger.setLevel(logging.DEBUG)
                
                # Create a file handler for detailed scheduler logs
                os.makedirs('logs', exist_ok=True)  # Ensure logs directory exists
                scheduler_file_handler = logging.FileHandler('logs/rpc_scheduler_detailed.log')
                scheduler_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                scheduler_file_handler.setLevel(logging.DEBUG)
                scheduler_logger.addHandler(scheduler_file_handler)
                
                logger.info("Configured scheduler logging")
                
                # Start the scheduler
                logger.info("Calling start_rpc_pool_scheduler")
                try:
                    rpc_pool_task = await start_rpc_pool_scheduler(
                        interval_hours=12.0,           # Full update every 12 hours
                        health_check_interval=1.0,     # Health check every 1 hour
                        max_test=50,                   # Test up to 50 endpoints
                        max_endpoints=10               # Keep top 10 endpoints in the pool
                    )
                    logger.info(f"start_rpc_pool_scheduler returned task: {rpc_pool_task}")
                    
                    if rpc_pool_task is None:
                        logger.error("start_rpc_pool_scheduler returned None instead of a task")
                    else:
                        background_tasks.append(rpc_pool_task)
                        logger.info("RPC pool update scheduler started successfully")
                        
                        # Check if the task is still running after a short delay
                        await asyncio.sleep(2)
                        if rpc_pool_task.done():
                            if rpc_pool_task.exception():
                                logger.error(f"RPC pool scheduler task failed: {rpc_pool_task.exception()}")
                            else:
                                logger.error("RPC pool scheduler task completed unexpectedly")
                        else:
                            logger.info("RPC pool scheduler task is running")
                except Exception as e:
                    logger.error(f"Error in start_rpc_pool_scheduler: {str(e)}")
                    logger.exception(e)
                    
                    # Try a direct update as a fallback
                    logger.info("Attempting direct RPC pool update as fallback")
                    from app.scripts.schedule_rpc_pool_update import update_rpc_pool
                    await update_rpc_pool(max_test=50, max_endpoints=10)
                    logger.info("Direct RPC pool update completed")
                    
            except Exception as e:
                logger.error(f"Error starting RPC pool scheduler: {str(e)}")
                logger.exception(e)
        
        except Exception as e:
            logger.error(f"Error starting scheduler: {str(e)}")
        
        yield
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise
    finally:
        # Cancel background tasks
        for task in background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
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
    allow_origins=[
        "http://localhost:5181",  # Frontend dev server
        "http://127.0.0.1:5181",
        "http://172.28.118.135:5181",  # Local network IP
        "http://localhost:4173",  # Vite preview
        "http://127.0.0.1:4173",
        "http://172.28.118.135:4173"  # Local network IP for preview
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-Total-Count"],
    max_age=600,  # Cache preflight requests for 10 minutes
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

# Add a simple test endpoint for browser connectivity checks
@app.get("/api/test-connection", tags=["Diagnostics"])
async def test_connection():
    """
    Simple endpoint to test API connectivity.
    This endpoint is used by the frontend to check if API requests are being blocked.
    """
    return {
        "status": "success",
        "message": "API connection successful",
        "timestamp": datetime.now().isoformat()
    }

# Add a test endpoint to manually start the scheduler
@app.get("/test_scheduler")
async def test_scheduler_endpoint():
    """Test endpoint to manually start the RPC pool scheduler."""
    try:
        # Configure scheduler logging
        scheduler_logger = logging.getLogger('app.scripts.schedule_rpc_pool_update')
        scheduler_logger.setLevel(logging.DEBUG)
        
        # Create a file handler for detailed scheduler logs
        os.makedirs('logs', exist_ok=True)  # Ensure logs directory exists
        scheduler_file_handler = logging.FileHandler('logs/rpc_scheduler_test.log')
        scheduler_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        scheduler_file_handler.setLevel(logging.DEBUG)
        scheduler_logger.addHandler(scheduler_file_handler)
        
        # Start the scheduler with shorter intervals for testing
        rpc_pool_task = await start_rpc_pool_scheduler(
            interval_hours=0.05,          # 3 minutes
            health_check_interval=0.02,   # 1.2 minutes
            max_test=10,                  # Test fewer endpoints for speed
            max_endpoints=5               # Keep fewer endpoints for testing
        )
        
        if rpc_pool_task is None:
            return {"status": "error", "message": "Scheduler returned None instead of a task"}
        
        # Check if the task is running
        await asyncio.sleep(2)
        if rpc_pool_task.done():
            if rpc_pool_task.exception():
                return {"status": "error", "message": f"Scheduler task failed: {rpc_pool_task.exception()}"}
            else:
                return {"status": "error", "message": "Scheduler task completed unexpectedly"}
        
        return {"status": "success", "message": "RPC pool scheduler started successfully"}
    except Exception as e:
        logger.exception(e)
        return {"status": "error", "message": f"Error starting scheduler: {str(e)}"}

@app.get("/rpc_pool_status")
async def rpc_pool_status():
    """Get the current status of the RPC connection pool."""
    try:
        pool = await get_connection_pool()
        
        # Get pool information
        status = {
            "initialized": pool._initialized,
            "last_update": pool.last_update,
            "last_update_human": datetime.fromtimestamp(pool.last_update).isoformat() if pool.last_update else None,
            "endpoints_count": len(pool._endpoints) if hasattr(pool, "_endpoints") else 0,
            "clients_count": len(pool._clients) if hasattr(pool, "_clients") else 0,
            "available_clients": len(pool._available_clients) if hasattr(pool, "_available_clients") else 0,
            "in_use_clients": len(pool._in_use) if hasattr(pool, "_in_use") else 0,
            "rate_limited_endpoints": list(pool._rate_limited_endpoints.keys()) if hasattr(pool, "_rate_limited_endpoints") else [],
            "failed_endpoints": list(pool._failed_endpoints.keys()) if hasattr(pool, "_failed_endpoints") else []
        }
        
        # Try to get the list of endpoints
        if hasattr(pool, "_endpoints"):
            status["endpoints"] = pool._endpoints
        
        return status
    except Exception as e:
        logger.exception(e)
        return {"status": "error", "message": f"Error getting RPC pool status: {str(e)}"}

@app.get("/update_rpc_pool")
async def update_rpc_pool_endpoint(max_test: int = 20, max_endpoints: int = 10, quick_mode: bool = False):
    """Manually trigger an RPC pool update."""
    try:
        from app.scripts.schedule_rpc_pool_update import update_rpc_pool
        
        logger.info(f"Manually triggering RPC pool update with max_test={max_test}, max_endpoints={max_endpoints}, quick_mode={quick_mode}")
        
        # Run the update
        await update_rpc_pool(max_test, max_endpoints, quick_mode)
        
        # Get the updated pool status
        return await rpc_pool_status()
    except Exception as e:
        logger.exception(e)
        return {"status": "error", "message": f"Error updating RPC pool: {str(e)}"}

# Include API router in app with proper prefix
app.include_router(api_router)

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    """
    return {"message": "Welcome to Soleco API. Visit /docs for API documentation."}
