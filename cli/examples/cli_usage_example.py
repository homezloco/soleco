#!/usr/bin/env python
"""
Example script demonstrating how to use the Soleco CLI programmatically.
This script shows how to:
1. Configure the Soleco CLI
2. Fetch network status
3. List RPC nodes
4. Analyze recent mints
5. Export results to different formats
"""

import os
import sys
import json
import logging
from rich.console import Console

# Add the parent directory to the path to import soleco_cli
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from soleco_cli.config import Config
from soleco_cli.api import SolecoAPI
from soleco_cli.utils import format_json, format_table, export_to_file

# Initialize console for rich output
console = Console()

def setup():
    """Setup the Soleco CLI configuration"""
    console.print("[bold blue]Setting up Soleco CLI...[/bold blue]")
    
    # Initialize configuration
    config = Config()
    
    # Set API URL if needed
    # config.set("api_url", "http://localhost:8000")
    
    # Enable debug mode
    config.set("debug", True)
    
    console.print(f"[green]Configuration loaded:[/green]")
    console.print(f"API URL: {config.get('api_url')}")
    console.print(f"Timeout: {config.get('timeout')} seconds")
    console.print(f"Debug: {config.get('debug')}")
    
    return config

def get_network_status(api):
    """Fetch and display network status"""
    console.print("\n[bold blue]Fetching Solana Network Status...[/bold blue]")
    
    try:
        response = api.get_network_status()
        
        # Display network status
        console.print("[green]Network Status:[/green]")
        
        if 'data' in response and 'status' in response['data']:
            status = response['data']['status']
            console.print(f"Status: [bold]{'HEALTHY' if status == 'healthy' else status.upper()}[/bold]")
        
        if 'data' in response and 'network_summary' in response['data']:
            summary = response['data']['network_summary']
            console.print("Network Summary:")
            for key, value in summary.items():
                console.print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Export to JSON
        export_to_file(response, "network_status.json", "json")
        console.print("[italic]Exported network status to network_status.json[/italic]")
        
        return response
    except Exception as e:
        console.print(f"[bold red]Error fetching network status: {str(e)}[/bold red]")
        return None

def list_rpc_nodes(api):
    """List RPC nodes"""
    console.print("\n[bold blue]Listing Solana RPC Nodes...[/bold blue]")
    
    try:
        # Get RPC nodes with details
        response = api.get_rpc_nodes(include_details=True)
        
        if 'data' in response and 'nodes' in response['data']:
            nodes = response['data']['nodes']
            console.print(f"[green]Found {len(nodes)} RPC nodes[/green]")
            
            # Format as table
            if nodes:
                # Extract relevant fields for display
                node_data = []
                for node in nodes:
                    node_data.append({
                        "url": node.get("url", "N/A"),
                        "version": node.get("version", "N/A"),
                        "features": len(node.get("features", [])),
                        "is_public": "Yes" if node.get("is_public", False) else "No"
                    })
                
                # Display table
                format_table(node_data, title="RPC Nodes")
            
            # Export to CSV
            export_to_file(nodes, "rpc_nodes.csv", "csv")
            console.print("[italic]Exported RPC nodes to rpc_nodes.csv[/italic]")
            
            return nodes
        else:
            console.print("[yellow]No RPC nodes found in response[/yellow]")
            return []
    except Exception as e:
        console.print(f"[bold red]Error listing RPC nodes: {str(e)}[/bold red]")
        return []

def analyze_recent_mints(api):
    """Analyze recent mints"""
    console.print("\n[bold blue]Analyzing Recent Mints...[/bold blue]")
    
    try:
        # Get recent mints
        response = api.get_recent_mints(limit=5)
        
        if 'data' in response and 'mints' in response['data']:
            mints = response['data']['mints']
            console.print(f"[green]Found {len(mints)} recent mints[/green]")
            
            # Display mint information
            for mint in mints:
                console.print(f"[bold]Block {mint.get('block_number', 'N/A')}[/bold]")
                console.print(f"  Timestamp: {mint.get('timestamp', 'N/A')}")
                console.print(f"  New Mint Addresses: {len(mint.get('new_mint_addresses', []))}")
                console.print(f"  Pump Tokens: {len(mint.get('pump_token_addresses', []))}")
                
                # Display pump tokens if any
                pump_tokens = mint.get('pump_token_addresses', [])
                if pump_tokens:
                    console.print("  [yellow]Pump Tokens:[/yellow]")
                    for token in pump_tokens[:3]:  # Show only first 3
                        console.print(f"    - {token}")
                    if len(pump_tokens) > 3:
                        console.print(f"    - ... and {len(pump_tokens) - 3} more")
                
                console.print("")
            
            # Export to JSON
            export_to_file(mints, "recent_mints.json", "json")
            console.print("[italic]Exported recent mints to recent_mints.json[/italic]")
            
            return mints
        else:
            console.print("[yellow]No recent mints found in response[/yellow]")
            return []
    except Exception as e:
        console.print(f"[bold red]Error analyzing recent mints: {str(e)}[/bold red]")
        return []

def main():
    """Main function"""
    console.print("[bold green]Soleco CLI Usage Example[/bold green]")
    
    # Setup configuration
    config = setup()
    
    # Initialize API client
    api = SolecoAPI(
        api_url=config.get("api_url"),
        timeout=config.get("timeout")
    )
    
    # Get network status
    network_status = get_network_status(api)
    
    # List RPC nodes
    rpc_nodes = list_rpc_nodes(api)
    
    # Analyze recent mints
    recent_mints = analyze_recent_mints(api)
    
    console.print("\n[bold green]Example completed![/bold green]")
    console.print("Check the generated files for exported data:")
    console.print("  - network_status.json")
    console.print("  - rpc_nodes.csv")
    console.print("  - recent_mints.json")

if __name__ == "__main__":
    main()
