import asyncio
import logging
import os
from app.scripts.schedule_rpc_pool_update import start_scheduler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/test_scheduler.log')
    ]
)
logger = logging.getLogger("test_scheduler")

async def test_scheduler():
    """Test the RPC pool scheduler"""
    logger.info("Starting scheduler test")
    
    try:
        # Start the scheduler with shorter intervals for testing
        task = await start_scheduler(
            interval_hours=0.05,          # 3 minutes
            health_check_interval=0.02,   # 1.2 minutes
            max_test=10,                  # Test fewer endpoints for speed
            max_endpoints=5               # Keep fewer endpoints for testing
        )
        
        logger.info("Scheduler started, waiting for 5 minutes to observe behavior")
        
        # Wait for 5 minutes to observe the scheduler behavior
        await asyncio.sleep(300)
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Scheduler task cancelled")
            
        logger.info("Scheduler test completed")
        
    except Exception as e:
        logger.error(f"Error testing scheduler: {str(e)}")
        logger.exception(e)

if __name__ == "__main__":
    asyncio.run(test_scheduler())
