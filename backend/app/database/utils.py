"""
Database utility functions for managing the SQLite database.
"""
import os
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

from app.database.sqlite import DB_FILE

# Configure logging
logger = logging.getLogger("app.database.utils")

def initialize_database():
    """
    Initialize the database if it doesn't exist.
    Creates the database file and tables.
    """
    try:
        # Ensure the data directory exists
        data_dir = Path(DB_FILE).parent
        os.makedirs(data_dir, exist_ok=True)
        
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Create cache table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache (
            endpoint TEXT PRIMARY KEY,
            data TEXT,
            params TEXT,
            timestamp TEXT,
            ttl INTEGER
        )
        ''')
        
        # Create network_status_history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS network_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT,
            timestamp TEXT,
            data TEXT
        )
        ''')
        
        # Create mint_analytics_history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mint_analytics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blocks INTEGER,
            new_mints_count INTEGER,
            pump_tokens_count INTEGER,
            timestamp TEXT,
            data TEXT
        )
        ''')
        
        # Create pump_tokens_history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pump_tokens_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeframe TEXT,
            sort_metric TEXT,
            tokens_count INTEGER,
            timestamp TEXT,
            data TEXT
        )
        ''')
        
        # Create rpc_nodes_history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rpc_nodes_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_nodes INTEGER,
            timestamp TEXT,
            data TEXT
        )
        ''')
        
        # Create performance_metrics_history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            max_tps REAL,
            avg_tps REAL,
            timestamp TEXT,
            data TEXT
        )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_network_status_timestamp ON network_status_history(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mint_analytics_timestamp ON mint_analytics_history(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pump_tokens_timestamp ON pump_tokens_history(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rpc_nodes_timestamp ON rpc_nodes_history(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics_history(timestamp)')
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {DB_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def cleanup_database(days_to_keep=7):
    """
    Clean up old records from the database.
    
    Args:
        days_to_keep: Number of days of data to keep
    """
    try:
        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Clean up expired cache entries
        cursor.execute('DELETE FROM cache WHERE datetime(timestamp) < datetime(?) OR (datetime(timestamp, "+" || ttl || " seconds") < datetime("now"))', (cutoff_date,))
        cache_deleted = cursor.rowcount
        
        # Clean up old history records
        cursor.execute('DELETE FROM network_status_history WHERE datetime(timestamp) < datetime(?)', (cutoff_date,))
        network_deleted = cursor.rowcount
        
        cursor.execute('DELETE FROM mint_analytics_history WHERE datetime(timestamp) < datetime(?)', (cutoff_date,))
        mint_deleted = cursor.rowcount
        
        cursor.execute('DELETE FROM pump_tokens_history WHERE datetime(timestamp) < datetime(?)', (cutoff_date,))
        pump_deleted = cursor.rowcount
        
        cursor.execute('DELETE FROM rpc_nodes_history WHERE datetime(timestamp) < datetime(?)', (cutoff_date,))
        rpc_deleted = cursor.rowcount
        
        cursor.execute('DELETE FROM performance_metrics_history WHERE datetime(timestamp) < datetime(?)', (cutoff_date,))
        performance_deleted = cursor.rowcount
        
        # Vacuum the database to reclaim space
        cursor.execute('VACUUM')
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info(f"Database cleanup complete. Deleted records: cache={cache_deleted}, network={network_deleted}, mint={mint_deleted}, pump={pump_deleted}, rpc={rpc_deleted}, performance={performance_deleted}")
        return True
    except Exception as e:
        logger.error(f"Error cleaning up database: {e}")
        return False

def export_database_stats():
    """
    Export database statistics.
    
    Returns:
        dict: Database statistics
    """
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get table row counts
        cursor.execute('SELECT COUNT(*) FROM cache')
        cache_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM network_status_history')
        network_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM mint_analytics_history')
        mint_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM pump_tokens_history')
        pump_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM rpc_nodes_history')
        rpc_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM performance_metrics_history')
        performance_count = cursor.fetchone()[0]
        
        # Get database file size
        db_size = os.path.getsize(DB_FILE)
        
        # Get earliest and latest timestamps
        cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM network_status_history')
        network_range = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        # Create stats dictionary
        stats = {
            'database_path': DB_FILE,
            'database_size_bytes': db_size,
            'database_size_mb': round(db_size / (1024 * 1024), 2),
            'row_counts': {
                'cache': cache_count,
                'network_status_history': network_count,
                'mint_analytics_history': mint_count,
                'pump_tokens_history': pump_count,
                'rpc_nodes_history': rpc_count,
                'performance_metrics_history': performance_count
            },
            'total_rows': cache_count + network_count + mint_count + pump_count + rpc_count + performance_count,
            'date_range': {
                'earliest': network_range[0],
                'latest': network_range[1]
            }
        }
        
        logger.info(f"Database stats: {json.dumps(stats, indent=2)}")
        return stats
    except Exception as e:
        logger.error(f"Error exporting database stats: {e}")
        return {'error': str(e)}

# Initialize the database when the module is imported
initialize_database()
