# RexTracking - Модульная структура

Этот проект был реорганизован в модульную структуру для создания полноценного сервиса с веб-интерфейсом.

## Структура проекта

```
tracking/
├── app/
│   ├── core/           # Основные компоненты
│   │   ├── capture.py      # Захват видео
│   │   ├── tracker.py      # YOLO трекинг
│   │   ├── osc.py          # OSC отправка
│   │   ├── objects_buffer.py # Буфер объектов
│   │   └── pipeline.py     # Основной пайплайн
│   ├── config/         # Конфигурация
│   │   ├── schema.py       # Pydantic схемы
│   │   └── loader.py       # Загрузчик YAML
│   ├── service/        # ✅ Управление сервисом
│   │   ├── manager.py      # ✅ Менеджер камер
│   │   ├── metrics.py      # ✅ Сбор метрик
│   │   └── logging.py      # ✅ Логирование
│   ├── api/            # ⏳ API endpoints
│   └── __init__.py
├── web/               # ⏳ Веб-интерфейс
├── cli.py             # ✅ Командная строка (одна камера)
├── service_cli.py     # ✅ Сервис CLI (несколько камер)
├── config.yaml        # ✅ Конфигурация (одна камера)
├── config_multi_cameras.yaml # ✅ Конфигурация (несколько камер)
├── test_service.py    # ✅ Тест менеджера сервиса
├── rextracking.py     # ✅ Старый файл (для совместимости)
└── README.md
```

## Компоненты

### Core модули

- **`capture.py`** - `CaptureThread` для захвата видео потоков
- **`tracker.py`** - `Tracker` для YOLO инференса
- **`osc.py`** - `OSCWorker` для отправки данных в TouchDesigner
- **`objects_buffer.py`** - `ObjectsBuffer` для управления трекингом объектов
- **`pipeline.py`** - `Pipeline` объединяет все компоненты

### Конфигурация

- **`schema.py`** - Pydantic модели для валидации конфигурации
- **`loader.py`** - Загрузка и сохранение YAML конфигурации

### Сервис (новое!)

- **`manager.py`** - `ServiceManager` для управления несколькими камерами
- **`metrics.py`** - `MetricsCollector` для сбора производительности
- **`logging.py`** - Централизованное логирование с цветами

## Использование

### Единая точка входа (новое!)

```bash
# API сервер (рекомендуется для разработки)
python main.py server

# Полная система (API + веб-интерфейс)
python main.py system

# CLI для одной камеры
python main.py cli --stream rtsp://camera/stream --model yolov8l

# Сервис для нескольких камер
python main.py service --config config/multi_cameras.yaml

# Тестирование
python main.py test --all
```

### Программно

```python
from app.core.pipeline import Pipeline

# Одна камера
pipeline = Pipeline(
    stream="rtsp://camera/stream",
    model="yolov8l",
    ip="127.0.0.1",
    port=5005
)
pipeline.run()

# Несколько камер через сервис
from app.service.manager import ServiceManager
from app.config.loader import ConfigLoader

config = ConfigLoader("config.yaml").load()
service = ServiceManager(config)
service.start()
```

### Конфигурация

```python
from app.config.loader import ConfigLoader

loader = ConfigLoader("config_multi_cameras.yaml")
config = loader.load()

# Использование конфигурации
for camera in config.cameras:
    if camera.enabled:
        print(f"Camera {camera.id}: {camera.name}")
        print(f"  Stream: {camera.stream}")
        print(f"  Classes: {camera.classes_filter}")
        print(f"  Confidence: {camera.override.confidence or config.tracking.confidence}")
```

## Менеджер сервиса

### Возможности

1. **Управление несколькими камерами** - каждая камера в отдельном потоке
2. **Отказоустойчивость** - автоматическое переподключение при ошибках
3. **Мониторинг** - сбор метрик производительности каждой камеры
4. **Горячая перезагрузка** - изменение настроек без перезапуска
5. **Логирование** - централизованные логи с цветами

### Статусы камер

- `stopped` - камера остановлена
- `starting` - камера запускается
- `running` - камера работает
- `error` - ошибка в работе камеры
- `reconnecting` - переподключение после ошибки

### Метрики

Система собирает метрики для каждой камеры:
- FPS входящий и обработанный
- Задержка обработки
- Количество объектов
- Время работы
- Количество ошибок и переподключений

### Пример конфигурации с несколькими камерами

```yaml
cameras:
  - id: entrance
    name: Входная дверь
    stream: rtsp://user:pass@192.168.1.100:554/stream1
    enabled: true
    classes_filter: ["person"]
    override:
      confidence: 0.35

  - id: parking
    name: Парковка
    stream: rtsp://user:pass@192.168.1.101:554/stream1
    enabled: true
    classes_filter: ["car", "person"]
    override:
      confidence: 0.3

  - id: lobby
    name: Холл
    stream: rtsp://user:pass@192.168.1.102:554/stream1
    enabled: false  # Отключена по умолчанию
    show_preview: true
    roi: [100, 100, 800, 600]  # Область интереса
```

## Тестирование

```bash
# Все тесты
python main.py test --all

# Тест импортов модулей  
python main.py test --imports

# Тест менеджера сервиса
python main.py test --service
```

## Следующие шаги

1. **API слой** - FastAPI для REST endpoints
2. **Веб-интерфейс** - React или Jinja2 шаблоны
3. **Горячая перезагрузка** - изменение настроек без перезапуска
4. **Метрики Prometheus** - интеграция с системами мониторинга

## Зависимости

Основные зависимости:
- `opencv-python`
- `ultralytics`
- `torch`
- `python-osc`
- `termcolor`

Новые зависимости для модульной структуры:
- `pydantic` - валидация конфигурации
- `pyyaml` - работа с YAML файлами

## Архитектура менеджера сервиса

```
ServiceManager
├── CameraWorker (entrance)
│   ├── Pipeline
│   │   ├── CaptureThread
│   │   ├── Tracker
│   │   └── OSCWorker
│   └── Error handling & reconnection
├── CameraWorker (parking)
│   └── ...
├── CameraWorker (lobby)
│   └── ...
└── MetricsCollector
    ├── SystemMetrics
    └── CameraMetrics (per camera)
```

Каждая камера работает в своем потоке, что обеспечивает:
- Изоляцию ошибок (падение одной камеры не влияет на другие)
- Параллельную обработку
- Независимое управление жизненным циклом
