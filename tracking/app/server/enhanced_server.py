"""
Enhanced server that can run FastAPI with optional status display
"""

import asyncio
import threading
import time
import signal
import sys
from typing import Optional

import uvicorn
from contextlib import asynccontextmanager

from ..console.status_display import StatusDisplay
from ..service.manager import ServiceManager


class EnhancedServer:
    """Enhanced server with optional status display"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080, 
                 show_status: bool = True, auto_start_service: bool = True):
        self.host = host
        self.port = port
        self.show_status = show_status
        self.auto_start_service = auto_start_service
        
        self.service_manager: Optional[ServiceManager] = None
        self.status_display: Optional[StatusDisplay] = None
        self.status_thread: Optional[threading.Thread] = None
        self.uvicorn_server: Optional[uvicorn.Server] = None
        self.server_thread: Optional[threading.Thread] = None
        
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def _run_status_display(self):
        """Run status display in background thread"""
        try:
            if self.status_display:
                self.status_display.run_live()
        except Exception as e:
            # Status display stopped, probably due to shutdown
            pass
    
    def _run_uvicorn_server(self):
        """Run uvicorn server in background thread"""
        try:
            # Create server config
            config = uvicorn.Config(
                "app.api.main:app",
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=True
            )
            
            self.uvicorn_server = uvicorn.Server(config)
            asyncio.run(self.uvicorn_server.serve())
            
        except Exception as e:
            if self.running:  # Only show error if we're supposed to be running
                print(f"❌ Server error: {e}")
    
    def _run_fallback_server(self):
        """Run server without status display"""
        print(f"🌐 Starting API server on http://{self.host}:{self.port}")
        self.server_thread = threading.Thread(target=self._run_uvicorn_server, daemon=True)
        self.server_thread.start()
        time.sleep(1)
        
        print(f"🌐 Server running at: http://{self.host}:{self.port}")
        print(f"📚 API docs: http://{self.host}:{self.port}/docs")
        print("Press Ctrl+C to shutdown")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    def start(self):
        """Start the enhanced server"""
        try:
            self.running = True
            print("🚀 Starting RexTracking Enhanced Server...")
            
            # Initialize service manager
            try:
                self.service_manager = ServiceManager()
                print("✅ Service manager initialized")
                
                if self.auto_start_service:
                    self.service_manager.start()
                    print("✅ Service started automatically")
                    
            except Exception as e:
                print(f"⚠️  Service manager initialization failed: {e}")
                print("   API will still start, but service features will be limited")
            
            if self.show_status:
                # Initialize status display first
                print("🖥️  Starting status display...")
                try:
                    self.status_display = StatusDisplay(self.service_manager)
                    print("📊 Status display initialized successfully")
                    
                    # Start uvicorn server in background thread
                    print(f"🌐 Starting API server on http://{self.host}:{self.port}")
                    self.server_thread = threading.Thread(target=self._run_uvicorn_server, daemon=True)
                    self.server_thread.start()
                    
                    # Wait a moment for server to start
                    time.sleep(2)
                    
                    print("🎯 Status display ready! Use Ctrl+C to shutdown gracefully.")
                    print(f"🌐 API docs available at: http://{self.host}:{self.port}/docs")
                    
                    # Run status display (this blocks until Ctrl+C)
                    print("🚀 Starting live status display...")
                    self.status_display.run_live()
                    
                except Exception as e:
                    import traceback
                    print(f"❌ Failed to start status display: {e}")
                    print("🔍 Status display error details:")
                    traceback.print_exc()
                    print("📊 Running server without status display...")
                    # Fallback to normal server mode
                    self._run_fallback_server()
            else:
                # Just run server without status display
                self._run_fallback_server()
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested by user")
            self.stop()
        except Exception as e:
            import traceback
            print(f"❌ Failed to start enhanced server: {e}")
            print("🔍 Full error traceback:")
            traceback.print_exc()
            self.stop()
    
    def stop(self):
        """Stop the enhanced server"""
        if not self.running:
            return
            
        print("🛑 Stopping enhanced server...")
        self.running = False
        
        # Stop service manager
        if self.service_manager:
            try:
                self.service_manager.stop()
                print("✅ Service manager stopped")
            except Exception as e:
                print(f"⚠️  Error stopping service manager: {e}")
        
        # Stop uvicorn server
        if self.uvicorn_server:
            try:
                self.uvicorn_server.should_exit = True
                print("✅ API server stopped")
            except Exception as e:
                print(f"⚠️  Error stopping API server: {e}")
        
        print("✅ Enhanced server stopped successfully")


def run_enhanced_server(host: str = "0.0.0.0", port: int = 8080, 
                       show_status: bool = True, auto_start_service: bool = True,
                       reload: bool = False):
    """Run the enhanced server with optional status display"""
    
    if reload:
        print("⚠️  Status display is not compatible with reload mode")
        print("   Starting regular uvicorn server with reload...")
        
        uvicorn.run(
            "app.api.main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info",
            access_log=True
        )
    else:
        server = EnhancedServer(
            host=host,
            port=port,
            show_status=show_status,
            auto_start_service=auto_start_service
        )
        server.start()