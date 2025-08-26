"""
Command line interface for RexTracking
"""

import argparse

from app.core.pipeline import Pipeline


def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="yolov8l",
        help="Model name which should be used for task: yolov8n, yolov8m, yolov8l, yolov8x")
    parser.add_argument("--ip", default="127.0.0.1",
        help="The ip of the OSC server from TouchDesigner")
    parser.add_argument("--port", type=int, default=5005,
        help="The port of the OSC server is listening on from TouchDesigner")
    parser.add_argument("--stream", default=r"D:\ultralytics\video-example.mp4",
        help="Video stream URL for inference (RTSP)")

    parser.add_argument("--debug", action='store_true',
        help="Print debug output for each frame")
    parser.add_argument("--show", action='store_true',
        help="Show separate window with frames tracking")
    
    parser.add_argument("--confidence", type=float, default=0.1,
        help="Minimum model confidence for object tracking (range from 0.0 to 1.0). Default: 0.1")
    parser.add_argument("--tracking_period", type=int, default=1,
        help="Number of frames between new trackings. Default: 1 (each frame with tracking)")
    parser.add_argument("--objects_max", type=int, default=10,
        help="Maximum objects detections. Default: 10")
    parser.add_argument("--objects_filter", default="",
        help="Filter objects by class name. Work when --single_class is not defined.")
    parser.add_argument("--object_persistance", type=int, default=10,
        help="Filter objects base on time (in ms). Default: 10 ms")
    parser.add_argument("--timeout", type=int, default=5,
        help="Timeout for connection retries (in seconds). Default: 5")
    parser.add_argument("--single_class", type=int, default=-1,
        help="Objects class to detect (ignore all other objects). Default: 0 - person")

    args = parser.parse_args()

    # Create and run pipeline
    pipeline = Pipeline(
        stream=args.stream,
        model=args.model,
        ip=args.ip,
        port=args.port,
        confidence=args.confidence,
        tracking_period=args.tracking_period,
        objects_max=args.objects_max,
        objects_filter=args.objects_filter,
        object_persistance=args.object_persistance,
        timeout=args.timeout,
        single_class=args.single_class,
        debug=args.debug,
        show=args.show
    )
    
    pipeline.run()


if __name__ == "__main__":
    main()
