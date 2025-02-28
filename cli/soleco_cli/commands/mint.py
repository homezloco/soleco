"""
Mint commands for the Soleco CLI
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
def mint():
    """Commands for interacting with Solana mint data"""
    pass

@mint.command('recent')
@click.option('--blocks', type=int, default=5, help='Number of recent blocks to analyze')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.option('--output', type=click.Path(), help='Save output to file')
@click.option('--pump-only', is_flag=True, help='Show only pump tokens')
@click.option('--new-only', is_flag=True, help='Show only new mint addresses')
@click.pass_context
def recent_mints(ctx, blocks, format, output, pump_only, new_only):
    """Get recently created mint addresses"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    # Create API client
    api = SolecoAPI(config.api_url, timeout=config.get('timeout', 30))
    
    try:
        with console.status("[bold green]Fetching recent mints..."):
            result = api.get_recent_mints(blocks=blocks)
        
        # Determine output format
        output_format = format or config.get('format', 'table')
        
        if output_format == 'table':
            _display_recent_mints_table(console, result, pump_only, new_only)
        else:
            # Handle other formats
            format_output(result, output_format, output, console)
            
    except APIError as e:
        handle_api_error(e, console)
    finally:
        api.close()

def _display_recent_mints_table(console: Console, data: Dict[str, Any], pump_only: bool, new_only: bool):
    """Display recent mints as a table"""
    # Display summary
    title = "Recent Mint Addresses"
    if pump_only:
        title += " (Pump Tokens Only)"
    elif new_only:
        title += " (New Mints Only)"
    
    console.print(Panel(f"[bold]{title}[/bold]", expand=False))
    
    if 'timestamp' in data:
        console.print(f"[dim]Data as of: {data['timestamp']}[/dim]")
    
    # Display summary stats
    if 'stats' in data:
        stats = data['stats']
        
        stats_table = Table(title="Summary Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")
        
        metrics = [
            ("Blocks Analyzed", stats.get('blocks_analyzed', 'N/A')),
            ("Total Mint Addresses", stats.get('total_mint_addresses', 'N/A')),
            ("Total New Mint Addresses", stats.get('total_new_mint_addresses', 'N/A')),
            ("Total Pump Tokens", stats.get('total_pump_tokens', 'N/A')),
            ("Average Mints Per Block", f"{stats.get('avg_mints_per_block', 'N/A'):.2f}"),
            ("Average New Mints Per Block", f"{stats.get('avg_new_mints_per_block', 'N/A'):.2f}"),
            ("Average Pump Tokens Per Block", f"{stats.get('avg_pump_tokens_per_block', 'N/A'):.2f}")
        ]
        
        for metric, value in metrics:
            stats_table.add_row(metric, str(value))
        
        console.print(stats_table)
    
    # Display mint addresses by block
    if 'blocks' in data:
        blocks = data['blocks']
        
        for block_data in blocks:
            block_slot = block_data.get('slot', 'Unknown')
            block_time = block_data.get('block_time', 'Unknown')
            
            # Determine which addresses to display
            addresses = []
            if pump_only and 'pump_tokens' in block_data:
                addresses = block_data['pump_tokens']
                address_type = "Pump Tokens"
            elif new_only and 'new_mint_addresses' in block_data:
                addresses = block_data['new_mint_addresses']
                address_type = "New Mint Addresses"
            elif 'mint_addresses' in block_data:
                addresses = block_data['mint_addresses']
                address_type = "Mint Addresses"
            
            # Skip if no addresses to display
            if not addresses:
                continue
            
            # Create table for this block
            block_table = Table(title=f"Block {block_slot} ({block_time})")
            block_table.add_column(address_type, style="green")
            
            # Add addresses to table
            for address in addresses:
                block_table.add_row(address)
            
            console.print(block_table)

