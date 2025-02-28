"""
API Security Audit Module

This module checks for API security issues such as:
- Rate limiting configuration
- CORS settings
- Input validation
- Authentication and authorization
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('security_audit.api_security')

def run_audit(codebase_path):
    """
    Run the API security audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check CORS configuration
    findings.extend(check_cors_config(codebase_path))
    
    # Check rate limiting
    findings.extend(check_rate_limiting(codebase_path))
    
    # Check input validation
    findings.extend(check_input_validation(codebase_path))
    
    # Check authentication
    findings.extend(check_authentication(codebase_path))
    
    return findings

def check_cors_config(codebase_path):
    """Check for insecure CORS configuration."""
    findings = []
    
    # Look for main.py or similar files that might contain CORS config
    main_files = list(Path(codebase_path).rglob('main.py')) + list(Path(codebase_path).rglob('app.py'))
    
    for file_path in main_files:
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Check for wildcard CORS
            if re.search(r'allow_origins=\["?\*"?\]', content):
                findings.append({
                    'title': 'Wildcard CORS Configuration',
                    'description': 'The application uses a wildcard (*) in CORS allow_origins, which allows any origin to make cross-origin requests.',
                    'location': str(file_path),
                    'severity': 'medium',
                    'recommendation': 'Restrict CORS to specific origins that need access to the API. Replace the wildcard with a list of allowed origins.',
                    'cwe': 'CWE-942: Permissive Cross-domain Policy with Untrusted Domains'
                })
    
    return findings

def check_rate_limiting(codebase_path):
    """Check for rate limiting implementation and configuration."""
    findings = []
    
    # Look for rate limiting files
    rate_limit_files = list(Path(codebase_path).rglob('*rate_limit*.py'))
    
    if not rate_limit_files:
        findings.append({
            'title': 'Missing Rate Limiting',
            'description': 'No rate limiting implementation was found. This could make the API vulnerable to DoS attacks.',
            'location': codebase_path,
            'severity': 'medium',
            'recommendation': 'Implement rate limiting for all API endpoints to prevent abuse.',
            'cwe': 'CWE-770: Allocation of Resources Without Limits or Throttling'
        })
    else:
        # Check rate limiting configuration
        for file_path in rate_limit_files:
            with open(file_path, 'r') as f:
                content = f.read()
                
                # Check for high rate limits
                rate_limit_match = re.search(r'requests_per_second:\s*float\s*=\s*(\d+\.\d+)', content)
                if rate_limit_match and float(rate_limit_match.group(1)) > 20:
                    findings.append({
                        'title': 'High Rate Limit',
                        'description': f'The rate limit is set to {rate_limit_match.group(1)} requests per second, which may be too high for some endpoints.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Consider lowering the rate limit for sensitive endpoints to prevent abuse.',
                        'cwe': 'CWE-770: Allocation of Resources Without Limits or Throttling'
                    })
    
    return findings

def check_input_validation(codebase_path):
    """Check for input validation in API endpoints."""
    findings = []
    
    # Look for router files
    router_files = list(Path(codebase_path).rglob('router*.py')) + list(Path(os.path.join(codebase_path, 'routers')).glob('*.py')) if os.path.exists(os.path.join(codebase_path, 'routers')) else []
    
    for file_path in router_files:
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Check for endpoints without validation
            endpoint_matches = re.finditer(r'@router\.(?:get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]', content)
            
            for match in endpoint_matches:
                endpoint = match.group(1)
                
                # Check if Pydantic models are used for validation
                if not re.search(r'def\s+\w+\([^)]*:\s*\w+\s*=', content) and not 'Depends' in content:
                    findings.append({
                        'title': 'Missing Input Validation',
                        'description': f'The endpoint {endpoint} may lack proper input validation.',
                        'location': f'{file_path}:{match.start()}',
                        'severity': 'medium',
                        'recommendation': 'Use Pydantic models or FastAPI dependency injection to validate input data.',
                        'cwe': 'CWE-20: Improper Input Validation'
                    })
    
    return findings

def check_authentication(codebase_path):
    """Check for authentication and authorization mechanisms."""
    findings = []
    
    # Look for authentication files
    auth_files = list(Path(codebase_path).rglob('*auth*.py'))
    
    if not auth_files:
        findings.append({
            'title': 'Missing Authentication',
            'description': 'No authentication implementation was found. This could expose sensitive endpoints.',
            'location': codebase_path,
            'severity': 'high',
            'recommendation': 'Implement proper authentication for all sensitive API endpoints.',
            'cwe': 'CWE-306: Missing Authentication for Critical Function'
        })
    
    # Check for JWT implementation
    jwt_files = [f for f in auth_files if 'jwt' in f.name.lower()]
    if jwt_files:
        for file_path in jwt_files:
            with open(file_path, 'r') as f:
                content = f.read()
                
                # Check for insecure JWT configuration
                if 'algorithms=["HS256"]' in content and not re.search(r'secret_key\s*=\s*os\.getenv', content):
                    findings.append({
                        'title': 'Hardcoded JWT Secret',
                        'description': 'The JWT secret key may be hardcoded instead of being stored in environment variables.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Store JWT secret keys in environment variables and ensure they are sufficiently complex.',
                        'cwe': 'CWE-798: Use of Hard-coded Credentials'
                    })
    
    return findings
