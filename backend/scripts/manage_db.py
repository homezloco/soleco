"""
Script to manage the database.
"""
import argparse
import sys
import os
import logging
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.utils import initialize_database, cleanup_database, export_database_stats
from app.utils.logging_config import setup_logging

# Configure logging
logger = setup_logging('scripts.manage_db')

def main():
    """
    Main function.
    """
    parser = argparse.ArgumentParser(description='Manage the Soleco database')
    parser.add_argument('--init', action='store_true', help='Initialize the database')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old records from the database')
    parser.add_argument('--days', type=int, default=7, help='Number of days of data to keep (default: 7)')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    
    args = parser.parse_args()
    
    if args.init:
        logger.info("Initializing database...")
        result = initialize_database()
        if result:
            logger.info("Database initialized successfully")
        else:
            logger.error("Failed to initialize database")
            return 1
    
    if args.cleanup:
        logger.info(f"Cleaning up database (keeping {args.days} days of data)...")
        result = cleanup_database(args.days)
        if result:
            logger.info("Database cleaned up successfully")
        else:
            logger.error("Failed to clean up database")
            return 1
    
    if args.stats:
        logger.info("Exporting database statistics...")
        stats = export_database_stats()
        if 'error' in stats:
            logger.error(f"Failed to export database statistics: {stats['error']}")
            return 1
        else:
            logger.info("Database statistics exported successfully")
    
    if not (args.init or args.cleanup or args.stats):
        parser.print_help()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
