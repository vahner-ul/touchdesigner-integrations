"""
Camera management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time

from ...config.schema import CameraConfig
from ...config.db_loader import DatabaseConfigLoader
from ...service.manager import ServiceManager
from ...core.network_scanner import DiscoveredCamera, get_network_scanner
from ...core.stream_checker import StreamChecker

router = APIRouter()

class CameraStatus(BaseModel):
    camera_id: str
    name: str
    status: str  # "running", "stopped", "error", "connecting"
    enabled: bool
    fps_input: float
    fps_processed: float
    latency_ms: float
    objects_count: int
    last_frame_time: Optional[float] = None
    error_message: Optional[str] = None
    stream: Optional[str] = None  # RTSP URL камеры
    queue_size: Optional[int] = None  # Размер очереди кадров

class CameraControlRequest(BaseModel):
    action: str  # "start", "stop", "restart"

class CameraAddRequest(BaseModel):
    id: str
    name: str
    stream: str
    enabled: bool = False  # Changed to False by default
    show_preview: bool = False
    roi: Optional[List[int]] = None
    classes_filter: List[str] = []
    override: Optional[Dict[str, Any]] = None

class DiscoveredCameraResponse(BaseModel):
    ip: str
    port: int
    protocol: str
    url: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    is_accessible: bool = False

class NetworkScanRequest(BaseModel):
    network_range: str = "192.168.1.0/24"
    timeout: float = 2.0

class NetworkScanResponse(BaseModel):
    cameras: List[DiscoveredCameraResponse]
    scan_time: float
    network_range: str

class StreamTestRequest(BaseModel):
    stream_url: str
    timeout: float = 5.0

class StreamTestResponse(BaseModel):
    accessible: bool
    error_message: Optional[str] = None
    test_time: float

def get_service_manager() -> Optional[ServiceManager]:
    """Dependency для получения ServiceManager"""
    from ..main import get_service_manager
    return get_service_manager()

def get_config_loader() -> DatabaseConfigLoader:
    """Dependency для получения DatabaseConfigLoader"""
    return DatabaseConfigLoader()

@router.get("/cameras", response_model=List[CameraStatus])
async def get_cameras(
    manager: ServiceManager = Depends(get_service_manager),
    config_loader: DatabaseConfigLoader = Depends(get_config_loader)
):
    """Получение списка всех камер"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        cameras = []
        
        # Получаем камеры из базы данных
        camera_configs = config_loader.get_cameras()
        
        for camera_config in camera_configs:
            # Получаем метрики камеры если она запущена
            metrics = manager.get_camera_metrics(camera_config.id)
            
            camera_status = CameraStatus(
                camera_id=camera_config.id,
                name=camera_config.name,
                status=metrics.status if metrics else "stopped",
                enabled=camera_config.enabled,
                fps_input=metrics.fps_input if metrics else 0.0,
                fps_processed=metrics.fps_processed if metrics else 0.0,
                latency_ms=metrics.latency_ms if metrics else 0.0,
                objects_count=metrics.objects_count if metrics else 0,
                last_frame_time=metrics.last_frame_time if metrics else None,
                error_message=metrics.error_message if metrics else None,
                stream=camera_config.stream,
                queue_size=metrics.queue_size if metrics else 0
            )
            cameras.append(camera_status)
        
        return cameras
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cameras: {str(e)}")

