"""
Transaction Validation Audit Module

This module checks for issues related to Solana transaction validation:
- Transaction signature verification
- Transaction simulation before submission
- Transaction fee estimation
- Transaction error handling
- Transaction confirmation
"""

import os
import re
import logging
from pathlib import Path
import time

logger = logging.getLogger('security_audit.transaction_validation')

def run_audit(codebase_path):
    """
    Run the transaction validation audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    start_time = time.time()
    logger.debug(f"Starting transaction validation audit on {codebase_path}")
    
    findings = []
    
    # Check for signature verification
    logger.debug("Checking for signature verification issues")
    findings.extend(check_signature_verification(codebase_path))
    logger.debug(f"Found {len(findings)} signature verification issues")
    
    # Check for transaction simulation
    logger.debug("Checking for transaction simulation issues")
    sim_findings = check_transaction_simulation(codebase_path)
    findings.extend(sim_findings)
    logger.debug(f"Found {len(sim_findings)} transaction simulation issues")
    
    # Check for fee estimation
    logger.debug("Checking for fee estimation issues")
    fee_findings = check_fee_estimation(codebase_path)
    findings.extend(fee_findings)
    logger.debug(f"Found {len(fee_findings)} fee estimation issues")
    
    # Check for error handling
    logger.debug("Checking for error handling issues")
    err_findings = check_error_handling(codebase_path)
    findings.extend(err_findings)
    logger.debug(f"Found {len(err_findings)} error handling issues")
    
    # Check for transaction confirmation
    logger.debug("Checking for transaction confirmation issues")
    conf_findings = check_transaction_confirmation(codebase_path)
    findings.extend(conf_findings)
    logger.debug(f"Found {len(conf_findings)} transaction confirmation issues")
    
    logger.debug(f"Transaction validation audit completed in {time.time() - start_time:.2f} seconds")
    logger.info(f"Total findings: {len(findings)}")
    
    return findings

def find_python_files(codebase_path):
    """Find all Python files in the codebase."""
    logger.debug(f"Finding Python files in {codebase_path}")
    start_time = time.time()
    python_files = list(Path(codebase_path).rglob('*.py'))
    logger.debug(f"Found {len(python_files)} Python files in {time.time() - start_time:.2f} seconds")
    return python_files

def check_signature_verification(codebase_path):
    """Check for signature verification issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for transaction creation without signature verification
                if re.search(r'Transaction\(', content) and not re.search(r'verify_signature|verify_signatures', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Missing Transaction Signature Verification',
                        'description': 'The file creates Solana transactions but may not verify signatures before processing.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Always verify transaction signatures before processing transactions, especially for transactions received from external sources.',
                        'cwe': 'CWE-347: Improper Verification of Cryptographic Signature'
                    })
                
                # Check for signature verification without proper error handling
                if re.search(r'verify_signature|verify_signatures', content, re.IGNORECASE) and not re.search(r'try|except|error', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Signature Verification Without Error Handling',
                        'description': 'The file verifies signatures but may not handle verification errors properly.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Implement proper error handling for signature verification failures, including logging and appropriate user feedback.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for potential signature bypass
                if re.search(r'skip_signature|bypass_signature|ignore_signature', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Signature Verification Bypass',
                        'description': 'The file may contain code that bypasses signature verification.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Remove any code that bypasses signature verification, as this can lead to unauthorized transactions.',
                        'cwe': 'CWE-287: Improper Authentication'
                    })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings

