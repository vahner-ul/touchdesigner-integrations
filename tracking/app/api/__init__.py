"""
API endpoints and WebSocket handlers
"""

from .main import app
from .routes import cameras, config, health, metrics

__all__ = ["app", "cameras", "config", "health", "metrics"]
