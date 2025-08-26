"""
Centralized logging configuration
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """Setup centralized logging configuration"""
    
    # Create logger
    logger = logging.getLogger("rextracking")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Use colored formatter for console
    colored_formatter = ColoredFormatter(log_format)
    console_handler.setFormatter(colored_formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Use regular formatter for file (no colors)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Set logging level for third-party libraries
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)
    logging.getLogger("opencv").setLevel(logging.WARNING)
    
    return logger


class LoggerMixin:
    """Mixin to add logging capabilities to classes"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return logging.getLogger(f"rextracking.{self.__class__.__name__}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(f"rextracking.{name}")


class MetricsLogHandler(logging.Handler):
    """Custom log handler for metrics events"""
    
    def __init__(self, metrics_collector=None):
        super().__init__()
        self.metrics_collector = metrics_collector
    
    def emit(self, record):
        if self.metrics_collector and hasattr(record, 'metrics_data'):
            # Handle metrics-specific logging
            pass
        
        # Regular logging behavior
        super().emit(record)


# Convenience functions for common log messages
def log_camera_start(camera_id: str, stream_url: str):
    """Log camera start event"""
    logger = get_logger("camera")
    logger.info(f"Starting camera {camera_id} with stream: {stream_url}")


def log_camera_stop(camera_id: str):
    """Log camera stop event"""
    logger = get_logger("camera")
    logger.info(f"Stopping camera {camera_id}")


def log_camera_error(camera_id: str, error: str):
    """Log camera error event"""
    logger = get_logger("camera")
    logger.error(f"Camera {camera_id} error: {error}")


def log_camera_reconnect(camera_id: str, attempt: int, max_attempts: int):
    """Log camera reconnection attempt"""
    logger = get_logger("camera")
    logger.warning(f"Camera {camera_id} reconnecting (attempt {attempt}/{max_attempts})")


def log_system_start(camera_count: int):
    """Log system start event"""
    logger = get_logger("system")
    logger.info(f"Starting RexTracking service with {camera_count} cameras")


def log_system_stop():
    """Log system stop event"""
    logger = get_logger("system")
    logger.info("Stopping RexTracking service")


def log_config_reload():
    """Log configuration reload event"""
    logger = get_logger("config")
    logger.info("Reloading configuration")


def log_performance_metrics(metrics: dict):
    """Log performance metrics"""
    logger = get_logger("metrics")
    logger.debug(f"Performance metrics: {metrics}")
