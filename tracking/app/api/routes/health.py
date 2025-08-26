"""
Health check endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import time
import psutil

from ...service.manager import ServiceManager

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    timestamp: float
    version: str
    uptime: float
    system: Dict[str, Any]

class SimpleHealthResponse(BaseModel):
    status: str
    timestamp: float

def get_service_manager() -> Optional[ServiceManager]:
    """Dependency для получения ServiceManager"""
    from ..main import get_service_manager
    return get_service_manager()

def get_system_info() -> Dict[str, Any]:
    """Получение системной информации"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2)
        }
    except Exception:
        # Fallback если psutil недоступен
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_available_gb": 0.0,
            "disk_percent": 0.0,
            "disk_free_gb": 0.0
        }

@router.get("/health", response_model=HealthResponse)
async def get_health(manager: ServiceManager = Depends(get_service_manager)):
    """Полная проверка здоровья системы"""
    try:
        # Получаем системную информацию
        system_info = get_system_info()
        
        # Определяем статус сервиса
        if not manager:
            status = "service_not_initialized"
            uptime = 0.0
        elif not manager.running:
            status = "service_stopped"
            uptime = 0.0
        elif not manager.is_healthy():
            status = "service_degraded"
            uptime = time.time() - manager.start_time if manager.start_time else 0.0
        else:
            status = "healthy"
            uptime = time.time() - manager.start_time if manager.start_time else 0.0
        
        return HealthResponse(
            status=status,
            timestamp=time.time(),
            version="1.0.0",
            uptime=uptime,
            system=system_info
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/health/simple", response_model=SimpleHealthResponse)
async def get_simple_health(manager: ServiceManager = Depends(get_service_manager)):
    """Простая проверка здоровья (для load balancer)"""
    try:
        if not manager:
            status = "not_initialized"
        elif not manager.running:
            status = "stopped"
        elif not manager.is_healthy():
            status = "degraded"
        else:
            status = "healthy"
        
        return SimpleHealthResponse(
            status=status,
            timestamp=time.time()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simple health check failed: {str(e)}")

@router.get("/health/service")
async def get_service_health(manager: ServiceManager = Depends(get_service_manager)):
    """Проверка здоровья только сервиса трекинга"""
    try:
        if not manager:
            return {
                "status": "not_initialized",
                "message": "Service manager not initialized",
                "timestamp": time.time()
            }
        
        # Проверяем состояние сервиса
        is_healthy = manager.is_healthy()
        running = manager.running
        
        if not running:
            status = "stopped"
            message = "Service is not running"
        elif not is_healthy:
            status = "degraded"
            message = "Service has issues"
        else:
            status = "healthy"
            message = "Service is running normally"
        
        # Получаем информацию о камерах
        cameras_info = {
            "total": len(manager.config.cameras),
            "active": len([w for w in manager.camera_workers.values() if w.metrics.status == "running"]),
            "stopped": len([w for w in manager.camera_workers.values() if w.metrics.status == "stopped"]),
            "error": len([w for w in manager.camera_workers.values() if w.metrics.status == "error"])
        }
        
        return {
            "status": status,
            "message": message,
            "running": running,
            "healthy": is_healthy,
            "uptime": time.time() - manager.start_time if manager.start_time else 0.0,
            "cameras": cameras_info,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service health check failed: {str(e)}")
