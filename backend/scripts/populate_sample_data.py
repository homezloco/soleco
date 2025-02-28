"""
Script to populate the database with sample data for testing.
"""
import argparse
import sys
import os
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.sqlite import db_cache
from app.utils.logging_config import setup_logging

# Configure logging
logger = setup_logging('scripts.populate_sample_data')

def generate_network_status_data(num_records=24, hours_back=24):
    """
    Generate sample network status data.
    
    Args:
        num_records: Number of records to generate
        hours_back: Number of hours to go back
        
    Returns:
        List of network status records
    """
    statuses = ['healthy', 'degraded', 'down']
    weights = [0.8, 0.15, 0.05]  # 80% healthy, 15% degraded, 5% down
    
    records = []
    for i in range(num_records):
        # Calculate timestamp
        timestamp = (datetime.now() - timedelta(hours=hours_back) + 
                    timedelta(hours=i * hours_back / num_records)).isoformat()
        
        # Generate status
        status = random.choices(statuses, weights=weights)[0]
        
        # Generate sample data
        data = {
            'status': status,
            'validators': {
                'active': random.randint(1500, 2000),
                'delinquent': random.randint(0, 50),
                'total': random.randint(1500, 2050)
            },
            'blocks': {
                'processed': random.randint(150000000, 160000000),
                'confirmed': random.randint(150000000, 160000000),
                'finalized': random.randint(150000000, 160000000)
            },
            'transactions': {
                'per_second_current': random.randint(1000, 5000),
                'per_second_max': random.randint(5000, 10000),
                'count_total': random.randint(100000000000, 200000000000)
            },
            'epoch': {
                'current': random.randint(400, 500),
                'slot_current': random.randint(0, 432000),
                'slot_total': 432000,
                'progress': random.random()
            }
        }
        
        records.append({
            'status': status,
            'timestamp': timestamp,
            'data': json.dumps(data)
        })
    
    return records

def generate_mint_analytics_data(num_records=24, hours_back=24, blocks=2):
    """
    Generate sample mint analytics data.
    
    Args:
        num_records: Number of records to generate
        hours_back: Number of hours to go back
        blocks: Number of blocks analyzed
        
    Returns:
        List of mint analytics records
    """
    records = []
    for i in range(num_records):
        # Calculate timestamp
        timestamp = (datetime.now() - timedelta(hours=hours_back) + 
                    timedelta(hours=i * hours_back / num_records)).isoformat()
        
        # Generate counts
        new_mints_count = random.randint(100, 1000)
        pump_tokens_count = random.randint(10, 100)
        
        # Generate sample data
        data = {
            'blocks': blocks,
            'new_mints': {
                'count': new_mints_count,
                'addresses': [f"mint{j}" for j in range(min(10, new_mints_count))]
            },
            'pump_tokens': {
                'count': pump_tokens_count,
                'tokens': [f"token{j}" for j in range(min(10, pump_tokens_count))]
            },
            'timestamp': timestamp
        }
        
        records.append({
            'blocks': blocks,
            'new_mints_count': new_mints_count,
            'pump_tokens_count': pump_tokens_count,
            'timestamp': timestamp,
            'data': json.dumps(data)
        })
    
    return records

def generate_pump_tokens_data(num_records=24, hours_back=24, timeframe='24h', sort_metric='volume'):
    """
    Generate sample pump tokens data.
    
    Args:
        num_records: Number of records to generate
        hours_back: Number of hours to go back
        timeframe: Timeframe (1h, 24h, 7d)
        sort_metric: Sort metric (volume, price_change, holder_growth)
        
    Returns:
        List of pump tokens records
    """
    records = []
    for i in range(num_records):
        # Calculate timestamp
        timestamp = (datetime.now() - timedelta(hours=hours_back) + 
                    timedelta(hours=i * hours_back / num_records)).isoformat()
        
        # Generate count
        tokens_count = random.randint(50, 200)
        
        # Generate sample data
        tokens = []
        for j in range(min(10, tokens_count)):
            tokens.append({
                'address': f"token{j}",
                'symbol': f"TKN{j}",
                'name': f"Token {j}",
                'volume': random.randint(10000, 1000000),
                'price_change': random.uniform(-0.5, 2.0),
                'holder_growth': random.uniform(0, 0.5)
            })
        
        data = {
            'timeframe': timeframe,
            'sort_metric': sort_metric,
            'tokens_count': tokens_count,
            'tokens': tokens,
            'timestamp': timestamp
        }
        
        records.append({
            'timeframe': timeframe,
            'sort_metric': sort_metric,
            'tokens_count': tokens_count,
            'timestamp': timestamp,
            'data': json.dumps(data)
        })
    
    return records

