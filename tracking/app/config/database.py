"""
SQLite database for configuration storage
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from .schema import AppConfig, CameraConfig, ServiceConfig, TrackingConfig, OSCConfig


class ConfigDatabase:
    """SQLite database for storing application configuration"""
    
    def __init__(self, db_path: str = "config/settings.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cameras (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    stream TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    show_preview INTEGER DEFAULT 0,
                    roi TEXT,
                    classes_filter TEXT,
                    override TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS service_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    listen TEXT DEFAULT '0.0.0.0',
                    port INTEGER DEFAULT 8080,
                    log_level TEXT DEFAULT 'info',
                    device TEXT DEFAULT 'auto',
                    models_dir TEXT DEFAULT './models',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracking_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    model TEXT DEFAULT 'yolov8l',
                    confidence REAL DEFAULT 0.25,
                    classes TEXT DEFAULT '[]',
                    objects_max INTEGER DEFAULT 10,
                    object_persistence_ms INTEGER DEFAULT 50,
                    period_frames INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS osc_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    host TEXT DEFAULT '127.0.0.1',
                    port INTEGER DEFAULT 5005,
                    address_prefix TEXT DEFAULT '/',
                    channel_format TEXT DEFAULT 'p{index}_{axis}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица метаданных настроек для веб-интерфейса
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_table TEXT NOT NULL,
                    config_field TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    description TEXT,
                    control_type TEXT NOT NULL,
                    is_editable INTEGER DEFAULT 1,
                    is_visible INTEGER DEFAULT 1,
                    validation_rules TEXT,
                    default_value TEXT,
                    options TEXT,
                    category TEXT DEFAULT 'general',
                    order_index INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(config_table, config_field)
                )
            """)
            
            # Insert default configs if they don't exist
            conn.execute("""
                INSERT OR IGNORE INTO service_config (id) VALUES (1)
            """)
            conn.execute("""
                INSERT OR IGNORE INTO tracking_config (id) VALUES (1)
            """)
            conn.execute("""
                INSERT OR IGNORE INTO osc_config (id) VALUES (1)
            """)
            
            # Insert default settings metadata
            self._insert_default_settings_metadata(conn)
            
            conn.commit()
    
    def _insert_default_settings_metadata(self, conn):
        """Insert default settings metadata for web interface"""
        default_metadata = [
            # Service Config
            ('service_config', 'port', 'Service Port', 'Port for the web API server', 'number', 1, 1, '{"min": 1, "max": 65535}', '8080', None, 'service', 1),
            ('service_config', 'log_level', 'Log Level', 'Logging level for the application', 'select', 1, 1, '{"options": ["debug", "info", "warning", "error"]}', 'info', '["debug", "info", "warning", "error"]', 'service', 2),
            ('service_config', 'device', 'Inference Device', 'Device for AI model inference', 'select', 1, 1, '{"options": ["auto", "cpu", "cuda:0", "cuda:1"]}', 'auto', '["auto", "cpu", "cuda:0", "cuda:1"]', 'service', 3),
            ('service_config', 'models_dir', 'Models Directory', 'Directory containing YOLO models', 'text', 1, 1, '{"pattern": "^[a-zA-Z0-9./_-]+$"}', './models', None, 'service', 4),
            
            # Tracking Config
            ('tracking_config', 'model', 'YOLO Model', 'YOLO model to use for object detection', 'select', 1, 1, '{"options": ["yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x"]}', 'yolov8l', '["yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x"]', 'tracking', 1),
            ('tracking_config', 'confidence', 'Confidence Threshold', 'Minimum confidence for object detection (0.0-1.0)', 'slider', 1, 1, '{"min": 0.0, "max": 1.0, "step": 0.05}', '0.25', None, 'tracking', 2),
            ('tracking_config', 'objects_max', 'Max Objects', 'Maximum number of objects to track simultaneously', 'number', 1, 1, '{"min": 1, "max": 100}', '10', None, 'tracking', 3),
            ('tracking_config', 'object_persistence_ms', 'Object Persistence (ms)', 'How long to keep tracking objects after detection (milliseconds)', 'number', 1, 1, '{"min": 0, "max": 10000}', '50', None, 'tracking', 4),
            ('tracking_config', 'period_frames', 'Frame Period', 'Process every N-th frame (1 = every frame)', 'number', 1, 1, '{"min": 1, "max": 30}', '1', None, 'tracking', 5),
            
            # OSC Config
            ('osc_config', 'host', 'OSC Host', 'OSC server host address', 'text', 1, 1, '{"pattern": "^[0-9.]+$"}', '127.0.0.1', None, 'osc', 1),
            ('osc_config', 'port', 'OSC Port', 'OSC server port number', 'number', 1, 1, '{"min": 1, "max": 65535}', '5005', None, 'osc', 2),
            ('osc_config', 'address_prefix', 'OSC Address Prefix', 'Prefix for OSC message addresses', 'text', 1, 1, '{"pattern": "^/[a-zA-Z0-9/_]*$"}', '/', None, 'osc', 3),
            ('osc_config', 'channel_format', 'Channel Format', 'Format for OSC channel names', 'text', 1, 1, '{"pattern": "^[a-zA-Z0-9_{}]+$"}', 'p{index}_{axis}', None, 'osc', 4),
        ]
        
        for metadata in default_metadata:
            conn.execute("""
                INSERT OR IGNORE INTO settings_metadata 
                (config_table, config_field, display_name, description, control_type, is_editable, is_visible, validation_rules, default_value, options, category, order_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, metadata)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def get_all_cameras(self) -> List[CameraConfig]:
        """Get all cameras from database"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cameras ORDER BY name")
            cameras = []
            for row in cursor.fetchall():
                camera_data = dict(row)
                # Parse JSON fields
                if camera_data['roi']:
                    camera_data['roi'] = json.loads(camera_data['roi'])
                if camera_data['classes_filter']:
                    camera_data['classes_filter'] = json.loads(camera_data['classes_filter'])
                else:
                    camera_data['classes_filter'] = []  # Ensure empty list instead of None
                if camera_data['override']:
                    camera_data['override'] = json.loads(camera_data['override'])
                
                cameras.append(CameraConfig(**camera_data))
            return cameras
    
    def get_camera(self, camera_id: str) -> Optional[CameraConfig]:
        """Get camera by ID"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            camera_data = dict(row)
            # Parse JSON fields
            if camera_data['roi']:
                camera_data['roi'] = json.loads(camera_data['roi'])
            if camera_data['classes_filter']:
                camera_data['classes_filter'] = json.loads(camera_data['classes_filter'])
            else:
                camera_data['classes_filter'] = []  # Ensure empty list instead of None
            if camera_data['override']:
                camera_data['override'] = json.loads(camera_data['override'])
            
            return CameraConfig(**camera_data)
    
    def save_camera(self, camera: CameraConfig) -> None:
        """Save camera to database"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cameras 
                (id, name, stream, enabled, show_preview, roi, classes_filter, override, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                camera.id,
                camera.name,
                camera.stream,
                camera.enabled,
                camera.show_preview,
                json.dumps(camera.roi) if camera.roi else None,
                json.dumps(camera.classes_filter) if camera.classes_filter else None,
                json.dumps(camera.override.model_dump()) if camera.override else None
            ))
            conn.commit()
    
    def delete_camera(self, camera_id: str) -> bool:
        """Delete camera by ID"""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_service_config(self) -> ServiceConfig:
        """Get service configuration"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM service_config WHERE id = 1")
            row = cursor.fetchone()
            return ServiceConfig(**dict(row))
    
    def save_service_config(self, config: ServiceConfig) -> None:
        """Save service configuration"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE service_config SET
                listen = ?, port = ?, log_level = ?, device = ?, models_dir = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (config.listen, config.port, config.log_level, config.device, config.models_dir))
            conn.commit()
    
    def get_tracking_config(self) -> TrackingConfig:
        """Get tracking configuration"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tracking_config WHERE id = 1")
            row = cursor.fetchone()
            data = dict(row)
            data['classes'] = json.loads(data['classes'])
            return TrackingConfig(**data)
    
    def save_tracking_config(self, config: TrackingConfig) -> None:
        """Save tracking configuration"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE tracking_config SET
                model = ?, confidence = ?, classes = ?, objects_max = ?, 
                object_persistence_ms = ?, period_frames = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (
                config.model, config.confidence, json.dumps(config.classes),
                config.objects_max, config.object_persistence_ms, config.period_frames
            ))
            conn.commit()
    
    def get_osc_config(self) -> OSCConfig:
        """Get OSC configuration"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM osc_config WHERE id = 1")
            row = cursor.fetchone()
            return OSCConfig(**dict(row))
    
    def save_osc_config(self, config: OSCConfig) -> None:
        """Save OSC configuration to database"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE osc_config SET
                    host = ?, port = ?, address_prefix = ?, channel_format = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (config.host, config.port, config.address_prefix, config.channel_format))
            conn.commit()

    # Settings metadata methods
    def get_settings_metadata(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get settings metadata for web interface"""
        with self._get_connection() as conn:
            if category:
                cursor = conn.execute("""
                    SELECT * FROM settings_metadata 
                    WHERE is_visible = 1 AND category = ?
                    ORDER BY order_index, display_name
                """, (category,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM settings_metadata 
                    WHERE is_visible = 1
                    ORDER BY category, order_index, display_name
                """)
            
            metadata = []
            for row in cursor.fetchall():
                item = dict(row)
                # Parse JSON fields with error handling
                if item.get('validation_rules'):
                    try:
                        item['validation_rules'] = json.loads(item['validation_rules'])
                    except json.JSONDecodeError:
                        item['validation_rules'] = {}
                if item.get('options'):
                    try:
                        item['options'] = json.loads(item['options'])
                    except json.JSONDecodeError:
                        item['options'] = []
                metadata.append(item)
            
            return metadata

    def get_setting_metadata(self, config_table: str, config_field: str) -> Optional[Dict[str, Any]]:
        """Get metadata for specific setting"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM settings_metadata 
                WHERE config_table = ? AND config_field = ?
            """, (config_table, config_field))
            
            row = cursor.fetchone()
            if row:
                item = dict(row)
                # Parse JSON fields with error handling
                if item.get('validation_rules'):
                    try:
                        item['validation_rules'] = json.loads(item['validation_rules'])
                    except json.JSONDecodeError:
                        item['validation_rules'] = {}
                if item.get('options'):
                    try:
                        item['options'] = json.loads(item['options'])
                    except json.JSONDecodeError:
                        item['options'] = []
                return item
            return None

    def update_setting_metadata(self, config_table: str, config_field: str, metadata: Dict[str, Any]) -> None:
        """Update setting metadata"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE settings_metadata SET
                    display_name = ?, description = ?, control_type = ?, is_editable = ?, is_visible = ?,
                    validation_rules = ?, default_value = ?, options = ?, category = ?, order_index = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE config_table = ? AND config_field = ?
            """, (
                metadata.get('display_name'),
                metadata.get('description'),
                metadata.get('control_type'),
                metadata.get('is_editable', 1),
                metadata.get('is_visible', 1),
                json.dumps(metadata.get('validation_rules', {})) if metadata.get('validation_rules') else None,
                metadata.get('default_value'),
                json.dumps(metadata.get('options', [])) if metadata.get('options') else None,
                metadata.get('category', 'general'),
                metadata.get('order_index', 0),
                config_table,
                config_field
            ))
            conn.commit()

    def get_settings_categories(self) -> List[str]:
        """Get list of available settings categories"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT category FROM settings_metadata 
                WHERE is_visible = 1
                ORDER BY category
            """)
            return [row['category'] for row in cursor.fetchall()]

    def get_current_settings_values(self) -> Dict[str, Any]:
        """Get current values of all configurable settings"""
        with self._get_connection() as conn:
            # Get service config
            service_cursor = conn.execute("SELECT * FROM service_config WHERE id = 1")
            service_row = service_cursor.fetchone()
            service_config = dict(service_row) if service_row else {}
            
            # Get tracking config
            tracking_cursor = conn.execute("SELECT * FROM tracking_config WHERE id = 1")
            tracking_row = tracking_cursor.fetchone()
            tracking_config = dict(tracking_row) if tracking_row else {}
            
            # Get OSC config
            osc_cursor = conn.execute("SELECT * FROM osc_config WHERE id = 1")
            osc_row = osc_cursor.fetchone()
            osc_config = dict(osc_row) if osc_row else {}
            
            # Parse JSON fields
            if service_config.get('classes'):
                service_config['classes'] = json.loads(service_config['classes'])
            if tracking_config.get('classes'):
                tracking_config['classes'] = json.loads(tracking_config['classes'])
            
            return {
                'service': service_config,
                'tracking': tracking_config,
                'osc': osc_config
            }

    def update_setting_value(self, config_table: str, config_field: str, value: Any) -> None:
        """Update a single setting value"""
        with self._get_connection() as conn:
            # Convert value to appropriate format
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            
            conn.execute(f"""
                UPDATE {config_table} SET
                    {config_field} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (value,))
            conn.commit()

    def get_settings_for_ui(self) -> Dict[str, Any]:
        """Get settings metadata and current values for web interface"""
        metadata = self.get_settings_metadata()
        current_values = self.get_current_settings_values()
        
        # Group metadata by category
        categories = {}
        for item in metadata:
            category = item['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        # Add current values to metadata
        for category_items in categories.values():
            for item in category_items:
                table = item['config_table']
                field = item['config_field']
                
                if table in current_values and field in current_values[table]:
                    item['current_value'] = current_values[table][field]
                else:
                    item['current_value'] = item.get('default_value')
        
        return {
            'categories': categories,
            'current_values': current_values
        }
    
    def get_full_config(self) -> AppConfig:
        """Get complete application configuration"""
        return AppConfig(
            service=self.get_service_config(),
            tracking=self.get_tracking_config(),
            osc=self.get_osc_config(),
            cameras=self.get_all_cameras()
        )
    
    def save_full_config(self, config: AppConfig) -> None:
        """Save complete application configuration"""
        self.save_service_config(config.service)
        self.save_tracking_config(config.tracking)
        self.save_osc_config(config.osc)
        
        # Save cameras
        for camera in config.cameras:
            self.save_camera(camera)
    
    def import_from_yaml(self, yaml_config: AppConfig) -> None:
        """Import configuration from YAML config object"""
        self.save_full_config(yaml_config)
