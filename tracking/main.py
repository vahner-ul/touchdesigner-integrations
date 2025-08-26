#!/usr/bin/env python3
"""
RexTracking - Unified Entry Point
Computer vision tracking system with TouchDesigner integration
"""

import sys
import os
from pathlib import Path

# Add bin directory to Python path so we can import the modules
bin_dir = Path(__file__).parent / "bin"
sys.path.insert(0, str(bin_dir))

import typer
from typing import Optional

app = typer.Typer(
    name="rextracking",
    help="RexTracking - Computer vision tracking system with TouchDesigner integration",
    epilog="""
Examples:
  python main.py server --status --auto-start    # API + Status Display + Auto-start service
  python main.py server --status                 # API + Status Display (manual service start)
  python main.py server                          # API only (classic mode)
  python main.py status                          # Service only with Status Display
  python main.py cli --stream rtsp://camera/url  # Single camera mode
    """
)

@app.command("server")
def run_server(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8080, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload on code changes"),
    log_level: str = typer.Option("info", help="Log level"),
    status: bool = typer.Option(False, help="Show beautiful status display while running"),
    auto_start: bool = typer.Option(False, help="Auto-start tracking service with server")
):
    """Start the FastAPI server with optional status display"""
    import logging
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Check for config file
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
    
    if status and not reload:
        # Use enhanced server with status display
        logger.info(f"Starting RexTracking Enhanced Server on {host}:{port}")
        logger.info("Status display will show real-time system monitoring")
        if auto_start:
            logger.info("Service will start automatically with the server")
        else:
            logger.info("Use /api/v1/service/start to start the tracking service")
        
        from app.server.enhanced_server import run_enhanced_server
        run_enhanced_server(
            host=host,
            port=port,
            show_status=True,
            auto_start_service=auto_start,
            reload=False
        )
    else:
        # Use regular uvicorn server
        if status and reload:
            logger.warning("Status display is not compatible with reload mode")
            logger.info("Starting regular server without status display...")
        
        import uvicorn
        
        logger.info(f"Starting RexTracking API server on {host}:{port}")
        if not auto_start:
            logger.info("Service manager will be initialized but not started automatically")
            logger.info("Use /api/v1/service/start to start the tracking service")
        logger.info(f"API documentation available at http://{host}:{port}/docs")
        
        # Start server
        uvicorn.run(
            "app.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True
        )

@app.command("system")
def run_system(
    api_port: int = typer.Option(8080, help="FastAPI server port"),
    web_port: int = typer.Option(3000, help="Web interface port"),
    api_only: bool = typer.Option(False, help="Run only FastAPI server"),
    web_only: bool = typer.Option(False, help="Run only web interface"),
    config: Optional[str] = typer.Option(None, help="Path to configuration file")
):
    """Start the full system (API + web interface)"""
    from run_system import main as system_main
    
    # Prepare arguments for system_main
    sys.argv = ["run_system"]
    if api_port != 8080:
        sys.argv.extend(["--api-port", str(api_port)])
    if web_port != 3000:
        sys.argv.extend(["--web-port", str(web_port)])
    if api_only:
        sys.argv.append("--api-only")
    if web_only:
        sys.argv.append("--web-only")
    if config:
        sys.argv.extend(["--config", config])
    
    system_main()

