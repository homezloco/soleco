#!/usr/bin/env python3
"""
Run Bandit security scan on the Soleco codebase.

Bandit is a tool designed to find common security issues in Python code.
This script runs Bandit on the Soleco codebase and generates a report.
"""

import os
import sys
import subprocess
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('run_bandit_scan')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run Bandit security scan on the Soleco codebase')
    parser.add_argument('--path', type=str, default='../backend',
                        help='Path to the codebase to scan')
    parser.add_argument('--output', type=str, default='bandit_report.html',
                        help='Output file for the scan report')
    parser.add_argument('--severity', type=str, default='low',
                        choices=['low', 'medium', 'high'],
                        help='Minimum severity level to report')
    parser.add_argument('--confidence', type=str, default='low',
                        choices=['low', 'medium', 'high'],
                        help='Minimum confidence level to report')
    return parser.parse_args()

def check_bandit_installed():
    """Check if Bandit is installed."""
    try:
        subprocess.run(['bandit', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_bandit_scan(codebase_path, output_file, severity, confidence):
    """
    Run Bandit security scan on the codebase.
    
    Args:
        codebase_path: Path to the codebase to scan
        output_file: Output file for the scan report
        severity: Minimum severity level to report
        confidence: Minimum confidence level to report
        
    Returns:
        bool: True if the scan completed successfully, False otherwise
    """
    logger.info(f"Running Bandit security scan on {codebase_path}")
    
    # Normalize and validate path
    codebase_path = os.path.abspath(os.path.expanduser(codebase_path))
    if not os.path.exists(codebase_path):
        logger.error(f"Path does not exist: {codebase_path}")
        return False
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Run Bandit
    try:
        cmd = [
            'bandit',
            '-r',  # Recursive
            codebase_path,
            '-f', 'html',  # Output format
            '-o', output_file,  # Output file
            '--severity-level', severity,  # Minimum severity level
            '--confidence-level', confidence,  # Minimum confidence level
            '--exclude', '*/tests/*,*/venv/*,*/.venv/*'  # Exclude test files and virtual environments
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Bandit scan completed successfully. Report saved to {output_file}")
            return True
        else:
            # Bandit returns non-zero if it finds issues, which is expected
            issues_found = "Issues found" in result.stderr or "Issues found" in result.stdout
            if issues_found:
                logger.warning(f"Bandit found security issues. Report saved to {output_file}")
                return True
            else:
                logger.error(f"Bandit scan failed: {result.stderr}")
                return False
    
    except Exception as e:
        logger.error(f"Error running Bandit scan: {e}")
        return False

def main():
    """Main entry point."""
    args = parse_args()
    
    # Check if Bandit is installed
    if not check_bandit_installed():
        logger.error("Bandit is not installed. Please run setup_security_tools.py first.")
        sys.exit(1)
    
    # Run Bandit scan
    success = run_bandit_scan(args.path, args.output, args.severity, args.confidence)
    
    if not success:
        logger.error("Bandit scan failed")
        sys.exit(1)
    
    logger.info("""
Bandit scan complete!

Common security issues to look for:
- Hardcoded passwords or secrets
- Use of insecure functions (e.g., eval, exec)
- SQL injection vulnerabilities
- Command injection vulnerabilities
- Use of insecure hash functions (e.g., MD5, SHA1)
- Insecure file permissions
- Use of assert statements in production code
- Use of pickle or yaml.load without safe_load
""")

if __name__ == "__main__":
    main()
