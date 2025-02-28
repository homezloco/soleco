"""
Diagnostics commands for the Soleco CLI
"""

import click
import logging
import json
import sys
import platform
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from typing import Dict, Any, Optional
from pathlib import Path

from soleco_cli.api import SolecoAPI, APIError
from soleco_cli.utils import format_output, handle_api_error

logger = logging.getLogger("soleco")

@click.group()
def diagnostics():
    """Commands for system diagnostics"""
    pass

@diagnostics.command('info')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.option('--output', type=click.Path(), help='Save output to file')
@click.pass_context
def info(ctx, format, output):
    """Get system diagnostic information"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    # Create API client
    api = SolecoAPI(config.api_url, timeout=config.get('timeout', 30))
    
    try:
        with console.status("[bold green]Fetching system diagnostics..."):
            result = api.get_diagnostics()
        
        # Determine output format
        output_format = format or config.get('format', 'table')
        
        if output_format == 'table':
            _display_diagnostics_table(console, result)
        else:
            # Handle other formats
            format_output(result, output_format, output, console)
            
    except APIError as e:
        handle_api_error(e, console)
    finally:
        api.close()

def _display_diagnostics_table(console: Console, data: Dict[str, Any]):
    """Display diagnostics as a table"""
    # Display summary
    console.print(Panel(f"[bold]System Diagnostics[/bold]", expand=False))
    
    if 'timestamp' in data:
        console.print(f"[dim]Data as of: {data['timestamp']}[/dim]")
    
    # Display system info
    if 'system_info' in data:
        system_info = data['system_info']
        
        system_table = Table(title="System Information")
        system_table.add_column("Property", style="cyan")
        system_table.add_column("Value", style="green")
        
        properties = [
            ("Version", system_info.get('version', 'N/A')),
            ("Python Version", system_info.get('python_version', 'N/A')),
            ("Platform", system_info.get('platform', 'N/A')),
            ("CPU Cores", system_info.get('cpu_cores', 'N/A')),
            ("Memory Total", f"{system_info.get('memory_total', 'N/A')} MB"),
            ("Memory Available", f"{system_info.get('memory_available', 'N/A')} MB"),
            ("Disk Total", f"{system_info.get('disk_total', 'N/A')} GB"),
            ("Disk Free", f"{system_info.get('disk_free', 'N/A')} GB"),
            ("Uptime", f"{system_info.get('uptime', 'N/A')} seconds")
        ]
        
        for prop, value in properties:
            system_table.add_row(prop, str(value))
        
        console.print(system_table)
    
    # Display API stats
    if 'api_stats' in data:
        api_stats = data['api_stats']
        
        api_table = Table(title="API Statistics")
        api_table.add_column("Metric", style="cyan")
        api_table.add_column("Value", style="green")
        
        metrics = [
            ("Total Requests", api_stats.get('total_requests', 'N/A')),
            ("Requests Per Minute", api_stats.get('requests_per_minute', 'N/A')),
            ("Average Response Time", f"{api_stats.get('avg_response_time', 'N/A'):.2f} ms"),
            ("Error Rate", f"{api_stats.get('error_rate', 'N/A')}%"),
            ("Active Connections", api_stats.get('active_connections', 'N/A'))
        ]
        
        for metric, value in metrics:
            api_table.add_row(metric, str(value))
        
        console.print(api_table)
    
    # Display endpoint stats
    if 'endpoint_stats' in data and data['endpoint_stats']:
        endpoint_stats = data['endpoint_stats']
        
        endpoint_table = Table(title="Endpoint Statistics")
        endpoint_table.add_column("Endpoint", style="cyan")
        endpoint_table.add_column("Requests", style="green")
        endpoint_table.add_column("Avg Response Time", style="green")
        endpoint_table.add_column("Error Rate", style="green")
        
        for endpoint in endpoint_stats:
            endpoint_table.add_row(
                endpoint.get('path', 'N/A'),
                str(endpoint.get('requests', 'N/A')),
                f"{endpoint.get('avg_response_time', 'N/A'):.2f} ms",
                f"{endpoint.get('error_rate', 'N/A')}%"
            )
        
        console.print(endpoint_table)
    
    # Display RPC stats
    if 'rpc_stats' in data:
        rpc_stats = data['rpc_stats']
        
        rpc_table = Table(title="RPC Statistics")
        rpc_table.add_column("Metric", style="cyan")
        rpc_table.add_column("Value", style="green")
        
        metrics = [
            ("Total RPC Requests", rpc_stats.get('total_requests', 'N/A')),
            ("RPC Requests Per Minute", rpc_stats.get('requests_per_minute', 'N/A')),
            ("Average RPC Response Time", f"{rpc_stats.get('avg_response_time', 'N/A'):.2f} ms"),
            ("RPC Error Rate", f"{rpc_stats.get('error_rate', 'N/A')}%"),
            ("Active RPC Connections", rpc_stats.get('active_connections', 'N/A')),
            ("RPC Connection Pool Size", rpc_stats.get('connection_pool_size', 'N/A'))
        ]
        
        for metric, value in metrics:
            rpc_table.add_row(metric, str(value))
        
        console.print(rpc_table)
    
    # Display health checks
    if 'health_checks' in data and data['health_checks']:
        health_checks = data['health_checks']
        
        health_table = Table(title="Health Checks")
        health_table.add_column("Component", style="cyan")
        health_table.add_column("Status", style="green")
        health_table.add_column("Message", style="green")
        
        for check in health_checks:
            status = check.get('status', 'unknown')
            status_color = {
                'ok': 'green',
                'warning': 'yellow',
                'error': 'red',
                'unknown': 'white'
            }.get(status.lower(), 'white')
            
            health_table.add_row(
                check.get('component', 'N/A'),
                f"[{status_color}]{status.upper()}[/{status_color}]",
                check.get('message', 'N/A')
            )
        
        console.print(health_table)
