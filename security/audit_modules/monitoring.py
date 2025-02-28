"""
Monitoring and Incident Response Audit Module

This module checks for issues related to monitoring and incident response:
- Logging configuration
- Error handling
- Intrusion detection
- Incident response procedures
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('security_audit.monitoring')

def run_audit(codebase_path):
    """
    Run the monitoring and incident response audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check for logging configuration
    findings.extend(check_logging_configuration(codebase_path))
    
    # Check for error handling
    findings.extend(check_error_handling(codebase_path))
    
    # Check for intrusion detection
    findings.extend(check_intrusion_detection(codebase_path))
    
    # Check for incident response procedures
    findings.extend(check_incident_response(codebase_path))
    
    return findings

def check_logging_configuration(codebase_path):
    """Check for proper logging configuration."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    # Check for logging imports and configuration
    logging_configured = False
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for logging imports
                if 'import logging' in content:
                    # Check for logging configuration
                    if 'logging.basicConfig' in content or 'logging.config' in content:
                        logging_configured = True
                        break
            except UnicodeDecodeError:
                continue
    
    if not logging_configured:
        findings.append({
            'title': 'Missing Logging Configuration',
            'description': 'No proper logging configuration was found in the codebase.',
            'location': codebase_path,
            'severity': 'medium',
            'recommendation': 'Implement proper logging configuration with appropriate log levels, formats, and handlers.',
            'cwe': 'CWE-778: Insufficient Logging'
        })
    
    # Check for sensitive data in logs
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for logging statements with potential sensitive data
                log_statements = re.findall(r'log(?:ger)?\.(?:debug|info|warning|error|critical|exception)\((.*?)\)', content, re.DOTALL)
                
                for statement in log_statements:
                    sensitive_patterns = [
                        r'password', r'secret', r'token', r'key', r'credential',
                        r'auth', r'jwt', r'private', r'ssn', r'credit'
                    ]
                    
                    for pattern in sensitive_patterns:
                        if re.search(pattern, statement, re.IGNORECASE):
                            findings.append({
                                'title': 'Potential Sensitive Data in Logs',
                                'description': f'Logging statements may contain sensitive data ({pattern}).',
                                'location': str(file_path),
                                'severity': 'medium',
                                'recommendation': 'Ensure sensitive data is redacted or masked before logging.',
                                'cwe': 'CWE-532: Insertion of Sensitive Information into Log File'
                            })
                            break
            except UnicodeDecodeError:
                continue
    
    return findings

def check_error_handling(codebase_path):
    """Check for proper error handling."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for bare except statements
                bare_excepts = re.findall(r'except\s*:', content)
                if bare_excepts:
                    findings.append({
                        'title': 'Bare Except Statements',
                        'description': f'The file contains {len(bare_excepts)} bare except statements, which can catch unexpected exceptions and hide errors.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Specify the exception types to catch and handle each appropriately.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for pass in except blocks
                pass_in_except = re.findall(r'except.*?:\s*pass', content, re.DOTALL)
                if pass_in_except:
                    findings.append({
                        'title': 'Empty Except Blocks',
                        'description': f'The file contains {len(pass_in_except)} except blocks with pass, which silently ignore exceptions.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Handle exceptions properly by logging them and taking appropriate action.',
                        'cwe': 'CWE-390: Detection of Error Condition Without Action'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_intrusion_detection(codebase_path):
    """Check for intrusion detection mechanisms."""
    findings = []
    
    # Look for security monitoring or intrusion detection
    security_monitoring_found = False
    
    # Check for common security monitoring libraries or patterns
    monitoring_patterns = [
        r'fail2ban', r'intrusion', r'detection', r'monitoring', r'alert',
        r'anomaly', r'threshold', r'rate limit', r'ban', r'block'
    ]
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read().lower()
                
                for pattern in monitoring_patterns:
                    if re.search(pattern, content):
                        security_monitoring_found = True
                        break
                
                if security_monitoring_found:
                    break
            except UnicodeDecodeError:
                continue
    
    if not security_monitoring_found:
        findings.append({
            'title': 'Missing Intrusion Detection',
            'description': 'No evidence of intrusion detection or security monitoring was found in the codebase.',
            'location': codebase_path,
            'severity': 'medium',
            'recommendation': 'Implement intrusion detection mechanisms such as failed login monitoring, rate limiting, and anomaly detection.',
            'cwe': 'CWE-778: Insufficient Logging'
        })
    
    return findings

def check_incident_response(codebase_path):
    """Check for incident response procedures."""
    findings = []
    
    # Look for incident response documentation
    incident_response_found = False
    
    # Check for common incident response file names
    incident_response_files = [
        'incident_response.md', 'incident.md', 'security_incident.md',
        'incident_response_plan.md', 'security_response.md', 'incident_handling.md',
        'incident_response.txt', 'incident.txt', 'security_incident.txt',
        'incident_response_plan.txt', 'security_response.txt', 'incident_handling.txt'
    ]
    
    for root, _, files in os.walk(codebase_path):
        for file in files:
            if file.lower() in incident_response_files:
                incident_response_found = True
                break
        
        if incident_response_found:
            break
    
    if not incident_response_found:
        findings.append({
            'title': 'Missing Incident Response Procedures',
            'description': 'No incident response procedures or documentation was found in the codebase.',
            'location': codebase_path,
            'severity': 'medium',
            'recommendation': 'Develop and document incident response procedures for handling security incidents.',
            'cwe': 'CWE-1053: Missing Documentation for Design'
        })
    
    return findings
