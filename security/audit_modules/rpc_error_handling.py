"""
RPC Error Handling Audit Module

This module checks for issues related to Solana RPC error handling:
- Coroutine handling
- Response processing
- Error handling
- Serialization
- Initialization
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('security_audit.rpc_error_handling')

def run_audit(codebase_path):
    """
    Run the RPC error handling audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        
    Returns:
        list: List of findings
    """
    findings = []
    
    # Check for coroutine handling
    findings.extend(check_coroutine_handling(codebase_path))
    
    # Check for response processing
    findings.extend(check_response_processing(codebase_path))
    
    # Check for error handling
    findings.extend(check_error_handling(codebase_path))
    
    # Check for serialization
    findings.extend(check_serialization(codebase_path))
    
    # Check for initialization
    findings.extend(check_initialization(codebase_path))
    
    return findings

def check_coroutine_handling(codebase_path):
    """Check for coroutine handling issues."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for async functions without proper awaiting
                if re.search(r'async\s+def', content) and not re.search(r'await', content):
                    findings.append({
                        'title': 'Potential Coroutine Handling Issues',
                        'description': 'The file contains async functions but may not properly await them.',
                        'location': str(file_path),
                        'severity': 'high',
                        'recommendation': 'Ensure all async functions are properly awaited to prevent coroutine handling issues.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for coroutines not being properly checked
                if re.search(r'asyncio\.iscoroutine', content) or re.search(r'inspect\.iscoroutine', content):
                    # This is good practice, but check if it's consistently used
                    if re.search(r'await', content) and not re.search(r'if\s+(?:asyncio|inspect)\.iscoroutine', content):
                        findings.append({
                            'title': 'Inconsistent Coroutine Checking',
                            'description': 'The file uses coroutine checking in some places but not others, which may lead to inconsistent behavior.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Consistently check if objects are coroutines before awaiting them, especially when handling dynamic inputs.',
                            'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                        })
                
                # Check for potential coroutine leaks
                if re.search(r'async\s+def', content) and re.search(r'return\s+\w+\(', content) and not re.search(r'return\s+await', content):
                    findings.append({
                        'title': 'Potential Coroutine Leak',
                        'description': 'The file may return a coroutine without awaiting it, which can lead to coroutine leaks.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Await coroutines before returning them from async functions, or ensure the caller knows to await the result.',
                        'cwe': 'CWE-404: Improper Resource Shutdown or Release'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_response_processing(codebase_path):
    """Check for response processing issues."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for direct dictionary access without checks
                if re.search(r'response\[', content) and not re.search(r'(?:if|try).*?response\s*(?:\.|get\(|\[)', content, re.DOTALL):
                    findings.append({
                        'title': 'Unsafe Response Access',
                        'description': 'The file accesses response data directly without checking if the keys exist.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Use response.get() with a default value or check if keys exist before accessing them.',
                        'cwe': 'CWE-754: Improper Check for Unusual or Exceptional Conditions'
                    })
                
                # Check for nested data access without validation
                if re.search(r'response(?:\[|\.).*?(?:\[|\.)', content) and not re.search(r'(?:if|try).*?response(?:\[|\.).*?(?:\[|\.)', content, re.DOTALL):
                    findings.append({
                        'title': 'Unsafe Nested Response Access',
                        'description': 'The file accesses nested response data without validating the structure.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Validate the response structure before accessing nested data, or use a recursive function to safely navigate the structure.',
                        'cwe': 'CWE-754: Improper Check for Unusual or Exceptional Conditions'
                    })
                
                # Check for lack of response validation
                if re.search(r'response', content) and not re.search(r'(?:if|try).*?response', content, re.DOTALL):
                    findings.append({
                        'title': 'Potential Missing Response Validation',
                        'description': 'The file handles responses but may not validate them properly.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Validate responses before processing them to handle unexpected formats or errors.',
                        'cwe': 'CWE-20: Improper Input Validation'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_error_handling(codebase_path):
    """Check for error handling issues."""
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
                
                # Check for RPC calls without timeout
                if re.search(r'rpc|solana', content, re.IGNORECASE) and not re.search(r'timeout', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Missing Timeout Handling',
                        'description': 'The file interacts with RPC but may not implement timeout handling.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Implement timeout handling for RPC calls to prevent hanging operations.',
                        'cwe': 'CWE-400: Uncontrolled Resource Consumption'
                    })
                
                # Check for lack of execution time tracking
                if re.search(r'rpc|solana', content, re.IGNORECASE) and not re.search(r'time\.|timer|duration|elapsed', content, re.IGNORECASE):
                    findings.append({
                        'title': 'Potential Missing Execution Time Tracking',
                        'description': 'The file interacts with RPC but may not track execution time for performance monitoring.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Track execution time for RPC calls to identify slow endpoints and performance issues.',
                        'cwe': 'CWE-1095: Loop Condition Value Update within the Loop'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_serialization(codebase_path):
    """Check for serialization issues."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for JSON serialization without error handling
                if re.search(r'json\.dumps', content) and not re.search(r'try.*?json\.dumps', content, re.DOTALL):
                    findings.append({
                        'title': 'Unsafe JSON Serialization',
                        'description': 'The file serializes data to JSON without error handling.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Wrap JSON serialization in try-except blocks to handle non-serializable objects.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
                
                # Check for custom serialization without type checking
                if re.search(r'def\s+serialize', content) and not re.search(r'isinstance|type\(', content):
                    findings.append({
                        'title': 'Potential Missing Type Checking in Serialization',
                        'description': 'The file implements custom serialization but may not check object types.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Implement type checking in custom serialization functions to handle different object types appropriately.',
                        'cwe': 'CWE-20: Improper Input Validation'
                    })
                
                # Check for handling of special methods in serialization
                if re.search(r'def\s+serialize', content) and not re.search(r'__.*?__|hasattr', content):
                    findings.append({
                        'title': 'Potential Missing Special Method Handling in Serialization',
                        'description': 'The file implements custom serialization but may not handle objects with special methods.',
                        'location': str(file_path),
                        'severity': 'low',
                        'recommendation': 'Check for and handle special methods (__str__, __repr__, etc.) in custom serialization functions.',
                        'cwe': 'CWE-755: Improper Handling of Exceptional Conditions'
                    })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_initialization(codebase_path):
    """Check for initialization issues."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for class usage without initialization
                class_definitions = re.findall(r'class\s+(\w+)', content)
                for class_name in class_definitions:
                    # Check if the class is used without initialization
                    if re.search(fr'{class_name}\.\w+', content) and not re.search(fr'{class_name}\(', content):
                        findings.append({
                            'title': 'Potential Missing Class Initialization',
                            'description': f'The class {class_name} may be used without proper initialization.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Ensure classes are properly initialized before use.',
                            'cwe': 'CWE-665: Improper Initialization'
                        })
                
                # Check for handlers without initialization
                if re.search(r'Handler', content) and re.search(r'get_.*?_metrics|get_.*?_status', content) and not re.search(r'__init__|initialize', content):
                    findings.append({
                        'title': 'Potential Missing Handler Initialization',
                        'description': 'The file contains handlers that may not be properly initialized before use.',
                        'location': str(file_path),
                        'severity': 'medium',
                        'recommendation': 'Ensure handlers are properly initialized before making RPC calls.',
                        'cwe': 'CWE-665: Improper Initialization'
                    })
                
                # Check for global variables without initialization
                global_vars = re.findall(r'^\s*(\w+)\s*=', content, re.MULTILINE)
                for var in global_vars:
                    if re.search(fr'{var}\.\w+', content) and not re.search(fr'{var}\s*=\s*\w+\(', content):
                        findings.append({
                            'title': 'Potential Missing Variable Initialization',
                            'description': f'The global variable {var} may be used without proper initialization.',
                            'location': str(file_path),
                            'severity': 'low',
                            'recommendation': 'Ensure global variables are properly initialized before use.',
                            'cwe': 'CWE-665: Improper Initialization'
                        })
            except UnicodeDecodeError:
                continue
    
    return findings
