#!/usr/bin/env python3
"""
Setup script for installing security audit tools.

This script installs the necessary tools for performing security audits
on the Soleco codebase.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('setup_security_tools')

def install_requirements():
    """Install required packages from requirements.txt."""
    requirements_file = Path(__file__).parent / 'requirements.txt'
    
    if not requirements_file.exists():
        logger.error(f"Requirements file not found: {requirements_file}")
        return False
    
    logger.info("Installing security audit tools...")
    
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)],
            check=True
        )
        logger.info("Successfully installed security audit tools")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install requirements: {e}")
        return False

def setup_pre_commit_hook():
    """Set up a pre-commit hook for security scanning."""
    git_dir = Path(os.getcwd()).parent / '.git'
    hooks_dir = git_dir / 'hooks'
    
    if not git_dir.exists():
        logger.warning("Not a git repository, skipping pre-commit hook setup")
        return False
    
    if not hooks_dir.exists():
        hooks_dir.mkdir(exist_ok=True)
    
    pre_commit_path = hooks_dir / 'pre-commit'
    
    logger.info("Setting up pre-commit hook for security scanning...")
    
    pre_commit_content = """#!/bin/sh
# Security pre-commit hook
echo "Running security checks..."

# Run bandit on changed Python files
CHANGED_PY_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\\.py$')
if [ -n "$CHANGED_PY_FILES" ]; then
    echo "Running Bandit on changed Python files..."
    bandit -r $CHANGED_PY_FILES || { echo "Bandit found security issues!"; exit 1; }
fi

# Run safety check on requirements
echo "Checking dependencies for vulnerabilities..."
safety check -r backend/requirements.txt || { echo "Safety found vulnerable dependencies!"; exit 1; }

echo "Security checks passed!"
exit 0
"""
    
    try:
        with open(pre_commit_path, 'w') as f:
            f.write(pre_commit_content)
        
        # Make the hook executable
        os.chmod(pre_commit_path, 0o755)
        
        logger.info(f"Pre-commit hook installed at {pre_commit_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to set up pre-commit hook: {e}")
        return False

def main():
    """Main entry point."""
    success = install_requirements()
    
    if success:
        setup_pre_commit_hook()
        
        logger.info("""
Security tools setup complete!

You can now run the security audit with:
    python security_audit.py

Available tools:
- Bandit: Static analysis for Python security issues
- Safety: Check dependencies for known vulnerabilities
- Pylint: General code quality and potential security issues
- Flake8: Code style and potential security issues
- Semgrep: Pattern-based security scanning
""")
    else:
        logger.error("Failed to set up security tools")
        sys.exit(1)

if __name__ == "__main__":
    main()
