"""
WebSocket endpoints for real-time data
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any, Optional, Callable
import json
import asyncio
import time
import logging
from enum import Enum
from dataclasses import asdict
from collections import defaultdict

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {
            "telemetry": [],
            "preview": [],
            "objects": [],
            "dashboard": []
        }
        self.service_manager: Optional[Any] = None
        self._connection_count = 0
        self._data_stream_tasks: Dict[str, Optional[asyncio.Task]] = {}
        self._stream_running = False
    
    def set_service_manager(self, service_manager):
        """Set the service manager reference for real data access"""
        self.service_manager = service_manager
    
    def _count_active_connections(self, channel: str) -> int:
        """Count active connections for a specific channel"""
        if channel not in self.active_connections:
            return 0
        
        # Clean up broken connections while counting
        active_connections = []
        for ws in self.active_connections[channel]:
            try:
                if hasattr(ws, 'client_state') and ws.client_state.name == 'CONNECTED':
                    active_connections.append(ws)
            except:
                pass
        
        self.active_connections[channel] = active_connections
        return len(active_connections)
    
    def has_active_connections(self, channel: str) -> bool:
        """Check if channel has any active connections"""
        return self._count_active_connections(channel) > 0
    
    async def connect(self, websocket: WebSocket, channel: str):
        """Connect websocket to channel and start data streams if needed"""
        await websocket.accept()
        
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        
        # Clean up broken connections before adding new one
        self._cleanup_broken_connections_for_channel(channel)
        
        self.active_connections[channel].append(websocket)
        self._connection_count += 1
        
        logger.info(f"WebSocket connected to {channel}. Active connections: {len(self.active_connections[channel])}")
        
        # Start data streams if this is the first connection
        if len(self.active_connections[channel]) == 1:
            await self._start_data_stream(channel)
    
    async def disconnect(self, websocket: WebSocket, channel: str):
        """Disconnect websocket from channel and stop data streams if no connections remain"""
        if channel in self.active_connections:
            try:
                self.active_connections[channel].remove(websocket)
                self._connection_count -= 1
                logger.info(f"WebSocket disconnected from {channel}. Remaining connections: {len(self.active_connections[channel])}")
                
                # Stop data streams if no connections remain
                if len(self.active_connections[channel]) == 0:
                    await self._stop_data_stream(channel)
                    
            except ValueError:
                logger.debug(f"WebSocket not found in {channel} connections")
        
        # Clean up from other channels as backup
        self._cleanup_websocket_from_all_channels(websocket)
    
    def _cleanup_websocket_from_all_channels(self, websocket: WebSocket):
        """Remove websocket from all channels (cleanup utility)"""
        for channel_name, connections in self.active_connections.items():
            initial_count = len(connections)
            connections[:] = [ws for ws in connections if ws != websocket]
            removed = initial_count - len(connections)
            
            if removed > 0:
                self._connection_count -= removed
                logger.debug(f"Cleaned up WebSocket from {channel_name}")
    
    def _cleanup_broken_connections_for_channel(self, channel: str):
        """Remove broken connections for specific channel"""
        if channel not in self.active_connections:
            return
            
        active_connections = []
        removed_count = 0
        
        for ws in self.active_connections[channel]:
            try:
                if hasattr(ws, 'client_state') and ws.client_state.name == 'CONNECTED':
                    active_connections.append(ws)
                else:
                    removed_count += 1
            except:
                removed_count += 1
        
        if removed_count > 0:
            self.active_connections[channel] = active_connections
            self._connection_count -= removed_count
            logger.debug(f"Cleaned up {removed_count} broken connections from {channel}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket) -> bool:
        try:
            if hasattr(websocket, 'client_state'):
                if websocket.client_state.name != 'CONNECTED':
                    return False
            await websocket.send_text(message)
            return True
        except Exception as e:
            logger.debug(f"Error sending personal message: {e}")
            self._cleanup_websocket_from_all_channels(websocket)
            return False
    
    async def broadcast(self, message: str, channel: str):
        """Broadcast message to all active connections in channel"""
        if channel not in self.active_connections or not self.active_connections[channel]:
            return
            
        disconnected = []
        for connection in self.active_connections[channel]:
            try:
                if hasattr(connection, 'client_state'):
                    if connection.client_state.name != 'CONNECTED':
                        disconnected.append(connection)
                        continue
                await connection.send_text(message)
            except Exception as e:
                logger.debug(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            try:
                self.active_connections[channel].remove(connection)
                self._connection_count -= 1
            except ValueError:
                pass

    def get_connection_stats(self) -> Dict[str, int]:
        """Get statistics about active connections"""
        # Clean up broken connections first
        for channel in self.active_connections.keys():
            self._cleanup_broken_connections_for_channel(channel)
        
        return {
            "total_connections": self._connection_count,
            "channels": {channel: len(connections) for channel, connections in self.active_connections.items()}
        }
    
    async def cleanup_all_connections(self):
        """Clean up all WebSocket connections and stop all data streams"""
        total_connections = self._connection_count
        
        # Stop all data streams
        for channel in self.active_connections.keys():
            await self._stop_data_stream(channel)
        
        # Clear all connections
        for channel in self.active_connections:
            self.active_connections[channel].clear()
        
        self._connection_count = 0
        if total_connections > 0:
            logger.info(f"Cleaned up all {total_connections} WebSocket connections")
    
    async def _start_data_stream(self, channel: str):
        """Start data streaming task for channel"""
        if channel in self._data_stream_tasks and self._data_stream_tasks[channel]:
            return  # Already running
        
        if channel == "dashboard":
            task = asyncio.create_task(self._dashboard_data_stream())
            self._data_stream_tasks[channel] = task
            logger.info(f"Started data stream for {channel}")
    
    async def _stop_data_stream(self, channel: str):
        """Stop data streaming task for channel"""
        if channel in self._data_stream_tasks and self._data_stream_tasks[channel]:
            self._data_stream_tasks[channel].cancel()
            self._data_stream_tasks[channel] = None
            logger.info(f"Stopped data stream for {channel}")
    
    async def _dashboard_data_stream(self):
        """Stream dashboard data while connections exist"""
        try:
            while self.has_active_connections("dashboard"):
                # Send consolidated dashboard update
                service_status = get_service_status()
                cameras = get_all_camera_statuses()
                system_metrics = get_system_metrics()
                
                update_data = {
                    "type": "dashboard_update",
                    "timestamp": time.time(),
                    "data": {
                        "service": service_status,
                        "cameras": cameras,
                        "system": system_metrics
                    }
                }
                
                await self.broadcast(json.dumps(update_data), "dashboard")
                await asyncio.sleep(2)  # Send updates every 2 seconds
                
        except asyncio.CancelledError:
            logger.debug("Dashboard data stream cancelled")
        except Exception as e:
            logger.error(f"Error in dashboard data stream: {e}")

# Global WebSocket connection manager
manager = WebSocketManager()

async def telemetry_websocket(websocket: WebSocket):
    """WebSocket для телеметрии (FPS, задержки, статус камер)"""
    try:
        await manager.connect(websocket, "telemetry")
        # Connection-specific logic can be added here if needed
        # Data streaming is now handled by the manager
        await websocket.receive_text()  # Wait for client disconnect
    except WebSocketDisconnect:
        logger.info("Telemetry WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in telemetry WebSocket: {e}")
    finally:
        await manager.disconnect(websocket, "telemetry")

async def preview_websocket(websocket: WebSocket):
    """WebSocket для превью камер (JPEG кадры)"""
    try:
        await manager.connect(websocket, "preview")
        # Connection-specific logic can be added here if needed
        await websocket.receive_text()  # Wait for client disconnect
    except WebSocketDisconnect:
        logger.info("Preview WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in preview WebSocket: {e}")
    finally:
        await manager.disconnect(websocket, "preview")

async def objects_websocket(websocket: WebSocket):
    """WebSocket для объектов в реальном времени"""
    try:
        await manager.connect(websocket, "objects")
        # Connection-specific logic can be added here if needed
        await websocket.receive_text()  # Wait for client disconnect
    except WebSocketDisconnect:
        logger.info("Objects WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in objects WebSocket: {e}")
    finally:
        await manager.disconnect(websocket, "objects")

async def dashboard_websocket(websocket: WebSocket, service_manager=None):
    """Unified WebSocket for dashboard - combines service status, camera metrics, system info"""
    try:
        # Set service manager if provided
        if service_manager:
            manager.set_service_manager(service_manager)
        
        # Connect and start data streaming (handled by manager)
        await manager.connect(websocket, "dashboard")
        
        # Send initial state immediately after connection
        await send_dashboard_initial_state(websocket)
        
        # Wait for client disconnect or error
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in dashboard WebSocket: {e}")
    finally:
        await manager.disconnect(websocket, "dashboard")

async def send_dashboard_initial_state(websocket: WebSocket):
    """Send complete initial state to new dashboard connection"""
    try:
        if hasattr(websocket, 'client_state'):
            if websocket.client_state.name != 'CONNECTED':
                return
        
        service_status = get_service_status()
        cameras = get_all_camera_statuses()
        system_metrics = get_system_metrics()
        
        initial_state = {
            "type": "dashboard_initial_state",
            "timestamp": time.time(),
            "data": {
                "service": service_status,
                "cameras": cameras,
                "system": system_metrics
            }
        }
        
        await websocket.send_text(json.dumps(initial_state))
        logger.debug("Sent dashboard initial state")
        
    except Exception as e:
        logger.error(f"Error sending dashboard initial state: {e}")

def get_service_status() -> Dict[str, Any]:
    """Get current service status"""
    if manager.service_manager:
        return {
            "status": "running" if manager.service_manager.running else "stopped",
            "running": manager.service_manager.running,
            "uptime": time.time() - manager.service_manager.start_time if manager.service_manager.start_time else 0,
            "cameras_count": len(manager.service_manager.camera_workers) if hasattr(manager.service_manager, 'camera_workers') else 0,
            "healthy": manager.service_manager.is_healthy() if hasattr(manager.service_manager, 'is_healthy') else True
        }
    return {
        "status": "not_initialized",
        "running": False,
        "uptime": 0,
        "cameras_count": 0,
        "healthy": False
    }

def get_all_camera_statuses() -> List[Dict[str, Any]]:
    """Get status of all cameras"""
    if not manager.service_manager or not hasattr(manager.service_manager, 'camera_workers'):
        return []
    
    cameras = []
    for camera_id, worker in manager.service_manager.camera_workers.items():
        metrics = worker.metrics if hasattr(worker, 'metrics') else None
        if metrics:
            camera_data = {
                "camera_id": camera_id,
                "name": worker.camera_config.name if hasattr(worker, 'camera_config') else camera_id,
                "status": metrics.status,
                "enabled": worker.camera_config.enabled if hasattr(worker, 'camera_config') else True,
                "fps_input": metrics.fps_input,
                "fps_processed": metrics.fps_processed,
                "latency_ms": metrics.latency_ms,
                "objects_count": metrics.objects_count,
                "last_frame_time": metrics.last_frame_time,
                "error_message": metrics.error_message,
                "stream": worker.camera_config.stream if hasattr(worker, 'camera_config') else "",
                "queue_size": metrics.queue_size
            }
            cameras.append(camera_data)
    
    return cameras

def get_system_metrics() -> Dict[str, Any]:
    """Get system-wide metrics"""
    if not manager.service_manager:
        return {
            "total_cameras": 0,
            "active_cameras": 0,
            "total_objects": 0,
            "average_latency_ms": 0.0,
            "system_cpu_percent": 0.0,
            "system_memory_percent": 0.0
        }
    
    cameras = get_all_camera_statuses()
    active_cameras = [c for c in cameras if c["status"] == "running"]
    
    return {
        "total_cameras": len(cameras),
        "active_cameras": len(active_cameras),
        "total_objects": sum(c["objects_count"] for c in active_cameras),
        "average_latency_ms": sum(c["latency_ms"] for c in active_cameras) / len(active_cameras) if active_cameras else 0.0,
        "system_cpu_percent": 0.0,  # TODO: Get real system metrics
        "system_memory_percent": 0.0  # TODO: Get real system metrics
    }

# Event broadcasting functions for ServiceManager integration
async def broadcast_service_status_change(status_data: Dict[str, Any]):
    """Broadcast service status change to all dashboard clients"""
    try:
        message = json.dumps({
            "type": "service_status_changed",
            "data": status_data,
            "timestamp": time.time()
        })
        await manager.broadcast(message, "dashboard")
    except Exception as e:
        print(f"Error broadcasting service status change: {e}")

async def broadcast_camera_status_change(camera_data: Dict[str, Any]):
    """Broadcast camera status change to all dashboard clients"""
    try:
        message = json.dumps({
            "type": "camera_status_changed",
            "data": camera_data,
            "timestamp": time.time()
        })
        await manager.broadcast(message, "dashboard")
    except Exception as e:
        print(f"Error broadcasting camera status change: {e}")

async def broadcast_camera_added(camera_data: Dict[str, Any]):
    """Broadcast camera addition to all dashboard clients"""
    try:
        message = json.dumps({
            "type": "camera_added",
            "data": camera_data,
            "timestamp": time.time()
        })
        await manager.broadcast(message, "dashboard")
    except Exception as e:
        print(f"Error broadcasting camera added: {e}")

async def broadcast_camera_removed(camera_id: str):
    """Broadcast camera removal to all dashboard clients"""
    try:
        message = json.dumps({
            "type": "camera_removed",
            "data": {"camera_id": camera_id},
            "timestamp": time.time()
        })
        await manager.broadcast(message, "dashboard")
    except Exception as e:
        print(f"Error broadcasting camera removed: {e}")

# Legacy functions for backward compatibility
async def broadcast_telemetry(data: Dict[str, Any]):
    """Отправка телеметрии всем подключенным клиентам"""
    try:
        await manager.broadcast(json.dumps(data), "telemetry")
    except Exception as e:
        print(f"Error broadcasting telemetry: {e}")

async def broadcast_preview(camera_id: str, frame_data: str):
    """Отправка превью камеры"""
    try:
        data = {
            "type": "preview",
            "timestamp": time.time(),
            "camera_id": camera_id,
            "frame_data": frame_data
        }
        await manager.broadcast(json.dumps(data), "preview")
    except Exception as e:
        print(f"Error broadcasting preview: {e}")

async def broadcast_objects(camera_id: str, objects: List[Dict[str, Any]]):
    """Отправка данных объектов"""
    try:
        data = {
            "type": "objects",
            "timestamp": time.time(),
            "camera_id": camera_id,
            "objects": objects
        }
        await manager.broadcast(json.dumps(data), "objects")
    except Exception as e:
        print(f"Error broadcasting objects: {e}")
