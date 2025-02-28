import sys
import os
import traceback
import inspect

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

def main():
    # Explicitly remove proxy-related environment variables
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    for var in proxy_vars:
        os.environ.pop(var, None)

    safe_print("Python Environment Details:")
    safe_print(f"Python Version: {sys.version}")
    safe_print(f"Python Executable: {sys.executable}")
    safe_print(f"Python Path: {sys.path}")

    safe_print("\nImport Diagnostics:")
    try:
        import solana
        
        safe_print("Solana Library Attributes:")
        safe_print(dir(solana))
        
        # Try to get version
        try:
            version = getattr(solana, '__version__', 'Not found')
            safe_print(f"Solana Library Version: {version}")
        except Exception as e:
            safe_print(f"Failed to get version: {e}")
        
        safe_print(f"Solana Library Location: {solana.__file__}")
    except Exception as e:
        safe_print(f"Failed to import solana: {e}")
        safe_print(traceback.format_exc())

    safe_print("\nClient Initialization Diagnostics:")
    try:
        from solana.rpc.api import Client  # Updated import path
        from solana.rpc.providers import http
        import httpx
        import inspect
        from typing import Optional, Dict
        from solana.rpc.commitment import Commitment
        
        safe_print("Synchronous Client Import: Successful")
        
        # Inspect Client initialization
        init_signature = inspect.signature(Client.__init__)
        safe_print("\nClient.__init__ Signature:")
        safe_print(init_signature)
        
        # List all parameters
        safe_print("\nParameters:")
        for name, param in init_signature.parameters.items():
            safe_print(f"- {name}: {param}")
        
        # Attempt client initialization
        safe_print("\nAttempting Client Initialization:")
        try:
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
                client = Client("https://api.mainnet-beta.solana.com")
                safe_print("Client initialized successfully")
            finally:
                # Restore original methods
                http.HTTPProvider.__init__ = original_http_init
                httpx.Client.__init__ = original_httpx_init
        
        except Exception as e:
            safe_print(f"Client initialization failed: {e}")
            safe_print(traceback.format_exc())

    except Exception as e:
        safe_print(f"Failed to import or inspect Client: {e}")
        safe_print(traceback.format_exc())

    safe_print("\nEnvironment Variables:")
    safe_print(f"HTTP_PROXY: {os.environ.get('HTTP_PROXY', 'Not set')}")
    safe_print(f"HTTPS_PROXY: {os.environ.get('HTTPS_PROXY', 'Not set')}")

    # Additional module checks
    safe_print("\nAdditional Module Information:")
    modules_to_check = ['httpx', 'websockets']
    for module_name in modules_to_check:
        try:
            module = safe_import(module_name)
            if module:
                safe_print(f"{module_name.capitalize()} Version: {module.__version__}")
        except Exception as e:
            safe_print(f"Failed to check {module_name}: {e}")

if __name__ == '__main__':
    main()
