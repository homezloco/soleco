"""
Configuration management for Soleco CLI
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("soleco")

DEFAULT_CONFIG = {
    "api_url": "http://localhost:8000",
    "format": "table",
    "timeout": 30,
    "max_retries": 3,
    "color": True,
}

class Config:
    """Configuration manager for Soleco CLI"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager"""
        # Determine config file path
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Default to ~/.soleco/config.json
            self.config_path = Path.home() / ".soleco" / "config.json"
        
        # Create parent directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or create config
        self.config = self._load_config()
        logger.debug(f"Loaded configuration from {self.config_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults for any missing keys
                return {**DEFAULT_CONFIG, **config}
            except Exception as e:
                logger.warning(f"Error loading config file: {e}")
                return DEFAULT_CONFIG.copy()
        else:
            # Create default config
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value"""
        self.config[key] = value
        self._save_config(self.config)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return self.config.copy()
    
    def reset(self) -> None:
        """Reset configuration to defaults"""
        self.config = DEFAULT_CONFIG.copy()
        self._save_config(self.config)
    
    @property
    def api_url(self) -> str:
        """Get the API URL"""
        return self.get("api_url")
    
    @api_url.setter
    def api_url(self, value: str) -> None:
        """Set the API URL"""
        self.set("api_url", value)
