"""
Utility functions for Soleco CLI
"""

import json
import csv
import logging
import sys
from typing import Dict, Any, Optional, List, TextIO
from rich.console import Console
from rich.panel import Panel
from pathlib import Path
from soleco_cli.api import APIError

logger = logging.getLogger("soleco")

def setup_logging(debug: bool = False):
    """Set up logging for the CLI"""
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Create file handler
    log_dir = Path.home() / ".soleco" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_dir / "soleco_cli.log")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure soleco logger
    soleco_logger = logging.getLogger("soleco")
    soleco_logger.setLevel(log_level)
    
    logger.debug("Logging initialized")

def format_output(data: Dict[str, Any], format_type: str, output_path: Optional[str], console: Console):
    """Format and output data"""
    if format_type == 'json':
        formatted_data = json.dumps(data, indent=2)
    elif format_type == 'csv':
        formatted_data = _dict_to_csv(data)
    else:
        # Default to JSON
        formatted_data = json.dumps(data, indent=2)
    
    if output_path:
        # Write to file
        try:
            with open(output_path, 'w') as f:
                f.write(formatted_data)
            console.print(f"[green]Output saved to {output_path}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving output to {output_path}: {str(e)}[/red]")
    else:
        # Print to console
        if format_type == 'json':
            console.print_json(formatted_data)
        else:
            console.print(formatted_data)

def _dict_to_csv(data: Dict[str, Any]) -> str:
    """Convert dictionary to CSV string"""
    # This is a simple implementation that works for flat dictionaries
    # For nested dictionaries, a more complex implementation would be needed
    
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    writer.writerow(data.keys())
    
    # Write data row
    writer.writerow(data.values())
    
    return output.getvalue()

def handle_api_error(error: APIError, console: Console):
    """Handle API errors"""
    console.print(Panel(f"[bold red]Error: {str(error)}[/bold red]", title="API Error", expand=False))
    logger.error(f"API error: {str(error)}")

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """Flatten a nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def truncate_string(s: str, max_length: int = 50) -> str:
    """Truncate a string to a maximum length"""
    if len(s) <= max_length:
        return s
    return s[:max_length - 3] + "..."

def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string"""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.2f}h"
    else:
        days = seconds / 86400
        return f"{days:.2f}d"

def format_bytes(size_bytes: int) -> str:
    """Format bytes to a human-readable string"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
