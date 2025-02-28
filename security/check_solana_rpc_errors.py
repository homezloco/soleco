#!/usr/bin/env python3
"""
Check for Solana-specific RPC error handling issues.

This script analyzes the codebase for common Solana RPC error handling issues
and provides recommendations for improvement.
"""

import os
import sys
import re
import json
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('check_solana_rpc_errors')

# Common Solana RPC error codes and their descriptions
SOLANA_RPC_ERRORS = {
    -32000: "Server error",
    -32001: "Method not found",
    -32002: "Invalid params",
    -32003: "Internal error",
    -32004: "Invalid request",
    -32005: "Method not supported",
    -32006: "Request limit exceeded",
    -32007: "Transaction simulation failed",
    -32008: "Transaction verification failed",
    -32009: "Block not available",
    -32010: "Node unhealthy",
    -32011: "Validator exit",
    -32012: "Resource exhausted",
    -32013: "Account not found",
    -32014: "Slot not found",
    -32015: "Node behind",
    -32016: "Transaction precompile verification failure",
}

def find_python_files(codebase_path):
    """Find all Python files in the codebase."""
    logger.debug(f"Finding Python files in {codebase_path}")
    start_time = time.time()
    python_files = list(Path(codebase_path).rglob('*.py'))
    logger.debug(f"Found {len(python_files)} Python files in {time.time() - start_time:.2f} seconds")
    return python_files

def check_rpc_error_handling(codebase_path):
    """Check for RPC error handling issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for RPC calls without error handling
                if re.search(r'(await\s+client\..*?\(|client\..*?\()', content) and not re.search(r'try.*?except', content, re.DOTALL):
                    findings.append({
                        'title': 'RPC Call Without Error Handling',
                        'description': 'The file contains RPC calls but may not have proper error handling, which could lead to unhandled exceptions.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Wrap RPC calls in try-except blocks and handle specific Solana RPC error codes appropriately.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for generic exception handling
                if re.search(r'try.*?except\s+Exception', content, re.DOTALL) and re.search(r'(await\s+client\..*?\(|client\..*?\()', content):
                    findings.append({
                        'title': 'Generic Exception Handling for RPC Calls',
                        'description': 'The file uses generic exception handling for RPC calls, which may not properly handle specific Solana RPC error codes.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Use specific exception handling for different Solana RPC error codes to provide better error messages and recovery options.',
                        'cwe': 'CWE-390: Detection of Error Condition Without Action'
                    })
                
                # Check for missing timeout handling
                if re.search(r'(await\s+client\..*?\(|client\..*?\()', content) and not re.search(r'timeout|asyncio\.wait_for', content):
                    findings.append({
                        'title': 'Missing Timeout Handling for RPC Calls',
                        'description': 'The file contains RPC calls but may not have timeout handling, which could lead to hanging requests.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Use asyncio.wait_for or similar mechanisms to set timeouts for RPC calls, and handle timeout exceptions appropriately.',
                        'cwe': 'CWE-400: Uncontrolled Resource Consumption'
                    })
                
                # Check for hardcoded RPC URLs
                if re.search(r'https?://[a-zA-Z0-9.-]+\.(solana\.com|genesysgo\.net|helius\.xyz|quicknode\.com)', content):
                    findings.append({
                        'title': 'Hardcoded RPC URLs',
                        'description': 'The file contains hardcoded RPC URLs, which may make it difficult to switch between networks or RPC providers.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Store RPC URLs in configuration files or environment variables, and consider implementing RPC fallback mechanisms.',
                        'cwe': 'CWE-547: Use of Hard-coded, Security-relevant Constants'
                    })
                
                # Check for missing rate limiting handling
                if re.search(r'(await\s+client\..*?\(|client\..*?\()', content) and not re.search(r'rate.*?limit|throttle|backoff|retry', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Missing Rate Limiting Handling',
                        'description': 'The file contains RPC calls but may not handle rate limiting errors, which could lead to failed requests during high load.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Implement exponential backoff or retry mechanisms for rate-limited RPC calls, and consider using a rate limiting library.',
                        'cwe': 'CWE-770: Allocation of Resources Without Limits or Throttling'
                    })
                
                # Check for missing transaction simulation
                if re.search(r'sendTransaction|send_transaction', content, re.IGNORECASE) and not re.search(r'simulateTransaction|simulate_transaction', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Missing Transaction Simulation',
                        'description': 'The file sends transactions but may not simulate them first, which could lead to failed transactions and wasted fees.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Simulate transactions before sending them to catch errors early and avoid wasting transaction fees.',
                        'cwe': 'CWE-754: Improper Check for Unusual or Exceptional Conditions'
                    })
                
                # Check for missing transaction confirmation
                if re.search(r'sendTransaction|send_transaction', content, re.IGNORECASE) and not re.search(r'confirmTransaction|confirm_transaction|getSignatureStatus|get_signature_status', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Missing Transaction Confirmation',
                        'description': 'The file sends transactions but may not confirm them, which could lead to uncertainty about transaction status.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Always confirm transactions after sending them, and implement proper error handling for failed confirmations.',
                        'cwe': 'CWE-754: Improper Check for Unusual or Exceptional Conditions'
                    })
                
                # Check for missing account data validation
                if re.search(r'getAccountInfo|get_account_info', content, re.IGNORECASE) and not re.search(r'if\s+.*?is\s+None|if\s+not\s+.*?:|if\s+.*?is\s+null', content):
                    findings.append({
                        'title': 'Missing Account Data Validation',
                        'description': 'The file retrieves account data but may not validate it before use, which could lead to null reference exceptions.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Always check if account data is None or null before using it, and handle missing accounts gracefully.',
                        'cwe': 'CWE-476: NULL Pointer Dereference'
                    })
                
                # Check for missing RPC response validation
                if re.search(r'(await\s+client\..*?\(|client\..*?\()', content) and not re.search(r'if\s+.*?result|if\s+.*?response|if\s+.*?data', content):
                    findings.append({
                        'title': 'Missing RPC Response Validation',
                        'description': 'The file makes RPC calls but may not validate the responses before use, which could lead to unexpected behavior.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Always validate RPC responses before using them, checking for null values, expected formats, and error codes.',
                        'cwe': 'CWE-20: Improper Input Validation'
                    })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings

def main():
    """Main entry point."""
    start_time = time.time()
    logger.info("Checking for Solana RPC error handling issues")
    
    # Get the path to the backend directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
    
    # Ensure the backend directory exists
    if not os.path.exists(backend_dir):
        logger.error(f"Backend directory does not exist: {backend_dir}")
        return 1
    
    # Check for RPC error handling issues
    findings = check_rpc_error_handling(backend_dir)
    
    # Print the findings
    if findings:
        logger.info(f"Found {len(findings)} issues:")
        for i, finding in enumerate(findings, 1):
            print(f"\n{i}. {finding['title']} ({finding['severity'].upper()})")
            print(f"   Location: {finding['location']}")
            print(f"   Description: {finding['description']}")
            print(f"   Recommendation: {finding['recommendation']}")
            print(f"   CWE: {finding['cwe']}")
    else:
        logger.info("No issues found.")
    
    # Save the findings to a JSON file
    output_file = os.path.join(current_dir, 'solana_rpc_errors_report.json')
    with open(output_file, 'w') as f:
        json.dump({
            'module': 'solana_rpc_errors',
            'findings': findings
        }, f, indent=2)
    
    logger.info(f"Saved findings to {output_file}")
    logger.info(f"Check completed in {time.time() - start_time:.2f} seconds")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
