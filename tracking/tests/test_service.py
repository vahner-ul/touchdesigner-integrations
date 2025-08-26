"""
Test script for service manager functionality
"""

import time
import threading
from app.config.loader import ConfigLoader
from app.service.manager import ServiceManager, CameraStatus
from app.service.metrics import MetricsCollector
from app.service.logging import setup_logging


def test_service_manager():
    """Test service manager functionality"""
    print("Testing Service Manager...")
    
    # Setup logging
    logger = setup_logging("DEBUG")
    
    # Load test configuration
    config_loader = ConfigLoader("config_multi_cameras.yaml")
    config = config_loader.load()
    
    print(f"Loaded configuration with {len(config.cameras)} cameras")
    
    # Create service manager
    service_manager = ServiceManager(config)
    metrics_collector = MetricsCollector()
    
    print("Service manager created")
    
    # Test individual camera control
    print("\n--- Testing individual camera control ---")
    
    # Start specific camera
    camera_id = "entrance"
    if camera_id in service_manager.cameras:
        print(f"Starting camera: {camera_id}")
        success = service_manager.start_camera(camera_id)
        print(f"Start result: {success}")
        
        # Wait a bit
        time.sleep(2)
        
        # Check status
        status = service_manager.get_status()
        camera_status = status["cameras"].get(camera_id)
        print(f"Camera status: {camera_status}")
        
        # Stop camera
        print(f"Stopping camera: {camera_id}")
        success = service_manager.stop_camera(camera_id)
        print(f"Stop result: {success}")
    
    # Test system-wide control
    print("\n--- Testing system-wide control ---")
    
    # Start all enabled cameras
    print("Starting all enabled cameras...")
    service_manager.start()
    
    # Monitor for a few seconds
    print("Monitoring cameras for 10 seconds...")
    for i in range(10):
        status = service_manager.get_status()
        metrics_collector.update_system_metrics(status)
        
        print(f"\nStatus update {i+1}:")
        print(f"  Running: {status['running']}")
        print(f"  Cameras: {len(status['cameras'])}")
        
        for cam_id, cam_status in status["cameras"].items():
            print(f"    {cam_id}: {cam_status['status']} (enabled: {cam_status['enabled']})")
        
        time.sleep(1)
    
    # Stop all cameras
    print("\nStopping all cameras...")
    service_manager.stop()
    
    # Final status
    status = service_manager.get_status()
    print(f"\nFinal status - Running: {status['running']}")
    
    print("\nService manager test completed!")


def test_metrics_collector():
    """Test metrics collector functionality"""
    print("\n--- Testing Metrics Collector ---")
    
    metrics = MetricsCollector()
    
    # Simulate some metrics
    from app.service.manager import CameraMetrics
    
    # Add some test data
    test_metrics = CameraMetrics(
        fps_in=30.0,
        fps_proc=25.0,
        latency_ms=50.0,
        objects_count=3,
        error_count=0,
        reconnect_count=1
    )
    
    metrics.update_camera_metrics("test_camera", test_metrics, CameraStatus.RUNNING)
    
    # Test system metrics
    test_status = {
        "running": True,
        "cameras": {
            "cam1": {
                "status": CameraStatus.RUNNING.value,
                "metrics": {"fps_proc": 25.0, "objects_count": 2}
            },
            "cam2": {
                "status": CameraStatus.STOPPED.value,
                "metrics": {"fps_proc": 0.0, "objects_count": 0}
            }
        }
    }
    
    metrics.update_system_metrics(test_status)
    
    # Get summary
    summary = metrics.get_summary()
    print(f"Metrics summary: {summary}")
    
    print("Metrics collector test completed!")


if __name__ == "__main__":
    try:
        test_metrics_collector()
        test_service_manager()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
