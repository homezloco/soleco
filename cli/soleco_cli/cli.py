"""
Soleco CLI - Command-line interface for the Soleco project
"""

import os
import sys
import click
import logging
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from .config import Config
from .api import SolecoAPI, APIError
from .utils import setup_logging, handle_api_error
from .commands.network import network
from .commands.rpc import rpc
from .commands.mint import mint
from .commands.diagnostics import diagnostics

# Set up logger
logger = logging.getLogger("soleco")

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config', type=click.Path(), help='Path to config file')
@click.option('--no-color', is_flag=True, help='Disable colored output')
@click.version_option(version='0.1.0')
@click.pass_context
def cli(ctx, debug, config, no_color):
    """Soleco CLI - Command-line interface for the Soleco project"""
    # Set up logging
    setup_logging(debug)
    
    # Initialize console
    console = Console(color_system=None if no_color else "auto")
    
    # Load configuration
    config_obj = Config(config)
    
    # Store in context
    ctx.ensure_object(dict)
    ctx.obj['console'] = console
    ctx.obj['config'] = config_obj
    ctx.obj['debug'] = debug
    
    logger.debug("CLI initialized")

# Add command groups
cli.add_command(network)
cli.add_command(rpc)
cli.add_command(mint)
cli.add_command(diagnostics)

@cli.command()
@click.option('--key', help='Configuration key to get')
@click.pass_context
def config(ctx, key):
    """Get or list configuration values"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    if key:
        # Get specific config value
        value = config.get(key)
        if value is not None:
            console.print(f"{key}: {value}")
        else:
            console.print(f"[yellow]Configuration key '{key}' not found[/yellow]")
    else:
        # List all config values
        config_data = config.get_all()
        
        table = Table(title="Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        
        for k, v in config_data.items():
            table.add_row(k, str(v))
        
        console.print(table)

@cli.command()
@click.argument('key')
@click.argument('value')
@click.pass_context
def set_config(ctx, key, value):
    """Set a configuration value"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    # Convert string value to appropriate type
    if value.lower() == 'true':
        typed_value = True
    elif value.lower() == 'false':
        typed_value = False
    elif value.isdigit():
        typed_value = int(value)
    elif value.replace('.', '', 1).isdigit():
        typed_value = float(value)
    else:
        typed_value = value
    
    # Set config value
    config.set(key, typed_value)
    console.print(f"[green]Configuration updated: {key} = {typed_value}[/green]")

@cli.command()
@click.pass_context
def reset_config(ctx):
    """Reset configuration to defaults"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    if Confirm.ask("Are you sure you want to reset all configuration to defaults?"):
        config.reset()
        console.print("[green]Configuration reset to defaults[/green]")
    else:
        console.print("[yellow]Reset cancelled[/yellow]")

@cli.command()
@click.pass_context
def shell(ctx):
    """Start an interactive shell"""
    console = ctx.obj['console']
    config = ctx.obj['config']
    
    console.print(Panel("[bold]Soleco Interactive Shell[/bold]\nType 'help' for a list of commands, 'exit' to quit", expand=False))
    
    while True:
        try:
            command = Prompt.ask("[bold blue]soleco[/bold blue]")
            
            if command.lower() in ('exit', 'quit'):
                break
            elif command.lower() == 'help':
                _display_shell_help(console)
            elif command.lower() == 'config':
                # Re-run the config command
                ctx.invoke(config)
            elif command.startswith('set '):
                # Parse set command
                parts = command.split(' ', 2)
                if len(parts) == 3:
                    _, key, value = parts
                    ctx.invoke(set_config, key=key, value=value)
                else:
                    console.print("[yellow]Invalid set command. Usage: set <key> <value>[/yellow]")
            elif command.lower() == 'status':
                # Get network status
                ctx.invoke(network.commands['status'], summary=True, format=None, output=None)
            elif command.lower() == 'rpc':
                # List RPC nodes
                ctx.invoke(rpc.commands['list'], details=False, health_check=False, format=None, output=None, version=None, status='all', sort=None)
            elif command.lower() == 'mints':
                # Get recent mints
                ctx.invoke(mint.commands['recent'], blocks=5, format=None, output=None, pump_only=False, new_only=False)
            elif command.lower() == 'diagnostics':
                # Get diagnostics
                ctx.invoke(diagnostics.commands['info'], format=None, output=None)
            else:
                # Try to run as a CLI command
                try:
                    # This is a simplified approach - a more robust solution would use a proper command parser
                    sys.argv = ['soleco'] + command.split()
                    cli(standalone_mode=False, obj=ctx.obj)
                except click.exceptions.UsageError:
                    console.print(f"[yellow]Unknown command: {command}[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Command interrupted[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            if ctx.obj['debug']:
                import traceback
                console.print(traceback.format_exc())
    
    console.print("[green]Exiting shell[/green]")

def _display_shell_help(console: Console):
    """Display help for the interactive shell"""
    help_table = Table(title="Available Commands")
    help_table.add_column("Command", style="cyan")
    help_table.add_column("Description", style="green")
    
    commands = [
        ("help", "Display this help message"),
        ("exit", "Exit the shell"),
        ("config", "Show current configuration"),
        ("set <key> <value>", "Set a configuration value"),
        ("status", "Show network status summary"),
        ("rpc", "List RPC nodes"),
        ("mints", "Show recent mints"),
        ("diagnostics", "Show system diagnostics"),
        ("<command> [args]", "Run any CLI command with arguments")
    ]
    
    for cmd, desc in commands:
        help_table.add_row(cmd, desc)
    
    console.print(help_table)

if __name__ == '__main__':
    cli()
