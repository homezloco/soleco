"""
CLI download and information endpoints
"""

import os
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(
    prefix="/cli",
    tags=["cli"],
    responses={404: {"description": "Not found"}},
)

class CLIInfo(BaseModel):
    """CLI information model"""
    version: str
    description: str
    features: Dict[str, Any]
    installation: Dict[str, str]
    documentation_url: str

# CLI information
CLI_INFO = {
    "version": "0.1.0",
    "description": "A powerful command-line interface for interacting with the Soleco Solana blockchain analytics platform.",
    "features": {
        "network_analytics": "Access Solana network status and performance metrics",
        "rpc_node_management": "List, analyze, and check health of Solana RPC nodes",
        "mint_analytics": "Track and analyze token mints, including pump tokens",
        "interactive_shell": "User-friendly shell for interactive exploration",
        "multiple_output_formats": "Export data as JSON, CSV, or formatted tables",
        "configuration_management": "Easily configure API endpoints and preferences"
    },
    "installation": {
        "pip": "pip install soleco-cli",
        "source": "git clone https://github.com/yourusername/soleco.git && cd soleco/cli && pip install -e ."
    },
    "documentation_url": "/cli/docs"
}

@router.get("/info", response_model=CLIInfo)
async def get_cli_info():
    """Get CLI information"""
    return CLI_INFO

@router.get("/download")
async def download_cli():
    """Download the latest CLI package"""
    # Path to the CLI package
    cli_package_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   "downloads", "soleco-cli-latest.tar.gz")
    
    # Check if the file exists
    if not os.path.exists(cli_package_path):
        raise HTTPException(status_code=404, detail="CLI package not found")
    
    return FileResponse(
        path=cli_package_path,
        filename="soleco-cli-latest.tar.gz",
        media_type="application/gzip"
    )

@router.get("/docs")
async def get_cli_docs():
    """Get CLI documentation"""
    # Path to the CLI documentation
    cli_docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                               "downloads", "soleco-cli-docs.html")
    
    # Check if the file exists
    if not os.path.exists(cli_docs_path):
        raise HTTPException(status_code=404, detail="CLI documentation not found")
    
    return FileResponse(
        path=cli_docs_path,
        filename="soleco-cli-docs.html",
        media_type="text/html"
    )
