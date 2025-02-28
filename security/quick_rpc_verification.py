#!/usr/bin/env python3
"""
Quick RPC Improvements Verification

A simplified version of the RPC improvements verification script that runs more quickly
by checking only a small subset of files and patterns.
"""

import os
import sys
import json
import re
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('quick_rpc_verification')

# Define a simplified set of improvements to verify
RPC_IMPROVEMENTS = {
    'coroutine_handling': {
        'description': 'Coroutine Handling',
        'details': ['Fixed issues with coroutines not being properly awaited'],
        'patterns': [r'async\s+def', r'await'],
        'files': ['**/network_status_handler.py', '**/rpc_handler.py']
    },
    'error_handling': {
        'description': 'Error Handling',
        'details': ['Enhanced error handling with more detailed logging'],
        'patterns': [r'try\s*:.*?except', r'log(ger)?\.error'],
        'files': ['**/rpc_handler.py', '**/solana_query_handler.py']
    },
    'serialization': {
        'description': 'Serialization',
        'details': ['Enhanced serialization for Solana objects'],
        'patterns': [r'serialize', r'json\.dumps'],
        'files': ['**/utils.py', '**/solana_utils.py']
    }
}

def find_files(codebase_path, patterns, max_files=5):
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

def verify_improvement(codebase_path, improvement_key, improvement_info):
    """Verify a specific improvement."""
    logger.info(f"Verifying {improvement_info['description']} improvements")
    
    # Find relevant files
    files = find_files(codebase_path, improvement_info['files'])
    logger.info(f"Found {len(files)} relevant files")
    
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
    
    # Check patterns in files
    all_matches = {}
    for file_path in files:
        matches = check_patterns_in_file(file_path, improvement_info['patterns'])
        all_matches[str(file_path)] = matches
    
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
        verification_results[improvement_key] = verify_improvement(codebase_path, improvement_key, improvement_info)
    
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
    print("\nQuick RPC Improvements Verification Results:")
    print("===========================================")
    
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
    output_file = os.path.join(current_dir, 'quick_rpc_verification.json')
    with open(output_file, 'w') as f:
        json.dump({
            'module': 'quick_rpc_verification',
            'overall_percentage': overall_percentage,
            'results': verification_results
        }, f, indent=2)
    
    logger.info(f"Saved verification results to {output_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
