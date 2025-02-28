#!/usr/bin/env python
"""
Example script demonstrating how to extend the Soleco CLI with custom commands.

This script shows how to:
1. Create custom Click commands
2. Integrate with the Soleco API
3. Add custom formatting and processing logic
4. Create a standalone CLI tool that extends Soleco functionality
"""

import os
import sys
import json
import click
import logging
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table

# Add the parent directory to the path to import soleco_cli
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from soleco_cli.config import Config
from soleco_cli.api import SolecoAPI
from soleco_cli.utils import setup_logging, format_json, format_table, export_to_file

# Initialize console for rich output
console = Console()

# Initialize configuration
config = Config()

# Initialize API client
api = SolecoAPI(
    api_url=config.get("api_url"),
    timeout=config.get("timeout")
)

# Create a Click group for our custom commands
@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.version_option(version='0.1.0')
def cli(debug):
    """Custom extension for the Soleco CLI with additional commands."""
    setup_logging(debug)
    if debug:
        click.echo("Debug mode enabled")

# Command to find pump tokens in recent blocks
@cli.command()
@click.option('--blocks', default=5, help='Number of blocks to analyze')
@click.option('--min-holders', default=0, type=int, help='Minimum number of holders')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.option('--output', type=str, help='Output file path')
def find_pump_tokens(blocks, min_holders, output_format, output):
    """Find pump tokens in recent blocks with filtering options."""
    try:
        console.print(f"[bold blue]Finding pump tokens in {blocks} recent blocks...[/bold blue]")
        
        # Get recent mints
        response = api.get_recent_mints(limit=blocks)
        
        if 'data' not in response or 'mints' not in response['data']:
            console.print("[bold red]Error: Invalid response from API[/bold red]")
            return
        
        mints = response['data']['mints']
        
        # Extract pump tokens
        pump_tokens = []
        for mint in mints:
            block_number = mint.get('block_number', 'unknown')
            timestamp = mint.get('timestamp', 'unknown')
            
            for token in mint.get('pump_token_addresses', []):
                # For a real implementation, we would fetch token details
                # Here we'll simulate some data
                holders = min_holders + 1  # Simulate holder count
                
                pump_tokens.append({
                    'address': token,
                    'block_number': block_number,
                    'timestamp': timestamp,
                    'holders': holders,
                    'name': f"PUMP{token[-4:]}",  # Simulate token name
                    'supply': 1000000000  # Simulate token supply
                })
        
        # Filter by minimum holders
        if min_holders > 0:
            pump_tokens = [t for t in pump_tokens if t['holders'] >= min_holders]
        
        # Display results
        if not pump_tokens:
            console.print("[yellow]No pump tokens found matching the criteria[/yellow]")
            return
        
        console.print(f"[green]Found {len(pump_tokens)} pump tokens[/green]")
        
        # Format output
        if output_format == 'table':
            table = Table(title=f"Pump Tokens (Last {blocks} Blocks)")
            table.add_column("Address", style="cyan")
            table.add_column("Block", style="blue")
            table.add_column("Timestamp", style="green")
            table.add_column("Holders", justify="right", style="yellow")
            table.add_column("Name", style="magenta")
            
            for token in pump_tokens:
                table.add_row(
                    token['address'],
                    str(token['block_number']),
                    token['timestamp'],
                    str(token['holders']),
                    token['name']
                )
            
            console.print(table)
        
        # Export if output file specified
        if output:
            export_to_file(pump_tokens, output, output_format)
            console.print(f"[italic]Exported pump tokens to {output}[/italic]")
        
    except Exception as e:
        console.print(f"[bold red]Error finding pump tokens: {str(e)}[/bold red]")

