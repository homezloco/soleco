"""
SQLite database module for caching dashboard data.
"""
import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Configure logging
logger = logging.getLogger("app.database.sqlite")

# Database file path
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "soleco_cache.db")

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

class DatabaseCache:
    """
    SQLite database cache for dashboard data.
    """
    def __init__(self):
        """Initialize the database connection and create tables if they don't exist."""
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()
        
    def __del__(self):
        """Ensure connection is closed when object is destroyed."""
        self._close()
    
    def _connect(self):
        """Connect to the SQLite database."""
        try:
            # Close existing connection if it exists
            self._close()
            
            # Create parent directory if it doesn't exist
            Path(os.path.dirname(DB_FILE)).mkdir(parents=True, exist_ok=True)
            
            # Connect with timeout and enable WAL mode for better concurrency
            self.conn = sqlite3.connect(DB_FILE, timeout=30.0)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to SQLite database at {DB_FILE}")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to SQLite database: {e}")
            raise
    
    def _close(self):
        """Close the database connection."""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.cursor = None
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    
    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        try:
            # Cache table for storing API responses
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                endpoint TEXT PRIMARY KEY,
                data TEXT,
                params TEXT,
                timestamp TIMESTAMP,
                ttl INTEGER
            )
            ''')
            
            # Network status history
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT,
                timestamp TIMESTAMP,
                data TEXT
            )
            ''')
            
            # Mint analytics history
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mint_analytics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blocks INTEGER,
                new_mints_count INTEGER,
                pump_tokens_count INTEGER,
                timestamp TIMESTAMP,
                data TEXT
            )
            ''')
            
            # Pump tokens history
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pump_tokens_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timeframe TEXT,
                sort_metric TEXT,
                tokens_count INTEGER,
                timestamp TIMESTAMP,
                data TEXT
            )
            ''')
            
            # RPC nodes history
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rpc_nodes_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_nodes INTEGER,
                timestamp TIMESTAMP,
                data TEXT
            )
            ''')
            
            # Performance metrics history
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                max_tps REAL,
                avg_tps REAL,
                timestamp TIMESTAMP,
                data TEXT
            )
            ''')
            
            # Pump token performance history
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pump_token_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mint TEXT,
                name TEXT,
                symbol TEXT,
                price REAL,
                price_change_1h REAL,
                price_change_24h REAL,
                price_change_7d REAL,
                volume_24h REAL,
                market_cap REAL,
                virtual_sol_reserves REAL,
                virtual_token_reserves REAL,
                timestamp TIMESTAMP,
                data TEXT
            )
            ''')
            
            self.conn.commit()
            logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def close(self):
        """Close the database connection."""
        self._close()
    
    def get_cached_data(self, endpoint: str, params: Optional[Dict[str, Any]] = None, max_age_seconds: int = 300) -> Optional[Dict[str, Any]]:
        """
        Get cached data for the given endpoint and parameters.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            max_age_seconds: Maximum age of cached data in seconds
            
        Returns:
            Cached data or None if not found or expired
        """
        try:
            params_str = json.dumps(params) if params else None
            
            # Get the cached data
            self.cursor.execute(
                "SELECT data, timestamp FROM cache WHERE endpoint = ? AND (params = ? OR (params IS NULL AND ? IS NULL))",
                (endpoint, params_str, params_str)
            )
            row = self.cursor.fetchone()
            
            if row:
                data = json.loads(row['data'])
                timestamp = datetime.fromisoformat(row['timestamp'])
                now = datetime.now()
                
                # Check if the cached data is still valid
                if (now - timestamp).total_seconds() <= max_age_seconds:
                    logger.debug(f"Cache hit for {endpoint} with params {params}")
                    return data
                else:
                    logger.debug(f"Cache expired for {endpoint} with params {params}")
            else:
                logger.debug(f"Cache miss for {endpoint} with params {params}")
            
            return None
        except Exception as e:
            logger.error(f"Error getting cached data for {endpoint}: {e}")
            return None
    
    def cache_data(self, endpoint: str, data: Dict[str, Any], params: Optional[Dict[str, Any]] = None, ttl: int = 300) -> bool:
        """
        Cache data for the given endpoint and parameters.
        
        Args:
            endpoint: API endpoint
            data: Data to cache
            params: Query parameters
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            params_str = json.dumps(params) if params else None
            data_str = json.dumps(data)
            timestamp = datetime.now().isoformat()
            
            # Insert or replace the cached data
            self.cursor.execute(
                "INSERT OR REPLACE INTO cache (endpoint, data, params, timestamp, ttl) VALUES (?, ?, ?, ?, ?)",
                (endpoint, data_str, params_str, timestamp, ttl)
            )
            self.conn.commit()
            logger.debug(f"Cached data for {endpoint} with params {params}")
            return True
        except Exception as e:
            logger.error(f"Error caching data for {endpoint}: {e}")
            return False
    
    def store_network_status(self, status: str, data: Dict[str, Any]) -> bool:
        """
        Store network status data in the history table.
        
        Args:
            status: Network status (healthy, degraded, etc.)
            data: Network status data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data_str = json.dumps(data)
            timestamp = datetime.now().isoformat()
            
            self.cursor.execute(
                "INSERT INTO network_status_history (status, timestamp, data) VALUES (?, ?, ?)",
                (status, timestamp, data_str)
            )
            self.conn.commit()
            logger.debug(f"Stored network status: {status}")
            return True
        except Exception as e:
            logger.error(f"Error storing network status: {e}")
            return False
    
    def store_mint_analytics(self, blocks: int, new_mints_count: int, pump_tokens_count: int, data: Dict[str, Any]) -> bool:
        """
        Store mint analytics data in the history table.
        
        Args:
            blocks: Number of blocks analyzed
            new_mints_count: Number of new mint addresses
            pump_tokens_count: Number of pump tokens
            data: Mint analytics data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data_str = json.dumps(data)
            timestamp = datetime.now().isoformat()
            
            self.cursor.execute(
                "INSERT INTO mint_analytics_history (blocks, new_mints_count, pump_tokens_count, timestamp, data) VALUES (?, ?, ?, ?, ?)",
                (blocks, new_mints_count, pump_tokens_count, timestamp, data_str)
            )
            self.conn.commit()
            logger.debug(f"Stored mint analytics for {blocks} blocks")
            return True
        except Exception as e:
            logger.error(f"Error storing mint analytics: {e}")
            return False
    
    def store_pump_tokens(self, timeframe: str, sort_metric: str, tokens_count: int, data: Dict[str, Any]) -> bool:
        """
        Store pump tokens data in the history table.
        
        Args:
            timeframe: Timeframe (1h, 24h, 7d)
            sort_metric: Sort metric (volume, price_change, holder_growth)
            tokens_count: Number of tokens
            data: Pump tokens data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data_str = json.dumps(data)
            timestamp = datetime.now().isoformat()
            
            self.cursor.execute(
                "INSERT INTO pump_tokens_history (timeframe, sort_metric, tokens_count, timestamp, data) VALUES (?, ?, ?, ?, ?)",
                (timeframe, sort_metric, tokens_count, timestamp, data_str)
            )
            self.conn.commit()
            logger.debug(f"Stored pump tokens for {timeframe} timeframe")
            return True
        except Exception as e:
            logger.error(f"Error storing pump tokens: {e}")
            return False
    
    def store_rpc_nodes(self, total_nodes: int, data: Dict[str, Any]) -> bool:
        """
        Store RPC nodes data in the history table.
        
        Args:
            total_nodes: Total number of RPC nodes
            data: RPC nodes data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data_str = json.dumps(data)
            timestamp = datetime.now().isoformat()
            
            self.cursor.execute(
                "INSERT INTO rpc_nodes_history (total_nodes, timestamp, data) VALUES (?, ?, ?)",
                (total_nodes, timestamp, data_str)
            )
            self.conn.commit()
            logger.debug(f"Stored RPC nodes: {total_nodes} nodes")
            return True
        except Exception as e:
            logger.error(f"Error storing RPC nodes: {e}")
            return False
    
    def store_performance_metrics(self, max_tps: float, avg_tps: float, data: Dict[str, Any]) -> bool:
        """
        Store performance metrics data in the history table.
        
        Args:
            max_tps: Maximum transactions per second
            avg_tps: Average transactions per second
            data: Performance metrics data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data_str = json.dumps(data)
            timestamp = datetime.now().isoformat()
            
            self.cursor.execute(
                "INSERT INTO performance_metrics_history (max_tps, avg_tps, timestamp, data) VALUES (?, ?, ?, ?)",
                (max_tps, avg_tps, timestamp, data_str)
            )
            self.conn.commit()
            logger.debug(f"Stored performance metrics: max TPS {max_tps}, avg TPS {avg_tps}")
            return True
        except Exception as e:
            logger.error(f"Error storing performance metrics: {e}")
            return False
    
    def store_token_performance(self, token_data: Dict[str, Any]) -> bool:
        """
        Store token performance data in the history table.
        
        Args:
            token_data: Token data from the Pump.fun API
            
        Returns:
            True if successful, False otherwise
        """
        try:
            mint = token_data.get('mint')
            if not mint:
                logger.warning("Cannot store token performance: missing mint address")
                return False
                
            # Extract relevant fields
            name = token_data.get('name', '')
            symbol = token_data.get('symbol', '')
            
            # Calculate price if possible
            price = 0
            if token_data.get('virtual_sol_reserves') and token_data.get('virtual_token_reserves'):
                sol_reserves = float(token_data.get('virtual_sol_reserves', 0)) / 1000000000  # Convert lamports to SOL
                token_reserves = float(token_data.get('virtual_token_reserves', 0)) / 1000000000  # Convert to standard units
                if token_reserves > 0:
                    price = sol_reserves / token_reserves
            
            # Other metrics
            price_change_1h = float(token_data.get('price_change_1h', 0))
            price_change_24h = float(token_data.get('price_change_24h', 0))
            price_change_7d = float(token_data.get('price_change_7d', 0))
            volume_24h = float(token_data.get('volume_24h', 0))
            market_cap = float(token_data.get('market_cap', 0))
            virtual_sol_reserves = float(token_data.get('virtual_sol_reserves', 0)) / 1000000000
            virtual_token_reserves = float(token_data.get('virtual_token_reserves', 0)) / 1000000000
            
            # Convert to JSON for storage
            data_str = json.dumps(token_data)
            timestamp = datetime.now().isoformat()
            
            self.cursor.execute(
                """
                INSERT INTO pump_token_performance 
                (mint, name, symbol, price, price_change_1h, price_change_24h, price_change_7d, 
                volume_24h, market_cap, virtual_sol_reserves, virtual_token_reserves, timestamp, data) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mint, name, symbol, price, price_change_1h, price_change_24h, price_change_7d, 
                volume_24h, market_cap, virtual_sol_reserves, virtual_token_reserves, timestamp, data_str)
            )
            self.conn.commit()
            logger.debug(f"Stored performance data for token {symbol} ({mint})")
            return True
        except Exception as e:
            logger.error(f"Error storing token performance: {e}")
            return False
    
    def get_network_status_history(self, limit: int = 24, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get network status history for the past hours.
        
        Args:
            limit: Maximum number of records to return
            hours: Number of hours to look back
            
        Returns:
            List of network status records
        """
        try:
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            self.cursor.execute(
                "SELECT status, timestamp, data FROM network_status_history WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (cutoff, limit)
            )
            rows = self.cursor.fetchall()
            
            return [
                {
                    "status": row["status"],
                    "timestamp": row["timestamp"],
                    "data": json.loads(row["data"])
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error getting network status history: {e}")
            return []
    
    def get_mint_analytics_history(self, blocks: int = 2, limit: int = 24, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get mint analytics history for the past hours.
        
        Args:
            blocks: Number of blocks analyzed
            limit: Maximum number of records to return
            hours: Number of hours to look back
            
        Returns:
            List of mint analytics records
        """
        try:
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            self.cursor.execute(
                "SELECT blocks, new_mints_count, pump_tokens_count, timestamp, data FROM mint_analytics_history WHERE blocks = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (blocks, cutoff, limit)
            )
            rows = self.cursor.fetchall()
            
            return [
                {
                    "blocks": row["blocks"],
                    "new_mints_count": row["new_mints_count"],
                    "pump_tokens_count": row["pump_tokens_count"],
                    "timestamp": row["timestamp"],
                    "data": json.loads(row["data"])
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error getting mint analytics history: {e}")
            return []
    
    def get_pump_tokens_history(self, timeframe: str = "24h", sort_metric: str = "volume", limit: int = 24, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get pump tokens history for the past hours.
        
        Args:
            timeframe: Timeframe (1h, 24h, 7d)
            sort_metric: Sort metric (volume, price_change, holder_growth)
            limit: Maximum number of records to return
            hours: Number of hours to look back
            
        Returns:
            List of pump tokens records
        """
        try:
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            self.cursor.execute(
                "SELECT timeframe, sort_metric, tokens_count, timestamp, data FROM pump_tokens_history WHERE timeframe = ? AND sort_metric = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (timeframe, sort_metric, cutoff, limit)
            )
            rows = self.cursor.fetchall()
            
            return [
                {
                    "timeframe": row["timeframe"],
                    "sort_metric": row["sort_metric"],
                    "tokens_count": row["tokens_count"],
                    "timestamp": row["timestamp"],
                    "data": json.loads(row["data"])
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error getting pump tokens history: {e}")
            return []
    
    def get_top_performing_tokens(self, metric: str = 'volume_24h', limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get top performing tokens based on the specified metric.
        
        Args:
            metric: Metric to sort by (volume_24h, price_change_24h, etc.)
            limit: Maximum number of tokens to return
            hours: Number of hours to look back
            
        Returns:
            List of top performing tokens
        """
        try:
            valid_metrics = ['volume_24h', 'price_change_1h', 'price_change_24h', 'price_change_7d', 'market_cap']
            if metric not in valid_metrics:
                logger.warning(f"Invalid metric: {metric}. Using volume_24h instead.")
                metric = 'volume_24h'
                
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # Get the latest record for each token within the time window
            self.cursor.execute(
                f"""
                WITH LatestTokens AS (
                    SELECT mint, MAX(timestamp) as max_timestamp
                    FROM pump_token_performance
                    WHERE timestamp > ?
                    GROUP BY mint
                )
                SELECT p.*
                FROM pump_token_performance p
                JOIN LatestTokens lt ON p.mint = lt.mint AND p.timestamp = lt.max_timestamp
                ORDER BY p.{metric} DESC
                LIMIT ?
                """,
                (cutoff, limit)
            )
            rows = self.cursor.fetchall()
            
            return [
                {
                    "mint": row["mint"],
                    "name": row["name"],
                    "symbol": row["symbol"],
                    "price": row["price"],
                    "price_change_1h": row["price_change_1h"],
                    "price_change_24h": row["price_change_24h"],
                    "price_change_7d": row["price_change_7d"],
                    "volume_24h": row["volume_24h"],
                    "market_cap": row["market_cap"],
                    "virtual_sol_reserves": row["virtual_sol_reserves"],
                    "virtual_token_reserves": row["virtual_token_reserves"],
                    "timestamp": row["timestamp"],
                    "data": json.loads(row["data"])
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error getting top performing tokens: {e}")
            return []

# Create a singleton instance
db_cache = DatabaseCache()
