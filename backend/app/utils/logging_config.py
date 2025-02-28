"""
Logging configuration for the Soleco project
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path

def setup_logging(logger_name: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    Set up logging configuration for a specific logger
    
    Args:
        logger_name: Name of the logger to configure
        log_level: Logging level to use
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(logger_name)
    
    # Set logging level
    if logger_name == 'solana_query':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(log_level)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create file handler
    log_file = log_dir / f"{logger_name.replace('.', '_')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10
    )
    if logger_name == 'solana_query':
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Add formatters to handlers
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger by name, creating it if it doesn't exist
    
    Args:
        name: Name of the logger
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)

# Create default logger and configure root logger
logger = setup_logging('soleco')
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('hpack').setLevel(logging.WARNING)
