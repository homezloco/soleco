"""
Solana Security Audit Module

This module checks for Solana-specific security issues:
- Program ID validation
- Account ownership validation
- Instruction data validation
- Cross-program invocation security
- Account data deserialization
"""

import os
import re
import logging
from pathlib import Path
import time

logger = logging.getLogger('security_audit.solana_security')

def run_audit(codebase_path):
    """
    Run the Solana security audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    start_time = time.time()
    logger.debug(f"Starting Solana security audit on {codebase_path}")
    
    findings = []
    
    # Check for program ID validation
    logger.debug("Checking for program ID validation issues")
    findings.extend(check_program_id_validation(codebase_path))
    
    # Check for account ownership validation
    logger.debug("Checking for account ownership validation issues")
    findings.extend(check_account_ownership_validation(codebase_path))
    
    # Check for instruction data validation
    logger.debug("Checking for instruction data validation issues")
    findings.extend(check_instruction_data_validation(codebase_path))
    
    # Check for cross-program invocation security
    logger.debug("Checking for cross-program invocation security issues")
    findings.extend(check_cross_program_invocation_security(codebase_path))
    
    # Check for account data deserialization
    logger.debug("Checking for account data deserialization issues")
    findings.extend(check_account_data_deserialization(codebase_path))
    
    logger.debug(f"Solana security audit completed in {time.time() - start_time:.2f} seconds")
    logger.info(f"Total findings: {len(findings)}")
    
    return findings

def find_python_files(codebase_path):
    """Find all Python files in the codebase."""
    logger.debug(f"Finding Python files in {codebase_path}")
    start_time = time.time()
    python_files = list(Path(codebase_path).rglob('*.py'))
    logger.debug(f"Found {len(python_files)} Python files in {time.time() - start_time:.2f} seconds")
    return python_files

def check_program_id_validation(codebase_path):
    """Check for program ID validation issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for program ID usage without validation
                if re.search(r'program_id|programId|program_address|programAddress', content, re.IGNORECASE):
                    if not re.search(r'check.*?program|validate.*?program|verify.*?program', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing Program ID Validation',
                            'description': 'The file uses program IDs but may not validate them before use, which could lead to interacting with malicious programs.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Always validate program IDs against expected values before interacting with Solana programs.',
                            'cwe': 'CWE-345: Insufficient Verification of Data Authenticity'
                        })
                
                # Check for hardcoded program IDs
                if re.search(r'program_id\s*=\s*[\'"][a-zA-Z0-9]{32,}[\'"]|programId\s*=\s*[\'"][a-zA-Z0-9]{32,}[\'"]', content):
                    if not re.search(r'const|PROGRAM_ID|PROGRAM_ADDRESS', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Hardcoded Program ID',
                            'description': 'The file contains hardcoded program IDs, which may make it difficult to update if program addresses change.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Store program IDs in configuration files or constants, and consider using environment variables for different networks.',
                            'cwe': 'CWE-547: Use of Hard-coded, Security-relevant Constants'
                        })
                
                # Check for program ID comparison without proper error handling
                if re.search(r'if\s+.*?program_id\s*==|if\s+.*?programId\s*==', content):
                    if not re.search(r'try|except|error', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Program ID Comparison Without Error Handling',
                            'description': 'The file compares program IDs but may not handle comparison errors properly.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Implement proper error handling for program ID comparison, including logging and appropriate user feedback.',
                            'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                        })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings

def check_account_ownership_validation(codebase_path):
    """Check for account ownership validation issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for account usage without ownership validation
                if re.search(r'account|Account', content) and re.search(r'owner|Owner', content):
                    if not re.search(r'check.*?owner|validate.*?owner|verify.*?owner|assert.*?owner', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing Account Ownership Validation',
                            'description': 'The file uses accounts but may not validate their ownership before use, which could lead to processing data from malicious accounts.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Always validate account ownership before processing account data.',
                            'cwe': 'CWE-284: Improper Access Control'
                        })
                
                # Check for account ownership validation without proper error handling
                if re.search(r'check.*?owner|validate.*?owner|verify.*?owner|assert.*?owner', content, re.IGNORECASE):
                    if not re.search(r'try|except|error', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Account Ownership Validation Without Error Handling',
                            'description': 'The file validates account ownership but may not handle validation errors properly.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Implement proper error handling for account ownership validation, including logging and appropriate user feedback.',
                            'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                        })
                
                # Check for account ownership comparison without proper error handling
                if re.search(r'if\s+.*?owner\s*==|if\s+.*?Owner\s*==', content):
                    if not re.search(r'try|except|error', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Account Ownership Comparison Without Error Handling',
                            'description': 'The file compares account ownership but may not handle comparison errors properly.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Implement proper error handling for account ownership comparison, including logging and appropriate user feedback.',
                            'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                        })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings

def check_instruction_data_validation(codebase_path):
    """Check for instruction data validation issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for instruction data usage without validation
                if re.search(r'instruction|Instruction', content) and re.search(r'data|Data', content):
                    if not re.search(r'check.*?data|validate.*?data|verify.*?data|assert.*?data|schema', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing Instruction Data Validation',
                            'description': 'The file uses instruction data but may not validate it before use, which could lead to processing malformed or malicious instructions.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Always validate instruction data before processing, including checking data length and format.',
                            'cwe': 'CWE-20: Improper Input Validation'
                        })
                
                # Check for instruction data validation without proper error handling
                if re.search(r'check.*?data|validate.*?data|verify.*?data|assert.*?data', content, re.IGNORECASE):
                    if not re.search(r'try|except|error', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Instruction Data Validation Without Error Handling',
                            'description': 'The file validates instruction data but may not handle validation errors properly.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Implement proper error handling for instruction data validation, including logging and appropriate user feedback.',
                            'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                        })
                
                # Check for instruction data deserialization without validation
                if re.search(r'deserialize|Deserialize|decode|Decode|parse|Parse', content) and re.search(r'instruction|Instruction', content):
                    if not re.search(r'try|except|error', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Instruction Data Deserialization Without Error Handling',
                            'description': 'The file deserializes instruction data but may not handle deserialization errors properly.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Implement proper error handling for instruction data deserialization, including logging and appropriate user feedback.',
                            'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                        })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings

def check_cross_program_invocation_security(codebase_path):
    """Check for cross-program invocation security issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for cross-program invocation without program ID validation
                if re.search(r'invoke|Invoke|CPI|cross.*?program', content, re.IGNORECASE):
                    if not re.search(r'check.*?program|validate.*?program|verify.*?program', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Cross-Program Invocation Without Program ID Validation',
                            'description': 'The file performs cross-program invocations but may not validate the target program ID, which could lead to invoking malicious programs.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Always validate target program IDs before performing cross-program invocations.',
                            'cwe': 'CWE-345: Insufficient Verification of Data Authenticity'
                        })
                
                # Check for cross-program invocation without proper error handling
                if re.search(r'invoke|Invoke|CPI|cross.*?program', content, re.IGNORECASE):
                    if not re.search(r'try|except|error', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Cross-Program Invocation Without Error Handling',
                            'description': 'The file performs cross-program invocations but may not handle invocation errors properly.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Implement proper error handling for cross-program invocations, including logging and appropriate user feedback.',
                            'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                        })
                
                # Check for cross-program invocation with hardcoded program IDs
                if re.search(r'invoke|Invoke|CPI|cross.*?program', content, re.IGNORECASE) and re.search(r'[\'"][a-zA-Z0-9]{32,}[\'"]', content):
                    if not re.search(r'const|PROGRAM_ID|PROGRAM_ADDRESS', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Cross-Program Invocation With Hardcoded Program IDs',
                            'description': 'The file performs cross-program invocations with hardcoded program IDs, which may make it difficult to update if program addresses change.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Store program IDs in configuration files or constants, and consider using environment variables for different networks.',
                            'cwe': 'CWE-547: Use of Hard-coded, Security-relevant Constants'
                        })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings

def check_account_data_deserialization(codebase_path):
    """Check for account data deserialization issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for account data deserialization without validation
                if re.search(r'deserialize|Deserialize|decode|Decode|parse|Parse', content) and re.search(r'account|Account', content):
                    if not re.search(r'check.*?data|validate.*?data|verify.*?data|assert.*?data|schema', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Account Data Deserialization Without Validation',
                            'description': 'The file deserializes account data but may not validate it before use, which could lead to processing malformed or malicious data.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Always validate account data before deserialization, including checking data length and format.',
                            'cwe': 'CWE-20: Improper Input Validation'
                        })
                
                # Check for account data deserialization without proper error handling
                if re.search(r'deserialize|Deserialize|decode|Decode|parse|Parse', content) and re.search(r'account|Account', content):
                    if not re.search(r'try|except|error', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Account Data Deserialization Without Error Handling',
                            'description': 'The file deserializes account data but may not handle deserialization errors properly.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Implement proper error handling for account data deserialization, including logging and appropriate user feedback.',
                            'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                        })
                
                # Check for account data size validation
                if re.search(r'account.*?data|Account.*?data', content, re.IGNORECASE):
                    if not re.search(r'len|size|length', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing Account Data Size Validation',
                            'description': 'The file uses account data but may not validate its size before use, which could lead to buffer overflows or other memory-related vulnerabilities.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Always validate account data size before processing, especially when deserializing structured data.',
                            'cwe': 'CWE-131: Incorrect Calculation of Buffer Size'
                        })
                
                # Check for account data type validation
                if re.search(r'account.*?data|Account.*?data', content, re.IGNORECASE):
                    if not re.search(r'isinstance|type|is_a|isA', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing Account Data Type Validation',
                            'description': 'The file uses account data but may not validate its type before use, which could lead to type confusion vulnerabilities.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Always validate account data types before processing, using type checks or schema validation.',
                            'cwe': 'CWE-843: Access of Resource Using Incompatible Type'
                        })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings
