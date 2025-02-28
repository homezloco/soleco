"""
RPC commands for the Soleco CLI
"""

import click
import logging
import json
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from typing import Dict, Any, Optional, List
from pathlib import Path

from soleco_cli.api import SolecoAPI, APIError
from soleco_cli.utils import format_output, handle_api_error

logger = logging.getLogger("soleco")

@click.group()
def rpc():
    """Commands for interacting with Solana RPC nodes"""
    pass

@rpc.command('list')
@click.option('--details', is_flag=True, help='Include detailed information for each RPC node')
@click.option('--health-check', is_flag=True, help='Perform health checks on a sample of RPC nodes')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.option('--output', type=click.Path(), help='Save output to file')
@click.option('--version', help='Filter RPC nodes by version')
@click.option('--status', type=click.Choice(['healthy', 'unhealthy', 'all']), default='all', help='Filter RPC nodes by status')
@click.option('--sort', type=click.Choice(['version', 'latency']), help='Sort RPC nodes by field')
@click.pass_context
def list_rpc_nodes(ctx, details, health_check, format, output, version, status, sort):
    """List available Solana RPC nodes"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    # Create API client
    api = SolecoAPI(config.api_url, timeout=config.get('timeout', 30))
    
    try:
        with console.status("[bold green]Fetching RPC nodes..."):
            result = api.get_rpc_nodes(include_details=details, health_check=health_check)
        
        # Apply filters
        if 'rpc_nodes' in result:
            nodes = result['rpc_nodes']
            
            # Filter by version
            if version:
                nodes = [node for node in nodes if node.get('version') == version]
            
            # Filter by status
            if status != 'all' and health_check:
                is_healthy = status == 'healthy'
                nodes = [node for node in nodes if node.get('is_healthy', False) == is_healthy]
            
            # Sort nodes
            if sort:
                if sort == 'version':
                    nodes.sort(key=lambda x: x.get('version', ''))
                elif sort == 'latency' and health_check:
                    nodes.sort(key=lambda x: x.get('latency', float('inf')))
            
            # Update the result with filtered nodes
            result['rpc_nodes'] = nodes
            result['filtered_count'] = len(nodes)
        
        # Determine output format
        output_format = format or config.get('format', 'table')
        
        if output_format == 'table':
            _display_rpc_nodes_table(console, result, details, health_check)
        else:
            # Handle other formats
            format_output(result, output_format, output, console)
            
    except APIError as e:
        handle_api_error(e, console)
    finally:
        api.close()

def _display_rpc_nodes_table(console: Console, data: Dict[str, Any], details: bool, health_check: bool):
    """Display RPC nodes as a table"""
    # Display summary
    console.print(Panel(f"[bold]Solana RPC Nodes[/bold]", expand=False))
    
    if 'timestamp' in data:
        console.print(f"[dim]Data as of: {data['timestamp']}[/dim]")
    
    # Display summary metrics
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    
    metrics = [
        ("Total RPC Nodes", data.get('total_rpc_nodes', 'N/A')),
        ("Filtered Count", data.get('filtered_count', data.get('total_rpc_nodes', 'N/A'))),
    ]
    
    if health_check:
        metrics.extend([
            ("Health Sample Size", data.get('health_sample_size', 'N/A')),
            ("Estimated Health %", f"{data.get('estimated_health_percentage', 'N/A')}%"),
        ])
    
    for metric, value in metrics:
        summary_table.add_row(metric, str(value))
    
    console.print(summary_table)
    
    # Display version distribution
    if 'version_distribution' in data:
        version_table = Table(title="Version Distribution")
        version_table.add_column("Version", style="cyan")
        version_table.add_column("Count", style="green")
        version_table.add_column("Percentage", style="green")
        
        for version, info in data['version_distribution'].items():
            version_table.add_row(
                version,
                str(info.get('count', 'N/A')),
                f"{info.get('percentage', 'N/A')}%"
            )
        
        console.print(version_table)
    
    # Display RPC nodes if details requested
    if details and 'rpc_nodes' in data:
        nodes = data['rpc_nodes']
        
        # Limit to 20 nodes to avoid overwhelming output
        display_nodes = nodes[:20]
        
        nodes_table = Table(title=f"RPC Nodes (showing {len(display_nodes)} of {len(nodes)})")
        nodes_table.add_column("Pubkey", style="cyan", no_wrap=True)
        nodes_table.add_column("RPC Endpoint", style="green")
        nodes_table.add_column("Version", style="green")
        
        if health_check:
            nodes_table.add_column("Health", style="green")
            nodes_table.add_column("Latency", style="green")
        
        for node in display_nodes:
            row = [
                node.get('pubkey', 'N/A')[:16] + "...",
                node.get('rpc_endpoint', 'N/A'),
                node.get('version', 'N/A'),
            ]
            
            if health_check:
                health_status = "✓" if node.get('is_healthy', False) else "✗"
                latency = f"{node.get('latency', 'N/A'):.2f}s" if isinstance(node.get('latency'), (int, float)) else 'N/A'
                row.extend([health_status, latency])
            
            nodes_table.add_row(*row)
        
        console.print(nodes_table)
        
        if len(nodes) > 20:
            console.print("[dim]Note: Only showing 20 nodes. Use --format json for complete data.[/dim]")

@rpc.command('stats')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.option('--output', type=click.Path(), help='Save output to file')
@click.option('--filtered', is_flag=True, help='Filter out private endpoints with API keys')
@click.pass_context
def stats(ctx, format, output, filtered):
    """Get RPC endpoint performance statistics"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    # Create API client
    api = SolecoAPI(config.api_url, timeout=config.get('timeout', 30))
    
    try:
        with console.status("[bold green]Fetching RPC statistics..."):
            if filtered:
                result = api.get_filtered_rpc_stats()
            else:
                result = api.get_rpc_stats()
        
        # Determine output format
        output_format = format or config.get('format', 'table')
        
        if output_format == 'table':
            _display_rpc_stats_table(console, result, filtered)
        else:
            # Handle other formats
            format_output(result, output_format, output, console)
            
    except APIError as e:
        handle_api_error(e, console)
    finally:
        api.close()

