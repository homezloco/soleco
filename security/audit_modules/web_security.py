"""
Web Security Audit Module

This module checks for issues related to web security:
- CSRF protection
- XSS prevention
- Content Security Policy
- HTTP security headers
- Cookie security
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('security_audit.web_security')

def run_audit(codebase_path):
    """
    Run the web security audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check for CSRF protection
    findings.extend(check_csrf_protection(codebase_path))
    
    # Check for XSS prevention
    findings.extend(check_xss_prevention(codebase_path))
    
    # Check for Content Security Policy
    findings.extend(check_content_security_policy(codebase_path))
    
    # Check for HTTP security headers
    findings.extend(check_security_headers(codebase_path))
    
    # Check for cookie security
    findings.extend(check_cookie_security(codebase_path))
    
    return findings

def check_csrf_protection(codebase_path):
    """Check for CSRF protection."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    # Check for CSRF protection in frameworks
    csrf_protection_found = False
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for FastAPI CSRF middleware or similar
                if re.search(r'csrf|CSRFProtect|csrf_protect|CSRFMiddleware', content):
                    csrf_protection_found = True
                    break
            except UnicodeDecodeError:
                continue
    
    if not csrf_protection_found:
        findings.append({
            'title': 'Missing CSRF Protection',
            'description': 'No CSRF protection mechanisms were found in the codebase.',
            'location': codebase_path,
            'severity': 'high',
            'recommendation': 'Implement CSRF protection for all state-changing operations. Use CSRF tokens and validate them on the server.',
            'cwe': 'CWE-352: Cross-Site Request Forgery (CSRF)'
        })
    
    # Check for forms without CSRF tokens
    html_files = list(Path(codebase_path).rglob('*.html')) + list(Path(codebase_path).rglob('*.htm'))
    
    for file_path in html_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Find forms
                forms = re.findall(r'<form[^>]*>.*?</form>', content, re.DOTALL | re.IGNORECASE)
                
                for form in forms:
                    # Check if the form has a CSRF token
                    has_csrf_token = re.search(r'csrf|_token|csrfmiddlewaretoken', form, re.IGNORECASE)
                    
                    if not has_csrf_token:
                        findings.append({
                            'title': 'Form Without CSRF Token',
                            'description': 'A form was found without a CSRF token.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Add CSRF tokens to all forms that modify state.',
                            'cwe': 'CWE-352: Cross-Site Request Forgery (CSRF)'
                        })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_xss_prevention(codebase_path):
    """Check for XSS prevention."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    # Check for templates with unescaped variables
    template_files = list(Path(codebase_path).rglob('*.html')) + list(Path(codebase_path).rglob('*.htm')) + list(Path(codebase_path).rglob('*.j2'))
    
    for file_path in template_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Look for potentially unsafe template variables
                # This is a simplified check and may have false positives/negatives
                unsafe_patterns = [
                    r'{{\s*[^|]*\s*}}',  # Jinja2/Django without filters
                    r'v-html=',  # Vue.js v-html directive
                    r'dangerouslySetInnerHTML',  # React
                    r'innerHTML\s*=',  # Direct DOM manipulation
                ]
                
                for pattern in unsafe_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        findings.append({
                            'title': 'Potential XSS Vulnerability',
                            'description': f'The template contains potentially unsafe output that may lead to XSS.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Always escape output in templates. Use safe filters or sanitize user input.',
                            'cwe': 'CWE-79: Improper Neutralization of Input During Web Page Generation (Cross-site Scripting)'
                        })
                        break
            except UnicodeDecodeError:
                continue
    
    # Check for JavaScript files with potential DOM-based XSS
    js_files = list(Path(codebase_path).rglob('*.js'))
    
    for file_path in js_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Look for potentially unsafe DOM manipulation
                unsafe_patterns = [
                    r'document\.write\(',
                    r'\.innerHTML\s*=',
                    r'\.outerHTML\s*=',
                    r'\.insertAdjacentHTML\(',
                    r'eval\(',
                    r'setTimeout\(\s*[\'"`]',
                    r'setInterval\(\s*[\'"`]',
                    r'new\s+Function\(',
                ]
                
                for pattern in unsafe_patterns:
                    if re.search(pattern, content):
                        findings.append({
                            'title': 'Potential DOM-based XSS',
                            'description': f'The JavaScript code contains potentially unsafe DOM manipulation that may lead to XSS.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Use safe DOM APIs like textContent instead of innerHTML. Sanitize user input before inserting into the DOM.',
                            'cwe': 'CWE-79: Improper Neutralization of Input During Web Page Generation (Cross-site Scripting)'
                        })
                        break
            except UnicodeDecodeError:
                continue
    
    return findings

def check_content_security_policy(codebase_path):
    """Check for Content Security Policy."""
    findings = []
    
    # Find all Python files that might set headers
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    # Check for CSP headers
    csp_found = False
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for CSP headers
                if re.search(r'Content-Security-Policy', content):
                    csp_found = True
                    break
            except UnicodeDecodeError:
                continue
    
    if not csp_found:
        findings.append({
            'title': 'Missing Content Security Policy',
            'description': 'No Content Security Policy headers were found in the codebase.',
            'location': codebase_path,
            'severity': 'medium',
            'recommendation': 'Implement a Content Security Policy to mitigate XSS and other code injection attacks.',
            'cwe': 'CWE-1021: Improper Restriction of Rendered UI Layers or Frames'
        })
    
    return findings

def check_security_headers(codebase_path):
    """Check for HTTP security headers."""
    findings = []
    
    # Find all Python files that might set headers
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    # Security headers to check for
    security_headers = {
        'X-Content-Type-Options': False,
        'X-Frame-Options': False,
        'X-XSS-Protection': False,
        'Strict-Transport-Security': False,
        'Referrer-Policy': False,
        'Permissions-Policy': False,
    }
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for each security header
                for header in security_headers:
                    if re.search(header, content):
                        security_headers[header] = True
            except UnicodeDecodeError:
                continue
    
    # Report missing security headers
    for header, found in security_headers.items():
        if not found:
            findings.append({
                'title': f'Missing {header} Header',
                'description': f'The {header} security header was not found in the codebase.',
                'location': codebase_path,
                'severity': 'low',
                'recommendation': f'Implement the {header} header to improve security.',
                'cwe': 'CWE-693: Protection Mechanism Failure'
            })
    
    return findings

def check_cookie_security(codebase_path):
    """Check for cookie security."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for cookie setting without secure flags
                cookie_settings = re.findall(r'set_cookie\(.*?\)', content, re.DOTALL)
                
                for cookie in cookie_settings:
                    # Check for secure flag
                    has_secure = 'secure=' in cookie.lower() and 'secure=False' not in cookie.lower()
                    # Check for httponly flag
                    has_httponly = 'httponly=' in cookie.lower() and 'httponly=False' not in cookie.lower()
                    # Check for samesite flag
                    has_samesite = 'samesite=' in cookie.lower()
                    
                    if not (has_secure and has_httponly and has_samesite):
                        findings.append({
                            'title': 'Insecure Cookie Settings',
                            'description': 'Cookies are being set without proper security flags.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Set the secure, httpOnly, and SameSite flags for all cookies.',
                            'cwe': 'CWE-614: Sensitive Cookie in HTTPS Session Without Secure Attribute'
                        })
                        break
            except UnicodeDecodeError:
                continue
    
    return findings
