#!/usr/bin/env python3
"""
Test imports for RexTracking
"""
import sys
import os
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all imports"""
    print("Testing imports...")
    
    try:
        import fastapi
        print("✓ FastAPI imported successfully")
    except ImportError as e:
        print(f"✗ FastAPI import failed: {e}")
    
    try:
        import uvicorn
        print("✓ Uvicorn imported successfully")
    except ImportError as e:
        print(f"✗ Uvicorn import failed: {e}")
    
    try:
        import yaml
        print("✓ PyYAML imported successfully")
    except ImportError as e:
        print(f"✗ PyYAML import failed: {e}")
    
    try:
        import pydantic
        print("✓ Pydantic imported successfully")
    except ImportError as e:
        print(f"✗ Pydantic import failed: {e}")
    
    try:
        from app.config.schema import AppConfig
        print("✓ AppConfig imported successfully")
    except ImportError as e:
        print(f"✗ AppConfig import failed: {e}")
    
    try:
        from app.config.loader import ConfigLoader
        print("✓ ConfigLoader imported successfully")
    except ImportError as e:
        print(f"✗ ConfigLoader import failed: {e}")
    
    try:
        from app.api.main import app
        print("✓ FastAPI app imported successfully")
    except ImportError as e:
        print(f"✗ FastAPI app import failed: {e}")
    
    try:
        from app.api.websockets import WebSocketManager
        print("✓ WebSocketManager imported successfully")
    except ImportError as e:
        print(f"✗ WebSocketManager import failed: {e}")
    
    try:
        from app.service.metrics import metrics_service
        print("✓ MetricsService imported successfully")
    except ImportError as e:
        print(f"✗ MetricsService import failed: {e}")
    
    try:
        import fastapi
        print("✓ FastAPI imported successfully")
    except ImportError as e:
        print(f"✗ FastAPI import failed: {e}")

if __name__ == "__main__":
    test_imports()
