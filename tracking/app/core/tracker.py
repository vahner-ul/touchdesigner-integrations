"""
YOLO model wrapper for object tracking
"""

import os.path
from typing import Any

import torch
from ultralytics import YOLO

from .capture import CaptureThread


class Tracker:
    """YOLO model wrapper for object tracking"""
    
    def __init__(self, model_name: str = "yolov8l", single_class: int = -1, debug: bool = False) -> None:
        """Initialize YOLO model"""
        self.model_task: str = "detection"
        self.model_name: str = model_name
        self.single_class: int = single_class
        self.debug: bool = debug
        self.model_path: str
        self.model: YOLO

        self.model_path = f"{self.model_name}.pt"

        print(f"Info: loading YOLO model {self.model_name}")

        if os.path.isfile(f"../models/{self.model_name}.pt"):
            self.model_path = f"../models/{self.model_name}.pt"

        self.model = YOLO(model=self.model_path, task=self.model_task, verbose=self.debug)
    
    def warm_up(self, cap: CaptureThread) -> None:
        """Warm up the model with first frames"""
        print("Info: warm up the model on first frames")

        frames = 10
        ret = None

        while not ret or frames > 0:
            ret, frame = cap.read()

            if not ret:
                continue
            
            self.process_frame(frame)
            frames -= 1
        
        print("Info: warm up successful, ready")

    def process_frame(self, frame: Any) -> Any:
        """Process frame with YOLO tracking"""
        # Run inference on frame
        if self.single_class >= 0:
            results = self.model.track(
                source=frame, 
                persist=True, 
                show=False, 
                verbose=self.debug, 
                classes=self.single_class
            )
        else:
            results = self.model.track(
                source=frame, 
                persist=True, 
                show=False, 
                verbose=self.debug
            )

        # Debugging: Print track IDs
        if self.debug:
            print('- read frame and run inference')
            if results[0].boxes.id is not None:
                print("Track IDs:", results[0].boxes.id)

        return results
