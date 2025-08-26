#!/usr/bin/env python3
"""
Simple test for database configuration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import ConfigDatabase
from app.config.schema import CameraConfig, AppConfig, ServiceConfig, TrackingConfig, OSCConfig

def test_database():
    """Test database operations"""
    print("Testing database configuration...")
    
    # Create database
    db = ConfigDatabase("test_settings.db")
    
    # Test service config
    print("\n1. Testing service config...")
    service_config = db.get_service_config()
    print(f"Default service config: {service_config}")
    
    # Update service config
    service_config.port = 9090
    service_config.log_level = "debug"
    db.save_service_config(service_config)
    
    # Read back
    updated_service = db.get_service_config()
    print(f"Updated service config: {updated_service}")
    
    # Test tracking config
    print("\n2. Testing tracking config...")
    tracking_config = db.get_tracking_config()
    print(f"Default tracking config: {tracking_config}")
    
    # Update tracking config
    tracking_config.confidence = 0.5
    tracking_config.classes = [0, 1, 2]
    db.save_tracking_config(tracking_config)
    
    # Read back
    updated_tracking = db.get_tracking_config()
    print(f"Updated tracking config: {updated_tracking}")
    
    # Test OSC config
    print("\n3. Testing OSC config...")
    osc_config = db.get_osc_config()
    print(f"Default OSC config: {osc_config}")
    
    # Update OSC config
    osc_config.host = "192.168.1.100"
    osc_config.port = 6000
    db.save_osc_config(osc_config)
    
    # Read back
    updated_osc = db.get_osc_config()
    print(f"Updated OSC config: {updated_osc}")
    
    # Test cameras
    print("\n4. Testing cameras...")
    cameras = db.get_all_cameras()
    print(f"Initial cameras: {len(cameras)}")
    
    # Add a test camera
    test_camera = CameraConfig(
        id="test_cam_1",
        name="Test Camera 1",
        stream="rtsp://test:pass@192.168.1.100:554/stream",
        enabled=True,
        show_preview=False,
        roi=[100, 100, 500, 400],
        classes_filter=["person", "car"]
    )
    
    db.save_camera(test_camera)
    print(f"Added camera: {test_camera}")
    
    # Read back all cameras
    cameras = db.get_all_cameras()
    print(f"Cameras after adding: {len(cameras)}")
    for cam in cameras:
        print(f"  - {cam.id}: {cam.name} ({cam.stream})")
    
    # Get specific camera
    camera = db.get_camera("test_cam_1")
    print(f"Retrieved camera: {camera}")
    
    # Test full config
    print("\n5. Testing full config...")
    full_config = db.get_full_config()
    print(f"Full config cameras: {len(full_config.cameras)}")
    print(f"Full config service port: {full_config.service.port}")
    print(f"Full config tracking confidence: {full_config.tracking.confidence}")
    print(f"Full config OSC host: {full_config.osc.host}")
    
    # Delete test camera
    print("\n6. Testing camera deletion...")
    deleted = db.delete_camera("test_cam_1")
    print(f"Camera deleted: {deleted}")
    
    cameras = db.get_all_cameras()
    print(f"Cameras after deletion: {len(cameras)}")
    
    print("\nDatabase test completed successfully!")
    
    # Clean up
    try:
        os.remove("test_settings.db")
        print("Test database cleaned up")
    except:
        pass

if __name__ == "__main__":
    test_database()
