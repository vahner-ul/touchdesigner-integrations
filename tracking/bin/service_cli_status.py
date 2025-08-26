"""
Enhanced Service CLI with beautiful status display for RexTracking
"""

import argparse
import signal
import sys
import time
import threading
from pathlib import Path

from app.config.loader import ConfigLoader
from app.service.manager import ServiceManager
from app.console.status_display import StatusDisplay


class EnhancedServiceCLI:
    """Enhanced command line interface with beautiful status display"""
    
    def __init__(self):
        """Initialize enhanced service CLI"""
        self.service_manager = None
        self.status_display = None
        self.running = False
        self.monitor_thread = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)
    
    def _monitor_cameras(self):
        """Background thread to monitor and restart failed cameras"""
        while self.running:
            try:
                if self.service_manager and self.service_manager.running:
                    # Check camera health
                    for camera_id, worker in self.service_manager.camera_workers.items():
                        if hasattr(worker, 'get_metrics'):
                            metrics = worker.get_metrics()
                            
                            # Restart cameras that are in error state
                            if metrics.status == "error" and hasattr(worker, 'camera_config') and worker.camera_config.enabled:
                                try:
                                    worker.restart()
                                except Exception as e:
                                    # Silent restart attempt - status display will show the issue
                                    pass
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                # Continue monitoring even if there's an error
                time.sleep(5)
    
    def run(self, config_path: str, log_level: str = "INFO", log_file: str = None):
        """Run the enhanced service with status display"""
        try:
            # Check if config file exists
            if not Path(config_path).exists():
                print(f"❌ Configuration file {config_path} not found.")
                print("Use --create-config to create a default configuration file.")
                sys.exit(1)
            
            # Load configuration
            config_loader = ConfigLoader(config_path)
            config = config_loader.load()
            
            # Initialize service manager
            self.service_manager = ServiceManager(config_path)
            
            # Initialize status display
            self.status_display = StatusDisplay(self.service_manager)
            
            # Start service
            print("🚀 Starting RexTracking service...")
            self.service_manager.start()
            self.running = True
            
            # Start background monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_cameras, daemon=True)
            self.monitor_thread.start()
            
            # Show a brief startup message
            print(f"✅ Service started with {len(config.cameras)} cameras")
            print("🖥️  Starting status display in 2 seconds...")
            time.sleep(2)
            
            # Run the beautiful status display
            self.status_display.run_live()
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested by user")
            self.stop()
        except Exception as e:
            print(f"❌ Failed to start service: {e}")
            if self.service_manager:
                self.service_manager.stop()
            sys.exit(1)
    
    def stop(self):
        """Stop the service gracefully"""
        if self.running:
            self.running = False
            
            if self.service_manager:
                print("🛑 Stopping service manager...")
                self.service_manager.stop()
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                print("🛑 Stopping monitoring thread...")
                # Thread will stop when self.running becomes False
            
            print("✅ Service stopped successfully")


def main():
    """Main entry point for enhanced service CLI"""
    parser = argparse.ArgumentParser(
        description="RexTracking Enhanced Service with Status Display",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python -m bin.service_cli_status --config config.yaml
  python -m bin.service_cli_status --create-config
  
The status display shows:
  - Real-time service status and health
  - Camera statuses with FPS and object counts
  - System metrics (CPU, memory, threads)
  - Socket leak monitoring with history
  - Live activity log

Press Ctrl+C to exit gracefully.
        """
    )
    
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Configuration file path (default: config.yaml)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (not used in status mode, but kept for compatibility)"
    )
    parser.add_argument(
        "--log-file",
        help="Log file path (not used in status mode, but kept for compatibility)"
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create default configuration file and exit"
    )
    
    args = parser.parse_args()
    
    # Create default config if requested
    if args.create_config:
        try:
            config_loader = ConfigLoader(args.config)
            config_loader.create_default_config()
            print(f"✅ Created default configuration at {args.config}")
            print("Edit the configuration file to match your setup, then run:")
            print(f"   python -m bin.service_cli_status --config {args.config}")
        except Exception as e:
            print(f"❌ Failed to create default configuration: {e}")
            sys.exit(1)
        return
    
    # Run enhanced service
    service = EnhancedServiceCLI()
    service.run(args.config, args.log_level, args.log_file)


if __name__ == "__main__":
    main()