# Command to compare RPC node performance
@cli.command()
@click.option('--top', default=5, help='Number of top nodes to show')
@click.option('--health-check', is_flag=True, help='Perform health check')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.option('--output', type=str, help='Output file path')
def compare_rpc_nodes(top, health_check, output_format, output):
    """Compare performance of RPC nodes and rank them."""
    try:
        console.print(f"[bold blue]Comparing RPC node performance...[/bold blue]")
        
        # Get RPC nodes with health check if requested
        response = api.get_rpc_nodes(health_check=health_check)
        
        if 'data' not in response or 'nodes' not in response['data']:
            console.print("[bold red]Error: Invalid response from API[/bold red]")
            return
        
        nodes = response['data']['nodes']
        
        if not nodes:
            console.print("[yellow]No RPC nodes found[/yellow]")
            return
        
        console.print(f"[green]Found {len(nodes)} RPC nodes[/green]")
        
        # For health-checked nodes, rank by latency
        if health_check:
            # Filter nodes with health check data
            healthy_nodes = [n for n in nodes if 'health_check' in n and n['health_check'].get('is_healthy', False)]
            
            if not healthy_nodes:
                console.print("[yellow]No healthy nodes found[/yellow]")
                return
            
            # Sort by latency
            ranked_nodes = sorted(
                healthy_nodes, 
                key=lambda n: n['health_check'].get('latency_ms', float('inf'))
            )
            
            # Take top N
            top_nodes = ranked_nodes[:top]
            
            # Format for display
            node_data = []
            for node in top_nodes:
                health = node.get('health_check', {})
                node_data.append({
                    "url": node.get("url", "N/A"),
                    "version": node.get("version", "N/A"),
                    "latency_ms": health.get("latency_ms", "N/A"),
                    "success_rate": f"{health.get('success_rate', 0) * 100:.1f}%",
                    "is_public": "Yes" if node.get("is_public", False) else "No"
                })
            
            # Display table
            if output_format == 'table':
                table = Table(title=f"Top {top} RPC Nodes by Latency")
                table.add_column("URL", style="cyan")
                table.add_column("Version", style="blue")
                table.add_column("Latency (ms)", justify="right", style="green")
                table.add_column("Success Rate", justify="right", style="yellow")
                table.add_column("Public", style="magenta")
                
                for node in node_data:
                    table.add_row(
                        node['url'],
                        node['version'],
                        str(node['latency_ms']),
                        node['success_rate'],
                        node['is_public']
                    )
                
                console.print(table)
            
            # Export if output file specified
            if output:
                export_to_file(node_data, output, output_format)
                console.print(f"[italic]Exported RPC node comparison to {output}[/italic]")
        else:
            console.print("[yellow]Health check is required for performance comparison[/yellow]")
            console.print("[yellow]Run with --health-check flag[/yellow]")
    
    except Exception as e:
        console.print(f"[bold red]Error comparing RPC nodes: {str(e)}[/bold red]")

