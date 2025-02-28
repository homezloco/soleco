"""
Dependency Security Audit Module

This module checks for security issues in project dependencies:
- Outdated packages with known vulnerabilities
- Insecure dependency sources
- Lack of dependency pinning
"""

import os
import re
import logging
import subprocess
import json
from pathlib import Path

logger = logging.getLogger('security_audit.dependency_security')

# Known vulnerable package versions (example - would be updated regularly)
KNOWN_VULNERABILITIES = {
    'aiohttp': [
        {'version': '<3.8.5', 'cve': 'CVE-2023-24329', 'severity': 'high', 'description': 'HTTP Request Smuggling vulnerability'},
    ],
    'cryptography': [
        {'version': '<39.0.1', 'cve': 'CVE-2023-23931', 'severity': 'medium', 'description': 'Timing side-channel vulnerability'},
    ],
    'fastapi': [
        {'version': '<0.95.2', 'cve': 'CVE-2023-29159', 'severity': 'medium', 'description': 'Path traversal vulnerability'},
    ],
    'pydantic': [
        {'version': '<1.10.8', 'cve': 'CVE-2023-36188', 'severity': 'medium', 'description': 'Denial of service vulnerability'},
    ],
    'solana': [
        {'version': '<0.30.0', 'cve': 'N/A', 'severity': 'medium', 'description': 'Potential transaction validation issues'},
    ],
}

def run_audit(codebase_path):
    """
    Run the dependency security audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check for requirements files
    requirements_files = list(Path(codebase_path).rglob('requirements*.txt'))
    
    if not requirements_files:
        findings.append({
            'title': 'Missing Requirements File',
            'description': 'No requirements.txt file was found. This makes it difficult to track and audit dependencies.',
            'location': codebase_path,
            'severity': 'low',
            'recommendation': 'Create a requirements.txt file to track all project dependencies.',
            'cwe': 'CWE-1104: Use of Unmaintained Third Party Components'
        })
        return findings
    
    # Check each requirements file
    for req_file in requirements_files:
        findings.extend(check_requirements_file(req_file))
    
    # Try to run safety check if available
    findings.extend(run_safety_check(codebase_path))
    
    return findings

def check_requirements_file(req_file):
    """Check a requirements.txt file for security issues."""
    findings = []
    
    with open(req_file, 'r') as f:
        content = f.read()
        
        # Parse requirements
        dependencies = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                dependencies.append(line)
        
        # Check for unpinned dependencies
        unpinned = []
        for dep in dependencies:
            if not re.search(r'==\d+\.\d+\.\d+', dep) and not dep.startswith('-e ') and not dep.startswith('-r '):
                unpinned.append(dep.split('[')[0].split('>')[0].split('<')[0].strip())
        
        if unpinned:
            findings.append({
                'title': 'Unpinned Dependencies',
                'description': f'The following dependencies are not pinned to specific versions: {", ".join(unpinned)}',
                'location': str(req_file),
                'severity': 'medium',
                'recommendation': 'Pin all dependencies to specific versions using the == operator.',
                'cwe': 'CWE-1104: Use of Unmaintained Third Party Components'
            })
        
        # Check for known vulnerable versions
        for dep in dependencies:
            # Extract package name and version
            match = re.match(r'([a-zA-Z0-9_-]+)([<>=~!]+)([0-9a-zA-Z.]+)', dep)
            if match:
                package, operator, version = match.groups()
                
                if package in KNOWN_VULNERABILITIES:
                    for vuln in KNOWN_VULNERABILITIES[package]:
                        if operator != '==' or is_vulnerable_version(version, vuln['version']):
                            findings.append({
                                'title': f'Vulnerable Dependency: {package}',
                                'description': f'{package} {operator}{version} has a known vulnerability: {vuln["description"]} ({vuln["cve"]})',
                                'location': str(req_file),
                                'severity': vuln['severity'],
                                'recommendation': f'Update {package} to a non-vulnerable version.',
                                'cwe': 'CWE-1104: Use of Unmaintained Third Party Components'
                            })
    
    return findings

def is_vulnerable_version(current, vulnerable_expr):
    """Check if the current version is vulnerable according to the expression."""
    # This is a simplified version - in a real implementation, you would use
    # a proper version comparison library like packaging.version
    if vulnerable_expr.startswith('<'):
        # Vulnerable if less than specified version
        return current < vulnerable_expr[1:]
    return False

def run_safety_check(codebase_path):
    """Run safety check if available."""
    findings = []
    
    try:
        # Check if safety is installed
        result = subprocess.run(['safety', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.info("Safety not installed, skipping dependency vulnerability scan")
            findings.append({
                'title': 'Safety Tool Not Installed',
                'description': 'The safety tool for checking Python dependencies for known vulnerabilities is not installed.',
                'location': codebase_path,
                'severity': 'info',
                'recommendation': 'Install safety with "pip install safety" and run "safety check" regularly.',
                'cwe': 'CWE-1104: Use of Unmaintained Third Party Components'
            })
            return findings
        
        # Run safety check
        requirements_files = list(Path(codebase_path).rglob('requirements*.txt'))
        for req_file in requirements_files:
            result = subprocess.run(['safety', 'check', '-r', str(req_file), '--json'], capture_output=True, text=True)
            
            if result.returncode != 0:
                try:
                    # Parse safety output
                    safety_results = json.loads(result.stdout)
                    
                    for vuln in safety_results.get('vulnerabilities', []):
                        findings.append({
                            'title': f'Vulnerable Dependency: {vuln["package_name"]}',
                            'description': f'{vuln["package_name"]} {vuln["vulnerable_spec"]} has a known vulnerability: {vuln["advisory"]}',
                            'location': str(req_file),
                            'severity': vuln.get('severity', 'medium'),
                            'recommendation': f'Update {vuln["package_name"]} to {vuln.get("fix_version", "the latest version")}.',
                            'cwe': 'CWE-1104: Use of Unmaintained Third Party Components'
                        })
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse safety output: {result.stdout}")
    
    except FileNotFoundError:
        logger.info("Safety not installed, skipping dependency vulnerability scan")
        findings.append({
            'title': 'Safety Tool Not Installed',
            'description': 'The safety tool for checking Python dependencies for known vulnerabilities is not installed.',
            'location': codebase_path,
            'severity': 'info',
            'recommendation': 'Install safety with "pip install safety" and run "safety check" regularly.',
            'cwe': 'CWE-1104: Use of Unmaintained Third Party Components'
        })
    
    return findings
