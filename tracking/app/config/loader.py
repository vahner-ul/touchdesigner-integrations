"""
Configuration loader for YAML files
"""

import os
from pathlib import Path
from typing import Optional

import yaml

from .schema import AppConfig


class ConfigLoader:
    """Configuration loader with YAML support"""
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize config loader"""
        self.config_path = config_path or "config.yaml"
    
    def load(self) -> AppConfig:
        """Load configuration from file"""
        try:
            if not os.path.exists(self.config_path):
                # Return default configuration
                return AppConfig()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            return AppConfig(**data)
        except Exception as e:
            print(f"Error loading config from {self.config_path}: {e}")
            # Return default configuration on error
            return AppConfig()
    
    def save(self, config: AppConfig) -> None:
        """Save configuration to file"""
        try:
            # Create directory if it doesn't exist
            config_dir = Path(self.config_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config.model_dump(), f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"Error saving config to {self.config_path}: {e}")
    
    def save_config(self, config_dict: dict) -> Path:
        """Save configuration dictionary to file"""
        try:
            # Create directory if it doesn't exist
            config_dir = Path(self.config_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            return Path(self.config_path)
        except Exception as e:
            print(f"Error saving config to {self.config_path}: {e}")
            raise
    
    def get_config_path(self) -> Path:
        """Get the path to the configuration file"""
        return Path(self.config_path)
    
    def create_default_config(self) -> None:
        """Create default configuration file"""
        config = AppConfig()
        
        # Add example camera
        from .schema import CameraConfig
        example_camera = CameraConfig(
            id="cam1",
            name="Example Camera",
            stream="rtsp://user:pass@host/stream",
            enabled=False  # Disabled by default
        )
        config.cameras.append(example_camera)
        
        self.save(config)
        print(f"Created default configuration at {self.config_path}")
