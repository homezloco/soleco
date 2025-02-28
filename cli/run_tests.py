#!/usr/bin/env python
"""
Test runner script for the Soleco CLI.
This script runs the test suite with coverage reporting.
"""

import os
import sys
import subprocess
import argparse

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run Soleco CLI tests')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage reporting')
    parser.add_argument('--html', action='store_true', help='Generate HTML coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Run tests in verbose mode')
    parser.add_argument('--test-path', type=str, default='tests', help='Path to test directory or file')
    return parser.parse_args()

def run_tests(args):
    """Run the test suite with the specified options."""
    # Determine the command to run
    cmd = ['pytest']
    
    # Add verbosity if requested
    if args.verbose:
        cmd.append('-v')
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend(['--cov=soleco_cli', '--cov-report=term'])
        if args.html:
            cmd.append('--cov-report=html')
    
    # Add the test path
    cmd.append(args.test_path)
    
    # Print the command being run
    print(f"Running: {' '.join(cmd)}")
    
    # Run the tests
    result = subprocess.run(cmd)
    return result.returncode

def main():
    """Main entry point."""
    args = parse_args()
    
    # Ensure we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Run the tests
    return_code = run_tests(args)
    
    # Print a message about the HTML report if generated
    if args.coverage and args.html:
        print("\nHTML coverage report generated in htmlcov/index.html")
    
    # Exit with the appropriate code
    sys.exit(return_code)

if __name__ == '__main__':
    main()
