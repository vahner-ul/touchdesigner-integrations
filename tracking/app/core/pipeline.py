"""
Main processing pipeline that combines capture, tracking and OSC output
"""

import json
import time
from typing import Optional, Any, Dict

import cv2
import torch

from .capture import CaptureThread
from .tracker import Tracker
from .osc import OSCWorker


class Pipeline:
    """Main processing pipeline that combines capture, tracking and OSC output"""
    
    def __init__(self, stream: str, model: str = "yolov8l", ip: str = "127.0.0.1", 
                 port: int = 5005, confidence: float = 0.1, tracking_period: int = 1,
                 objects_max: int = 10, objects_filter: str = "", 
                 object_persistance: int = 10, timeout: int = 5,
                 single_class: int = -1, debug: bool = False, show: bool = False) -> None:
        """Initialize the processing pipeline"""
        self.stream = stream
        self.debug = debug
        self.show = show
        self.tracking_period = tracking_period
        
        # Check CUDA availability
        print("Info: check for CUDA availability...")
        if torch.cuda.is_available():
            print(" - CUDA available, inference will run fast on GPU")
        else:
            print(" - CUDA not found, inference will run slower on CPU")
        
        # Initialize components
        self.osc_worker = OSCWorker(
            ip=ip, port=port, confidence=confidence, 
            objects_filter=objects_filter, object_persistance=object_persistance,
            objects_max=objects_max, timeout=timeout, debug=debug
        )
        
        self.tracker = Tracker(
            model_name=model, single_class=single_class, debug=debug
        )
        
        self.capture = CaptureThread(stream)
        
        print("Info: all things seem to be ready, starting main loop...")
    
    def run(self) -> None:
        """Run the main processing loop"""
        try:
            while not self.capture.ready:
                continue
            
            self.tracker.warm_up(self.capture)
            frame_index = 0

            while True:
                start_time = time.time()
                ret, frame = self.capture.read()

                if not ret:
                    if self.capture.type == 'stream':
                        continue
                    else:
                        print('Warning: end of frames')
                        self.capture.stop()
                        self.capture.join()
                        cv2.destroyAllWindows()
                        break

                frame_index += 1
                if frame_index >= self.tracking_period:
                    frame_index = 0
                else:
                    continue

                # Process the frame
                results = self.tracker.process_frame(frame)
                detections_json = results[0].tojson()
                detections = json.loads(detections_json)

                self.osc_worker.send_tracking_data(detections)

                if self.show:
                    annotated_frame = results[0].plot()
                    cv2.imshow("Tracking results", annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                        
        except KeyboardInterrupt:
            print('Info: close video stream capture')
            self.capture.stop()
            cv2.destroyAllWindows()
    
    def stop(self) -> None:
        """Stop the pipeline"""
        self.capture.stop()
        if hasattr(self, 'osc_worker'):
            self.osc_worker.cleanup()
        cv2.destroyAllWindows()


class TrackingPipeline:
    """Enhanced pipeline for service management with metrics and status tracking"""
    
    def __init__(self, stream_url: str, model_name: str = "yolov8l", 
                 confidence: float = 0.25, device: str = "auto",
                 osc_host: str = "127.0.0.1", osc_port: int = 5005,
                 osc_address_prefix: str = "/", objects_max: int = 10,
                 object_persistence_ms: int = 50, period_frames: int = 1,
                 objects_filter: str = "", timeout: int = 5,
                 single_class: int = -1, debug: bool = False) -> None:
        """Initialize the tracking pipeline for service management"""
        self.stream_url = stream_url
        self.model_name = model_name
        self.confidence = confidence
        self.device = device
        self.osc_host = osc_host
        self.osc_port = osc_port
        self.osc_address_prefix = osc_address_prefix
        self.objects_max = objects_max
        self.object_persistence_ms = object_persistence_ms
        self.period_frames = period_frames
        self.objects_filter = objects_filter
        self.timeout = timeout
        self.single_class = single_class
        self.debug = debug
        
        # Status tracking
        self._running = False
        self._start_time = None
        self._last_frame_time = None
        
        # Metrics
        self._fps_input = 0.0
        self._fps_processed = 0.0
        self._latency_ms = 0.0
        self._objects_count = 0
        self._queue_size = 0
        self._frame_count = 0
        self._processed_count = 0
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize pipeline components"""
        # Check CUDA availability
        if self.debug:
            print("Info: check for CUDA availability...")
            if torch.cuda.is_available():
                print(" - CUDA available, inference will run fast on GPU")
            else:
                print(" - CUDA not found, inference will run slower on CPU")
        
        # Initialize components
        self.osc_worker = OSCWorker(
            ip=self.osc_host, 
            port=self.osc_port, 
            confidence=self.confidence, 
            objects_filter=self.objects_filter, 
            object_persistance=self.object_persistence_ms,
            objects_max=self.objects_max, 
            timeout=self.timeout, 
            debug=self.debug
        )
        
        self.tracker = Tracker(
            model_name=self.model_name, 
            single_class=self.single_class, 
            debug=self.debug
        )
        
        self.capture = CaptureThread(self.stream_url)
        
        if self.debug:
            print("Info: all components initialized")
    
    def start(self) -> None:
        """Start the tracking pipeline"""
        if self._running:
            return
            
        self._running = True
        self._start_time = time.time()
        
        # Start capture thread
        if not self.capture.ready:
            while not self.capture.ready:
                time.sleep(0.1)
        
        # Warm up tracker
        self.tracker.warm_up(self.capture)
        
        if self.debug:
            print("Info: tracking pipeline started")
    
    def stop(self) -> None:
        """Stop the tracking pipeline"""
        self._running = False
        
        # Stop capture thread
        if hasattr(self, 'capture'):
            self.capture.stop()
        
        # Cleanup OSC worker
        if hasattr(self, 'osc_worker'):
            self.osc_worker.cleanup()
        
        cv2.destroyAllWindows()
        
        if self.debug:
            print("Info: tracking pipeline stopped")
    
    def is_running(self) -> bool:
        """Check if the pipeline is running"""
        return self._running and (self.capture.ready if hasattr(self, 'capture') else False)
    
    def process_frame(self) -> bool:
        """Process a single frame and update metrics"""
        if not self._running:
            return False
        
        try:
            start_time = time.time()
            ret, frame = self.capture.read()
            
            if not ret:
                if self.capture.type == 'stream':
                    return True  # Continue for streams
                else:
                    self._running = False
                    return False
            
            self._frame_count += 1
            self._last_frame_time = time.time()
            
            # Process every N frames based on period_frames
            if self._frame_count % self.period_frames != 0:
                return True
            
            self._processed_count += 1
            
            # Process the frame
            results = self.tracker.process_frame(frame)
            detections_json = results[0].tojson()
            detections = json.loads(detections_json)
            
            # Update object count
            self._objects_count = len(detections)
            
            # Send tracking data
            self.osc_worker.send_tracking_data(detections)
            
            # Update latency
            self._latency_ms = (time.time() - start_time) * 1000
            
            # Update FPS metrics
            if self._start_time:
                elapsed = time.time() - self._start_time
                if elapsed > 0:
                    self._fps_input = self._frame_count / elapsed
                    self._fps_processed = self._processed_count / elapsed
            
            return True
            
        except Exception as e:
            if self.debug:
                print(f"Error processing frame: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current pipeline metrics"""
        return {
            "fps_input": self._fps_input,
            "fps_processed": self._fps_processed,
            "latency_ms": self._latency_ms,
            "objects_count": self._objects_count,
            "queue_size": self._queue_size,
            "last_frame_time": self._last_frame_time,
            "frame_count": self._frame_count,
            "processed_count": self._processed_count,
            "running": self._running
        }
    
    def run_continuous(self) -> None:
        """Run the pipeline continuously (for standalone mode)"""
        self.start()
        
        try:
            while self._running:
                if not self.process_frame():
                    break
                time.sleep(0.001)  # Small delay to prevent busy waiting
        except KeyboardInterrupt:
            if self.debug:
                print('Info: stopping tracking pipeline')
        finally:
            self.stop()
