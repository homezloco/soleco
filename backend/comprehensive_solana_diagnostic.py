import sys
import os
import traceback
import json
import inspect
from typing import Any, Dict, Optional

# Add the backend directory to Python path
sys.path.append('/mnt/c/Users/Shane Holmes/CascadeProjects/windsurf-project/soleco/backend')

def safe_print(message):
    """Print with error handling"""
    try:
        print(message)
    except Exception as e:
        sys.stderr.write(f"Error printing message: {e}\n")

def safe_import(module_name):
    """Safely import a module"""
    try:
        return __import__(module_name)
    except Exception as e:
        safe_print(f"Failed to import {module_name}: {e}")
        safe_print(traceback.format_exc())
        return None

def inspect_module(module):
    """
    Provide a comprehensive inspection of a module
    
    Args:
        module (module): Python module to inspect
    
    Returns:
        Dict: Detailed module information
    """
    try:
        module_info = {
            'name': module.__name__,
            'file': getattr(module, '__file__', 'N/A'),
            'version': getattr(module, '__version__', 'N/A'),
            'doc': getattr(module, '__doc__', 'N/A'),
            'attributes': dir(module)
        }
        return module_info
    except Exception as e:
        safe_print(f"Error inspecting module {module}: {e}")
        return {}

def test_solana_rpc_connection(rpc_url: str = "https://api.mainnet-beta.solana.com"):
    """
    Test Solana RPC connection and basic operations
    
    Args:
        rpc_url (str): Solana RPC endpoint to test
    
    Returns:
        Dict: Connection test results
    """
    try:
        from solana.rpc.api import Client
        from solana.rpc.providers import http
        import httpx
        import inspect
        
        # Store original methods
        original_http_init = http.HTTPProvider.__init__
        original_httpx_init = httpx.Client.__init__
        
        def patched_http_init(self, *args, **kwargs):
            # Remove proxy from kwargs
            kwargs.pop('proxy', None)
            return original_http_init(self, *args, **kwargs)
        
        def patched_httpx_init(self, *args, **kwargs):
            # Remove proxy from kwargs
            kwargs.pop('proxy', None)
            return original_httpx_init(self, *args, **kwargs)
        
        try:
            # Patch initialization methods
            http.HTTPProvider.__init__ = patched_http_init
            httpx.Client.__init__ = patched_httpx_init
            
            # Initialize client
            client = Client(rpc_url)
            
            # Perform basic RPC calls
            cluster_nodes = client.get_cluster_nodes()
            results = {
                'cluster_nodes': len(cluster_nodes.value) if hasattr(cluster_nodes, 'value') else 0,
                'version': str(client.get_version()),
                'epoch_info': str(client.get_epoch_info())
            }
            
            return {
                'connection_successful': True,
                'rpc_url': rpc_url,
                'results': results
            }
        except Exception as e:
            return {
                'connection_successful': False,
                'error': str(e),
                'rpc_url': rpc_url
            }
        finally:
            # Restore original methods
            http.HTTPProvider.__init__ = original_http_init
            httpx.Client.__init__ = original_httpx_init
    
    except Exception as e:
        return {
            'connection_successful': False,
            'error': str(e),
            'rpc_url': rpc_url
        }

def main():
    # Explicitly remove proxy-related environment variables
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    for var in proxy_vars:
        os.environ.pop(var, None)

    safe_print("🔍 Comprehensive Solana Library Diagnostic")
    safe_print("=" * 50)

    # Python Environment Details
    safe_print("\n📋 Python Environment:")
    safe_print(f"Version: {sys.version}")
    safe_print(f"Executable: {sys.executable}")
    safe_print(f"Path: {sys.path}")

    # Solana Library Diagnostics
    safe_print("\n🔬 Solana Library Inspection:")
    try:
        import solana
        
        # Detailed module inspection
        solana_info = inspect_module(solana)
        safe_print("Solana Library Details:")
        safe_print(json.dumps(solana_info, indent=2))

        # Inspect library structure
        safe_print("\nSolana Library Structure:")
        solana_dir = os.path.dirname(solana.__file__)
        structure = {
            'root_contents': os.listdir(solana_dir),
            'rpc_contents': os.listdir(os.path.join(solana_dir, 'rpc'))
        }
        safe_print(json.dumps(structure, indent=2))
    except Exception as e:
        safe_print(f"Failed to inspect Solana library: {e}")
        safe_print(traceback.format_exc())

    # RPC Connection Test
    safe_print("\n🌐 Solana RPC Connection Test:")
    rpc_test_result = test_solana_rpc_connection()
    safe_print(json.dumps(rpc_test_result, indent=2))

    # Dependency Checks
    safe_print("\n📦 Dependency Information:")
    dependencies = ['solders', 'httpx', 'construct']
    for dep in dependencies:
        try:
            module = safe_import(dep)
            if module:
                dep_info = inspect_module(module)
                safe_print(f"{dep.capitalize()} Details:")
                safe_print(json.dumps(dep_info, indent=2))
        except Exception as e:
            safe_print(f"Failed to check {dep}: {e}")

    # Solana Specific Diagnostics
    safe_print("\n🔧 Solana-Specific Diagnostics:")
    try:
        # Try multiple import paths
        try:
            from solana.rpc.api import Client
        except ImportError:
            from solana.rpc.async_api import AsyncClient as Client
        
        from solders.pubkey import Pubkey as PublicKey
        
        from solders.transaction import Transaction
        
        safe_print("Solana Core Components:")
        safe_print(f"Client Class: {Client}")
        safe_print(f"PublicKey/Pubkey Class: {PublicKey}")
        safe_print(f"Transaction Class: {Transaction}")
        
        # Inspect method signatures
        safe_print("\nMethod Signatures:")
        safe_print(f"Client.__init__: {inspect.signature(Client.__init__)}")
        safe_print(f"PublicKey.__init__: {inspect.signature(PublicKey.__init__)}")
        safe_print(f"Transaction.__init__: {inspect.signature(Transaction.__init__)}")
    
    except Exception as e:
        safe_print(f"Failed to inspect Solana components: {e}")
        safe_print(traceback.format_exc())

    safe_print("\n✅ Diagnostic Complete")

if __name__ == '__main__':
    main()
