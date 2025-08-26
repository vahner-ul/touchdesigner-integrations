"""
FastAPI main application
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

try:
    from .routes import cameras, config, health, metrics
    from .websockets import telemetry_websocket, preview_websocket, objects_websocket, dashboard_websocket, manager as ws_manager
    from ..service.manager import ServiceManager
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    # Create dummy modules if imports fail
    cameras = None
    config = None
    health = None
    metrics = None
    telemetry_websocket = None
    preview_websocket = None
    objects_websocket = None
    dashboard_websocket = None
    ws_manager = None
    ServiceManager = None

# Глобальное состояние сервиса
service_manager: Optional[ServiceManager] = None

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global service_manager
    
    # Запуск сервиса при старте приложения
    if ServiceManager:
        try:
            logger.info("Initializing RexTracking service...")
            service_manager = ServiceManager()
            
            # Connect WebSocket manager to service manager
            if ws_manager:
                ws_manager.set_service_manager(service_manager)
                logger.info("WebSocket manager connected to service manager")
            
            # НЕ запускаем сервис автоматически - только инициализируем
            logger.info("Service manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize service manager: {e}")
            service_manager = None
    
    yield
    
    # Остановка сервиса при завершении
    if service_manager:
        try:
            logger.info("Shutting down RexTracking service...")
            service_manager.stop()
            logger.info("Service manager stopped")
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")
    
    # Clean up WebSocket connections
    if ws_manager:
        try:
            logger.info("Cleaning up WebSocket connections...")
            await ws_manager.cleanup_all_connections()
            logger.info("WebSocket connections cleaned up")
        except Exception as e:
            logger.error(f"Error during WebSocket cleanup: {e}")

# Create FastAPI app
app = FastAPI(
    title="RexTracking API",
    description="API для управления системой трекинга объектов",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Dependency для получения ServiceManager
def get_service_manager() -> Optional[ServiceManager]:
    """Получение экземпляра ServiceManager"""
    return service_manager

# Include routers с передачей ServiceManager
if health:
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
if metrics:
    app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])
if config:
    app.include_router(config.router, prefix="/api/v1", tags=["config"])
if cameras:
    app.include_router(cameras.router, prefix="/api/v1", tags=["cameras"])

# WebSocket endpoints
if telemetry_websocket:
    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket):
        await telemetry_websocket(websocket)

if preview_websocket:
    @app.websocket("/ws/preview")
    async def websocket_preview(websocket: WebSocket):
        await preview_websocket(websocket)

if objects_websocket:
    @app.websocket("/ws/objects")
    async def websocket_objects(websocket: WebSocket):
        await objects_websocket(websocket)

if dashboard_websocket:
    @app.websocket("/ws/dashboard")
    async def websocket_dashboard(websocket: WebSocket):
        await dashboard_websocket(websocket, get_service_manager())

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "RexTracking API",
        "version": "1.0.0",
        "service_status": "running" if service_manager else "not_initialized",
        "docs": "/docs",
        "health": "/api/v1/health",
        "websockets": {
            "telemetry": "/ws/telemetry",
            "preview": "/ws/preview", 
            "objects": "/ws/objects",
            "dashboard": "/ws/dashboard"
        }
    }

@app.post("/api/v1/service/start")
async def start_service(manager: ServiceManager = Depends(get_service_manager)):
    """Запуск сервиса трекинга"""
    if not manager:
        raise HTTPException(status_code=503, detail="Service manager not initialized")
    
    try:
        manager.start()
        return {"message": "Service started successfully", "status": "running"}
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start service: {str(e)}")

@app.post("/api/v1/service/stop")
async def stop_service(manager: ServiceManager = Depends(get_service_manager)):
    """Остановка сервиса трекинга"""
    if not manager:
        raise HTTPException(status_code=503, detail="Service manager not initialized")
    
    try:
        manager.stop()
        return {"message": "Service stopped successfully", "status": "stopped"}
    except Exception as e:
        logger.error(f"Failed to stop service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop service: {str(e)}")

@app.get("/api/v1/service/status")
async def get_service_status(manager: ServiceManager = Depends(get_service_manager)):
    """Получение статуса сервиса"""
    if not manager:
        return {"status": "not_initialized", "running": False}
    
    return {
        "status": "running" if manager.running else "stopped",
        "running": manager.running,
        "uptime": manager.start_time,
        "cameras_count": len(manager.camera_workers),
        "healthy": manager.is_healthy()
    }

@app.get("/api/v1/websockets/stats")
async def get_websocket_stats():
    """Получение статистики WebSocket соединений"""
    if ws_manager:
        return ws_manager.get_connection_stats()
    else:
        return {"total_connections": 0, "channels": {}}
