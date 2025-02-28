"""
Transaction Security Audit Module

This module checks for security issues related to blockchain transactions:
- Transaction validation
- Signature verification
- Simulation before execution
- Gas limit controls
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('security_audit.transaction_security')

def run_audit(codebase_path):
    """
    Run the transaction security audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check transaction validation
    findings.extend(check_transaction_validation(codebase_path))
    
    # Check signature verification
    findings.extend(check_signature_verification(codebase_path))
    
    # Check transaction simulation
    findings.extend(check_transaction_simulation(codebase_path))
    
    # Check gas limit controls
    findings.extend(check_gas_limit_controls(codebase_path))
    
    return findings

def check_transaction_validation(codebase_path):
    """Check for proper transaction validation."""
    findings = []
    
    # Find files that handle transactions
    transaction_files = []
    for root, _, files in os.walk(codebase_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        content = f.read().lower()
                        if ('transaction' in content or 'tx' in content) and ('solana' in content or 'blockchain' in content):
                            transaction_files.append(file_path)
                    except UnicodeDecodeError:
                        continue
    
    for file_path in transaction_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for validation
                has_validation = re.search(r'validate|verify|check|confirm', content, re.IGNORECASE)
                
                if not has_validation:
                    findings.append({
                        'title': 'Missing Transaction Validation',
                        'description': 'The file appears to handle blockchain transactions without proper validation.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Implement proper validation for all blockchain transactions to prevent errors or attacks.',
                        'cwe': 'CWE-345: Insufficient Verification of Data Authenticity'
                    })
            except UnicodeDecodeError:
                logger.warning(f"Could not decode file: {file_path}")
    
    return findings

def check_signature_verification(codebase_path):
    """Check for proper signature verification."""
    findings = []
    
    # Find files that handle signatures
    signature_files = []
    for root, _, files in os.walk(codebase_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        content = f.read().lower()
                        if 'signature' in content and ('solana' in content or 'blockchain' in content):
                            signature_files.append(file_path)
                    except UnicodeDecodeError:
                        continue
    
    for file_path in signature_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for verification
                has_verification = re.search(r'verify_signature|verify\s*\(|is_valid|check_signature', content, re.IGNORECASE)
                
                if not has_verification:
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

def check_transaction_simulation(codebase_path):
    """Check for transaction simulation before execution."""
    findings = []
    
    # Find files that might execute transactions
    execution_files = []
    for root, _, files in os.walk(codebase_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        content = f.read().lower()
                        if ('send_transaction' in content or 'execute_transaction' in content) and ('solana' in content or 'blockchain' in content):
                            execution_files.append(file_path)
                    except UnicodeDecodeError:
                        continue
    
    for file_path in execution_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for simulation
                has_simulation = re.search(r'simulate|dry[_-]?run|test[_-]?run', content, re.IGNORECASE)
                
                if not has_simulation:
                    findings.append({
                        'title': 'Missing Transaction Simulation',
                        'description': 'The file appears to execute blockchain transactions without prior simulation.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Always simulate transactions before executing them to detect potential issues.',
                        'cwe': 'CWE-754: Improper Check for Unusual or Exceptional Conditions'
                    })
            except UnicodeDecodeError:
                logger.warning(f"Could not decode file: {file_path}")
    
    return findings

def check_gas_limit_controls(codebase_path):
    """Check for gas limit controls."""
    findings = []
    
    # Find files that might set gas limits
    gas_files = []
    for root, _, files in os.walk(codebase_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        content = f.read().lower()
                        if ('gas' in content or 'fee' in content or 'compute_budget' in content) and ('solana' in content or 'blockchain' in content):
                            gas_files.append(file_path)
                    except UnicodeDecodeError:
                        continue
    
    for file_path in gas_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for gas limit controls
                has_gas_limit = re.search(r'gas_limit|max_gas|compute_budget|max_fee', content, re.IGNORECASE)
                
                if not has_gas_limit:
                    findings.append({
                        'title': 'Missing Gas Limit Controls',
                        'description': 'The file appears to handle blockchain transactions without gas limit controls.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Implement gas limit controls to prevent excessive gas consumption.',
                        'cwe': 'CWE-770: Allocation of Resources Without Limits or Throttling'
                    })
            except UnicodeDecodeError:
                logger.warning(f"Could not decode file: {file_path}")
    
    return findings
