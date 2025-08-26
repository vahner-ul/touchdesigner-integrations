# RexTracking System - Динамическое управление

Система трекинга объектов с веб-интерфейсом для динамического управления камерами.

## Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │   FastAPI       │    │   Service       │
│   (React/Next)  │◄──►│   Server        │◄──►│   Manager       │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Camera        │    │   Tracking      │
                       │   Workers       │    │   Pipelines     │
                       │                 │    │                 │
                       └─────────────────┘    └─────────────────┘
```

## Быстрый старт

### 1. Запуск API сервера

```bash
# Переходим в директорию проекта
cd touchdesigner-integrations/tracking

# Устанавливаем зависимости
pip install -r requirements.txt

# Запускаем API сервер
python run_api_only.py
```

API сервер запустится на `http://localhost:8080`

### 2. Запуск веб-интерфейса

```bash
# В новой терминале, переходим в директорию веб-интерфейса
cd touchdesigner-integrations/tracking/web

# Устанавливаем зависимости
npm install

# Запускаем веб-интерфейс
npm run dev
```

Веб-интерфейс будет доступен на `http://localhost:3000`

## Использование

### 1. Управление сервисом

1. Откройте веб-интерфейс в браузере
2. Перейдите на вкладку "System"
3. Нажмите "Start Service" для запуска сервиса трекинга
4. Сервис запустится в фоновом режиме без камер

### 2. Добавление камер

1. Перейдите на вкладку "Cameras"
2. Нажмите "Add Camera"
3. Заполните форму:
   - **Camera ID**: уникальный идентификатор (например, `cam1`)
   - **Name**: название камеры (например, `Front Door`)
   - **Stream URL**: RTSP URL камеры (например, `rtsp://user:pass@192.168.1.100/stream`)
4. Нажмите "Add Camera"

### 3. Управление камерами

- **Start**: запуск трекинга на камере
- **Stop**: остановка трекинга
- **Restart**: перезапуск камеры
- **Remove**: удаление камеры из системы

### 4. Мониторинг

- **Service Status**: статус сервиса трекинга
- **Cameras Running**: количество активных камер
- **Cameras with Issues**: камеры с ошибками
- **Real-time metrics**: FPS, задержка, количество объектов

## API Endpoints

### Сервис
- `GET /api/v1/service/status` - статус сервиса
- `POST /api/v1/service/start` - запуск сервиса
- `POST /api/v1/service/stop` - остановка сервиса

### Камеры
- `GET /api/v1/cameras` - список камер
- `POST /api/v1/cameras` - добавление камеры
- `DELETE /api/v1/cameras/{id}` - удаление камеры
- `POST /api/v1/cameras/{id}/start` - запуск камеры
- `POST /api/v1/cameras/{id}/stop` - остановка камеры
- `POST /api/v1/cameras/{id}/restart` - перезапуск камеры

### Метрики
- `GET /api/v1/metrics` - все метрики
- `GET /api/v1/metrics/system` - системные метрики
- `GET /api/v1/metrics/cameras` - метрики камер

### Конфигурация
- `GET /api/v1/config` - текущая конфигурация
- `PUT /api/v1/config` - обновление конфигурации
- `POST /api/v1/config/reload` - перезагрузка конфигурации

## Конфигурация

### config.yaml

```yaml
service:
  listen: 0.0.0.0
  port: 8080
  log_level: info
  device: auto
  models_dir: ./models

tracking:
  model: yolov8l
  confidence: 0.25
  classes: []
  objects_max: 10
  object_persistence_ms: 50
  period_frames: 1

osc:
  host: 127.0.0.1
  port: 5005
  address_prefix: /
  channel_format: p{index}_{axis}

cameras:
  - id: cam1
    name: Example Camera
    stream: rtsp://user:pass@host/stream
    enabled: false  # По умолчанию отключена
    show_preview: false
    roi: null
    classes_filter: []
    override:
      confidence: 0.35
```

## Особенности

### Фоновый режим работы
- Сервис запускается без камер
- Камеры добавляются динамически через веб-интерфейс
- Автоматическое переподключение при ошибках

### Горячая перезагрузка
- Изменение конфигурации без перезапуска
- Добавление/удаление камер в runtime
- Обновление настроек трекинга

### Мониторинг
- Real-time метрики камер
- Системные ресурсы (CPU, память)
- Логирование ошибок и событий

### Безопасность
- Валидация конфигурации
- Обработка ошибок RTSP
- Graceful shutdown

## Troubleshooting

### Сервис не запускается
1. Проверьте логи: `python run_api_only.py --log-level debug`
2. Убедитесь, что порт 8080 свободен
3. Проверьте права доступа к файлам

### Камера не подключается
1. Проверьте RTSP URL
2. Убедитесь, что камера доступна по сети
3. Проверьте логи в веб-интерфейсе

### Низкая производительность
1. Уменьшите `period_frames` в конфигурации
2. Используйте более легкую модель (yolov8n вместо yolov8l)
3. Проверьте системные ресурсы

## Разработка

### Структура проекта
```
tracking/
├── app/
│   ├── api/           # FastAPI endpoints
│   ├── config/        # Конфигурация
│   ├── core/          # Основные компоненты
│   └── service/       # Управление сервисом
├── web/               # React веб-интерфейс
├── config.yaml        # Конфигурация
└── run_api_only.py    # Скрипт запуска
```

### Добавление новых функций
1. Создайте endpoint в `app/api/routes/`
2. Добавьте метод в `ServiceManager`
3. Обновите веб-интерфейс
4. Протестируйте через API docs: `http://localhost:8080/docs`

## Лицензия

MIT License
