#!/usr/bin/env python3
"""
Check RPC Error Handling

This script checks the Soleco codebase for proper implementation of the
RPC error handling improvements described in the memory.
"""

import os
import sys
import re
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('check_rpc_error_handling')

def check_coroutine_handling(codebase_path):
    """Check for proper coroutine handling."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for NetworkStatusHandler.get_comprehensive_status method
                if 'class NetworkStatusHandler' in content and 'def get_comprehensive_status' in content:
                    if not re.search(r'await.*?_get_data_with_timeout', content):
                        findings.append({
                            'title': 'Missing await in get_comprehensive_status',
                            'description': 'The NetworkStatusHandler.get_comprehensive_status method may not properly await coroutines.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Ensure that coroutines are properly awaited in the get_comprehensive_status method.',
                        })
                
                # Check for _get_data_with_timeout method
                if 'def _get_data_with_timeout' in content:
                    if not re.search(r'(?:asyncio|inspect)\.iscoroutine', content):
                        findings.append({
                            'title': 'Missing coroutine check in _get_data_with_timeout',
                            'description': 'The _get_data_with_timeout method may not properly check if the input is a coroutine.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Use asyncio.iscoroutine or inspect.iscoroutine to check if the input is a coroutine before awaiting it.',
                        })
                
                # Check for detailed logging of coroutine execution
                if 'async def' in content and 'logger' in content:
                    if not re.search(r'logger\.(?:debug|info|warning|error).*?coroutine', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing detailed logging for coroutine execution',
                            'description': 'The file contains async functions but may not include detailed logging for coroutine execution.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Add detailed logging for coroutine execution and response handling.',
                        })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_response_processing(codebase_path):
    """Check for proper response processing."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for SolanaQueryHandler.get_vote_accounts method
                if 'class SolanaQueryHandler' in content and 'def get_vote_accounts' in content:
                    if not re.search(r'try.*?response\s*(?:\.|get\(|\[)', content, re.DOTALL):
                        findings.append({
                            'title': 'Missing response validation in get_vote_accounts',
                            'description': 'The SolanaQueryHandler.get_vote_accounts method may not properly validate the response from the Solana RPC API.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Add proper response validation to handle missing or malformed data from the Solana RPC API.',
                        })
                
                # Check for _process_stake_info method
                if 'def _process_stake_info' in content:
                    if not re.search(r'recursive|find.*?any.*?level|nested', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing nested structure handling in _process_stake_info',
                            'description': 'The _process_stake_info method may not properly handle nested structures and find validator data at any level of nesting.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Enhance the _process_stake_info method to better handle nested structures and find validator data at any level of nesting.',
                        })
                
                # Check for recursive search for validator data
                if 'validator' in content.lower() and 'data' in content.lower():
                    if not re.search(r'recursive|find.*?any.*?level|nested', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing recursive search for validator data',
                            'description': 'The file may not implement recursive search for validator data in complex response structures.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Add recursive search for validator data in complex response structures.',
                        })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_error_handling(codebase_path):
    """Check for proper error handling."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for safe_rpc_call_async function
                if 'def safe_rpc_call_async' in content:
                    if not re.search(r'logger\.(?:debug|info|warning|error)', content):
                        findings.append({
                            'title': 'Missing detailed logging in safe_rpc_call_async',
                            'description': 'The safe_rpc_call_async function may not include detailed logging for better error handling.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Add detailed logging to the safe_rpc_call_async function for better error handling.',
                        })
                    
                    if not re.search(r'time\.|timer|duration|elapsed', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing execution time tracking in safe_rpc_call_async',
                            'description': 'The safe_rpc_call_async function may not track execution time for RPC calls.',
                            'location': str(file_path),
                            'severity': 'low',
                            'recommendation': 'Add execution time tracking for RPC calls to help identify slow endpoints.',
                        })
                    
                    if not re.search(r'structured.*?error|error.*?response', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing structured error responses in safe_rpc_call_async',
                            'description': 'The safe_rpc_call_async function may not return structured error responses.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Improve error messages and return structured error responses from the safe_rpc_call_async function.',
                        })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_serialization(codebase_path):
    """Check for proper serialization."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for serialize_solana_object function
                if 'def serialize_solana_object' in content:
                    if not re.search(r'isinstance.*?Pubkey', content):
                        findings.append({
                            'title': 'Missing Pubkey handling in serialize_solana_object',
                            'description': 'The serialize_solana_object function may not properly handle Pubkey objects.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Add specific handling for Pubkey objects in the serialize_solana_object function.',
                        })
                    
                    if not re.search(r'(?:asyncio|inspect)\.iscoroutine', content):
                        findings.append({
                            'title': 'Missing coroutine handling in serialize_solana_object',
                            'description': 'The serialize_solana_object function may not properly handle coroutines.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Add specific handling for coroutines in the serialize_solana_object function.',
                        })
                    
                    if not re.search(r'hasattr.*?__.*?__|special.*?method', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing special method handling in serialize_solana_object',
                            'description': 'The serialize_solana_object function may not properly handle objects with special methods.',
                            'location': str(file_path),
                            'severity': 'low',
                            'recommendation': 'Add specific handling for objects with special methods in the serialize_solana_object function.',
                        })
                    
                    if not re.search(r'logger\.(?:debug|info|warning|error).*?serializ', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing error logging during serialization',
                            'description': 'The serialize_solana_object function may not include error logging during serialization.',
                            'location': str(file_path),
                            'severity': 'low',
                            'recommendation': 'Improve error logging during serialization in the serialize_solana_object function.',
                        })
            except UnicodeDecodeError:
                continue
    
    return findings

