#!/usr/bin/env python3
"""
Verify RPC Improvements

This script verifies that the RPC error handling improvements have been properly implemented.
It checks for the following improvements:
1. Coroutine Handling
2. Response Processing
3. Error Handling
4. Serialization
5. Initialization

The script analyzes the codebase and reports on the implementation status of each improvement.
"""

import os
import sys
import json
import re
import time
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('verify_rpc_improvements')

# Define the improvements to verify
RPC_IMPROVEMENTS = {
    'coroutine_handling': {
        'description': 'Coroutine Handling',
        'details': [
            'Fixed issues with coroutines not being properly awaited in the NetworkStatusHandler.get_comprehensive_status method',
            'Enhanced the _get_data_with_timeout method to properly check if the input is a coroutine and handle it appropriately',
            'Added detailed logging for coroutine execution and response handling'
        ],
        'patterns': [
            r'async\s+def\s+get_comprehensive_status',
            r'_get_data_with_timeout.*?inspect\.iscoroutine',
            r'await\s+asyncio\.wait_for',
            r'log(ger)?\..*?(coroutine|await)'
        ],
        'files': [
            '**/network_status_handler.py',
            '**/solana_query_handler.py',
            '**/rpc_handler.py'
        ]
    },
    'response_processing': {
        'description': 'Response Processing',
        'details': [
            'Improved the SolanaQueryHandler.get_vote_accounts method to properly handle the response from the Solana RPC API',
            'Enhanced the _process_stake_info method to better handle nested structures and find validator data at any level of nesting',
            'Added recursive search for validator data in complex response structures'
        ],
        'patterns': [
            r'def\s+get_vote_accounts',
            r'def\s+_process_stake_info',
            r'recursive.*?search|find.*?recursive',
            r'if\s+isinstance\(.*?,\s+dict\)'
        ],
        'files': [
            '**/solana_query_handler.py',
            '**/stake_handler.py',
            '**/validator_handler.py'
        ]
    },
    'error_handling': {
        'description': 'Error Handling',
        'details': [
            'Enhanced the safe_rpc_call_async function with more detailed logging and better error handling',
            'Added execution time tracking for RPC calls to help identify slow endpoints',
            'Improved error messages and structured error responses'
        ],
        'patterns': [
            r'def\s+safe_rpc_call_async',
            r'start_time\s*=\s*time\.time\(\)',
            r'time\.time\(\)\s*-\s*start_time',
            r'try\s*:.*?except\s+Exception\s+as\s+e\s*:',
            r'log(ger)?\.error\('
        ],
        'files': [
            '**/rpc_handler.py',
            '**/solana_query_handler.py',
            '**/network_status_handler.py'
        ]
    },
    'serialization': {
        'description': 'Serialization',
        'details': [
            'Enhanced the serialize_solana_object function to better handle various response types',
            'Added specific handling for Pubkey objects, coroutines, and objects with special methods',
            'Improved error logging during serialization'
        ],
        'patterns': [
            r'def\s+serialize_solana_object',
            r'isinstance\(.*?,\s*Pubkey\)',
            r'hasattr\(.*?,\s*[\'"]__bytes__[\'"]\)',
            r'inspect\.iscoroutine',
            r'log(ger)?\..*?serializ'
        ],
        'files': [
            '**/serialization.py',
            '**/utils.py',
            '**/solana_utils.py'
        ]
    },
    'initialization': {
        'description': 'Initialization',
        'details': [
            'Ensured proper initialization of handlers before making RPC calls',
            'Added explicit initialization in the get_performance_metrics function'
        ],
        'patterns': [
            r'def\s+__init__\s*\(',
            r'def\s+initialize\s*\(',
            r'if\s+not\s+self\._initialized',
            r'self\._initialized\s*=\s*True',
            r'def\s+get_performance_metrics'
        ],
        'files': [
            '**/network_status_handler.py',
            '**/solana_query_handler.py',
            '**/performance_handler.py'
        ]
    }
}

def find_files(codebase_path, patterns, max_files=100):
    """Find files matching the given patterns with a limit on the number of files."""
    matching_files = []
    
    for pattern in patterns:
        # Convert glob pattern to regex pattern for Path.glob
        if pattern.startswith('**/'):
            glob_pattern = f"**/{pattern[3:]}"
        else:
            glob_pattern = pattern
        
        # Find matching files with a limit
        count = 0
        for file_path in Path(codebase_path).glob(glob_pattern):
            if file_path.is_file() and file_path not in matching_files:
                matching_files.append(file_path)
                count += 1
                if count >= max_files:
                    logger.warning(f"Reached maximum file limit ({max_files}) for pattern {pattern}")
                    break
    
    return matching_files

def check_patterns_in_file(file_path, patterns):
    """Check if the file contains the given patterns."""
    matches = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            for pattern in patterns:
                if re.search(pattern, content, re.DOTALL | re.MULTILINE):
                    matches[pattern] = True
                else:
                    matches[pattern] = False
    except Exception as e:
        logger.warning(f"Error reading file {file_path}: {e}")
        # Set all patterns to False for this file
        for pattern in patterns:
            matches[pattern] = False
    
    return matches

