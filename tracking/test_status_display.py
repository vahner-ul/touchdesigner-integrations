#!/usr/bin/env python3
"""Test the status display directly"""

import time
from app.console.status_display import StatusDisplay

def test_status_display():
    print("Testing StatusDisplay directly...")
    try:
        sd = StatusDisplay()
        print("StatusDisplay initialized")
        
        print("Starting live display for 5 seconds...")
        # Just run for a few seconds to test
        import threading
        
        def stop_after_delay():
            time.sleep(5)
            print("\nTest timeout reached, stopping...")
            # This won't work perfectly, but should demonstrate if the display works
            import os
            os._exit(0)
        
        stop_thread = threading.Thread(target=stop_after_delay, daemon=True)
        stop_thread.start()
        
        sd.run_live()
        
    except KeyboardInterrupt:
        print("\nReceived Ctrl+C, stopping test")
    except Exception as e:
        print(f"Error in status display test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_status_display()