@mint.command('analyze')
@click.argument('mint_address')
@click.option('--history', is_flag=True, help='Include transaction history')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.option('--output', type=click.Path(), help='Save output to file')
@click.pass_context
def analyze_mint(ctx, mint_address, history, format, output):
    """Analyze a specific mint address"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    # Create API client
    api = SolecoAPI(config.api_url, timeout=config.get('timeout', 30))
    
    try:
        with console.status(f"[bold green]Analyzing mint address {mint_address}..."):
            result = api.analyze_mint(mint_address, include_history=history)
        
        # Determine output format
        output_format = format or config.get('format', 'table')
        
        if output_format == 'table':
            _display_mint_analysis_table(console, result, mint_address)
        else:
            # Handle other formats
            format_output(result, output_format, output, console)
            
    except APIError as e:
        handle_api_error(e, console)
    finally:
        api.close()

def _display_mint_analysis_table(console: Console, data: Dict[str, Any], mint_address: str):
    """Display mint analysis as a table"""
    # Display mint info
    console.print(Panel(f"[bold]Mint Analysis: {mint_address}[/bold]", expand=False))
    
    if 'timestamp' in data:
        console.print(f"[dim]Data as of: {data['timestamp']}[/dim]")
    
    # Display mint details
    if 'mint_info' in data:
        mint_info = data['mint_info']
        
        info_table = Table(title="Mint Information")
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="green")
        
        properties = [
            ("Mint Address", mint_address),
            ("Creation Date", mint_info.get('creation_date', 'N/A')),
            ("Creator", mint_info.get('creator', 'N/A')),
            ("Is Pump Token", "Yes" if mint_info.get('is_pump_token', False) else "No"),
            ("Supply", mint_info.get('supply', 'N/A')),
            ("Decimals", mint_info.get('decimals', 'N/A')),
            ("Freeze Authority", mint_info.get('freeze_authority', 'N/A')),
            ("Mint Authority", mint_info.get('mint_authority', 'N/A'))
        ]
        
        for prop, value in properties:
            info_table.add_row(prop, str(value))
        
        console.print(info_table)
    
    # Display transaction statistics
    if 'transaction_stats' in data:
        tx_stats = data['transaction_stats']
        
        tx_table = Table(title="Transaction Statistics")
        tx_table.add_column("Metric", style="cyan")
        tx_table.add_column("Value", style="green")
        
        metrics = [
            ("Total Transactions", tx_stats.get('total_transactions', 'N/A')),
            ("First Transaction", tx_stats.get('first_transaction_date', 'N/A')),
            ("Last Transaction", tx_stats.get('last_transaction_date', 'N/A')),
            ("Unique Senders", tx_stats.get('unique_senders', 'N/A')),
            ("Unique Recipients", tx_stats.get('unique_recipients', 'N/A')),
            ("Total Volume", tx_stats.get('total_volume', 'N/A')),
            ("Average Transaction Size", tx_stats.get('avg_transaction_size', 'N/A'))
        ]
        
        for metric, value in metrics:
            tx_table.add_row(metric, str(value))
        
        console.print(tx_table)
    
    # Display transaction history if available
    if 'transaction_history' in data and data['transaction_history']:
        history = data['transaction_history']
        
        history_table = Table(title="Transaction History")
        history_table.add_column("Signature", style="cyan")
        history_table.add_column("Date", style="green")
        history_table.add_column("Type", style="green")
        history_table.add_column("Amount", style="green")
        
        # Show only the most recent transactions
        for tx in history[:10]:
            history_table.add_row(
                tx.get('signature', 'N/A')[:16] + "...",
                tx.get('date', 'N/A'),
                tx.get('type', 'N/A'),
                str(tx.get('amount', 'N/A'))
            )
        
        console.print(history_table)
        
        if len(history) > 10:
            console.print(f"[dim]Note: Only showing 10 of {len(history)} transactions. Use --format json for complete data.[/dim]")

@mint.command('stats')
@click.option('--timeframe', type=click.Choice(['1h', '6h', '12h', '24h', '7d', '30d']), default='24h', 
              help='Timeframe for statistics')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.option('--output', type=click.Path(), help='Save output to file')
@click.pass_context
def statistics(ctx, timeframe, format, output):
    """Get mint creation statistics for a specific timeframe"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    # Create API client
    api = SolecoAPI(config.api_url, timeout=config.get('timeout', 30))
    
    try:
        with console.status(f"[bold green]Fetching mint statistics for {timeframe}..."):
            result = api.get_mint_statistics(timeframe=timeframe)
        
        # Determine output format
        output_format = format or config.get('format', 'table')
        
        if output_format == 'table':
            _display_mint_statistics_table(console, result, timeframe)
        else:
            # Handle other formats
            format_output(result, output_format, output, console)
            
    except APIError as e:
        handle_api_error(e, console)
    finally:
        api.close()

