#!/usr/bin/env python3
"""
Quick Transaction Validation Audit

This script performs a simplified transaction validation audit on a small subset of files
to quickly identify potential issues without scanning the entire codebase.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('quick_transaction_audit')

def check_file_for_issues(file_path):
    """Check a single file for transaction validation issues."""
    findings = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # Check for transaction creation without signature verification
            if 'Transaction(' in content and not any(term in content.lower() for term in ['verify_signature', 'verify_signatures']):
                findings.append({
                    'title': 'Missing Transaction Signature Verification',
                    'description': 'The file creates Solana transactions but may not verify signatures before processing.',
                    'location': str(file_path),
                    'severity': 'high'
                })
            
            # Check for transaction submission without simulation
            if any(term in content for term in ['send_transaction', 'sendTransaction']) and not any(term in content.lower() for term in ['simulate_transaction', 'simulatetransaction', 'dry_run', 'dryrun']):
                findings.append({
                    'title': 'Missing Transaction Simulation',
                    'description': 'The file sends transactions but may not simulate them before submission.',
                    'location': str(file_path),
                    'severity': 'medium'
                })
            
            # Check for transaction submission without error handling
            if any(term in content for term in ['send_transaction', 'sendTransaction']) and not any(term in content.lower() for term in ['try', 'except', 'error']):
                findings.append({
                    'title': 'Missing Transaction Error Handling',
                    'description': 'The file sends transactions but may not handle transaction errors properly.',
                    'location': str(file_path),
                    'severity': 'medium'
                })
            
            # Check for transaction submission without confirmation
            if any(term in content for term in ['send_transaction', 'sendTransaction']) and not any(term in content.lower() for term in ['confirm_transaction', 'confirmtransaction', 'wait_for_confirmation', 'waitforconfirmation']):
                findings.append({
                    'title': 'Missing Transaction Confirmation',
                    'description': 'The file sends transactions but may not confirm they were successfully processed by the network.',
                    'location': str(file_path),
                    'severity': 'medium'
                })
    except Exception as e:
        logger.warning(f"Error processing file {file_path}: {e}")
    
    return findings

def main():
    """Main entry point."""
    start_time = time.time()
    
    # Get the path to the backend directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
    
    # Ensure the backend directory exists
    if not os.path.exists(backend_dir):
        logger.error(f"Backend directory does not exist: {backend_dir}")
        return 1
    
    # Define key directories to check
    key_dirs = [
        os.path.join(backend_dir, 'app', 'api'),
        os.path.join(backend_dir, 'app', 'blockchain'),
        os.path.join(backend_dir, 'app', 'services'),
    ]
    
    # Find Python files in key directories
    python_files = []
    for dir_path in key_dirs:
        if os.path.exists(dir_path):
            python_files.extend(list(Path(dir_path).rglob('*.py')))
    
    logger.info(f"Found {len(python_files)} Python files to check")
    
    # Check each file for issues
    all_findings = []
    for file_path in python_files:
        logger.info(f"Checking {file_path}")
        findings = check_file_for_issues(file_path)
        all_findings.extend(findings)
    
    # Print the findings
    if all_findings:
        logger.info(f"Found {len(all_findings)} issues:")
        for i, finding in enumerate(all_findings, 1):
            print(f"\n{i}. {finding['title']} ({finding['severity'].upper()})")
            print(f"   Location: {finding['location']}")
            print(f"   Description: {finding['description']}")
    else:
        logger.info("No issues found.")
    
    # Save the findings to a JSON file
    output_file = os.path.join(current_dir, 'quick_transaction_audit_report.json')
    with open(output_file, 'w') as f:
        json.dump({
            'module': 'quick_transaction_validation',
            'findings': all_findings
        }, f, indent=2)
    
    logger.info(f"Saved findings to {output_file}")
    logger.info(f"Audit completed in {time.time() - start_time:.2f} seconds")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
