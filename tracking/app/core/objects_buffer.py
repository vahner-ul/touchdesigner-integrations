"""
Objects buffer for managing detected objects with persistent tracking IDs
"""

import time
from typing import Dict, Any


class ObjectsBuffer:
    """Buffer for managing detected objects with persistent tracking IDs"""
    
    def __init__(self, size: int = 10) -> None:
        self.objects: Dict[str, Dict[str, Any]] = {}
        self.maxSize = size
        self.setup()

    def setup(self) -> None:
        """Initialize object slots"""
        for i in range(self.maxSize):
            self.objects[f"p{i+1}"] = {
                'track_id': -1, 
                'time': 0, 
                'free': True, 
                'index': i+1, 
                'center': [0, 0]
            }

    def free(self) -> None:
        """Mark all objects as free"""
        for obj_id in self.objects:
            self.objects[obj_id]['free'] = True
    
    def found(self, track_id: int) -> bool:
        """Mark existing track_id as found and not free"""
        for obj_id in self.objects:
            if self.objects[obj_id]['track_id'] == track_id:
                self.objects[obj_id]['free'] = False
                if self.objects[obj_id]['time'] == 0:
                    self.objects[obj_id]['time'] = time.time()
                return True
        return False

    def add(self, track_id: int) -> int:
        """Add new track_id to buffer, return index"""
        if self.found(track_id):
            return 0

        for obj_id, obj in self.objects.items():
            if obj['free']:
                obj['track_id'] = track_id
                obj['free'] = False
                obj['time'] = time.time()
                return obj['index']
        
        return 0

    def set_center(self, track_id: int, box: Dict[str, float]) -> None:
        """Set center coordinates for track_id from bounding box"""
        if not all(key in box for key in ['x1', 'x2', 'y1', 'y2']):
            return

        center_x = (box['x1'] + box['x2']) / 2
        center_y = (box['y1'] + box['y2']) / 2

        for obj_id, obj in self.objects.items():
            if obj['track_id'] == track_id:
                obj['center'] = [center_x, center_y]
                break

    def each(self):
        """Generator to iterate over all objects"""
        for id in self.objects:
            yield self.objects[id]
    
    def reset_time(self) -> None:
        """Reset time for free objects"""
        for obj_id in self.objects:
            if self.objects[obj_id]['free']:
                self.objects[obj_id]['time'] = 0

    def dump(self) -> None:
        """Debug print of all objects"""
        print(self.objects)
