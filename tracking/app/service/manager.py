"""
Service manager for camera tracking
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from threading import Thread, Event
from dataclasses import dataclass
from pathlib import Path

from ..config.schema import AppConfig, CameraConfig
from ..config.loader import ConfigLoader
from ..config.db_loader import DatabaseConfigLoader
from ..core.pipeline import TrackingPipeline
from ..core.capture import CaptureThread
from ..core.tracker import Tracker
from ..core.osc import OSCWorker
from ..core.objects_buffer import ObjectsBuffer

logger = logging.getLogger(__name__)

@dataclass
class CameraMetrics:
    """Метрики камеры"""
    camera_id: str
    status: str
    fps_input: float = 0.0
    fps_processed: float = 0.0
    latency_ms: float = 0.0
    objects_count: int = 0
    queue_size: int = 0
    last_frame_time: Optional[float] = None
    error_message: Optional[str] = None

class CameraWorker:
    """Рабочий поток для одной камеры"""
    
    def __init__(self, camera_config: CameraConfig, tracking_config: dict, osc_config: dict):
        self.camera_config = camera_config
        self.tracking_config = tracking_config
        self.osc_config = osc_config
        self.metrics = CameraMetrics(camera_id=camera_config.id, status="stopped")
        
        # Компоненты пайплайна
        self.pipeline: Optional[TrackingPipeline] = None
        self.thread: Optional[Thread] = None
        self.stop_event = Event()
        
    def start(self):
        """Запуск камеры"""
        if self.thread and self.thread.is_alive():
            logger.warning(f"Camera {self.camera_config.id} is already running")
            return
            
        try:
            self.metrics.status = "starting"
            self.stop_event.clear()
            
            # Создаем пайплайн
            self.pipeline = TrackingPipeline(
                stream_url=self.camera_config.stream,
                model_name=self.tracking_config.get("model", "yolov8l"),
                confidence=self.tracking_config.get("confidence", 0.25),
                device=self.tracking_config.get("device", "auto"),
                osc_host=self.osc_config.get("host", "127.0.0.1"),
                osc_port=self.osc_config.get("port", 5005),
                osc_address_prefix=self.osc_config.get("address_prefix", "/"),
                objects_max=self.tracking_config.get("objects_max", 10),
                object_persistence_ms=self.tracking_config.get("object_persistence_ms", 50),
                period_frames=self.tracking_config.get("period_frames", 1)
            )
            
            # Запускаем в отдельном потоке
            self.thread = Thread(target=self._run, daemon=True)
            self.thread.start()
            
            logger.info(f"Camera {self.camera_config.id} started")
            
        except Exception as e:
            self.metrics.status = "error"
            self.metrics.error_message = str(e)
            logger.error(f"Failed to start camera {self.camera_config.id}: {e}")
            raise
    
    def stop(self):
        """Остановка камеры"""
        if not self.thread or not self.thread.is_alive():
            logger.warning(f"Camera {self.camera_config.id} is not running")
            return
            
        try:
            self.metrics.status = "stopping"
            self.stop_event.set()
            
            if self.pipeline:
                self.pipeline.stop()
            
            if self.thread:
                self.thread.join(timeout=5.0)
                
            self.metrics.status = "stopped"
            logger.info(f"Camera {self.camera_config.id} stopped")
            
        except Exception as e:
            self.metrics.status = "error"
            self.metrics.error_message = str(e)
            logger.error(f"Failed to stop camera {self.camera_config.id}: {e}")
            raise
    
    def restart(self):
        """Перезапуск камеры"""
        logger.info(f"Restarting camera {self.camera_config.id}")
        self.stop()
        time.sleep(1)  # Небольшая пауза
        self.start()
    
    def _run(self):
        """Основной цикл работы камеры"""
        try:
            self.metrics.status = "running"
            
            # Start the pipeline
            if self.pipeline:
                self.pipeline.start()
            
            while not self.stop_event.is_set():
                if self.pipeline:
                    # Process a frame
                    if not self.pipeline.process_frame():
                        self.metrics.status = "error"
                        self.metrics.error_message = "Pipeline frame processing failed"
                        break
                    
                    # Обновляем метрики
                    self._update_metrics()
                    
                    # Проверяем состояние пайплайна
                    if not self.pipeline.is_running():
                        self.metrics.status = "error"
                        self.metrics.error_message = "Pipeline stopped unexpectedly"
                        break
                        
                time.sleep(0.001)  # Smaller delay for better responsiveness
                
        except Exception as e:
            self.metrics.status = "error"
            self.metrics.error_message = str(e)
            logger.error(f"Camera {self.camera_config.id} runtime error: {e}")
        finally:
            if self.pipeline:
                self.pipeline.stop()
            self.metrics.status = "stopped"
    
    def _update_metrics(self):
        """Обновление метрик камеры"""
        if self.pipeline:
            # Получаем метрики из пайплайна
            pipeline_metrics = self.pipeline.get_metrics()
            
            self.metrics.fps_input = pipeline_metrics.get("fps_input", 0.0)
            self.metrics.fps_processed = pipeline_metrics.get("fps_processed", 0.0)
            self.metrics.latency_ms = pipeline_metrics.get("latency_ms", 0.0)
            self.metrics.objects_count = pipeline_metrics.get("objects_count", 0)
            self.metrics.queue_size = pipeline_metrics.get("queue_size", 0)
            self.metrics.last_frame_time = pipeline_metrics.get("last_frame_time")
    
    def get_metrics(self) -> CameraMetrics:
        """Получение текущих метрик"""
        return self.metrics

class ServiceManager:
    """Менеджер сервиса для управления всеми камерами"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        # Используем базу данных для конфигурации
        self.config_loader = DatabaseConfigLoader()
        self.config: Optional[AppConfig] = None
        
        # Рабочие потоки камер
        self.camera_workers: Dict[str, CameraWorker] = {}
        
        # Состояние сервиса
        self.running = False
        self.start_time: Optional[float] = None
        
        # Загружаем конфигурацию
        self._load_config()
    
    def _load_config(self):
        """Загрузка конфигурации из базы данных"""
        try:
            self.config = self.config_loader.load()
            logger.info("Configuration loaded from database successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration from database: {e}")
            raise
    
    def start(self):
        """Запуск сервиса"""
        if self.running:
            logger.warning("Service is already running")
            return
            
        try:
            logger.info("Starting RexTracking service...")
            self.running = True
            self.start_time = time.time()
            
            # Загружаем камеры из базы данных и запускаем их
            cameras = self.config_loader.get_cameras()
            for camera in cameras:
                if camera.enabled:
                    self._start_camera(camera)
            
            logger.info(f"Service started with {len(self.camera_workers)} cameras")
            
        except Exception as e:
            self.running = False
            logger.error(f"Failed to start service: {e}")
            raise
    
    def stop(self):
        """Остановка сервиса"""
        if not self.running:
            logger.warning("Service is not running")
            return
            
        try:
            logger.info("Stopping RexTracking service...")
            self.running = False
            
            # Останавливаем все камеры
            for camera_id, worker in self.camera_workers.items():
                try:
                    worker.stop()
                except Exception as e:
                    logger.error(f"Failed to stop camera {camera_id}: {e}")
            
            self.camera_workers.clear()
            logger.info("Service stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            raise
    
    def restart(self):
        """Перезапуск сервиса"""
        logger.info("Restarting service...")
        self.stop()
        time.sleep(1)
        self.start()
    
    def _start_camera(self, camera_config: CameraConfig):
        """Запуск отдельной камеры"""
        try:
            worker = CameraWorker(
                camera_config=camera_config,
                tracking_config=self.config.tracking.model_dump(),
                osc_config=self.config.osc.model_dump()
            )
            
            worker.start()
            self.camera_workers[camera_config.id] = worker
            
            logger.info(f"Camera {camera_config.id} started")
            
        except Exception as e:
            logger.error(f"Failed to start camera {camera_config.id}: {e}")
            raise
    
    def get_camera_metrics(self, camera_id: str) -> Optional[CameraMetrics]:
        """Получение метрик камеры"""
        worker = self.camera_workers.get(camera_id)
        if worker:
            return worker.get_metrics()
        return None
    
    def get_all_camera_metrics(self) -> List[CameraMetrics]:
        """Получение метрик всех камер"""
        return [worker.get_metrics() for worker in self.camera_workers.values()]
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Получение системных метрик"""
        # Получаем камеры из базы данных
        cameras = self.config_loader.get_cameras()
        total_cameras = len(cameras)
        active_cameras = len([w for w in self.camera_workers.values() if w.metrics.status == "running"])
        total_objects = sum(w.metrics.objects_count for w in self.camera_workers.values())
        
        # Вычисляем среднюю задержку
        latencies = [w.metrics.latency_ms for w in self.camera_workers.values() if w.metrics.latency_ms > 0]
        average_latency = sum(latencies) / len(latencies) if latencies else 0.0
        
        return {
            "total_cameras": total_cameras,
            "active_cameras": active_cameras,
            "total_objects": total_objects,
            "average_latency_ms": average_latency,
            "uptime": time.time() - self.start_time if self.start_time else 0.0
        }
    
    def control_camera(self, camera_id: str, action: str):
        """Управление камерой"""
        worker = self.camera_workers.get(camera_id)
        if not worker:
            raise ValueError(f"Camera {camera_id} not found")
        
        if action == "start":
            worker.start()
        elif action == "stop":
            worker.stop()
        elif action == "restart":
            worker.restart()
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def reload_config(self):
        """Перезагрузка конфигурации"""
        logger.info("Reloading configuration...")
        
        # Останавливаем сервис
        was_running = self.running
        if was_running:
            self.stop()
        
        # Загружаем новую конфигурацию
        self._load_config()
        
        # Перезапускаем если был запущен
        if was_running:
            self.start()
        
        logger.info("Configuration reloaded")
    
    def is_healthy(self) -> bool:
        """Проверка здоровья сервиса"""
        if not self.running:
            return False
        
        # Проверяем, что все камеры работают корректно
        for worker in self.camera_workers.values():
            if worker.metrics.status == "error":
                return False
        
        return True
