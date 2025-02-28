#!/usr/bin/env python3
"""
Check dependencies for known vulnerabilities.

This script uses the safety tool to check Python dependencies for known
security vulnerabilities.
"""

import os
import sys
import subprocess
import argparse
import logging
import json
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('check_dependencies')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Check dependencies for known vulnerabilities')
    parser.add_argument('--requirements', type=str, default='../backend/requirements.txt',
                        help='Path to requirements.txt file')
    parser.add_argument('--output', type=str, default='dependency_check_report.json',
                        help='Output file for the scan report')
    return parser.parse_args()

def check_safety_installed():
    """Check if safety is installed."""
    try:
        subprocess.run(['safety', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_safety_check(requirements_file, output_file):
    """
    Run safety check on the requirements file.
    
    Args:
        requirements_file: Path to requirements.txt file
        output_file: Output file for the scan report
        
    Returns:
        bool: True if the scan completed successfully, False otherwise
    """
    logger.info(f"Checking dependencies in {requirements_file} for vulnerabilities")
    
    # Normalize and validate path
    requirements_file = os.path.abspath(os.path.expanduser(requirements_file))
    if not os.path.exists(requirements_file):
        logger.error(f"Requirements file not found: {requirements_file}")
        return False
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Run safety check
    try:
        cmd = [
            'safety',
            'check',
            '-r', requirements_file,  # Requirements file
            '--json',  # JSON output
            '--output', output_file,  # Output file
            '--full-report'  # Include full vulnerability details
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"No vulnerabilities found in dependencies")
            
            # Create an empty report
            with open(output_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'requirements_file': requirements_file,
                    'vulnerabilities': []
                }, f, indent=2)
            
            return True
        else:
            # Safety returns non-zero if it finds vulnerabilities, which is expected
            try:
                # Try to parse the output
                with open(output_file, 'r') as f:
                    report = json.load(f)
                
                vuln_count = len(report.get('vulnerabilities', []))
                logger.warning(f"Found {vuln_count} vulnerable dependencies. Report saved to {output_file}")
                return True
            except (json.JSONDecodeError, FileNotFoundError):
                logger.error(f"Failed to parse safety output: {result.stderr}")
                return False
    
    except Exception as e:
        logger.error(f"Error running safety check: {e}")
        return False

def main():
    """Main entry point."""
    args = parse_args()
    
    # Check if safety is installed
    if not check_safety_installed():
        logger.error("Safety is not installed. Please run setup_security_tools.py first.")
        sys.exit(1)
    
    # Run safety check
    success = run_safety_check(args.requirements, args.output)
    
    if not success:
        logger.error("Dependency check failed")
        sys.exit(1)
    
    logger.info("""
Dependency check complete!

If vulnerabilities were found, consider:
- Updating the vulnerable dependencies to secure versions
- Checking if the vulnerabilities affect your specific usage
- Adding security controls to mitigate the vulnerabilities
- Replacing the vulnerable dependencies with secure alternatives
""")

if __name__ == "__main__":
    main()
