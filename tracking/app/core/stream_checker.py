"""
Stream connectivity checker utility
"""
import cv2
import time
import asyncio
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class StreamChecker:
    """Utility for checking stream connectivity"""
    
    @staticmethod
    def check_stream_connectivity(stream_url: str, timeout: float = 5.0) -> Tuple[bool, Optional[str]]:
        """
        Check if a stream URL is accessible and can provide frames
        
        Args:
            stream_url: The stream URL to check
            timeout: Maximum time to wait for connection
            
        Returns:
            Tuple of (is_accessible, error_message)
        """
        cap = None
        start_time = time.time()
        
        try:
            logger.info(f"Checking stream connectivity: {stream_url}")
            
            # Create video capture
            cap = cv2.VideoCapture(stream_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Try to open the stream
            if not cap.isOpened():
                return False, "Failed to open video capture"
            
            # Wait for the first frame with timeout
            while time.time() - start_time < timeout:
                ret, frame = cap.read()
                if ret and frame is not None:
                    logger.info(f"Stream {stream_url} is accessible")
                    return True, None
                time.sleep(0.1)
            
            return False, f"Timeout waiting for frame (>{timeout}s)"
            
        except Exception as e:
            error_msg = f"Exception during stream check: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        finally:
            if cap is not None:
                cap.release()

    @staticmethod
    async def check_stream_connectivity_async(stream_url: str, timeout: float = 5.0) -> Tuple[bool, Optional[str]]:
        """
        Async version of stream connectivity check
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            StreamChecker.check_stream_connectivity, 
            stream_url, 
            timeout
        )
