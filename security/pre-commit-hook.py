#!/usr/bin/env python3
"""
Pre-commit hook for Soleco security checks.

This script runs basic security checks on the files being committed.
It should be installed as a pre-commit hook in the .git/hooks directory.

To install:
1. Make this file executable: chmod +x pre-commit-hook.py
2. Create a symlink in .git/hooks: ln -s ../../security/pre-commit-hook.py .git/hooks/pre-commit
   Or copy this file to .git/hooks/pre-commit
"""

import os
import sys
import subprocess
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pre-commit-hook')

def get_staged_python_files():
    """Get a list of staged Python files."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
            capture_output=True,
            text=True,
            check=True
        )
        files = result.stdout.strip().split('\n')
        return [f for f in files if f.endswith('.py') and os.path.exists(f)]
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get staged files: {e}")
        return []

def check_for_secrets(file_path):
    """Check for hardcoded secrets in a file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
        # Patterns for potential secrets
        patterns = [
            # API keys
            r'api[_-]?key["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
            r'api[_-]?secret["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
            # AWS keys
            r'aws[_-]?access[_-]?key[_-]?id["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
            r'aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
            # Private keys
            r'private[_-]?key["\']?\s*[:=]\s*["\']([a-zA-Z0-9/+]{30,})["\']',
            r'-----BEGIN PRIVATE KEY-----',
            r'-----BEGIN RSA PRIVATE KEY-----',
            r'-----BEGIN DSA PRIVATE KEY-----',
            r'-----BEGIN EC PRIVATE KEY-----',
            # Passwords
            r'password["\']?\s*[:=]\s*["\']([^"\']{8,})["\']',
            r'passwd["\']?\s*[:=]\s*["\']([^"\']{8,})["\']',
            # Tokens
            r'token["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-.]{20,})["\']',
            r'secret["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-.]{20,})["\']',
            # Solana keys
            r'[1-9A-HJ-NP-Za-km-z]{32,44}',
        ]
        
        findings = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            if matches or re.search(pattern, content):
                findings.append(pattern)
        
        return findings

def check_for_security_issues(file_path):
    """Check for common security issues in a file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
        # Patterns for potential security issues
        patterns = {
            'Hardcoded IP address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            'Hardcoded port': r'port\s*=\s*\d{1,5}',
            'Hardcoded URL': r'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(/[a-zA-Z0-9\-\._~:/?#\[\]@!$&\'\(\)\*\+,;=]*)?',
            'SQL injection vulnerability': r'execute\([\'"].*?\%.*?[\'"].*?,',
            'Command injection vulnerability': r'os\.system\(|subprocess\.call\(|subprocess\.Popen\(|eval\(|exec\(',
            'Insecure deserialization': r'pickle\.loads|yaml\.load\([^s]',
            'Insecure random': r'random\.|randint|randrange',
            'Insecure hash': r'md5|sha1',
            'Insecure cipher': r'DES|RC4|Blowfish',
            'Debug flag': r'DEBUG\s*=\s*True',
            'Bare except': r'except\s*:',
            'Pass in except': r'except.*?:\s*pass',
        }
        
        findings = {}
        for issue, pattern in patterns.items():
            if re.search(pattern, content):
                findings[issue] = pattern
        
        return findings

def run_bandit(files):
    """Run bandit on the specified files."""
    if not files:
        return True
    
    try:
        cmd = ['bandit', '-r'] + files
        logger.info(f"Running bandit: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning("Bandit found issues:")
            print(result.stdout)
            return False
        
        return True
    except FileNotFoundError:
        logger.warning("Bandit not found. Install with: pip install bandit")
        return True
    except Exception as e:
        logger.error(f"Failed to run bandit: {e}")
        return True

def main():
    """Main entry point."""
    files = get_staged_python_files()
    if not files:
        logger.info("No Python files to check")
        return 0
    
    logger.info(f"Checking {len(files)} Python files")
    
    all_clear = True
    
    # Check for secrets
    for file_path in files:
        secret_findings = check_for_secrets(file_path)
        if secret_findings:
            logger.warning(f"Potential secrets found in {file_path}:")
            for pattern in secret_findings:
                logger.warning(f"  - Matches pattern: {pattern}")
            all_clear = False
    
    # Check for security issues
    for file_path in files:
        security_findings = check_for_security_issues(file_path)
        if security_findings:
            logger.warning(f"Potential security issues found in {file_path}:")
            for issue, pattern in security_findings.items():
                logger.warning(f"  - {issue} (pattern: {pattern})")
            all_clear = False
    
    # Run bandit
    if not run_bandit(files):
        all_clear = False
    
    if not all_clear:
        logger.error("Security issues found. Please fix them before committing.")
        logger.error("To bypass this check, use git commit --no-verify")
        return 1
    
    logger.info("No security issues found")
    return 0

if __name__ == "__main__":
    sys.exit(main())
