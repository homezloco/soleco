"""
Input Validation Audit Module

This module checks for proper input validation in the codebase:
- API endpoint parameter validation
- User-provided data sanitization
- SQL/NoSQL injection prevention
- Command injection prevention
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('security_audit.input_validation')

def run_audit(codebase_path):
    """
    Run the input validation audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check API endpoint parameter validation
    findings.extend(check_api_validation(codebase_path))
    
    # Check for SQL injection vulnerabilities
    findings.extend(check_sql_injection(codebase_path))
    
    # Check for command injection vulnerabilities
    findings.extend(check_command_injection(codebase_path))
    
    # Check for proper validation of blockchain addresses and signatures
    findings.extend(check_blockchain_validation(codebase_path))
    
    return findings

def check_api_validation(codebase_path):
    """Check for proper API endpoint parameter validation."""
    findings = []
    
    # Find all router files
    router_files = []
    for root, _, files in os.walk(codebase_path):
        if 'routers' in root or 'routes' in root:
            for file in files:
                if file.endswith('.py'):
                    router_files.append(os.path.join(root, file))
    
    for file_path in router_files:
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Find all API endpoints
            endpoint_matches = re.finditer(r'@router\.(?:get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]', content)
            
            for match in endpoint_matches:
                endpoint = match.group(1)
                endpoint_pos = match.start()
                
                # Find the corresponding function
                func_match = re.search(r'async\s+def\s+(\w+)\s*\([^)]*\)\s*:', content[endpoint_pos:])
                if func_match:
                    func_name = func_match.group(1)
                    func_pos = endpoint_pos + func_match.start()
                    
                    # Check for parameter validation
                    has_pydantic = re.search(r':\s*\w+\s*=', content[func_pos:func_pos+500])
                    has_validation = re.search(r'validate|sanitize|check|clean', content[func_pos:func_pos+500], re.IGNORECASE)
                    
                    if not has_pydantic and not has_validation:
                        findings.append({
                            'title': 'Missing Input Validation',
                            'description': f'The endpoint {endpoint} (function {func_name}) may lack proper input validation.',
                            'location': f'{file_path}:{content[:endpoint_pos].count(os.linesep) + 1}',
                            'severity': 'medium',
                            'recommendation': 'Use Pydantic models or explicit validation functions to validate all user input.',
                            'cwe': 'CWE-20: Improper Input Validation'
                        })
    
    return findings

def check_sql_injection(codebase_path):
    """Check for SQL injection vulnerabilities."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for raw SQL queries with string formatting
                sql_matches = re.finditer(r'(?:execute|query|cursor\.execute)\s*\(\s*[f]?[\'"]SELECT|UPDATE|DELETE|INSERT', content)
                
                for match in sql_matches:
                    # Check if using string formatting or concatenation
                    line_start = content[:match.start()].rfind('\n') if '\n' in content[:match.start()] else 0
                    line_end = content[match.end():].find('\n') if '\n' in content[match.end():] else len(content) - match.end()
                    line = content[line_start:match.end() + line_end]
                    
                    if '%' in line or '+' in line or 'f"' in line or 'f\'' in line or '.format' in line:
                        findings.append({
                            'title': 'Potential SQL Injection',
                            'description': 'Raw SQL query uses string formatting or concatenation, which could lead to SQL injection.',
                            'location': f'{file_path}:{content[:match.start()].count(os.linesep) + 1}',
                            'severity': 'high',
                            'recommendation': 'Use parameterized queries or an ORM instead of string formatting/concatenation for SQL queries.',
                            'cwe': 'CWE-89: Improper Neutralization of Special Elements used in an SQL Command'
                        })
            except UnicodeDecodeError:
                logger.warning(f"Could not decode file: {file_path}")
    
    return findings

def check_command_injection(codebase_path):
    """Check for command injection vulnerabilities."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for os.system, subprocess.call, etc. with string formatting
                cmd_matches = re.finditer(r'(?:os\.system|os\.popen|subprocess\.(?:call|run|Popen))\s*\(\s*[f]?[\'"]', content)
                
                for match in cmd_matches:
                    # Check if using string formatting or concatenation
                    line_start = content[:match.start()].rfind('\n') if '\n' in content[:match.start()] else 0
                    line_end = content[match.end():].find('\n') if '\n' in content[match.end():] else len(content) - match.end()
                    line = content[line_start:match.end() + line_end]
                    
                    if '%' in line or '+' in line or 'f"' in line or 'f\'' in line or '.format' in line:
                        findings.append({
                            'title': 'Potential Command Injection',
                            'description': 'Command execution uses string formatting or concatenation, which could lead to command injection.',
                            'location': f'{file_path}:{content[:match.start()].count(os.linesep) + 1}',
                            'severity': 'high',
                            'recommendation': 'Use subprocess.run with the args parameter as a list instead of shell=True or string formatting.',
                            'cwe': 'CWE-78: Improper Neutralization of Special Elements used in an OS Command'
                        })
            except UnicodeDecodeError:
                logger.warning(f"Could not decode file: {file_path}")
    
    return findings

def check_blockchain_validation(codebase_path):
    """Check for proper validation of blockchain addresses and signatures."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for wallet address handling without validation
                if ('wallet' in content.lower() or 'address' in content.lower()) and 'solana' in content.lower():
                    # Check if there's validation
                    has_validation = re.search(r'validate|is_valid|check|verify', content, re.IGNORECASE)
                    
                    if not has_validation:
                        findings.append({
                            'title': 'Missing Blockchain Address Validation',
                            'description': 'The file appears to handle blockchain addresses without proper validation.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Implement proper validation for all blockchain addresses to prevent errors or attacks.',
                            'cwe': 'CWE-20: Improper Input Validation'
                        })
                
                # Check for signature verification
                if 'signature' in content.lower() and 'verify' not in content.lower():
                    findings.append({
                        'title': 'Missing Signature Verification',
                        'description': 'The file appears to handle signatures without proper verification.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Always verify signatures cryptographically before trusting signed data.',
                        'cwe': 'CWE-347: Improper Verification of Cryptographic Signature'
                    })
            except UnicodeDecodeError:
                logger.warning(f"Could not decode file: {file_path}")
    
    return findings
