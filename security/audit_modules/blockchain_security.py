"""
Blockchain Security Audit Module

This module checks for issues related to blockchain security:
- Solana RPC security
- Transaction validation
- Account validation
- Signature verification
- Error handling in blockchain operations
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('security_audit.blockchain_security')

def run_audit(codebase_path):
    """
    Run the blockchain security audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check for Solana RPC security
    findings.extend(check_rpc_security(codebase_path))
    
    # Check for transaction validation
    findings.extend(check_transaction_validation(codebase_path))
    
    # Check for account validation
    findings.extend(check_account_validation(codebase_path))
    
    # Check for signature verification
    findings.extend(check_signature_verification(codebase_path))
    
    # Check for error handling in blockchain operations
    findings.extend(check_blockchain_error_handling(codebase_path))
    
    return findings

def check_rpc_security(codebase_path):
    """Check for Solana RPC security issues."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for hardcoded RPC endpoints
                rpc_patterns = [
                    r'https?://api\..*\.solana\.com',
                    r'https?://.*\.rpcpool\.com',
                    r'https?://.*\.mainnet\.rpcpool\.com',
                    r'https?://.*\.devnet\.rpcpool\.com',
                    r'https?://.*\.testnet\.rpcpool\.com',
                ]
                
                for pattern in rpc_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        findings.append({
                            'title': 'Hardcoded RPC Endpoint',
                            'description': f'The file contains hardcoded Solana RPC endpoints: {", ".join(matches)}',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Store RPC endpoints in configuration files or environment variables, and implement RPC endpoint rotation or fallback mechanisms.',
                            'cwe': 'CWE-798: Use of Hard-coded Credentials'
                        })
                        break
                
                # Check for lack of RPC rate limiting
                if 'solana' in content.lower() and 'rpc' in content.lower() and not re.search(r'rate.?limit|throttle', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Missing RPC Rate Limiting',
                        'description': 'The file appears to interact with Solana RPC but may not implement rate limiting.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Implement rate limiting for RPC calls to prevent service disruption and excessive charges.',
                        'cwe': 'CWE-770: Allocation of Resources Without Limits or Throttling'
                    })
                
                # Check for lack of RPC response validation
                if 'solana' in content.lower() and 'rpc' in content.lower() and not re.search(r'try|except|error|validate', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Missing RPC Response Validation',
                        'description': 'The file appears to interact with Solana RPC but may not validate responses or handle errors properly.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Validate RPC responses and implement proper error handling for RPC calls.',
                        'cwe': 'CWE-20: Improper Input Validation'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_transaction_validation(codebase_path):
    """Check for transaction validation issues."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for transaction creation without validation
                if re.search(r'Transaction\(', content) and not re.search(r'validate|verify|check', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Missing Transaction Validation',
                        'description': 'The file creates Solana transactions but may not validate them before submission.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Validate transactions before submission, including checking account permissions, balance sufficiency, and instruction validity.',
                        'cwe': 'CWE-345: Insufficient Verification of Data Authenticity'
                    })
                
                # Check for lack of transaction simulation
                if re.search(r'send.*transaction', content, re.IGNORECASE) and not re.search(r'simulate|simulation|dry.?run', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Missing Transaction Simulation',
                        'description': 'The file sends transactions but may not simulate them before submission.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Simulate transactions before submission to catch errors and prevent wasted fees.',
                        'cwe': 'CWE-754: Improper Check for Unusual or Exceptional Conditions'
                    })
                
                # Check for lack of gas/fee estimation
                if re.search(r'send.*transaction', content, re.IGNORECASE) and not re.search(r'fee|gas|lamport', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Missing Fee Estimation',
                        'description': 'The file sends transactions but may not estimate or check fees before submission.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Estimate transaction fees before submission and ensure the payer account has sufficient balance.',
                        'cwe': 'CWE-400: Uncontrolled Resource Consumption'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_account_validation(codebase_path):
    """Check for account validation issues."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for account creation without validation
                if re.search(r'(Account|Keypair|PublicKey)\(', content) and not re.search(r'validate|verify|check', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Missing Account Validation',
                        'description': 'The file creates or uses Solana accounts but may not validate them.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Validate accounts before use, including checking if they exist, have the correct owner, and have sufficient balance.',
                        'cwe': 'CWE-345: Insufficient Verification of Data Authenticity'
                    })
                
                # Check for hardcoded account addresses
                pubkey_pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
                if re.search(pubkey_pattern, content):
                    findings.append({
                        'title': 'Potential Hardcoded Account Addresses',
                        'description': 'The file may contain hardcoded Solana account addresses.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Store account addresses in configuration files or environment variables, and validate them before use.',
                        'cwe': 'CWE-798: Use of Hard-coded Credentials'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_signature_verification(codebase_path):
    """Check for signature verification issues."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for lack of signature verification
                if re.search(r'signature|sign', content, re.IGNORECASE) and not re.search(r'verify|validate|check', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Missing Signature Verification',
                        'description': 'The file handles signatures but may not verify them properly.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Always verify signatures before accepting signed data or transactions.',
                        'cwe': 'CWE-347: Improper Verification of Cryptographic Signature'
                    })
                
                # Check for insecure signature schemes
                if re.search(r'ed25519', content, re.IGNORECASE) and re.search(r'sign', content, re.IGNORECASE) and not re.search(r'nacl|tweetnacl|pynacl', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Insecure Signature Implementation',
                        'description': 'The file implements Ed25519 signatures but may not use a secure library.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Use established cryptographic libraries like PyNaCl for Ed25519 signatures.',
                        'cwe': 'CWE-327: Use of a Broken or Risky Cryptographic Algorithm'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_blockchain_error_handling(codebase_path):
    """Check for error handling issues in blockchain operations."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for blockchain operations without error handling
                blockchain_operations = [
                    r'get_account_info',
                    r'get_balance',
                    r'get_transaction',
                    r'get_program_accounts',
                    r'send_transaction',
                    r'confirm_transaction',
                    r'get_confirmed_transaction',
                    r'get_confirmed_signature',
                    r'get_signatures_for_address',
                    r'get_token_account_balance',
                    r'get_token_accounts_by_owner',
                    r'get_token_supply',
                    r'get_minimum_balance_for_rent_exemption',
                    r'get_recent_blockhash',
                    r'get_latest_blockhash',
                    r'get_fee_for_message',
                    r'get_slot',
                    r'get_epoch_info',
                    r'get_inflation_reward',
                    r'get_inflation_rate',
                    r'get_vote_accounts',
                    r'get_cluster_nodes',
                    r'get_block',
                    r'get_blocks',
                    r'get_block_time',
                    r'get_epoch_schedule',
                    r'get_genesis_hash',
                    r'get_identity',
                    r'get_inflation_governor',
                    r'get_largest_accounts',
                    r'get_leader_schedule',
                    r'get_minimum_ledger_slot',
                    r'get_slot_leader',
                    r'get_supply',
                    r'get_token_largest_accounts',
                    r'get_version',
                    r'request_airdrop',
                    r'get_multiple_accounts',
                    r'get_program_accounts',
                    r'get_confirmed_blocks',
                    r'get_confirmed_signatures_for_address',
                    r'get_confirmed_transaction',
                    r'get_confirmed_signatures_for_address',
                    r'get_confirmed_signature_for_address',
                    r'get_confirmed_signature_for_address2',
                    r'get_confirmed_transaction',
                    r'get_confirmed_transactions',
                    r'get_confirmed_block',
                    r'get_confirmed_blocks',
                    r'get_confirmed_block_with_encoding',
                    r'get_confirmed_blocks_with_limit',
                    r'get_confirmed_transaction',
                    r'get_confirmed_transactions',
                    r'get_confirmed_transaction_with_config',
                    r'get_confirmed_transactions_with_config',
                    r'get_confirmed_signature_for_address',
                    r'get_confirmed_signatures_for_address',
                    r'get_confirmed_signatures_for_address2',
                    r'get_confirmed_signatures_for_address_with_config',
                    r'get_confirmed_signatures_for_address2_with_config',
                    r'get_confirmed_signature_for_address_with_config',
                    r'get_confirmed_signature_for_address2_with_config',
                    r'get_confirmed_block',
                    r'get_confirmed_blocks',
                    r'get_confirmed_block_with_encoding',
                    r'get_confirmed_blocks_with_limit',
                    r'get_confirmed_transaction',
                    r'get_confirmed_transactions',
                    r'get_confirmed_transaction_with_config',
                    r'get_confirmed_transactions_with_config',
                ]
                
                for operation in blockchain_operations:
                    if re.search(operation, content) and not re.search(r'try|except|error|handle', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Potential Missing Error Handling in Blockchain Operations',
                            'description': f'The file performs blockchain operations ({operation}) but may not handle errors properly.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Implement proper error handling for blockchain operations, including retries for transient errors and graceful degradation for persistent errors.',
                            'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                        })
                        break
                
                # Check for coroutine handling issues
                if re.search(r'async\s+def', content) and re.search(r'solana|rpc', content, re.IGNORECASE) and not re.search(r'await', content):
                    findings.append({
                        'title': 'Potential Coroutine Handling Issues',
                        'description': 'The file contains async functions for Solana RPC calls but may not properly await them.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Ensure all async functions are properly awaited to prevent coroutine handling issues.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for timeout handling
                if re.search(r'solana|rpc', content, re.IGNORECASE) and not re.search(r'timeout', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Missing Timeout Handling',
                        'description': 'The file interacts with Solana RPC but may not implement timeout handling.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Implement timeout handling for RPC calls to prevent hanging operations.',
                        'cwe': 'CWE-400: Uncontrolled Resource Consumption'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings
