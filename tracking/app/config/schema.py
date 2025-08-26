"""
Configuration schema using Pydantic
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field


class ServiceConfig(BaseModel):
    """Service configuration"""
    listen: str = Field(default="0.0.0.0", description="Service listen address")
    port: int = Field(default=8080, description="Service port")
    log_level: str = Field(default="info", description="Logging level")
    device: str = Field(default="auto", description="Device for inference: auto|cuda:0|cpu")
    models_dir: str = Field(default="./models", description="Directory with YOLO models")


class TrackingConfig(BaseModel):
    """Tracking configuration"""
    model: str = Field(default="yolov8l", description="YOLO model name")
    confidence: float = Field(default=0.25, ge=0.0, le=1.0, description="Confidence threshold")
    classes: List[int] = Field(default=[], description="Classes to detect (empty = all)")
    objects_max: int = Field(default=10, ge=1, description="Maximum objects to track")
    object_persistence_ms: int = Field(default=50, ge=0, description="Object persistence time in ms")
    period_frames: int = Field(default=1, ge=1, description="Process every N-th frame")


class OSCConfig(BaseModel):
    """OSC output configuration"""
    host: str = Field(default="127.0.0.1", description="OSC server host")
    port: int = Field(default=5005, description="OSC server port")
    address_prefix: str = Field(default="/", description="OSC address prefix")
    channel_format: str = Field(default="p{index}_{axis}", description="OSC channel format")


class CameraOverride(BaseModel):
    """Camera-specific overrides"""
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    classes_filter: Optional[List[Union[str, int]]] = Field(default=None)
    roi: Optional[List[int]] = Field(default=None, description="Region of interest [x1, y1, x2, y2]")


class CameraConfig(BaseModel):
    """Camera configuration"""
    id: str = Field(description="Unique camera ID")
    name: str = Field(description="Camera display name")
    stream: str = Field(description="Video stream URL")
    enabled: bool = Field(default=True, description="Camera enabled state")
    show_preview: bool = Field(default=False, description="Show preview window")
    roi: Optional[List[int]] = Field(default=None, description="Region of interest [x1, y1, x2, y2]")
    classes_filter: List[Union[str, int]] = Field(default=[], description="Filter by class names or IDs")
    override: Optional[CameraOverride] = Field(default=None, description="Camera-specific overrides")


class AppConfig(BaseModel):
    """Main application configuration"""
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    osc: OSCConfig = Field(default_factory=OSCConfig)
    cameras: List[CameraConfig] = Field(default=[], description="List of cameras")
