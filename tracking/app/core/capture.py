"""
Thread for capturing video frames from stream or file
"""

import threading
import time
import queue
from typing import Optional, Tuple, Any

import cv2


class CaptureThread:
    """Thread for capturing video frames from stream or file"""
    
    def __init__(self, src: str) -> None:
        """Initialize capture thread"""
        print("Info: create new daemon thread for stream capturing")

        self.lock = threading.Lock()
        self.src: str = src
        self.cap: Optional[cv2.VideoCapture] = None
        self.ret: bool = False
        self.frame: Optional[Any] = None
        self.stopped: bool = False
        self.ready: bool = False
        self.waiting: float = 0
        self.fps: float = 0
        self.type: str

        self.q: queue.Queue = queue.Queue()
        self.thread_run: threading.Thread = threading.Thread(target=self.run)
        self.thread_run.daemon = True

        if "://" in f"{src}":
            self.type = 'stream'
        else:
            self.type = 'video'

        self.thread_run.start()

        self.init()

        print("Info: capture thread started")

    def init(self) -> None:
        """Initialize video capture"""
        while True:
            if self.ready:
                break

            if self.cap is None or not self.cap.isOpened():
                # Clean up previous instance if it exists
                if self.cap is not None:
                    self.cap.release()
                
                self.cap = cv2.VideoCapture(self.src)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            time.sleep(3)

    def run(self) -> None:
        """Main capture loop"""
        while not self.stopped:
            if self.cap is None or not self.cap.isOpened():
                if self.waiting == 0:
                    self.ready = False
                    self.waiting = time.time()
                    # Clean up failed capture instance
                    if self.cap is not None:
                        self.cap.release()
                        self.cap = None
            
                waited = int(time.time() - self.waiting)

                if waited > 0:
                    print(f"Pause: waiting for stream start {waited} s", end="\r", flush=True)

                # Try to reconnect every 3 seconds
                if waited % 3 == 0:
                    try:
                        self.cap = cv2.VideoCapture(self.src)
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    except Exception as e:
                        print(f"Failed to reconnect: {e}")
                        if self.cap is not None:
                            self.cap.release()
                            self.cap = None
                
                continue
            
            if self.waiting > 0:
                self.waiting = 0

            start_time = time.time()
            # Grab the next frame
            try:
                grabbed = self.cap.grab()
            except:
                continue

            if not grabbed:
                continue

            self.ready = True

            # Retrieve and decode the frame
            ret, frame = self.cap.retrieve()
            if ret:
                with self.lock:
                    self.ret = ret
                    self.frame = frame
            
            # Wait until the next frame should be displayed for video file
            if self.type == 'video' and hasattr(self, 'fps') and self.fps > 0:
                time.sleep(max(1./self.fps - (time.time() - start_time), 0))

    def detect_fps(self) -> None:
        """Detect and set FPS from video source"""
        # Find OpenCV version and get FPS
        (major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')
        if int(major_ver) < 3:
            self.fps = self.cap.get(cv2.cv.CV_CAP_PROP_FPS)
        else:
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"Info: detected source FPS - {self.fps}")

    def read(self) -> Tuple[bool, Optional[Any]]:
        """Read the latest frame"""
        with self.lock:
            return self.ret, self.frame

    def stop(self) -> None:
        """Stop capture thread"""
        self.stopped = True
        if self.cap:
            self.cap.release()
    
    def join(self) -> None:
        """Wait for the capture thread to finish"""
        if self.thread_run and self.thread_run.is_alive():
            self.thread_run.join()
