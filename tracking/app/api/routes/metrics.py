"""
Metrics endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
import psutil

from ...service.manager import ServiceManager

router = APIRouter()

class SystemMetrics(BaseModel):
    total_cameras: int
    active_cameras: int
    total_objects: int
    average_latency_ms: float
    system_cpu_percent: float
    system_memory_percent: float

class CameraMetrics(BaseModel):
    camera_id: str
    name: str
    status: str
    fps_input: float
    fps_processed: float
    latency_ms: float
    objects_count: int
    queue_size: int
    last_frame_time: Optional[float] = None
    error_message: Optional[str] = None
    stream: Optional[str] = None  # RTSP URL камеры

class MetricsResponse(BaseModel):
    timestamp: float
    system: SystemMetrics
    cameras: List[CameraMetrics]

def get_service_manager() -> Optional[ServiceManager]:
    """Dependency для получения ServiceManager"""
    from ..main import get_service_manager
    return get_service_manager()

def get_system_metrics() -> SystemMetrics:
    """Получение системных метрик"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
    except Exception:
        # Fallback если psutil недоступен
        cpu_percent = 0.0
        memory_percent = 0.0
    
    return SystemMetrics(
        total_cameras=0,  # Будет заполнено из ServiceManager
        active_cameras=0,
        total_objects=0,
        average_latency_ms=0.0,
        system_cpu_percent=cpu_percent,
        system_memory_percent=memory_percent
    )

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(manager: ServiceManager = Depends(get_service_manager)):
    """Получение всех метрик системы и камер"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Получаем системные метрики
        system_metrics = get_system_metrics()
        
        # Получаем метрики камер
        cameras_metrics = []
        for camera_config in manager.config.cameras:
            metrics = manager.get_camera_metrics(camera_config.id)
            
            camera_metrics = CameraMetrics(
                camera_id=camera_config.id,
                name=camera_config.name,
                status=metrics.status if metrics else "stopped",
                fps_input=metrics.fps_input if metrics else 0.0,
                fps_processed=metrics.fps_processed if metrics else 0.0,
                latency_ms=metrics.latency_ms if metrics else 0.0,
                objects_count=metrics.objects_count if metrics else 0,
                queue_size=metrics.queue_size if metrics else 0,
                last_frame_time=metrics.last_frame_time if metrics else None,
                error_message=metrics.error_message if metrics else None,
                stream=camera_config.stream
            )
            cameras_metrics.append(camera_metrics)
        
        # Обновляем системные метрики из ServiceManager
        system_metrics_dict = manager.get_system_metrics()
        system_metrics.total_cameras = system_metrics_dict.get("total_cameras", 0)
        system_metrics.active_cameras = system_metrics_dict.get("active_cameras", 0)
        system_metrics.total_objects = system_metrics_dict.get("total_objects", 0)
        system_metrics.average_latency_ms = system_metrics_dict.get("average_latency_ms", 0.0)
        
        return MetricsResponse(
            timestamp=time.time(),
            system=system_metrics,
            cameras=cameras_metrics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.get("/metrics/system", response_model=SystemMetrics)
async def get_system_metrics_endpoint(manager: ServiceManager = Depends(get_service_manager)):
    """Получение только системных метрик"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Получаем базовые системные метрики
        system_metrics = get_system_metrics()
        
        # Обновляем метрики из ServiceManager
        manager_metrics = manager.get_system_metrics()
        system_metrics.total_cameras = manager_metrics.get("total_cameras", 0)
        system_metrics.active_cameras = manager_metrics.get("active_cameras", 0)
        system_metrics.total_objects = manager_metrics.get("total_objects", 0)
        system_metrics.average_latency_ms = manager_metrics.get("average_latency_ms", 0.0)
        
        return system_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")

@router.get("/metrics/cameras", response_model=List[CameraMetrics])
async def get_cameras_metrics(manager: ServiceManager = Depends(get_service_manager)):
    """Получение метрик всех камер"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        cameras_metrics = []
        
        for camera_config in manager.config.cameras:
            metrics = manager.get_camera_metrics(camera_config.id)
            
            camera_metrics = CameraMetrics(
                camera_id=camera_config.id,
                name=camera_config.name,
                status=metrics.status if metrics else "stopped",
                fps_input=metrics.fps_input if metrics else 0.0,
                fps_processed=metrics.fps_processed if metrics else 0.0,
                latency_ms=metrics.latency_ms if metrics else 0.0,
                objects_count=metrics.objects_count if metrics else 0,
                queue_size=metrics.queue_size if metrics else 0,
                last_frame_time=metrics.last_frame_time if metrics else None,
                error_message=metrics.error_message if metrics else None,
                stream=camera_config.stream
            )
            cameras_metrics.append(camera_metrics)
        
        return cameras_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cameras metrics: {str(e)}")

@router.get("/metrics/cameras/{camera_id}", response_model=CameraMetrics)
async def get_camera_metrics(camera_id: str, manager: ServiceManager = Depends(get_service_manager)):
    """Получение метрик конкретной камеры"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Ищем камеру в конфигурации
        camera_config = None
        for cam in manager.config.cameras:
            if cam.id == camera_id:
                camera_config = cam
                break
        
        if not camera_config:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
        
        # Получаем метрики камеры
        metrics = manager.get_camera_metrics(camera_id)
        
        return CameraMetrics(
            camera_id=camera_config.id,
            name=camera_config.name,
            status=metrics.status if metrics else "stopped",
            fps_input=metrics.fps_input if metrics else 0.0,
            fps_processed=metrics.fps_processed if metrics else 0.0,
            latency_ms=metrics.latency_ms if metrics else 0.0,
            objects_count=metrics.objects_count if metrics else 0,
            queue_size=metrics.queue_size if metrics else 0,
            last_frame_time=metrics.last_frame_time if metrics else None,
            error_message=metrics.error_message if metrics else None,
            stream=camera_config.stream
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get camera metrics: {str(e)}")