def check_initialization(codebase_path):
    """Check for proper initialization."""
    findings = []
    
    # Find all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                content = f.read()
                
                # Check for handler initialization before RPC calls
                if 'Handler' in content and ('rpc' in content.lower() or 'solana' in content.lower()):
                    if not re.search(r'initialize|init|__init__', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing handler initialization',
                            'description': 'The file may not properly initialize handlers before making RPC calls.',
                            'location': str(file_path),
                            'severity': 'high',
                            'recommendation': 'Ensure proper initialization of handlers before making RPC calls.',
                        })
                
                # Check for get_performance_metrics function
                if 'def get_performance_metrics' in content:
                    if not re.search(r'initialize|init|__init__', content, re.IGNORECASE):
                        findings.append({
                            'title': 'Missing initialization in get_performance_metrics',
                            'description': 'The get_performance_metrics function may not include explicit initialization.',
                            'location': str(file_path),
                            'severity': 'medium',
                            'recommendation': 'Add explicit initialization in the get_performance_metrics function.',
                        })
            except UnicodeDecodeError:
                continue
    
    return findings

def main():
    """Main entry point."""
    # Get the path to the backend directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
    
    # Ensure the backend directory exists
    if not os.path.exists(backend_dir):
        logger.error(f"Backend directory does not exist: {backend_dir}")
        return 1
    
    # Run the checks
    logger.info(f"Checking RPC error handling in {backend_dir}")
    
    coroutine_findings = check_coroutine_handling(backend_dir)
    response_findings = check_response_processing(backend_dir)
    error_findings = check_error_handling(backend_dir)
    serialization_findings = check_serialization(backend_dir)
    initialization_findings = check_initialization(backend_dir)
    
    all_findings = (
        coroutine_findings +
        response_findings +
        error_findings +
        serialization_findings +
        initialization_findings
    )
    
    # Create a console for rich output
    console = Console()
    
    # Display the findings
    if all_findings:
        console.print(Panel(f"[bold red]Found {len(all_findings)} issues with RPC error handling[/bold red]"))
        
        # Create a table for the findings
        table = Table(title="RPC Error Handling Issues")
        table.add_column("Category", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Location", style="yellow")
        table.add_column("Severity", style="red")
        
        for finding in all_findings:
            category = ""
            if finding in coroutine_findings:
                category = "Coroutine Handling"
            elif finding in response_findings:
                category = "Response Processing"
            elif finding in error_findings:
                category = "Error Handling"
            elif finding in serialization_findings:
                category = "Serialization"
            elif finding in initialization_findings:
                category = "Initialization"
            
            table.add_row(
                category,
                finding['title'],
                finding['location'],
                finding['severity'].upper()
            )
        
        console.print(table)
        
        # Display detailed findings
        console.print("\n[bold]Detailed Findings:[/bold]")
        for i, finding in enumerate(all_findings, 1):
            console.print(f"\n[bold]{i}. {finding['title']}[/bold] ([bold red]{finding['severity'].upper()}[/bold red])")
            console.print(f"   [yellow]Location:[/yellow] {finding['location']}")
            console.print(f"   [yellow]Description:[/yellow] {finding['description']}")
            console.print(f"   [yellow]Recommendation:[/yellow] {finding['recommendation']}")
    else:
        console.print(Panel("[bold green]No issues found with RPC error handling[/bold green]"))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
