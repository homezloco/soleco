#!/usr/bin/env python3
"""
Quick Security Audit

This script performs a fast security audit by focusing on the most critical
security issues and only scanning key directories in the codebase.
"""

import os
import sys
import json
import time
import logging
import threading
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('quick_security_audit')

def load_config():
    """Load the audit configuration."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audit_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return None

def find_python_files(directory, include_dirs=None, exclude_dirs=None):
    """Find Python files in the specified directory."""
    python_files = []
    
    # Convert directory to Path object
    directory = Path(directory)
    
    # If include_dirs is specified, only scan those directories
    if include_dirs:
        for include_dir in include_dirs:
            include_path = Path(include_dir)
            if include_path.is_absolute():
                # If absolute path, use it directly
                scan_path = include_path
            else:
                # If relative path, join with the base directory
                scan_path = directory / include_path
            
            # Find Python files in this directory
            python_files.extend(list(scan_path.rglob('*.py')))
    else:
        # Scan the entire directory
        python_files = list(directory.rglob('*.py'))
    
    # Filter out excluded directories
    if exclude_dirs:
        filtered_files = []
        for file_path in python_files:
            exclude = False
            for exclude_dir in exclude_dirs:
                exclude_path = Path(exclude_dir)
                if exclude_path.is_absolute():
                    # If absolute path, check if file is in this directory
                    if str(file_path).startswith(str(exclude_path)):
                        exclude = True
                        break
                else:
                    # If relative path, check if the relative path is in the file path
                    rel_file_path = file_path.relative_to(directory)
                    if str(rel_file_path).startswith(str(exclude_path)):
                        exclude = True
                        break
            
            if not exclude:
                filtered_files.append(file_path)
        
        python_files = filtered_files
    
    return python_files

def check_for_security_issues(file_path):
    """Check a file for security issues."""
    findings = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # Check for hardcoded secrets
            if any(pattern in content for pattern in ['password', 'secret', 'api_key', 'apikey', 'token']):
                if any(pattern in content for pattern in ['="', "='", '= "', "= '"]):
                    findings.append({
                        'title': 'Potential Hardcoded Secret',
                        'description': 'The file may contain hardcoded secrets such as passwords, API keys, or tokens.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Store secrets in environment variables or a secure vault, not in code.',
                        'cwe': 'CWE-798: Use of Hard-coded Credentials'
                    })
            
            # Check for SQL injection
            if 'execute(' in content and any(pattern in content for pattern in ['%s', '?', 'format(', 'f"']):
                findings.append({
                    'title': 'Potential SQL Injection',
                    'description': 'The file may be vulnerable to SQL injection attacks.',
                    'location': str(file_path),
                    'severity': 'high',
                    'recommendation': 'Use parameterized queries or an ORM to prevent SQL injection.',
                    'cwe': 'CWE-89: Improper Neutralization of Special Elements used in an SQL Command'
                })
            
            # Check for missing signature verification
            if 'sendTransaction' in content or 'send_transaction' in content:
                if not ('verify_signature' in content or 'verifySignature' in content):
                    findings.append({
                        'title': 'Missing Signature Verification',
                        'description': 'The file sends transactions but may not verify signatures.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Always verify transaction signatures before processing them.',
                        'cwe': 'CWE-345: Insufficient Verification of Data Authenticity'
                    })
            
            # Check for missing input validation
            if any(pattern in content for pattern in ['request.', 'params', 'query', 'body']):
                if not any(pattern in content for pattern in ['validate', 'schema', 'sanitize']):
                    findings.append({
                        'title': 'Missing Input Validation',
                        'description': 'The file accepts user input but may not validate it properly.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Validate all user input using a schema validation library or input sanitization.',
                        'cwe': 'CWE-20: Improper Input Validation'
                    })
            
            # Check for insecure deserialization
            if any(pattern in content for pattern in ['pickle.loads', 'yaml.load(', 'json.loads']):
                if 'yaml.load(' in content and 'Loader=yaml.SafeLoader' not in content:
                    findings.append({
                        'title': 'Insecure Deserialization',
                        'description': 'The file uses insecure deserialization methods.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Use safe deserialization methods like yaml.safe_load() or specify a safe loader.',
                        'cwe': 'CWE-502: Deserialization of Untrusted Data'
                    })
            
            # Check for missing error handling
            if 'try:' in content and 'except Exception' in content and not any(pattern in content for pattern in ['log.', 'logger.', 'logging.']):
                findings.append({
                    'title': 'Generic Exception Handling',
                    'description': 'The file uses generic exception handling without proper logging.',
                    'location': str(file_path),
                    'severity': 'medium',
                    'recommendation': 'Use specific exception handling and proper logging for better error tracking.',
                    'cwe': 'CWE-390: Detection of Error Condition Without Action'
                })
    
    except Exception as e:
        logger.warning(f"Error processing file {file_path}: {e}")
    
    return findings

def run_quick_audit(codebase_path, include_dirs=None, exclude_dirs=None, timeout=60):
    """Run a quick security audit on the codebase."""
    findings = []
    
    # Find Python files
    start_time = time.time()
    logger.info(f"Finding Python files in {codebase_path}")
    python_files = find_python_files(codebase_path, include_dirs, exclude_dirs)
    logger.info(f"Found {len(python_files)} Python files in {time.time() - start_time:.2f} seconds")
    
    # Check each file for security issues
    start_time = time.time()
    logger.info("Checking for security issues")
    
    # Use a list to store findings from the thread
    thread_findings = []
    
    # Define a function to run in a separate thread
    def audit_thread():
        for file_path in python_files:
            file_findings = check_for_security_issues(file_path)
            if file_findings:
                thread_findings.extend(file_findings)
    
    # Run the audit in a separate thread with a timeout
    audit_thread = threading.Thread(target=audit_thread)
    audit_thread.daemon = True
    audit_thread.start()
    audit_thread.join(timeout)
    
    if audit_thread.is_alive():
        logger.error(f"Audit timed out after {timeout} seconds")
    else:
        logger.info(f"Audit completed in {time.time() - start_time:.2f} seconds")
    
    # Extend the findings list with the thread findings
    findings.extend(thread_findings)
    
    return findings

def main():
    """Main entry point."""
    # Get the path to the backend directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
    
    # Ensure the backend directory exists
    if not os.path.exists(backend_dir):
        logger.error(f"Backend directory does not exist: {backend_dir}")
        return 1
    
    # Load configuration
    config = load_config()
    
    # Run the quick audit
    if config and 'include_dirs' in config:
        include_dirs = [os.path.join(backend_dir, d) for d in config['include_dirs']]
        exclude_dirs = [os.path.join(backend_dir, d) for d in config['exclude_dirs']]
        findings = run_quick_audit(backend_dir, include_dirs=include_dirs, exclude_dirs=exclude_dirs)
    else:
        findings = run_quick_audit(backend_dir)
    
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
    output_file = os.path.join(current_dir, 'quick_security_audit_report.json')
    with open(output_file, 'w') as f:
        json.dump({
            'module': 'quick_security_audit',
            'findings': findings
        }, f, indent=2)
    
    logger.info(f"Saved findings to {output_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
