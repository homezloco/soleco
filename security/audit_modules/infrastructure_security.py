"""
Infrastructure Security Audit Module

This module checks for issues related to infrastructure security:
- Deployment security
- Container security
- Network security
- Configuration management
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('security_audit.infrastructure_security')

def run_audit(codebase_path):
    """
    Run the infrastructure security audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check for deployment security
    findings.extend(check_deployment_security(codebase_path))
    
    # Check for container security
    findings.extend(check_container_security(codebase_path))
    
    # Check for network security
    findings.extend(check_network_security(codebase_path))
    
    # Check for configuration management
    findings.extend(check_configuration_management(codebase_path))
    
    return findings

def check_deployment_security(codebase_path):
    """Check for deployment security issues."""
    findings = []
    
    # Check for CI/CD configuration files
    ci_cd_files = [
        '.github/workflows',
        '.gitlab-ci.yml',
        'Jenkinsfile',
        'azure-pipelines.yml',
        'bitbucket-pipelines.yml',
        'cloudbuild.yaml',
        'buildspec.yml',
        'appveyor.yml',
        'travis.yml',
        '.circleci/config.yml'
    ]
    
    ci_cd_found = False
    for ci_cd_file in ci_cd_files:
        if os.path.exists(os.path.join(codebase_path, ci_cd_file)):
            ci_cd_found = True
            break
    
    if not ci_cd_found:
        findings.append({
            'title': 'Missing CI/CD Configuration',
            'description': 'No CI/CD configuration files were found in the codebase.',
            'location': codebase_path,
            'severity': 'low',
            'recommendation': 'Implement CI/CD pipelines with security scanning and testing.',
            'cwe': 'CWE-1053: Missing Documentation for Design'
        })
    
    # Check for deployment scripts
    deployment_scripts = list(Path(codebase_path).glob('deploy*.sh')) + list(Path(codebase_path).glob('deploy*.py'))
    
    for script_path in deployment_scripts:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for hardcoded credentials
                if re.search(r'password|secret|token|key|credential|auth', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Hardcoded Credentials in Deployment Scripts',
                        'description': 'The deployment script may contain hardcoded credentials.',
                        'location': str(script_path),
                        'severity': 'high',
                        'recommendation': 'Use environment variables or a secrets management system for credentials.',
                        'cwe': 'CWE-798: Use of Hard-coded Credentials'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_container_security(codebase_path):
    """Check for container security issues."""
    findings = []
    
    # Check for Dockerfile
    dockerfile_paths = list(Path(codebase_path).glob('**/Dockerfile')) + list(Path(codebase_path).glob('**/dockerfile'))
    
    if not dockerfile_paths:
        # No Dockerfile found, skip this check
        return findings
    
    for dockerfile_path in dockerfile_paths:
        with open(dockerfile_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for root user
                if not re.search(r'USER\s+(?!root)', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Container Running as Root',
                        'description': 'The Dockerfile does not specify a non-root user.',
                        'location': str(dockerfile_path),
                        'severity': 'medium',
                        'recommendation': 'Use a non-root user in the Dockerfile to reduce the impact of container breakout vulnerabilities.',
                        'cwe': 'CWE-250: Execution with Unnecessary Privileges'
                    })
                
                # Check for latest tag
                if re.search(r'FROM\s+[^:]+:latest', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Using Latest Tag in Dockerfile',
                        'description': 'The Dockerfile uses the "latest" tag, which can lead to unpredictable builds.',
                        'location': str(dockerfile_path),
                        'severity': 'low',
                        'recommendation': 'Use specific version tags in Dockerfile to ensure reproducible builds.',
                        'cwe': 'CWE-1104: Use of Unmaintained Third Party Components'
                    })
                
                # Check for secrets in build args
                if re.search(r'ARG\s+(?:PASSWORD|SECRET|TOKEN|KEY|CREDENTIAL|AUTH)', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Secrets in Docker Build Arguments',
                        'description': 'The Dockerfile uses build arguments for secrets, which can be leaked in the image history.',
                        'location': str(dockerfile_path),
                        'severity': 'high',
                        'recommendation': 'Use multi-stage builds and/or Docker secrets instead of build arguments for secrets.',
                        'cwe': 'CWE-798: Use of Hard-coded Credentials'
                    })
                
                # Check for HEALTHCHECK
                if not re.search(r'HEALTHCHECK', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Missing Container Health Check',
                        'description': 'The Dockerfile does not include a HEALTHCHECK instruction.',
                        'location': str(dockerfile_path),
                        'severity': 'low',
                        'recommendation': 'Add a HEALTHCHECK instruction to the Dockerfile to enable container health monitoring.',
                        'cwe': 'CWE-703: Improper Check or Handling of Exceptional Conditions'
                    })
            except UnicodeDecodeError:
                continue
    
    # Check for docker-compose.yml
    compose_paths = list(Path(codebase_path).glob('**/docker-compose.yml')) + list(Path(codebase_path).glob('**/docker-compose.yaml'))
    
    for compose_path in compose_paths:
        with open(compose_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for privileged mode
                if re.search(r'privileged:\s*true', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Container Running in Privileged Mode',
                        'description': 'A container is configured to run in privileged mode, which gives it full access to the host.',
                        'location': str(compose_path),
                        'severity': 'high',
                        'recommendation': 'Avoid using privileged mode. Use specific capabilities instead if needed.',
                        'cwe': 'CWE-250: Execution with Unnecessary Privileges'
                    })
                
                # Check for host network mode
                if re.search(r'network_mode:\s*host', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Container Using Host Network',
                        'description': 'A container is configured to use the host network, which bypasses container network isolation.',
                        'location': str(compose_path),
                        'severity': 'medium',
                        'recommendation': 'Use bridge networks and expose only necessary ports instead of using host network mode.',
                        'cwe': 'CWE-668: Exposure of Resource to Wrong Sphere'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_network_security(codebase_path):
    """Check for network security issues."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for insecure protocols
                if re.search(r'http://(?!localhost|127\.0\.0\.1)', content):
                    findings.append({
                        'title': 'Use of Insecure HTTP Protocol',
                        'description': 'The code uses the insecure HTTP protocol for external resources.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Use HTTPS for all external resources.',
                        'cwe': 'CWE-319: Cleartext Transmission of Sensitive Information'
                    })
                
                # Check for insecure socket connections
                if re.search(r'socket\.(socket|create_connection)', content) and not re.search(r'ssl\.(wrap_socket|create_default_context)', content):
                    findings.append({
                        'title': 'Potential Insecure Socket Connection',
                        'description': 'The code creates socket connections without SSL/TLS.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Use SSL/TLS for all socket connections.',
                        'cwe': 'CWE-319: Cleartext Transmission of Sensitive Information'
                    })
                
                # Check for wildcard CORS
                if re.search(r'(CORS|cors).*["\']\\*["\']', content):
                    findings.append({
                        'title': 'Wildcard CORS Policy',
                        'description': 'The code uses a wildcard CORS policy, which allows any origin to access the API.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Restrict CORS to specific origins instead of using a wildcard.',
                        'cwe': 'CWE-942: Overly Permissive Cross-domain Whitelist'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_configuration_management(codebase_path):
    """Check for configuration management issues."""
    findings = []
    
    # Check for environment variables
    env_files = list(Path(codebase_path).glob('**/.env')) + list(Path(codebase_path).glob('**/.env.*'))
    
    for env_file in env_files:
        with open(env_file, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for sensitive data in .env files
                sensitive_patterns = [
                    r'PASSWORD=',
                    r'SECRET=',
                    r'TOKEN=',
                    r'KEY=',
                    r'CREDENTIAL=',
                    r'AUTH='
                ]
                
                for pattern in sensitive_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append({
                            'title': 'Sensitive Data in Environment File',
                            'description': f'The environment file contains sensitive data ({pattern.replace("=", "")}).',
                            'location': str(env_file),
                            'severity': 'high',
                            'recommendation': 'Do not commit .env files with sensitive data. Use .env.example with placeholders instead.',
                            'cwe': 'CWE-312: Cleartext Storage of Sensitive Information'
                        })
                        break
            except UnicodeDecodeError:
                continue
    
    # Check for config files
    config_files = list(Path(codebase_path).rglob('*.config')) + list(Path(codebase_path).rglob('*.conf')) + list(Path(codebase_path).rglob('config.*'))
    
    for config_file in config_files:
        with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for hardcoded credentials
                if re.search(r'password|secret|token|key|credential|auth', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Hardcoded Credentials in Configuration',
                        'description': 'The configuration file may contain hardcoded credentials.',
                        'location': str(config_file),
                        'severity': 'high',
                        'recommendation': 'Use environment variables or a secrets management system for credentials.',
                        'cwe': 'CWE-798: Use of Hard-coded Credentials'
                    })
            except UnicodeDecodeError:
                continue
    
    # Check for gitignore
    gitignore_path = os.path.join(codebase_path, '.gitignore')
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for ignored sensitive files
                sensitive_patterns = [
                    r'\.env',
                    r'\.pem',
                    r'\.key',
                    r'\.crt',
                    r'\.pfx',
                    r'\.p12',
                    r'secret',
                    r'password',
                    r'credential'
                ]
                
                for pattern in sensitive_patterns:
                    if not re.search(pattern, content, re.IGNORECASE):
                        findings.append({
                            'title': f'Missing {pattern} in .gitignore',
                            'description': f'The .gitignore file does not exclude {pattern} files, which may contain sensitive data.',
                            'location': gitignore_path,
                            'severity': 'low',
                            'recommendation': f'Add {pattern} to .gitignore to prevent accidental commit of sensitive files.',
                            'cwe': 'CWE-312: Cleartext Storage of Sensitive Information'
                        })
            except UnicodeDecodeError:
                continue
    else:
        findings.append({
            'title': 'Missing .gitignore File',
            'description': 'No .gitignore file was found in the codebase.',
            'location': codebase_path,
            'severity': 'low',
            'recommendation': 'Create a .gitignore file to prevent accidental commit of sensitive files.',
            'cwe': 'CWE-312: Cleartext Storage of Sensitive Information'
        })
    
    return findings
