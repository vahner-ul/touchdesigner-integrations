"""
Database-based configuration loader
"""

import os
from typing import Optional

from .database import ConfigDatabase
from .loader import ConfigLoader
from .schema import AppConfig


class DatabaseConfigLoader:
    """Configuration loader with SQLite database support"""
    
    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize database config loader"""
        self.db = ConfigDatabase(db_path or "config/settings.db")
        self.yaml_loader = ConfigLoader()  # Fallback to YAML
    
    def load(self) -> AppConfig:
        """Load configuration from database, fallback to YAML if empty"""
        try:
            # Try to load from database
            config = self.db.get_full_config()
            
            # If no cameras in database, try to import from YAML
            if not config.cameras:
                yaml_config = self.yaml_loader.load()
                if yaml_config.cameras:
                    print("Importing cameras from YAML to database...")
                    self.db.import_from_yaml(yaml_config)
                    config = self.db.get_full_config()
            
            return config
        except Exception as e:
            print(f"Error loading config from database: {e}")
            # Fallback to YAML
            print("Falling back to YAML configuration...")
            return self.yaml_loader.load()
    
    def save(self, config: AppConfig) -> None:
        """Save configuration to database"""
        try:
            self.db.save_full_config(config)
        except Exception as e:
            print(f"Error saving config to database: {e}")
            # Fallback to YAML
            self.yaml_loader.save(config)
    
    def get_cameras(self):
        """Get cameras from database"""
        return self.db.get_all_cameras()
    
    def get_camera(self, camera_id: str):
        """Get camera by ID from database"""
        return self.db.get_camera(camera_id)
    
    def save_camera(self, camera):
        """Save camera to database"""
        self.db.save_camera(camera)
    
    def delete_camera(self, camera_id: str) -> bool:
        """Delete camera from database"""
        return self.db.delete_camera(camera_id)
    
    def get_service_config(self):
        """Get service config from database"""
        return self.db.get_service_config()
    
    def save_service_config(self, config):
        """Save service config to database"""
        self.db.save_service_config(config)
    
    def get_tracking_config(self):
        """Get tracking config from database"""
        return self.db.get_tracking_config()
    
    def save_tracking_config(self, config):
        """Save tracking config to database"""
        self.db.save_tracking_config(config)
    
    def get_osc_config(self):
        """Get OSC config from database"""
        return self.db.get_osc_config()
    
    def save_osc_config(self, config):
        """Save OSC config to database"""
        self.db.save_osc_config(config)
