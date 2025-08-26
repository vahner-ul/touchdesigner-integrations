#!/usr/bin/env python3
"""
RexTracking API Server
Запуск только API сервера без автоматического старта сервиса трекинга
"""

import uvicorn
import argparse
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="RexTracking API Server")
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
        "--log-level", 
        default="info", 
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)"
    )
    
    args = parser.parse_args()
    
    # Проверяем, что мы в правильной директории
    if not Path("config.yaml").exists():
        logger.warning("config.yaml not found in current directory")
        logger.info("Creating default configuration...")
        
        try:
            from app.config.loader import ConfigLoader
            config_loader = ConfigLoader()
            config_loader.create_default_config()
            logger.info("Default configuration created")
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
    
    logger.info(f"Starting RexTracking API server on {args.host}:{args.port}")
    logger.info("Service manager will be initialized but not started automatically")
    logger.info("Use /api/v1/service/start to start the tracking service")
    logger.info("API documentation available at http://localhost:8080/docs")
    
    # Запускаем сервер
    uvicorn.run(
        "app.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        access_log=True
    )

if __name__ == "__main__":
    main()
