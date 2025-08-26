"""
Service CLI for running RexTracking with multiple cameras
"""

import argparse
import signal
import sys
import time
from pathlib import Path

from app.config.loader import ConfigLoader
from app.service.manager import ServiceManager
from app.service.metrics import MetricsCollector, MetricsLogger
from app.service.logging import setup_logging, log_system_start, log_system_stop


class ServiceCLI:
    """Command line interface for RexTracking service"""
    
    def __init__(self):
        """Initialize service CLI"""
        self.service_manager = None
        self.metrics_collector = None
        self.metrics_logger = None
        self.logger = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def run(self, config_path: str, log_level: str = "INFO", log_file: str = None):
        """Run the service"""
        try:
            # Setup logging
            self.logger = setup_logging(log_level, log_file)
            
            # Load configuration
            self.logger.info(f"Loading configuration from {config_path}")
            config_loader = ConfigLoader(config_path)
            config = config_loader.load()
            
            # Initialize service components
            self.service_manager = ServiceManager(config)
            self.metrics_collector = MetricsCollector()
            self.metrics_logger = MetricsLogger(log_file.replace('.log', '_metrics.log') if log_file else None)
            
            # Start service
            log_system_start(len(config.cameras))
            self.service_manager.start()
            self.running = True
            
            # Main loop
            self.logger.info("Service started, monitoring cameras...")
            while self.running:
                try:
                    # Update metrics
                    status = self.service_manager.get_status()
                    self.metrics_collector.update_system_metrics(status)
                    
                    # Log metrics periodically
                    self.metrics_logger.log_metrics(self.metrics_collector)
                    
                    # Check for stopped cameras and restart if needed
                    self._check_camera_health()
                    
                    time.sleep(10)  # Update every 10 seconds
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    time.sleep(5)
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start service: {e}")
            else:
                print(f"Failed to start service: {e}")
            sys.exit(1)
    
    def stop(self):
        """Stop the service"""
        if self.service_manager:
            log_system_stop()
            self.service_manager.stop()
        self.running = False
    
    def _check_camera_health(self):
        """Check camera health and restart failed cameras"""
        if not self.service_manager:
            return
            
        status = self.service_manager.get_status()
        for camera_id, camera_status in status["cameras"].items():
            if (camera_status["enabled"] and 
                camera_status["status"] in ["error", "stopped"]):
                self.logger.warning(f"Restarting failed camera: {camera_id}")
                self.service_manager.start_camera(camera_id)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="RexTracking Service")
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Configuration file path"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    parser.add_argument(
        "--log-file",
        help="Log file path (optional)"
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create default configuration file"
    )
    
    args = parser.parse_args()
    
    # Create default config if requested
    if args.create_config:
        config_loader = ConfigLoader(args.config)
        config_loader.create_default_config()
        print(f"Created default configuration at {args.config}")
        return
    
    # Check if config file exists
    if not Path(args.config).exists():
        print(f"Configuration file {args.config} not found.")
        print("Use --create-config to create a default configuration file.")
        sys.exit(1)
    
    # Run service
    service = ServiceCLI()
    service.run(args.config, args.log_level, args.log_file)


if __name__ == "__main__":
    main()