# Command to generate a daily report
@cli.command()
@click.option('--days', default=1, help='Number of days to include in report')
@click.option('--format', 'output_format', type=click.Choice(['markdown', 'json', 'html']), default='markdown', help='Output format')
@click.option('--output', type=str, help='Output file path')
def daily_report(days, output_format, output):
    """Generate a daily report of Solana network activity."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        console.print(f"[bold blue]Generating daily report from {start_date.date()} to {end_date.date()}...[/bold blue]")
        
        # Collect data for report
        report_data = {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "network_status": None,
            "rpc_nodes": {
                "total": 0,
                "versions": {}
            },
            "mint_activity": {
                "total_new_mints": 0,
                "total_pump_tokens": 0,
                "recent_pump_tokens": []
            }
        }
        
        # Get network status
        try:
            network_status = api.get_network_status()
            if 'data' in network_status:
                report_data["network_status"] = network_status["data"]
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch network status: {str(e)}[/yellow]")
        
        # Get RPC nodes
        try:
            rpc_response = api.get_rpc_nodes()
            if 'data' in rpc_response and 'nodes' in rpc_response['data']:
                nodes = rpc_response['data']['nodes']
                report_data["rpc_nodes"]["total"] = len(nodes)
                
                # Count versions
                versions = {}
                for node in nodes:
                    version = node.get("version", "unknown")
                    versions[version] = versions.get(version, 0) + 1
                
                report_data["rpc_nodes"]["versions"] = versions
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch RPC nodes: {str(e)}[/yellow]")
        
        # Get recent mints
        try:
            mints_response = api.get_recent_mints(limit=10)
            if 'data' in mints_response and 'mints' in mints_response['data']:
                mints = mints_response['data']['mints']
                
                # Count new mints and pump tokens
                total_new_mints = sum(len(mint.get('new_mint_addresses', [])) for mint in mints)
                total_pump_tokens = sum(len(mint.get('pump_token_addresses', [])) for mint in mints)
                
                report_data["mint_activity"]["total_new_mints"] = total_new_mints
                report_data["mint_activity"]["total_pump_tokens"] = total_pump_tokens
                
                # Collect recent pump tokens
                for mint in mints:
                    for token in mint.get('pump_token_addresses', [])[:5]:  # Limit to 5 per block
                        report_data["mint_activity"]["recent_pump_tokens"].append({
                            "address": token,
                            "block_number": mint.get('block_number', 'unknown'),
                            "timestamp": mint.get('timestamp', 'unknown')
                        })
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch recent mints: {str(e)}[/yellow]")
        
        # Generate report in requested format
        if output_format == 'json':
            report_content = json.dumps(report_data, indent=2)
        elif output_format == 'html':
            # Simple HTML report
            report_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Soleco Daily Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .section {{ margin-bottom: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>Soleco Daily Report</h1>
    <p>Period: {start_date.date()} to {end_date.date()} ({days} days)</p>
    
    <div class="section">
        <h2>Network Status</h2>
        <p>Status: {report_data['network_status'].get('status', 'Unknown') if report_data['network_status'] else 'Unknown'}</p>
        
        {f'''
        <h3>Network Summary</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Nodes</td><td>{report_data['network_status']['network_summary'].get('total_nodes', 'N/A')}</td></tr>
            <tr><td>RPC Nodes Available</td><td>{report_data['network_status']['network_summary'].get('rpc_nodes_available', 'N/A')}</td></tr>
            <tr><td>Latest Version</td><td>{report_data['network_status']['network_summary'].get('latest_version', 'N/A')}</td></tr>
        </table>
        ''' if report_data['network_status'] and 'network_summary' in report_data['network_status'] else ''}
    </div>
    
    <div class="section">
        <h2>RPC Nodes</h2>
        <p>Total RPC Nodes: {report_data['rpc_nodes']['total']}</p>
        
        <h3>Version Distribution</h3>
        <table>
            <tr><th>Version</th><th>Count</th></tr>
            {''.join(f'<tr><td>{version}</td><td>{count}</td></tr>' for version, count in report_data['rpc_nodes']['versions'].items())}
        </table>
    </div>
    
    <div class="section">
        <h2>Mint Activity</h2>
        <p>Total New Mints: {report_data['mint_activity']['total_new_mints']}</p>
        <p>Total Pump Tokens: {report_data['mint_activity']['total_pump_tokens']}</p>
        
        <h3>Recent Pump Tokens</h3>
        <table>
            <tr><th>Address</th><th>Block</th><th>Timestamp</th></tr>
            {''.join(f'<tr><td>{token["address"]}</td><td>{token["block_number"]}</td><td>{token["timestamp"]}</td></tr>' for token in report_data['mint_activity']['recent_pump_tokens'])}
        </table>
    </div>
</body>
</html>"""
        else:  # markdown
            # Generate markdown report
            report_content = f"""# Soleco Daily Report

Period: {start_date.date()} to {end_date.date()} ({days} days)

## Network Status

Status: **{report_data['network_status'].get('status', 'Unknown').upper() if report_data['network_status'] else 'UNKNOWN'}**

"""
            if report_data['network_status'] and 'network_summary' in report_data['network_status']:
                summary = report_data['network_status']['network_summary']
                report_content += f"""### Network Summary

- Total Nodes: {summary.get('total_nodes', 'N/A')}
- RPC Nodes Available: {summary.get('rpc_nodes_available', 'N/A')}
- RPC Availability: {summary.get('rpc_availability_percentage', 'N/A')}%
- Latest Version: {summary.get('latest_version', 'N/A')}
- Nodes on Latest Version: {summary.get('nodes_on_latest_version_percentage', 'N/A')}%

"""
            
            report_content += f"""## RPC Nodes

Total RPC Nodes: **{report_data['rpc_nodes']['total']}**

### Version Distribution

| Version | Count |
|---------|-------|
"""
            for version, count in report_data['rpc_nodes']['versions'].items():
                report_content += f"| {version} | {count} |\n"
            
            report_content += f"""
## Mint Activity

- Total New Mints: **{report_data['mint_activity']['total_new_mints']}**
- Total Pump Tokens: **{report_data['mint_activity']['total_pump_tokens']}**

### Recent Pump Tokens

| Address | Block | Timestamp |
|---------|-------|-----------|
"""
            for token in report_data['mint_activity']['recent_pump_tokens']:
                report_content += f"| {token['address']} | {token['block_number']} | {token['timestamp']} |\n"
        
        # Output report
        if output:
            with open(output, 'w') as f:
                f.write(report_content)
            console.print(f"[green]Report saved to {output}[/green]")
        else:
            console.print("\n" + report_content)
    
    except Exception as e:
        console.print(f"[bold red]Error generating daily report: {str(e)}[/bold red]")

if __name__ == "__main__":
    cli()