def _display_mint_statistics_table(console: Console, data: Dict[str, Any], timeframe: str):
    """Display mint statistics as a table"""
    # Display summary
    console.print(Panel(f"[bold]Mint Creation Statistics ({timeframe})[/bold]", expand=False))
    
    if 'timestamp' in data:
        console.print(f"[dim]Data as of: {data['timestamp']}[/dim]")
    
    # Display summary stats
    if 'summary' in data:
        summary = data['summary']
        
        summary_table = Table(title="Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        metrics = [
            ("Total Mints Created", summary.get('total_mints_created', 'N/A')),
            ("Total New Mints", summary.get('total_new_mints', 'N/A')),
            ("Total Pump Tokens", summary.get('total_pump_tokens', 'N/A')),
            ("Average Mints Per Hour", f"{summary.get('avg_mints_per_hour', 'N/A'):.2f}"),
            ("Peak Mints Per Hour", summary.get('peak_mints_per_hour', 'N/A')),
            ("Peak Hour", summary.get('peak_hour', 'N/A'))
        ]
        
        for metric, value in metrics:
            summary_table.add_row(metric, str(value))
        
        console.print(summary_table)
    
    # Display hourly breakdown if available
    if 'hourly_breakdown' in data and data['hourly_breakdown']:
        hourly = data['hourly_breakdown']
        
        hourly_table = Table(title="Hourly Breakdown")
        hourly_table.add_column("Hour", style="cyan")
        hourly_table.add_column("Total Mints", style="green")
        hourly_table.add_column("New Mints", style="green")
        hourly_table.add_column("Pump Tokens", style="green")
        
        for hour_data in hourly:
            hourly_table.add_row(
                hour_data.get('hour', 'N/A'),
                str(hour_data.get('total_mints', 'N/A')),
                str(hour_data.get('new_mints', 'N/A')),
                str(hour_data.get('pump_tokens', 'N/A'))
            )
        
        console.print(hourly_table)
    
    # Display top creators if available
    if 'top_creators' in data and data['top_creators']:
        creators = data['top_creators']
        
        creators_table = Table(title="Top Creators")
        creators_table.add_column("Creator", style="cyan")
        creators_table.add_column("Mints Created", style="green")
        creators_table.add_column("Percentage", style="green")
        
        for creator in creators:
            creators_table.add_row(
                creator.get('address', 'N/A'),
                str(creator.get('mints_created', 'N/A')),
                f"{creator.get('percentage', 'N/A')}%"
            )
        
        console.print(creators_table)

@mint.command('extract')
@click.option('--limit', type=int, default=1, help='Number of recent blocks to analyze')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.option('--output', type=click.Path(), help='Save output to file')
@click.pass_context
def extract(ctx, limit, format, output):
    """Extract mint addresses from recent blocks"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    # Create API client
    api = SolecoAPI(config.api_url, timeout=config.get('timeout', 30))
    
    try:
        with console.status(f"[bold green]Extracting mint addresses from {limit} recent blocks..."):
            result = api.extract_mints_from_block(limit=limit)
        
        # Determine output format
        output_format = format or config.get('format', 'table')
        
        if output_format == 'table':
            _display_extracted_mints_table(console, result)
        else:
            # Handle other formats
            format_output(result, output_format, output, console)
            
    except APIError as e:
        handle_api_error(e, console)
    finally:
        api.close()

def _display_extracted_mints_table(console: Console, data: Dict[str, Any]):
    """Display extracted mint addresses as a table"""
    # Display summary
    console.print(Panel(f"[bold]Extracted Mint Addresses[/bold]", expand=False))
    
    if 'timestamp' in data:
        console.print(f"[dim]Data as of: {data['timestamp']}[/dim]")
    
    # Display summary stats
    if 'stats' in data:
        stats = data['stats']
        
        stats_table = Table(title="Summary Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")
        
        metrics = [
            ("Blocks Analyzed", stats.get('blocks_analyzed', 'N/A')),
            ("Total Mint Addresses", stats.get('total_mint_addresses', 'N/A')),
            ("Total New Mint Addresses", stats.get('total_new_mint_addresses', 'N/A')),
            ("Total Pump Tokens", stats.get('total_pump_tokens', 'N/A')),
            ("Processing Time", f"{stats.get('processing_time', 'N/A'):.2f}s")
        ]
        
        for metric, value in metrics:
            stats_table.add_row(metric, str(value))
        
        console.print(stats_table)
    
    # Display blocks
    if 'blocks' in data:
        blocks = data['blocks']
        
        for block_data in blocks:
            slot = block_data.get('slot', 'Unknown')
            block_time = block_data.get('block_time', 'Unknown')
            
            # Create block panel
            console.print(Panel(f"[bold]Block {slot} ({block_time})[/bold]", expand=False))
            
            # Display mint addresses
            if 'mint_addresses' in block_data and block_data['mint_addresses']:
                mint_table = Table(title="All Mint Addresses")
                mint_table.add_column("Address", style="green")
                
                for address in block_data['mint_addresses'][:20]:  # Limit to 20 addresses
                    mint_table.add_row(address)
                
                console.print(mint_table)
                
                if len(block_data['mint_addresses']) > 20:
                    console.print(f"[dim]Note: Only showing 20 of {len(block_data['mint_addresses'])} addresses.[/dim]")
            
            # Display new mint addresses
            if 'new_mint_addresses' in block_data and block_data['new_mint_addresses']:
                new_mint_table = Table(title="New Mint Addresses")
                new_mint_table.add_column("Address", style="cyan")
                
                for address in block_data['new_mint_addresses']:
                    new_mint_table.add_row(address)
                
                console.print(new_mint_table)
            
            # Display pump tokens
            if 'pump_token_addresses' in block_data and block_data['pump_token_addresses']:
                pump_table = Table(title="Pump Tokens")
                pump_table.add_column("Address", style="magenta")
                
                for address in block_data['pump_token_addresses']:
                    pump_table.add_row(address)
                
                console.print(pump_table)
