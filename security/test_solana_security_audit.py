#!/usr/bin/env python3
"""
Test script for the Solana security audit module.

This script runs the Solana security audit module on the Soleco codebase
and prints the findings.
"""

import os
import sys
import json
import logging
import time
import threading
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_solana_security_audit')

# Global variable to store findings
global_findings = []
audit_completed = False

def run_audit_with_timeout(codebase_path, timeout=60):
    """Run the audit with a timeout."""
    def audit_target():
        global global_findings, audit_completed
        try:
            # Import the Solana security audit module
            from audit_modules.solana_security import run_audit
            
            # Run the audit
            findings = run_audit(codebase_path)
            global_findings = findings
            audit_completed = True
        except Exception as e:
            logger.error(f"Error in audit thread: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Create and start the audit thread
    audit_thread = threading.Thread(target=audit_target)
    audit_thread.daemon = True
    audit_thread.start()
    
    # Wait for the audit to complete or timeout
    start_time = time.time()
    while time.time() - start_time < timeout and not audit_completed:
        time.sleep(1)
        logger.debug(f"Waiting for audit to complete... ({int(time.time() - start_time)}s)")
    
    if not audit_completed:
        logger.error(f"Audit timed out after {timeout} seconds")
        return []
    
    return global_findings

def main():
    """Main entry point."""
    start_time = time.time()
    logger.debug("Starting Solana security audit")
    
    # Get the path to the backend directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logger.debug(f"Current directory: {current_dir}")
    
    backend_dir = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
    logger.debug(f"Backend directory: {backend_dir}")
    
    # Ensure the backend directory exists
    if not os.path.exists(backend_dir):
        logger.error(f"Backend directory does not exist: {backend_dir}")
        return 1
    
    # Add the current directory to the Python path
    sys.path.insert(0, current_dir)
    logger.debug(f"Python path: {sys.path}")
    
    try:
        # Run the audit with a timeout
        findings = run_audit_with_timeout(backend_dir, timeout=120)  # 2 minute timeout
        logger.debug(f"Audit completed in {time.time() - start_time:.2f} seconds")
        
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
        output_file = os.path.join(current_dir, 'solana_security_audit_report.json')
        with open(output_file, 'w') as f:
            json.dump({
                'module': 'solana_security',
                'findings': findings
            }, f, indent=2)
        
        logger.info(f"Saved findings to {output_file}")
        
        return 0
    except ImportError as e:
        logger.error(f"Failed to import Solana security audit module: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error running Solana security audit: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