def check_transaction_simulation(codebase_path):
    """Check for transaction simulation issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for transaction submission without simulation
                if re.search(r'send_transaction|sendTransaction', content) and not re.search(r'simulate_transaction|simulateTransaction|dry_run|dryRun', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Missing Transaction Simulation',
                        'description': 'The file sends transactions but may not simulate them before submission.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Simulate transactions before submission to catch errors and prevent wasted fees.',
                        'cwe': 'CWE-754: Improper Check for Unusual or Exceptional Conditions'
                    })
                
                # Check for simulation without error handling
                if re.search(r'simulate_transaction|simulateTransaction', content, re.IGNORECASE) and not re.search(r'try|except|error', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Simulation Without Error Handling',
                        'description': 'The file simulates transactions but may not handle simulation errors properly.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Implement proper error handling for simulation errors, including logging and appropriate user feedback.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for simulation results not being checked
                if re.search(r'simulate_transaction|simulateTransaction', content, re.IGNORECASE) and not re.search(r'if.*?simulate|check.*?simulate', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Simulation Results Not Checked',
                        'description': 'The file simulates transactions but may not check the simulation results before submission.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Check simulation results before submitting transactions to ensure they will succeed.',
                        'cwe': 'CWE-754: Improper Check for Unusual or Exceptional Conditions'
                    })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings

def check_fee_estimation(codebase_path):
    """Check for fee estimation issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for transaction submission without fee estimation
                if re.search(r'send_transaction|sendTransaction', content) and not re.search(r'get_fee|getFee|estimate_fee|estimateFee|calculate_fee|calculateFee', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Missing Fee Estimation',
                        'description': 'The file sends transactions but may not estimate fees before submission.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Estimate transaction fees before submission and ensure the payer account has sufficient balance.',
                        'cwe': 'CWE-400: Uncontrolled Resource Consumption'
                    })
                
                # Check for fee estimation without error handling
                if re.search(r'get_fee|getFee|estimate_fee|estimateFee', content, re.IGNORECASE) and not re.search(r'try|except|error', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Fee Estimation Without Error Handling',
                        'description': 'The file estimates fees but may not handle estimation errors properly.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Implement proper error handling for fee estimation errors, including logging and appropriate user feedback.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for hardcoded fees
                if re.search(r'fee\s*=\s*\d+', content) or re.search(r'lamports\s*=\s*\d+', content):
                    findings.append({
                        'title': 'Hardcoded Transaction Fees',
                        'description': 'The file may use hardcoded transaction fees, which can lead to transaction failures if network fees change.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Dynamically estimate transaction fees based on the current network conditions instead of using hardcoded values.',
                        'cwe': 'CWE-330: Use of Insufficiently Random Values'
                    })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings

def check_error_handling(codebase_path):
    """Check for transaction error handling issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for transaction submission without error handling
                if re.search(r'send_transaction|sendTransaction', content) and not re.search(r'try|except|error', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Missing Transaction Error Handling',
                        'description': 'The file sends transactions but may not handle transaction errors properly.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Implement proper error handling for transaction submission, including retries for transient errors and appropriate user feedback.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for bare except blocks
                if re.search(r'try.*?send_transaction|try.*?sendTransaction', content, re.DOTALL) and re.search(r'except\s*:', content):
                    findings.append({
                        'title': 'Bare Except Blocks in Transaction Handling',
                        'description': 'The file uses bare except blocks when handling transaction errors, which can catch unexpected exceptions and hide errors.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Specify the exception types to catch and handle each appropriately. Avoid using bare except blocks.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for transaction errors being ignored
                if re.search(r'try.*?send_transaction.*?except.*?pass', content, re.DOTALL) or re.search(r'try.*?sendTransaction.*?except.*?pass', content, re.DOTALL):
                    findings.append({
                        'title': 'Transaction Errors Being Ignored',
                        'description': 'The file ignores transaction errors, which can lead to silent failures and data inconsistency.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Handle transaction errors properly by logging them and taking appropriate action, such as notifying the user or rolling back changes.',
                        'cwe': 'CWE-390: Detection of Error Condition Without Action'
                    })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings

def check_transaction_confirmation(codebase_path):
    """Check for transaction confirmation issues."""
    findings = []
    
    # Find all Python files
    python_files = find_python_files(codebase_path)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for transaction submission without confirmation
                if re.search(r'send_transaction|sendTransaction', content) and not re.search(r'confirm_transaction|confirmTransaction|wait_for_confirmation|waitForConfirmation', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Missing Transaction Confirmation',
                        'description': 'The file sends transactions but may not confirm they were successfully processed by the network.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Confirm transactions after submission to ensure they were successfully processed by the network.',
                        'cwe': 'CWE-754: Improper Check for Unusual or Exceptional Conditions'
                    })
                
                # Check for confirmation without error handling
                if re.search(r'confirm_transaction|confirmTransaction', content, re.IGNORECASE) and not re.search(r'try|except|error', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Confirmation Without Error Handling',
                        'description': 'The file confirms transactions but may not handle confirmation errors properly.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Implement proper error handling for confirmation errors, including logging and appropriate user feedback.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for insufficient confirmation depth
                if re.search(r'confirm_transaction|confirmTransaction', content, re.IGNORECASE) and re.search(r'confirmations\s*=\s*1', content):
                    findings.append({
                        'title': 'Insufficient Confirmation Depth',
                        'description': 'The file may use an insufficient confirmation depth (1) for transactions, which can lead to accepting transactions that may be rolled back.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Use a higher confirmation depth (e.g., 32 or more) for transactions that require strong finality guarantees.',
                        'cwe': 'CWE-346: Origin Validation Error'
                    })
                
                # Check for confirmation timeout issues
                if re.search(r'confirm_transaction|confirmTransaction', content, re.IGNORECASE) and not re.search(r'timeout', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Missing Confirmation Timeout',
                        'description': 'The file confirms transactions but may not implement a timeout for confirmation, which can lead to hanging operations.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Implement a timeout for transaction confirmation to prevent hanging operations.',
                        'cwe': 'CWE-400: Uncontrolled Resource Consumption'
                    })
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            continue
    
    return findings
