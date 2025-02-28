"""
Test runner script for the Solana RPC error handling tests.

This script runs all the test files for the enhanced Solana RPC error handling.
"""

import os
import sys
import pytest
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('run_handler_tests')

def run_tests():
    """Run all the handler tests."""
    # Get the directory of this script
    script_dir = Path(__file__).parent
    
    # Get the handlers directory
    handlers_dir = script_dir / 'handlers'
    
    # Check if the handlers directory exists
    if not handlers_dir.exists():
        logger.error(f"Handlers directory not found: {handlers_dir}")
        return 1
    
    # Get all test files
    test_files = list(handlers_dir.glob('test_*.py'))
    
    if not test_files:
        logger.error("No test files found in handlers directory")
        return 1
    
    logger.info(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        logger.info(f"  - {test_file.name}")
    
    # Run the tests
    logger.info("Running tests...")
    result = pytest.main([
        '-xvs',  # Verbose output, stop on first failure
        str(handlers_dir)
    ])
    
    if result == 0:
        logger.info("All tests passed!")
    else:
        logger.error("Some tests failed")
    
    return result

if __name__ == "__main__":
    sys.exit(run_tests())