@app.command("cli")
def run_cli(
    stream: str = typer.Option("", help="Video stream URL for inference (RTSP)"),
    model: str = typer.Option("yolov8l", help="YOLO model to use"),
    ip: str = typer.Option("127.0.0.1", help="TouchDesigner OSC server IP"),
    port: int = typer.Option(5005, help="TouchDesigner OSC server port"),
    confidence: float = typer.Option(0.1, help="Minimum confidence threshold"),
    tracking_period: int = typer.Option(1, help="Frames between tracking updates"),
    objects_max: int = typer.Option(10, help="Maximum objects to track"),
    objects_filter: str = typer.Option("", help="Filter objects by class name"),
    object_persistance: int = typer.Option(10, help="Object persistence time (ms)"),
    timeout: int = typer.Option(5, help="Connection timeout (seconds)"),
    single_class: int = typer.Option(-1, help="Single class to detect (-1 for all)"),
    debug: bool = typer.Option(False, help="Enable debug output"),
    show: bool = typer.Option(False, help="Show tracking window")
):
    """Run single camera CLI mode"""
    if not stream:
        typer.echo("Error: --stream is required for CLI mode", err=True)
        raise typer.Exit(1)
    
    from app.core.pipeline import Pipeline
    
    # Create and run pipeline
    pipeline = Pipeline(
        stream=stream,
        model=model,
        ip=ip,
        port=port,
        confidence=confidence,
        tracking_period=tracking_period,
        objects_max=objects_max,
        objects_filter=objects_filter,
        object_persistance=object_persistance,
        timeout=timeout,
        single_class=single_class,
        debug=debug,
        show=show
    )
    
    pipeline.run()

@app.command("service")
def run_service(
    config: Optional[str] = typer.Option(None, help="Configuration file path"),
    log_level: str = typer.Option("INFO", help="Logging level"),
    log_file: Optional[str] = typer.Option(None, help="Log file path"),
    create_config: bool = typer.Option(False, help="Create default configuration"),
    status: bool = typer.Option(False, help="Use beautiful status display (recommended)")
):
    """Run multi-camera service mode"""
    if status:
        # Use the new beautiful status display
        from service_cli_status import main as status_service_main
        
        # Prepare arguments for enhanced service
        sys.argv = ["service_cli_status"]
        if config:
            sys.argv.extend(["--config", config])
        if log_level != "INFO":
            sys.argv.extend(["--log-level", log_level])
        if log_file:
            sys.argv.extend(["--log-file", log_file])
        if create_config:
            sys.argv.append("--create-config")
        
        status_service_main()
    else:
        # Use the original service CLI
        from service_cli import main as service_main
        
        # Prepare arguments for service_main
        sys.argv = ["service_cli"]
        if config:
            sys.argv.extend(["--config", config])
        if log_level != "INFO":
            sys.argv.extend(["--log-level", log_level])
        if log_file:
            sys.argv.extend(["--log-file", log_file])
        if create_config:
            sys.argv.append("--create-config")
        
        service_main()

@app.command("status")
def run_status_service(
    config: Optional[str] = typer.Option("config.yaml", help="Configuration file path"),
    create_config: bool = typer.Option(False, help="Create default configuration")
):
    """Run service with beautiful real-time status display (recommended)"""
    from service_cli_status import main as status_service_main
    
    # Prepare arguments for enhanced service
    sys.argv = ["service_cli_status"]
    if config:
        sys.argv.extend(["--config", config])
    if create_config:
        sys.argv.append("--create-config")
    
    status_service_main()

@app.command("test")
def run_tests(
    imports: bool = typer.Option(False, help="Test module imports"),
    service: bool = typer.Option(False, help="Test service functionality"),
    all: bool = typer.Option(False, help="Run all tests")
):
    """Run tests"""
    import subprocess
    
    if all or imports:
        typer.echo("Running import tests...")
        result = subprocess.run([sys.executable, "tests/test_imports.py"])
        if result.returncode != 0:
            typer.echo("Import tests failed!", err=True)
            raise typer.Exit(1)
    
    if all or service:
        typer.echo("Running service tests...")
        result = subprocess.run([sys.executable, "tests/test_service.py"])
        if result.returncode != 0:
            typer.echo("Service tests failed!", err=True)
            raise typer.Exit(1)
    
    if not any([imports, service, all]):
        typer.echo("Running all tests...")
        result1 = subprocess.run([sys.executable, "tests/test_imports.py"])
        result2 = subprocess.run([sys.executable, "tests/test_service.py"])
        if result1.returncode != 0 or result2.returncode != 0:
            typer.echo("Some tests failed!", err=True)
            raise typer.Exit(1)
    
    typer.echo("All tests passed! ✅")

if __name__ == "__main__":
    app()