def process_file(file_path, patterns):
    """Process a single file and check for patterns."""
    logger.debug(f"Checking patterns in {file_path}")
    return str(file_path), check_patterns_in_file(file_path, patterns)

def verify_improvement(codebase_path, improvement_key, improvement_info):
    """Verify a specific improvement."""
    logger.info(f"Verifying {improvement_info['description']} improvements")
    
    # Find relevant files
    start_time = time.time()
    files = find_files(codebase_path, improvement_info['files'])
    logger.info(f"Found {len(files)} relevant files in {time.time() - start_time:.2f} seconds")
    
    if not files:
        logger.warning(f"No files found for {improvement_info['description']} improvements")
        return {
            'key': improvement_key,
            'description': improvement_info['description'],
            'details': improvement_info['details'],
            'status': "Not Implemented",
            'implementation_percentage': 0,
            'files_checked': 0,
            'patterns_matched': 0,
            'total_patterns': len(improvement_info['patterns']),
            'file_matches': {}
        }
    
    # Check patterns in files using multi-threading
    all_matches = {}
    start_time = time.time()
    
    # Use a smaller number of workers to avoid overwhelming the system
    max_workers = min(10, len(files))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_file, file_path, improvement_info['patterns']): file_path
            for file_path in files
        }
        
        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_file)):
            file_path = future_to_file[future]
            try:
                file_path_str, matches = future.result()
                all_matches[file_path_str] = matches
                
                # Log progress every 10 files
                if (i + 1) % 10 == 0 or i == len(files) - 1:
                    logger.info(f"Processed {i + 1}/{len(files)} files for {improvement_info['description']}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
    
    logger.info(f"Checked patterns in {len(files)} files in {time.time() - start_time:.2f} seconds")
    
    # Calculate implementation percentage
    total_patterns = len(improvement_info['patterns']) * len(files) if files else 1
    matched_patterns = sum(sum(matches.values()) for matches in all_matches.values())
    implementation_percentage = matched_patterns / total_patterns * 100 if total_patterns > 0 else 0
    
    # Determine status
    if implementation_percentage >= 90:
        status = "Fully Implemented"
    elif implementation_percentage >= 50:
        status = "Partially Implemented"
    else:
        status = "Not Implemented"
    
    # Create verification result
    verification_result = {
        'key': improvement_key,
        'description': improvement_info['description'],
        'details': improvement_info['details'],
        'status': status,
        'implementation_percentage': implementation_percentage,
        'files_checked': len(files),
        'patterns_matched': matched_patterns,
        'total_patterns': total_patterns,
        'file_matches': all_matches
    }
    
    return verification_result

def verify_rpc_improvements(codebase_path):
    """Verify all RPC improvements."""
    verification_results = {}
    
    for improvement_key, improvement_info in RPC_IMPROVEMENTS.items():
        start_time = time.time()
        verification_results[improvement_key] = verify_improvement(codebase_path, improvement_key, improvement_info)
        logger.info(f"Verified {improvement_info['description']} in {time.time() - start_time:.2f} seconds")
    
    return verification_results

def main():
    """Main entry point."""
    # Get the path to the backend directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
    
    # Check if backend directory exists, if not, use a mock directory for testing
    if not os.path.exists(backend_dir):
        logger.warning(f"Backend directory does not exist: {backend_dir}")
        logger.info("Using current directory for testing")
        backend_dir = current_dir
    
    # Verify RPC improvements
    logger.info(f"Verifying RPC improvements in {backend_dir}")
    start_time = time.time()
    verification_results = verify_rpc_improvements(backend_dir)
    logger.info(f"Verification completed in {time.time() - start_time:.2f} seconds")
    
    # Print verification results
    print("\nRPC Improvements Verification Results:")
    print("=====================================")
    
    overall_percentage = sum(result['implementation_percentage'] for result in verification_results.values()) / len(verification_results)
    print(f"Overall Implementation: {overall_percentage:.2f}%\n")
    
    for improvement_key, result in verification_results.items():
        print(f"{result['description']} ({result['status']}): {result['implementation_percentage']:.2f}%")
        print(f"  - Files checked: {result['files_checked']}")
        print(f"  - Patterns matched: {result['patterns_matched']} / {result['total_patterns']}")
        
        # Print details of the improvement
        print("  - Details:")
        for detail in result['details']:
            print(f"    * {detail}")
        
        print()
    
    # Save verification results to a JSON file
    output_file = os.path.join(current_dir, 'rpc_improvements_verification.json')
    with open(output_file, 'w') as f:
        json.dump({
            'module': 'rpc_improvements_verification',
            'overall_percentage': overall_percentage,
            'results': verification_results
        }, f, indent=2)
    
    logger.info(f"Saved verification results to {output_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
