"""
OSC worker for sending tracking data to TouchDesigner
"""

import time
from typing import Dict, List, Optional, Any

from pythonosc.udp_client import SimpleUDPClient

from .objects_buffer import ObjectsBuffer


class OSCWorker:
    """OSC worker for sending tracking data to TouchDesigner"""
    
    def __init__(self, ip: str = "127.0.0.1", port: int = 5005, 
                 confidence: float = 0.1, objects_filter: str = "",
                 object_persistance: int = 10, objects_max: int = 10,
                 timeout: int = 5, debug: bool = False) -> None:
        """Establish connection with TouchDesigner OSC server"""
        self.ip: str = ip
        self.port: int = port
        self.debug: bool = debug
        self.confidence: float = confidence
        self.objectsFilter: str = objects_filter
        self.objectPersistance: int = object_persistance
        self.objectsBuf: ObjectsBuffer = ObjectsBuffer(objects_max)
        self.client: Optional[SimpleUDPClient] = None
        self.status: bool = False

        retry_count = 0
        max_retries = 10  # Prevent infinite loop
        
        while retry_count < max_retries:
            try:
                # Clean up previous client if it exists
                if self.client is not None:
                    self.client = None
                
                self.client = SimpleUDPClient(self.ip, self.port)
                self.status = True
                print("Info: UDP client ready to send data")
                break
            except Exception as e:
                self.status = False
                retry_count += 1
                print(f"Warning: connection failed ({e}), retrying in {timeout} seconds... ({retry_count}/{max_retries})")
                
                # Clean up failed client
                if self.client is not None:
                    self.client = None
                    
                if retry_count >= max_retries:
                    print(f"Error: Failed to establish OSC connection after {max_retries} attempts")
                    break
                    
                time.sleep(timeout)

    def send_tracking_data(self, detections: List[Dict[str, Any]]) -> None:
        """Process and send tracking data via OSC"""
        now = time.time()

        # Filter and sort detections
        if self.objectsFilter:
            # Parse filter string as comma-separated values
            filter_classes = [cls.strip() for cls in self.objectsFilter.split(',') if cls.strip()]
            if filter_classes:
                detections = [item for item in detections if item["name"] in filter_classes]
        
        detections = sorted(detections, key=lambda x: (-x["confidence"], x.get("track_id", float('inf'))))

        # Free all objects
        self.objectsBuf.free()

        # First, find all prev track_ids
        for detected in detections:
            if "track_id" in detected:
                self.objectsBuf.found(detected["track_id"])
        
        # Second, add new track_ids
        for detected in detections:
            if detected['confidence'] < self.confidence or not "track_id" in detected:
                continue

            self.objectsBuf.add(detected['track_id'])

            self.objectsBuf.set_center(detected['track_id'], detected['box'])

        if self.debug:
            self.objectsBuf.dump()

        self.objectsBuf.reset_time()

        # Third, send data from buffer to OSC server
        for object in self.objectsBuf.each():
            objectPersist = (now - object['time']) * 1000
            if not object['free'] and object['track_id'] > 0 and objectPersist >= self.objectPersistance:
                self.send(f"/p{object['index']}_x", float(object['center'][0]))
                self.send(f"/p{object['index']}_y", float(object['center'][1]))
    
    def send(self, channel: str, data: float) -> None:
        """Send OSC message"""
        if self.client is not None:
            self.client.send_message(channel, data)
    
    def cleanup(self) -> None:
        """Clean up OSC worker resources"""
        if self.client is not None:
            self.client = None
        self.status = False
