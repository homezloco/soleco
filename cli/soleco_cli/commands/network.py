"""
Network commands for the Soleco CLI
"""

import click
import logging
import json
import sys
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
def network():
    """Commands for interacting with Solana network data"""
    pass

@network.command()
@click.option('--summary', is_flag=True, help='Show only summary information')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.option('--output', type=click.Path(), help='Save output to file')
@click.pass_context
def status(ctx, summary, format, output):
    """Get Solana network status"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    # Create API client
    api = SolecoAPI(config.api_url, timeout=config.get('timeout', 30))
    
    try:
        with console.status("[bold green]Fetching network status..."):
            result = api.get_network_status(summary_only=summary)
        
        # Determine output format
        output_format = format or config.get('format', 'table')
        
        if output_format == 'table':
            _display_network_status_table(console, result, summary)
        else:
            # Handle other formats
            format_output(result, output_format, output, console)
            
    except APIError as e:
        handle_api_error(e, console)
    finally:
        api.close()

def _display_network_status_table(console: Console, data: Dict[str, Any], summary_only: bool = False):
    """Display network status as a table"""
    # Display overall status
    status_value = data.get('status', 'unknown')
    status_color = {
        'healthy': 'green',
        'degraded': 'yellow',
        'error': 'red'
    }.get(status_value.lower(), 'white')
    
    console.print(Panel(f"[bold {status_color}]Network Status: {status_value.upper()}[/bold {status_color}]", 
                        title="Solana Network", expand=False))
    
    # Display timestamp
    if 'timestamp' in data:
        console.print(f"[dim]Data as of: {data['timestamp']}[/dim]")
    
    # Display network summary
    if 'network_summary' in data:
        summary = data['network_summary']
        
        summary_table = Table(title="Network Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        metrics = [
            ("Total Nodes", summary.get('total_nodes', 'N/A')),
            ("RPC Nodes Available", summary.get('rpc_nodes_available', 'N/A')),
            ("RPC Availability", f"{summary.get('rpc_availability_percentage', 'N/A')}%"),
            ("Latest Version", summary.get('latest_version', 'N/A')),
            ("Nodes on Latest Version", f"{summary.get('nodes_on_latest_version_percentage', 'N/A')}%"),
            ("Total Versions in Use", summary.get('total_versions_in_use', 'N/A')),
            ("Total Feature Sets", summary.get('total_feature_sets_in_use', 'N/A'))
        ]
        
        for metric, value in metrics:
            summary_table.add_row(metric, str(value))
        
        console.print(summary_table)
        
        # Display version distribution
        if 'version_distribution' in summary:
            version_table = Table(title="Version Distribution")
            version_table.add_column("Version", style="cyan")
            version_table.add_column("Count", style="green")
            version_table.add_column("Percentage", style="green")
            
            for version, info in summary['version_distribution'].items():
                version_table.add_row(
                    version,
                    str(info.get('count', 'N/A')),
                    f"{info.get('percentage', 'N/A')}%"
                )
            
            console.print(version_table)
    
    # Display detailed information if not summary only
    if not summary_only and 'cluster_nodes' in data:
        # Show only a sample of nodes to avoid overwhelming output
        nodes = data['cluster_nodes'][:10]  # First 10 nodes
        
        nodes_table = Table(title=f"Cluster Nodes (showing {len(nodes)} of {len(data['cluster_nodes'])})")
        nodes_table.add_column("Pubkey", style="cyan", no_wrap=True)
        nodes_table.add_column("Version", style="green")
        nodes_table.add_column("Feature Set", style="green")
        nodes_table.add_column("RPC", style="green")
        
        for node in nodes:
            nodes_table.add_row(
                node.get('pubkey', 'N/A')[:16] + "...",
                node.get('version', 'N/A'),
                str(node.get('feature_set', 'N/A')),
                "✓" if node.get('rpc', False) else "✗"
            )
        
        console.print(nodes_table)
        console.print("[dim]Note: Only showing a sample of nodes. Use --format json for complete data.[/dim]")

@network.command()
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.option('--output', type=click.Path(), help='Save output to file')
@click.pass_context
def performance(ctx, format, output):
    """Get Solana network performance metrics"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    # Create API client
    api = SolecoAPI(config.api_url, timeout=config.get('timeout', 30))
    
    try:
        with console.status("[bold green]Fetching performance metrics..."):
            result = api.get_performance_metrics()
        
        # Determine output format
        output_format = format or config.get('format', 'table')
        
        if output_format == 'table':
            _display_performance_metrics_table(console, result)
        else:
            # Handle other formats
            format_output(result, output_format, output, console)
            
    except APIError as e:
        handle_api_error(e, console)
    finally:
        api.close()

def _display_performance_metrics_table(console: Console, data: Dict[str, Any]):
    """Display performance metrics as a table"""
    if 'performance_samples' in data:
        samples = data['performance_samples']
        
        # Create performance table
        perf_table = Table(title="Performance Metrics")
        perf_table.add_column("Metric", style="cyan")
        perf_table.add_column("Value", style="green")
        
        if 'summary' in data:
            summary = data['summary']
            metrics = [
                ("Avg. TPS", f"{summary.get('avg_tps', 'N/A'):.2f}"),
                ("Max TPS", f"{summary.get('max_tps', 'N/A'):.2f}"),
                ("Avg. Block Time", f"{summary.get('avg_block_time', 'N/A'):.2f} ms"),
                ("Avg. Slot Time", f"{summary.get('avg_slot_time', 'N/A'):.2f} ms"),
                ("Current Slot", str(summary.get('current_slot', 'N/A'))),
                ("Slot Height", str(summary.get('slot_height', 'N/A'))),
                ("Transaction Count", str(summary.get('transaction_count', 'N/A')))
            ]
            
            for metric, value in metrics:
                perf_table.add_row(metric, value)
        
        console.print(perf_table)
        
        # Display recent samples
        if len(samples) > 0:
            samples_table = Table(title="Recent Performance Samples")
            samples_table.add_column("Slot", style="cyan")
            samples_table.add_column("TPS", style="green")
            samples_table.add_column("Block Time", style="green")
            samples_table.add_column("Success Rate", style="green")
            
            for sample in samples[:10]:  # Show only the most recent samples
                samples_table.add_row(
                    str(sample.get('slot', 'N/A')),
                    f"{sample.get('tps', 'N/A'):.2f}",
                    f"{sample.get('block_time', 'N/A'):.2f} ms",
                    f"{sample.get('success_rate', 'N/A') * 100:.1f}%"
                )
            
            console.print(samples_table)
    else:
        console.print("[yellow]No performance data available[/yellow]")
