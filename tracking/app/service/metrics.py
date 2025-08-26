"""
System metrics service
"""
import time
from typing import Dict, Any

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. Using dummy metrics.")

class MetricsService:
    """Service for collecting system metrics"""
    
    def __init__(self):
        self.start_time = time.time()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        if PSUTIL_AVAILABLE:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
            except Exception as e:
                print(f"Error getting system metrics: {e}")
                cpu_percent = 0.0
                memory_percent = 0.0
        else:
            # Dummy metrics when psutil is not available
            cpu_percent = 0.0
            memory_percent = 0.0
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "uptime": time.time() - self.start_time
        }
    
    def get_process_metrics(self) -> Dict[str, Any]:
        """Get current process metrics"""
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                return {
                    "memory_rss": memory_info.rss,
                    "memory_vms": memory_info.vms,
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads()
                }
            except Exception as e:
                print(f"Error getting process metrics: {e}")
                return self._get_dummy_process_metrics()
        else:
            return self._get_dummy_process_metrics()
    
    def _get_dummy_process_metrics(self) -> Dict[str, Any]:
        """Get dummy process metrics when psutil is not available"""
        return {
            "memory_rss": 0,
            "memory_vms": 0,
            "cpu_percent": 0.0,
            "num_threads": 1
        }

# Глобальный экземпляр сервиса метрик
metrics_service = MetricsService()
