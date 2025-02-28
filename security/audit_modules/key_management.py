"""
Key Management Audit Module

This module checks for issues related to API key and secret management:
- Hardcoded API keys
- Insecure storage of secrets
- Lack of key rotation mechanisms
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('security_audit.key_management')

def run_audit(codebase_path):
    """
    Run the key management audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check for hardcoded API keys
    findings.extend(check_hardcoded_keys(codebase_path))
    
    # Check for secure secret storage
    findings.extend(check_secret_storage(codebase_path))
    
    # Check for key rotation mechanisms
    findings.extend(check_key_rotation(codebase_path))
    
    return findings

def check_hardcoded_keys(codebase_path):
    """Check for hardcoded API keys and secrets."""
    findings = []
    
    # Common API key patterns
    api_key_patterns = [
        r'api[-_]?key\s*=\s*[\'"]([^\'"]{8,})[\'"]',
        r'secret[-_]?key\s*=\s*[\'"]([^\'"]{8,})[\'"]',
        r'password\s*=\s*[\'"]([^\'"]{8,})[\'"]',
        r'token\s*=\s*[\'"]([^\'"]{8,})[\'"]',
        r'auth[-_]?token\s*=\s*[\'"]([^\'"]{8,})[\'"]',
        r'access[-_]?token\s*=\s*[\'"]([^\'"]{8,})[\'"]',
        r'client[-_]?secret\s*=\s*[\'"]([^\'"]{8,})[\'"]',
    ]
    
    # Exclude patterns (common false positives)
    exclude_patterns = [
        r'os\.getenv',
        r'env\.get',
        r'config\.get',
        r'placeholder',
        r'example',
        r'your-api-key',
    ]
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                for pattern in api_key_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    
                    for match in matches:
                        # Check if this is a false positive
                        line = content[max(0, match.start() - 50):min(len(content), match.end() + 50)]
                        if any(re.search(exclude, line) for exclude in exclude_patterns):
                            continue
                        
                        # This is likely a hardcoded key
                        key_value = match.group(1)
                        masked_key = key_value[:4] + '*' * (len(key_value) - 8) + key_value[-4:] if len(key_value) > 8 else '****'
                        
                        findings.append({
                            'title': 'Hardcoded API Key or Secret',
                            'description': f'A hardcoded API key or secret was found: {masked_key}',
                            'location': f'{file_path}:{content[:match.start()].count(os.linesep) + 1}',
                            'severity': 'high',
                            'recommendation': 'Move all API keys and secrets to environment variables or a secure secrets management solution.',
                            'cwe': 'CWE-798: Use of Hard-coded Credentials'
                        })
            except UnicodeDecodeError:
                logger.warning(f"Could not decode file: {file_path}")
    
    return findings

def check_secret_storage(codebase_path):
    """Check for secure secret storage mechanisms."""
    findings = []
    
    # Look for config files
    config_files = list(Path(codebase_path).rglob('config.py')) + list(Path(codebase_path).rglob('settings.py'))
    
    env_file_usage = False
    vault_usage = False
    aws_secrets_usage = False
    
    for file_path in config_files:
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Check for environment variable usage
            if re.search(r'load_dotenv\(\)', content) or re.search(r'os\.getenv', content):
                env_file_usage = True
            
            # Check for advanced secret management
            if re.search(r'vault', content, re.IGNORECASE):
                vault_usage = True
            
            if re.search(r'secretsmanager', content) or re.search(r'aws.*secrets', content, re.IGNORECASE):
                aws_secrets_usage = True
    
    if not env_file_usage and not vault_usage and not aws_secrets_usage:
        findings.append({
            'title': 'Insecure Secret Management',
            'description': 'No secure secret management solution was found. Secrets may be stored insecurely.',
            'location': codebase_path,
            'severity': 'medium',
            'recommendation': 'Use environment variables (.env files) at minimum, or preferably a dedicated secrets management solution like HashiCorp Vault or AWS Secrets Manager.',
            'cwe': 'CWE-522: Insufficiently Protected Credentials'
        })
    elif env_file_usage and not vault_usage and not aws_secrets_usage:
        findings.append({
            'title': 'Basic Secret Management',
            'description': 'The application uses environment variables for secret management, which is better than hardcoding but not ideal for production.',
            'location': codebase_path,
            'severity': 'low',
            'recommendation': 'Consider using a dedicated secrets management solution like HashiCorp Vault or AWS Secrets Manager for production environments.',
            'cwe': 'CWE-522: Insufficiently Protected Credentials'
        })
    
    return findings

def check_key_rotation(codebase_path):
    """Check for key rotation mechanisms."""
    findings = []
    
    # Look for key rotation implementation
    rotation_files = []
    for root, _, files in os.walk(codebase_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        content = f.read()
                        if 'rotat' in content.lower() and ('key' in content.lower() or 'secret' in content.lower() or 'token' in content.lower()):
                            rotation_files.append(file_path)
                    except UnicodeDecodeError:
                        continue
    
    if not rotation_files:
        findings.append({
            'title': 'Missing Key Rotation',
            'description': 'No key rotation mechanism was found. API keys and secrets should be rotated regularly.',
            'location': codebase_path,
            'severity': 'medium',
            'recommendation': 'Implement a key rotation mechanism to regularly rotate API keys and secrets.',
            'cwe': 'CWE-798: Use of Hard-coded Credentials'
        })
    
    return findings
