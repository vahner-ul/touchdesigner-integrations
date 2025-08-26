"""
Configuration management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
import os

from ...service.manager import ServiceManager
from ...config.loader import ConfigLoader
from ...config.database import ConfigDatabase

router = APIRouter()

class ConfigResponse(BaseModel):
    config: Dict[str, Any]
    file_path: str
    last_modified: float

class ConfigUpdateRequest(BaseModel):
    config: Dict[str, Any]

class ConfigValidationResponse(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]

class SettingUpdateRequest(BaseModel):
    config_table: str
    config_field: str
    value: Any

class SettingsMetadataResponse(BaseModel):
    categories: Dict[str, List[Dict[str, Any]]]
    current_values: Dict[str, Any]

def get_service_manager() -> Optional[ServiceManager]:
    """Dependency для получения ServiceManager"""
    from ..main import get_service_manager
    return get_service_manager()

def get_config_loader() -> ConfigLoader:
    """Dependency для получения ConfigLoader"""
    return ConfigLoader()

def get_config_database() -> ConfigDatabase:
    """Dependency для получения ConfigDatabase"""
    return ConfigDatabase()

@router.get("/config", response_model=ConfigResponse)
async def get_config(manager: ServiceManager = Depends(get_service_manager)):
    """Получение текущей конфигурации"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Получаем конфигурацию из ServiceManager
        config_dict = manager.config.model_dump()
        
        # Получаем информацию о файле конфигурации
        config_loader = ConfigLoader()
        config_path = config_loader.get_config_path()
        
        if os.path.exists(config_path):
            last_modified = os.path.getmtime(config_path)
        else:
            last_modified = time.time()
        
        return ConfigResponse(
            config=config_dict,
            file_path=str(config_path),
            last_modified=last_modified
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@router.put("/config")
async def update_config(
    request: ConfigUpdateRequest,
    manager: ServiceManager = Depends(get_service_manager)
):
    """Обновление конфигурации"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Валидируем новую конфигурацию
        config_loader = ConfigLoader()
        try:
            # Создаем временную конфигурацию для валидации
            from ...config.schema import AppConfig
            new_config = AppConfig(**request.config)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")
        
        # Сохраняем конфигурацию в файл
        config_path = config_loader.save_config(request.config)
        
        # Обновляем конфигурацию в ServiceManager
        manager.config = new_config
        
        return {
            "message": "Configuration updated successfully",
            "file_path": str(config_path),
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")

@router.post("/config/reload")
async def reload_config(manager: ServiceManager = Depends(get_service_manager)):
    """Перезагрузка конфигурации из файла"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Перезагружаем конфигурацию
        manager.reload_config()
        
        return {
            "message": "Configuration reloaded successfully",
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload config: {str(e)}")

@router.post("/config/validate", response_model=ConfigValidationResponse)
async def validate_config(request: ConfigUpdateRequest):
    """Валидация конфигурации"""
    try:
        errors = []
        warnings = []
        
        # Пытаемся создать конфигурацию
        try:
            from ...config.schema import AppConfig
            config = AppConfig(**request.config)
        except Exception as e:
            errors.append(f"Configuration validation failed: {str(e)}")
            return ConfigValidationResponse(
                valid=False,
                errors=errors,
                warnings=warnings
            )
        
        # Проверяем камеры
        for i, camera in enumerate(config.cameras):
            # Проверяем уникальность ID
            if any(cam.id == camera.id for j, cam in enumerate(config.cameras) if i != j):
                errors.append(f"Duplicate camera ID: {camera.id}")
            
            # Проверяем RTSP URL
            if not camera.stream.startswith(('rtsp://', 'http://', 'https://', 'file://')):
                warnings.append(f"Camera {camera.id}: stream URL format may be invalid")
        
        # Проверяем настройки трекинга
        if config.tracking.confidence < 0 or config.tracking.confidence > 1:
            errors.append("Confidence must be between 0 and 1")
        
        if config.tracking.objects_max <= 0:
            errors.append("objects_max must be greater than 0")
        
        # Проверяем OSC настройки
        if config.osc.port < 1 or config.osc.port > 65535:
            errors.append("OSC port must be between 1 and 65535")
        
        return ConfigValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate config: {str(e)}")

@router.get("/config/schema")
async def get_config_schema():
    """Получение схемы конфигурации"""
    try:
        from ...config.schema import AppConfig
        
        # Получаем JSON схему из Pydantic модели
        schema = AppConfig.model_json_schema()
        
        return {
            "schema": schema,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config schema: {str(e)}")

@router.get("/config/default")
async def get_default_config():
    """Получение конфигурации по умолчанию"""
    try:
        from ...config.schema import AppConfig
        
        # Создаем конфигурацию с дефолтными значениями
        default_config = AppConfig()
        
        return {
            "config": default_config.model_dump(),
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get default config: {str(e)}")

@router.post("/config/reset")
async def reset_config(manager: ServiceManager = Depends(get_service_manager)):
    """Сброс конфигурации к значениям по умолчанию"""
    try:
        if not manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Создаем конфигурацию по умолчанию
        from ...config.schema import AppConfig
        default_config = AppConfig()
        
        # Сохраняем в файл
        config_loader = ConfigLoader()
        config_path = config_loader.save_config(default_config.model_dump())
        
        # Обновляем в ServiceManager
        manager.config = default_config
        
        return {
            "message": "Configuration reset to defaults successfully",
            "file_path": str(config_path),
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset config: {str(e)}")

@router.get("/settings", response_model=SettingsMetadataResponse)
async def get_settings_for_ui(db: ConfigDatabase = Depends(get_config_database)):
    """Получение настроек для веб-интерфейса"""
    try:
        return db.get_settings_for_ui()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")

@router.get("/settings/categories")
async def get_settings_categories(db: ConfigDatabase = Depends(get_config_database)):
    """Получение списка категорий настроек"""
    try:
        categories = db.get_settings_categories()
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings categories: {str(e)}")

@router.get("/settings/metadata")
async def get_settings_metadata(
    category: Optional[str] = None,
    db: ConfigDatabase = Depends(get_config_database)
):
    """Получение метаданных настроек"""
    try:
        metadata = db.get_settings_metadata(category)
        return {"metadata": metadata}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings metadata: {str(e)}")

@router.put("/settings/{config_table}/{config_field}")
async def update_setting(
    config_table: str,
    config_field: str,
    request: SettingUpdateRequest,
    db: ConfigDatabase = Depends(get_config_database),
    manager: ServiceManager = Depends(get_service_manager)
):
    """Обновление отдельной настройки"""
    try:
        # Validate that the setting exists and is editable
        metadata = db.get_setting_metadata(config_table, config_field)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Setting {config_table}.{config_field} not found")
        
        if not metadata.get('is_editable', True):
            raise HTTPException(status_code=403, detail=f"Setting {config_table}.{config_field} is not editable")
        
        # Validate the value based on metadata
        validation_rules = metadata.get('validation_rules', {})
        value = request.value
        
        # Type validation
        if metadata.get('control_type') == 'number':
            try:
                value = float(value) if '.' in str(value) else int(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Value must be a number for {config_field}")
        
        # Range validation
        if 'min' in validation_rules and value < validation_rules['min']:
            raise HTTPException(status_code=400, detail=f"Value must be >= {validation_rules['min']}")
        
        if 'max' in validation_rules and value > validation_rules['max']:
            raise HTTPException(status_code=400, detail=f"Value must be <= {validation_rules['max']}")
        
        # Options validation
        if 'options' in validation_rules and value not in validation_rules['options']:
            raise HTTPException(status_code=400, detail=f"Value must be one of: {validation_rules['options']}")
        
        # Update the setting in database
        db.update_setting_value(config_table, config_field, value)
        
        # Reload configuration in service manager if available
        if manager:
            try:
                manager.reload_config()
            except Exception as e:
                print(f"Warning: Failed to reload config after setting update: {e}")
        
        return {
            "message": f"Setting {config_table}.{config_field} updated successfully",
            "value": value,
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}")

@router.put("/settings/metadata/{config_table}/{config_field}")
async def update_setting_metadata(
    config_table: str,
    config_field: str,
    metadata: Dict[str, Any],
    db: ConfigDatabase = Depends(get_config_database)
):
    """Обновление метаданных настройки"""
    try:
        # Validate that the setting exists
        existing_metadata = db.get_setting_metadata(config_table, config_field)
        if not existing_metadata:
            raise HTTPException(status_code=404, detail=f"Setting {config_table}.{config_field} not found")
        
        # Update metadata
        db.update_setting_metadata(config_table, config_field, metadata)
        
        return {
            "message": f"Metadata for {config_table}.{config_field} updated successfully",
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update setting metadata: {str(e)}")

@router.post("/settings/reset")
async def reset_settings_to_defaults(
    db: ConfigDatabase = Depends(get_config_database),
    manager: ServiceManager = Depends(get_service_manager)
):
    """Сброс всех настроек к значениям по умолчанию"""
    try:
        # Get all settings metadata
        metadata = db.get_settings_metadata()
        
        # Reset each setting to its default value
        for item in metadata:
            if item.get('is_editable', True):
                default_value = item.get('default_value')
                if default_value is not None:
                    # Convert default value to appropriate type
                    if item.get('control_type') == 'number':
                        try:
                            default_value = float(default_value) if '.' in str(default_value) else int(default_value)
                        except ValueError:
                            continue
                    
                    db.update_setting_value(item['config_table'], item['config_field'], default_value)
        
        # Reload configuration in service manager if available
        if manager:
            try:
                manager.reload_config()
            except Exception as e:
                print(f"Warning: Failed to reload config after settings reset: {e}")
        
        return {
            "message": "All settings reset to defaults successfully",
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset settings: {str(e)}")

@router.post("/settings/validate")
async def validate_setting_value(
    request: SettingUpdateRequest,
    db: ConfigDatabase = Depends(get_config_database)
):
    """Валидация значения настройки"""
    try:
        # Get setting metadata
        metadata = db.get_setting_metadata(request.config_table, request.config_field)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Setting {request.config_table}.{request.config_field} not found")
        
        validation_rules = metadata.get('validation_rules', {})
        value = request.value
        errors = []
        warnings = []
        
        # Type validation
        if metadata.get('control_type') == 'number':
            try:
                value = float(value) if '.' in str(value) else int(value)
            except ValueError:
                errors.append(f"Value must be a number for {request.config_field}")
        
        # Range validation
        if 'min' in validation_rules and value < validation_rules['min']:
            errors.append(f"Value must be >= {validation_rules['min']}")
        
        if 'max' in validation_rules and value > validation_rules['max']:
            errors.append(f"Value must be <= {validation_rules['max']}")
        
        # Options validation
        if 'options' in validation_rules and value not in validation_rules['options']:
            errors.append(f"Value must be one of: {validation_rules['options']}")
        
        # Pattern validation for text fields
        if metadata.get('control_type') == 'text' and 'pattern' in validation_rules:
            import re
            if not re.match(validation_rules['pattern'], str(value)):
                errors.append(f"Value does not match required pattern")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "value": value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate setting: {str(e)}")