@router.get("/cameras/{camera_id}", response_model=CameraStatus)
async def get_camera(
    camera_id: str, 
    manager: ServiceManager = Depends(get_service_manager),
    config_loader: DatabaseConfigLoader = Depends(get_config_loader)
):
    """Получение статуса конкретной камеры"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Получаем камеру из базы данных
        camera_config = config_loader.get_camera(camera_id)
        
        if not camera_config:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
        
        # Получаем метрики камеры
        metrics = manager.get_camera_metrics(camera_id)
        
        return CameraStatus(
            camera_id=camera_config.id,
            name=camera_config.name,
            status=metrics.status if metrics else "stopped",
            enabled=camera_config.enabled,
            fps_input=metrics.fps_input if metrics else 0.0,
            fps_processed=metrics.fps_processed if metrics else 0.0,
            latency_ms=metrics.latency_ms if metrics else 0.0,
            objects_count=metrics.objects_count if metrics else 0,
            last_frame_time=metrics.last_frame_time if metrics else None,
            error_message=metrics.error_message if metrics else None,
            stream=camera_config.stream,
            queue_size=metrics.queue_size if metrics else 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get camera: {str(e)}")

@router.post("/cameras/{camera_id}/control")
async def control_camera(
    camera_id: str, 
    request: CameraControlRequest,
    manager: ServiceManager = Depends(get_service_manager),
    config_loader: DatabaseConfigLoader = Depends(get_config_loader)
):
    """Управление камерой (старт/стоп/перезапуск)"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        action = request.action.lower()
        
        if action not in ["start", "stop", "restart"]:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'start', 'stop', or 'restart'")
        
        # Проверяем, что камера существует в базе данных
        camera_config = config_loader.get_camera(camera_id)
        if not camera_config:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found in configuration")
        
        # Выполняем действие
        manager.control_camera(camera_id, action)
        
        return {
            "message": f"Camera {camera_id} {action} command sent successfully",
            "camera_id": camera_id,
            "action": action,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to control camera: {str(e)}")

@router.post("/cameras/{camera_id}/start")
async def start_camera(
    camera_id: str, 
    manager: ServiceManager = Depends(get_service_manager),
    config_loader: DatabaseConfigLoader = Depends(get_config_loader)
):
    """Запуск камеры"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Проверяем, что камера существует в базе данных
        camera_config = config_loader.get_camera(camera_id)
        if not camera_config:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found in configuration")
        
        # Запускаем камеру
        manager.control_camera(camera_id, "start")
        
        # Отправляем WebSocket событие об изменении статуса камеры
        try:
            from ..websockets import broadcast_camera_status_change
            import asyncio
            
            # Получаем обновленные метрики камеры
            metrics = manager.get_camera_metrics(camera_id)
            if metrics:
                camera_data = {
                    "camera_id": camera_id,
                    "name": camera_config.name,
                    "status": metrics.status,
                    "enabled": camera_config.enabled,
                    "fps_input": metrics.fps_input,
                    "fps_processed": metrics.fps_processed,
                    "latency_ms": metrics.latency_ms,
                    "objects_count": metrics.objects_count,
                    "last_frame_time": metrics.last_frame_time,
                    "error_message": metrics.error_message,
                    "stream": camera_config.stream,
                    "queue_size": metrics.queue_size
                }
                
                # Отправляем событие асинхронно
                asyncio.create_task(broadcast_camera_status_change(camera_data))
        except Exception as e:
            # Логируем ошибку, но не прерываем запуск камеры
            print(f"Warning: Failed to broadcast camera status change event: {e}")
        
        return {
            "message": f"Camera {camera_id} started successfully",
            "camera_id": camera_id,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start camera: {str(e)}")

@router.post("/cameras/{camera_id}/stop")
async def stop_camera(camera_id: str, manager: ServiceManager = Depends(get_service_manager)):
    """Остановка камеры"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Останавливаем камеру
        manager.control_camera(camera_id, "stop")
        
        # Отправляем WebSocket событие об изменении статуса камеры
        try:
            from ..websockets import broadcast_camera_status_change
            import asyncio
            
            # Получаем обновленные метрики камеры
            metrics = manager.get_camera_metrics(camera_id)
            if metrics:
                camera_data = {
                    "camera_id": camera_id,
                    "name": "Unknown",  # Будем получать из конфига если нужно
                    "status": metrics.status,
                    "enabled": True,  # Будем получать из конфига если нужно
                    "fps_input": metrics.fps_input,
                    "fps_processed": metrics.fps_processed,
                    "latency_ms": metrics.latency_ms,
                    "objects_count": metrics.objects_count,
                    "last_frame_time": metrics.last_frame_time,
                    "error_message": metrics.error_message,
                    "stream": "",  # Будем получать из конфига если нужно
                    "queue_size": metrics.queue_size
                }
                
                # Отправляем событие асинхронно
                asyncio.create_task(broadcast_camera_status_change(camera_data))
        except Exception as e:
            # Логируем ошибку, но не прерываем остановку камеры
            print(f"Warning: Failed to broadcast camera status change event: {e}")
        
        return {
            "message": f"Camera {camera_id} stopped successfully",
            "camera_id": camera_id,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop camera: {str(e)}")

@router.post("/cameras/{camera_id}/restart")
async def restart_camera(camera_id: str, manager: ServiceManager = Depends(get_service_manager)):
    """Перезапуск камеры"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Перезапускаем камеру
        manager.control_camera(camera_id, "restart")
        
        # Отправляем WebSocket событие об изменении статуса камеры
        try:
            from ..websockets import broadcast_camera_status_change
            import asyncio
            
            # Получаем обновленные метрики камеры
            metrics = manager.get_camera_metrics(camera_id)
            if metrics:
                camera_data = {
                    "camera_id": camera_id,
                    "name": "Unknown",  # Будем получать из конфига если нужно
                    "status": metrics.status,
                    "enabled": True,  # Будем получать из конфига если нужно
                    "fps_input": metrics.fps_input,
                    "fps_processed": metrics.fps_processed,
                    "latency_ms": metrics.latency_ms,
                    "objects_count": metrics.objects_count,
                    "last_frame_time": metrics.last_frame_time,
                    "error_message": metrics.error_message,
                    "stream": "",  # Будем получать из конфига если нужно
                    "queue_size": metrics.queue_size
                }
                
                # Отправляем событие асинхронно
                asyncio.create_task(broadcast_camera_status_change(camera_data))
        except Exception as e:
            # Логируем ошибку, но не прерываем перезапуск камеры
            print(f"Warning: Failed to broadcast camera status change event: {e}")
        
        return {
            "message": f"Camera {camera_id} restarted successfully",
            "camera_id": camera_id,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart camera: {str(e)}")

@router.post("/cameras")
async def add_camera(
    request: CameraAddRequest, 
    manager: ServiceManager = Depends(get_service_manager),
    config_loader: DatabaseConfigLoader = Depends(get_config_loader)
):
    """Добавление новой камеры"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Проверяем, что камера с таким ID не существует
        existing_cameras = config_loader.get_cameras()
        if any(cam.id == request.id for cam in existing_cameras):
            raise HTTPException(status_code=409, detail=f"Camera with ID {request.id} already exists")
        
        # Проверяем доступность потока
        stream_accessible, stream_error = await StreamChecker.check_stream_connectivity_async(request.stream)
        
        # Создаем новую конфигурацию камеры
        new_camera = CameraConfig(
            id=request.id,
            name=request.name,
            stream=request.stream,
            enabled=request.enabled,
            show_preview=request.show_preview,
            roi=request.roi,
            classes_filter=request.classes_filter,
            override=request.override or {}
        )
        
        # Сохраняем камеру в базу данных
        config_loader.save_camera(new_camera)
        
        # Отправляем WebSocket событие о добавлении камеры
        try:
            from ..websockets import broadcast_camera_added
            import asyncio
            
            # Создаем данные камеры для WebSocket события
            camera_data = {
                "camera_id": new_camera.id,
                "name": new_camera.name,
                "status": "stopped",  # Новая камера по умолчанию остановлена
                "enabled": new_camera.enabled,
                "fps_input": 0.0,
                "fps_processed": 0.0,
                "latency_ms": 0.0,
                "objects_count": 0,
                "last_frame_time": None,
                "error_message": None,
                "stream": new_camera.stream,
                "queue_size": 0
            }
            
            # Отправляем событие асинхронно
            asyncio.create_task(broadcast_camera_added(camera_data))
        except Exception as e:
            # Логируем ошибку, но не прерываем добавление камеры
            print(f"Warning: Failed to broadcast camera added event: {e}")
        
        # Возвращаем результат с информацией о доступности потока
        response_data = {
            "message": f"Camera {request.id} added successfully",
            "camera_id": request.id,
            "stream_accessible": stream_accessible,
            "stream_error": stream_error,
            "timestamp": time.time()
        }
        
        if not stream_accessible:
            response_data["warning"] = f"Camera added but stream is not accessible: {stream_error}"
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add camera: {str(e)}")

@router.delete("/cameras/{camera_id}")
async def remove_camera(
    camera_id: str, 
    manager: ServiceManager = Depends(get_service_manager),
    config_loader: DatabaseConfigLoader = Depends(get_config_loader)
):
    """Удаление камеры"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Останавливаем камеру если она запущена
        if camera_id in manager.camera_workers:
            manager.control_camera(camera_id, "stop")
        
        # Удаляем камеру из базы данных
        deleted = config_loader.delete_camera(camera_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
        
        # Отправляем WebSocket событие об удалении камеры
        try:
            from ..websockets import broadcast_camera_removed
            import asyncio
            
            # Отправляем событие асинхронно
            asyncio.create_task(broadcast_camera_removed(camera_id))
        except Exception as e:
            # Логируем ошибку, но не прерываем удаление камеры
            print(f"Warning: Failed to broadcast camera removed event: {e}")
        
        return {
            "message": f"Camera {camera_id} removed successfully",
            "camera_id": camera_id,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove camera: {str(e)}")

@router.post("/cameras/scan-network", response_model=NetworkScanResponse)
async def scan_network(request: NetworkScanRequest = NetworkScanRequest()):
    """Сканирование сети на наличие IP камер"""
    try:
        start_time = time.time()
        
        # Получаем сканер сети
        scanner = get_network_scanner(request.network_range)
        scanner.timeout = request.timeout
        
        # Выполняем сканирование
        discovered_cameras = await scanner.scan_network()
        
        # Преобразуем в формат ответа
        cameras_response = []
        for camera in discovered_cameras:
            cameras_response.append(DiscoveredCameraResponse(
                ip=camera.ip,
                port=camera.port,
                protocol=camera.protocol,
                url=camera.url,
                manufacturer=camera.manufacturer,
                model=camera.model,
                is_accessible=camera.is_accessible
            ))
        
        scan_time = time.time() - start_time
        
        return NetworkScanResponse(
            cameras=cameras_response,
            scan_time=scan_time,
            network_range=request.network_range
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan network: {str(e)}")

@router.post("/cameras/scan-network/{camera_id}/add")
async def add_discovered_camera(
    camera_id: str, 
    request: CameraAddRequest,
    manager: ServiceManager = Depends(get_service_manager),
    config_loader: DatabaseConfigLoader = Depends(get_config_loader)
):
    """Добавление найденной камеры с автоматическим именем"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Проверяем, что камера с таким ID не существует
        existing_cameras = config_loader.get_cameras()
        if any(cam.id == request.id for cam in existing_cameras):
            raise HTTPException(status_code=409, detail=f"Camera with ID {request.id} already exists")
        
        # Проверяем доступность потока
        stream_accessible, stream_error = await StreamChecker.check_stream_connectivity_async(request.stream)
        
        # Создаем новую конфигурацию камеры
        new_camera = CameraConfig(
            id=request.id,
            name=request.name,
            stream=request.stream,
            enabled=request.enabled,
            show_preview=request.show_preview,
            roi=request.roi,
            classes_filter=request.classes_filter,
            override=request.override or {}
        )
        
        # Сохраняем камеру в базу данных
        config_loader.save_camera(new_camera)
        
        # Возвращаем результат с информацией о доступности потока
        response_data = {
            "message": f"Discovered camera {request.id} added successfully",
            "camera_id": request.id,
            "stream_accessible": stream_accessible,
            "stream_error": stream_error,
            "timestamp": time.time()
        }
        
        if not stream_accessible:
            response_data["warning"] = f"Camera added but stream is not accessible: {stream_error}"
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add discovered camera: {str(e)}")

@router.post("/cameras/test-stream", response_model=StreamTestResponse)
async def test_stream_connectivity(request: StreamTestRequest):
    """Тестирование доступности потока камеры"""
    try:
        start_time = time.time()
        
        # Проверяем доступность потока
        accessible, error_message = await StreamChecker.check_stream_connectivity_async(
            request.stream_url, 
            request.timeout
        )
        
        test_time = time.time() - start_time
        
        return StreamTestResponse(
            accessible=accessible,
            error_message=error_message,
            test_time=test_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test stream: {str(e)}")