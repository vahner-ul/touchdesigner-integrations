#!/usr/bin/env python3
"""
FastAPI server for RexTracking
"""
import uvicorn
import argparse
import os
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from app.api.main import app
from app.config.loader import ConfigLoader

def main():
    parser = argparse.ArgumentParser(description="RexTracking FastAPI Server")
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080, 
        help="Port to bind to (default: 8080)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true", 
        help="Enable auto-reload on code changes"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level", 
        default="info", 
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)"
    )
    
    args = parser.parse_args()
    
    # Устанавливаем переменную окружения для конфигурации
    if args.config:
        os.environ["REXTRACKING_CONFIG"] = args.config
    
    print(f"Starting RexTracking API server on {args.host}:{args.port}")
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print(f"Health Check: http://{args.host}:{args.port}/api/v1/health")
    
    try:
        # Запускаем сервер
        uvicorn.run(
            "app.api.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\nStopping FastAPI Server...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