def _display_rpc_stats_table(console: Console, data: Dict[str, Any], filtered: bool):
    """Display RPC statistics as a table"""
    title = "RPC Endpoint Statistics"
    if filtered:
        title += " (Filtered)"
    
    console.print(Panel(f"[bold]{title}[/bold]", expand=False))
    
    if 'summary' in data:
        summary = data['summary']
        
        summary_table = Table(title="Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        metrics = [
            ("Total Endpoints", summary.get('total_endpoints', 'N/A')),
            ("Active Endpoints", summary.get('active_endpoints', 'N/A')),
            ("Average Latency", f"{summary.get('average_latency', 'N/A'):.3f}s"),
            ("Total Success", summary.get('total_success', 'N/A')),
            ("Total Failures", summary.get('total_failures', 'N/A')),
            ("Overall Success Rate", f"{summary.get('overall_success_rate', 'N/A')}%")
        ]
        
        for metric, value in metrics:
            summary_table.add_row(metric, str(value))
        
        console.print(summary_table)
    
    # Display top performers
    if 'top_performers' in data:
        performers = data['top_performers']
        
        performers_table = Table(title="Top Performing Endpoints")
        performers_table.add_column("Endpoint", style="cyan")
        performers_table.add_column("Latency", style="green")
        performers_table.add_column("Success Rate", style="green")
        performers_table.add_column("Success/Failure", style="green")
        
        for endpoint in performers:
            performers_table.add_row(
                endpoint.get('endpoint', 'N/A'),
                f"{endpoint.get('avg_latency', 'N/A'):.3f}s",
                f"{endpoint.get('success_rate', 'N/A')}%",
                f"{endpoint.get('success_count', 0)}/{endpoint.get('failure_count', 0)}"
            )
        
        console.print(performers_table)
    
    # Display endpoint details
    if 'endpoints' in data:
        endpoints = data['endpoints']
        
        # Limit to 10 endpoints to avoid overwhelming output
        display_endpoints = endpoints[:10]
        
        endpoints_table = Table(title=f"Endpoint Details (showing {len(display_endpoints)} of {len(endpoints)})")
        endpoints_table.add_column("Endpoint", style="cyan")
        endpoints_table.add_column("Name", style="green")
        endpoints_table.add_column("Success Rate", style="green")
        endpoints_table.add_column("Avg Latency", style="green")
        endpoints_table.add_column("Status", style="green")
        
        for endpoint in display_endpoints:
            status = "Active" if endpoint.get('is_active', False) else "Inactive"
            endpoints_table.add_row(
                endpoint.get('url', 'N/A'),
                endpoint.get('name', 'N/A'),
                f"{endpoint.get('success_rate', 'N/A')}%",
                f"{endpoint.get('avg_latency', 'N/A'):.3f}s",
                status
            )
        
        console.print(endpoints_table)
        
        if len(endpoints) > 10:
            console.print("[dim]Note: Only showing 10 endpoints. Use --format json for complete data.[/dim]")
