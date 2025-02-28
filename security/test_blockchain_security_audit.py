#!/usr/bin/env python3
"""
Test script for the blockchain security audit module.

This script runs the blockchain security audit module on the Soleco codebase
and prints the findings.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_blockchain_security_audit')

def main():
    """Main entry point."""
    # Get the path to the backend directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
    
    # Ensure the backend directory exists
    if not os.path.exists(backend_dir):
        logger.error(f"Backend directory does not exist: {backend_dir}")
        return 1
    
    # Add the current directory to the Python path
    sys.path.insert(0, current_dir)
    
    try:
        # Import the blockchain security audit module
        from audit_modules.blockchain_security import run_audit
        
        # Run the audit
        logger.info(f"Running blockchain security audit on {backend_dir}")
        findings = run_audit(backend_dir)
        
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
        output_file = os.path.join(current_dir, 'blockchain_security_audit_report.json')
        with open(output_file, 'w') as f:
            json.dump({
                'module': 'blockchain_security',
                'findings': findings
            }, f, indent=2)
        
        logger.info(f"Saved findings to {output_file}")
        
        return 0
    except ImportError as e:
        logger.error(f"Failed to import blockchain security audit module: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error running blockchain security audit: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