def generate_rpc_nodes_data(num_records=24, hours_back=24):
    """
    Generate sample RPC nodes data.
    
    Args:
        num_records: Number of records to generate
        hours_back: Number of hours to go back
        
    Returns:
        List of RPC nodes records
    """
    records = []
    for i in range(num_records):
        # Calculate timestamp
        timestamp = (datetime.now() - timedelta(hours=hours_back) + 
                    timedelta(hours=i * hours_back / num_records)).isoformat()
        
        # Generate count
        total_nodes = random.randint(2000, 3000)
        
        # Generate sample data
        data = {
            'total_nodes': total_nodes,
            'version_distribution': {
                '1.14.0': random.randint(500, 1000),
                '1.13.0': random.randint(500, 1000),
                '1.12.0': random.randint(500, 1000)
            },
            'timestamp': timestamp
        }
        
        records.append({
            'total_nodes': total_nodes,
            'timestamp': timestamp,
            'data': json.dumps(data)
        })
    
    return records

def generate_performance_metrics_data(num_records=24, hours_back=24):
    """
    Generate sample performance metrics data.
    
    Args:
        num_records: Number of records to generate
        hours_back: Number of hours to go back
        
    Returns:
        List of performance metrics records
    """
    records = []
    for i in range(num_records):
        # Calculate timestamp
        timestamp = (datetime.now() - timedelta(hours=hours_back) + 
                    timedelta(hours=i * hours_back / num_records)).isoformat()
        
        # Generate metrics
        max_tps = random.uniform(5000, 10000)
        avg_tps = random.uniform(2000, 5000)
        
        # Generate sample data
        data = {
            'max_tps': max_tps,
            'avg_tps': avg_tps,
            'latency': {
                'p50': random.uniform(0.1, 0.5),
                'p90': random.uniform(0.5, 1.0),
                'p99': random.uniform(1.0, 2.0)
            },
            'timestamp': timestamp
        }
        
        records.append({
            'max_tps': max_tps,
            'avg_tps': avg_tps,
            'timestamp': timestamp,
            'data': json.dumps(data)
        })
    
    return records

def main():
    """Main function to populate the database with sample data."""
    parser = argparse.ArgumentParser(description="Populate the SQLite database with sample data.")
    parser.add_argument("--records", type=int, default=24, help="Number of records to generate (default: 24)")
    parser.add_argument("--hours", type=int, default=24, help="Number of hours to go back (default: 24)")
    args = parser.parse_args()
    
    num_records = args.records
    hours_back = args.hours
    
    logger.info(f"Populating database with {num_records} records over {hours_back} hours...")
    
    try:
        # Initialize database connection
        from app.database.sqlite import db_cache
        
        # Generate and store network status data
        logger.info("Generating network status data...")
        network_status_data = generate_network_status_data(num_records, hours_back)
        for record in network_status_data:
            try:
                db_cache.store_network_status(record['status'], json.loads(record['data']))
            except Exception as e:
                logger.error(f"Error storing network status record: {e}")
        
        # Generate and store mint analytics data
        logger.info("Generating mint analytics data...")
        for blocks in [2, 5, 10]:
            mint_analytics_data = generate_mint_analytics_data(num_records, hours_back, blocks)
            for record in mint_analytics_data:
                try:
                    db_cache.store_mint_analytics(
                        blocks, 
                        record['new_mints_count'], 
                        record['pump_tokens_count'], 
                        json.loads(record['data'])
                    )
                except Exception as e:
                    logger.error(f"Error storing mint analytics record: {e}")
        
        # Generate and store pump tokens data
        logger.info("Generating pump tokens data...")
        for timeframe in ['1h', '24h', '7d']:
            for sort_metric in ['volume', 'price_change', 'holder_growth']:
                pump_tokens_data = generate_pump_tokens_data(
                    num_records, hours_back, timeframe, sort_metric
                )
                for record in pump_tokens_data:
                    try:
                        db_cache.store_pump_tokens(
                            timeframe, 
                            sort_metric, 
                            record['tokens_count'], 
                            json.loads(record['data'])
                        )
                    except Exception as e:
                        logger.error(f"Error storing pump tokens record: {e}")
        
        # Generate and store RPC nodes data
        logger.info("Generating RPC nodes data...")
        rpc_nodes_data = generate_rpc_nodes_data(num_records, hours_back)
        for record in rpc_nodes_data:
            try:
                db_cache.store_rpc_nodes(record['total_nodes'], json.loads(record['data']))
            except Exception as e:
                logger.error(f"Error storing RPC nodes record: {e}")
        
        # Generate and store performance metrics data
        logger.info("Generating performance metrics data...")
        performance_metrics_data = generate_performance_metrics_data(num_records, hours_back)
        for record in performance_metrics_data:
            try:
                db_cache.store_performance_metrics(
                    record['max_tps'], 
                    record['avg_tps'], 
                    json.loads(record['data'])
                )
            except Exception as e:
                logger.error(f"Error storing performance metrics record: {e}")
        
        logger.info("Sample data population complete")
        logger.info("Database populated successfully")
    
    except Exception as e:
        logger.error(f"Error populating database: {e}")
        logger.error("Failed to populate database")
        sys.exit(1)

if __name__ == '__main__':
    sys.exit(main())
