"""
Data Protection Audit Module

This module checks for issues related to data protection:
- PII handling
- Data encryption
- Data minimization
- Secure storage
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('security_audit.data_protection')

def run_audit(codebase_path):
    """
    Run the data protection audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check for PII handling
    findings.extend(check_pii_handling(codebase_path))
    
    # Check for data encryption
    findings.extend(check_data_encryption(codebase_path))
    
    # Check for data minimization
    findings.extend(check_data_minimization(codebase_path))
    
    # Check for secure storage
    findings.extend(check_secure_storage(codebase_path))
    
    return findings

def check_pii_handling(codebase_path):
    """Check for proper handling of personally identifiable information (PII)."""
    findings = []
    
    # PII patterns to look for
    pii_patterns = [
        r'email',
        r'address',
        r'phone',
        r'name',
        r'ssn',
        r'social security',
        r'birth',
        r'passport',
        r'license',
        r'user.*data',
        r'personal.*data',
    ]
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read().lower()
                
                # Check for PII patterns
                for pattern in pii_patterns:
                    if re.search(pattern, content):
                        # Check for privacy policy or GDPR compliance
                        has_privacy = re.search(r'privacy|gdpr|ccpa|data protection', content)
                        has_consent = re.search(r'consent|opt[- ]in|permission', content)
                        
                        if not has_privacy or not has_consent:
                            findings.append({
                                'title': 'Potential PII Handling Issues',
                                'description': f'The file appears to handle PII ({pattern}) without clear privacy controls or consent mechanisms.',
                                'location': str(file_path),
                                'severity': 'medium',
                                'recommendation': 'Implement proper privacy controls, consent mechanisms, and compliance with privacy regulations like GDPR or CCPA.',
                                'cwe': 'CWE-359: Exposure of Private Personal Information to an Unauthorized Actor'
                            })
                        break  # Only report once per file
            except UnicodeDecodeError:
                logger.warning(f"Could not decode file: {file_path}")
    
    return findings

def check_data_encryption(codebase_path):
    """Check for proper data encryption."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    # Check for encryption usage
    encryption_used = False
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read().lower()
                if 'encrypt' in content or 'cipher' in content or 'cryptography' in content:
                    encryption_used = True
                    break
            except UnicodeDecodeError:
                continue
    
    if not encryption_used:
        findings.append({
            'title': 'Missing Data Encryption',
            'description': 'No evidence of data encryption was found in the codebase.',
            'location': codebase_path,
            'severity': 'medium',
            'recommendation': 'Implement encryption for sensitive data at rest and in transit.',
            'cwe': 'CWE-311: Missing Encryption of Sensitive Data'
        })
    
    # Check for secure encryption algorithms
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for weak encryption
                if re.search(r'DES|MD5|SHA1|RC4', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Weak Encryption Algorithm',
                        'description': 'The file appears to use a weak or outdated encryption algorithm.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Use strong, modern encryption algorithms like AES-256, SHA-256, or better.',
                        'cwe': 'CWE-327: Use of a Broken or Risky Cryptographic Algorithm'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_data_minimization(codebase_path):
    """Check for data minimization principles."""
    findings = []
    
    # Find model files that might define data structures
    model_files = []
    for root, _, files in os.walk(codebase_path):
        if 'models' in root or 'schemas' in root:
            for file in files:
                if file.endswith('.py'):
                    model_files.append(os.path.join(root, file))
    
    for file_path in model_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Look for large models with many fields
                class_matches = re.finditer(r'class\s+(\w+)(?:\(.*\))?\s*:', content)
                
                for match in class_matches:
                    class_name = match.group(1)
                    class_start = match.end()
                    
                    # Find the end of the class (next class or end of file)
                    next_class = re.search(r'class\s+\w+(?:\(.*\))?\s*:', content[class_start:])
                    class_end = class_start + next_class.start() if next_class else len(content)
                    
                    # Count fields in the class
                    class_content = content[class_start:class_end]
                    field_count = len(re.findall(r'^\s+\w+\s*[=:]', class_content, re.MULTILINE))
                    
                    if field_count > 15:  # Arbitrary threshold for "too many fields"
                        findings.append({
                            'title': 'Potential Data Over-Collection',
                            'description': f'The class {class_name} has {field_count} fields, which may indicate collecting more data than necessary.',
                            'location': f'{file_path}:{content[:match.start()].count(os.linesep) + 1}',
                            'severity': 'low',
                            'recommendation': 'Review the data model and apply data minimization principles to collect only necessary data.',
                            'cwe': 'CWE-212: Improper Removal of Sensitive Information Before Storage or Transfer'
                        })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_secure_storage(codebase_path):
    """Check for secure data storage practices."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read().lower()
                
                # Check for plaintext storage
                if ('password' in content or 'secret' in content or 'key' in content) and 'store' in content:
                    # Check if using encryption or hashing
                    has_protection = re.search(r'encrypt|hash|bcrypt|scrypt|pbkdf2', content)
                    
                    if not has_protection:
                        findings.append({
                            'title': 'Potential Plaintext Storage of Sensitive Data',
                            'description': 'The file appears to store sensitive data without encryption or hashing.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Always encrypt sensitive data before storage, and hash passwords using strong algorithms like bcrypt or Argon2.',
                            'cwe': 'CWE-312: Cleartext Storage of Sensitive Information'
                        })
            except UnicodeDecodeError:
                continue
    
    return findings
