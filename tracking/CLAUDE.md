# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RexTracking is a modular computer vision system that processes IP camera streams using YOLO models and sends tracking data to TouchDesigner via OSC. The system consists of a Python FastAPI backend and a Next.js React frontend for dynamic camera management.

## Architecture

### Core Components

- **Backend**: Python FastAPI server (`app/`) with modular architecture
- **Frontend**: Next.js React web interface (`web/`) with real-time monitoring
- **Communication**: RESTful API + WebSocket for live telemetry
- **Processing Pipeline**: RTSP capture → YOLO inference → OSC output

### Key Data Flow

```
RTSP Camera → CaptureThread → Tracker (YOLO) → ObjectsBuffer → OSCWorker → TouchDesigner
                ↓
              Metrics Collection → FastAPI → WebSocket → React UI
```

## Development Commands

### Backend Setup
```bash
# Install Python dependencies (including new typer dependency)
python -m pip install -r requirements.txt

# Start API server only (recommended for development)
python main.py server

# Alternative: Start full system (API + web)
python main.py system
```

### Frontend Setup
```bash
cd web
npm install
npm run dev
```

### Testing and Validation
```bash
# Run all tests
python main.py test --all

# Test module imports only
python main.py test --imports

# Test service functionality only
python main.py test --service

# Single camera CLI mode
python main.py cli --stream rtsp://camera/stream

# Multi-camera service mode
python main.py service --config config/multi_cameras.yaml

# Validate configuration
python -c "from app.config.loader import ConfigLoader; ConfigLoader('config.yaml').load()"
```

## Core System Architecture

### Backend Structure (`app/`)

**Core Processing (`app/core/`)**:
- `pipeline.py` - Main processing orchestrator combining capture→tracking→OSC
- `capture.py` - `CaptureThread` handles RTSP streams with reconnection logic
- `tracker.py` - YOLO model wrapper with GPU/CPU auto-detection
- `osc.py` - `OSCWorker` sends formatted tracking data to TouchDesigner
- `objects_buffer.py` - Manages object persistence and slot assignment (p1, p2, etc.)

**Configuration (`app/config/`)**:
- `schema.py` - Pydantic models for configuration validation
- `loader.py` - YAML configuration loading with environment variable support

**Service Management (`app/service/`)**:
- `manager.py` - `ServiceManager` orchestrates multiple camera workers
- `metrics.py` - Real-time performance metrics collection
- `logging.py` - Centralized logging with color output

**API Layer (`app/api/`)**:
- `main.py` - FastAPI application with lifecycle management
- `routes/` - REST endpoints for cameras, config, health, metrics
- `websockets.py` - Real-time telemetry and preview streams

### Frontend Structure (`web/`)

**Core App**:
- `app/layout.tsx` - Root layout with font configuration
- `app/page.tsx` - Main dashboard with tabbed interface
- `app/dashboard/page.tsx` - System overview and camera management

**Components**:
- `SystemStatus.tsx` - Service control and status monitoring
- `CameraControl.tsx` - Individual camera management
- `NetworkScanner.tsx` - Automatic camera discovery

**API Integration**:
- `lib/api.ts` - Comprehensive TypeScript API client with error handling
- WebSocket clients for real-time telemetry, preview, and object data

## Configuration System

### Main Configuration (`config.yaml`)

The system uses a hierarchical configuration structure:

```yaml
service:          # API server settings
tracking:         # Global YOLO tracking parameters  
osc:             # TouchDesigner output settings
cameras:         # Array of camera definitions with per-camera overrides
```

**Key Configuration Points**:
- `tracking.model` - YOLO model selection (yolov8n/s/m/l/x)
- `tracking.confidence` - Global detection threshold
- `osc.channel_format` - TouchDesigner channel naming (e.g., `p{index}_{axis}`)
- `cameras[].override` - Per-camera parameter overrides

## Service Management Patterns

### ServiceManager Lifecycle
1. **Initialization** - Load config, create camera workers (but don't start)
2. **Start** - Begin processing for enabled cameras in separate threads
3. **Runtime** - Dynamic camera add/remove via API
4. **Stop** - Graceful shutdown of all camera workers

### Camera Worker States
- `stopped` - Camera not processing
- `starting` - Connection being established
- `running` - Active processing
- `error` - Connection/processing failure
- `reconnecting` - Automatic recovery attempt

## API Architecture

### REST Endpoints
- `/api/v1/service/*` - Service lifecycle control
- `/api/v1/cameras/*` - Camera CRUD operations and control
- `/api/v1/metrics/*` - Performance and system metrics
- `/api/v1/config/*` - Configuration management

### WebSocket Streams
- `/ws/telemetry` - Real-time camera metrics and system status
- `/ws/preview` - JPEG frame previews (when enabled)
- `/ws/objects` - Live tracking data stream

## Development Patterns

### Adding New Camera Features
1. Update `app/config/schema.py` with new Pydantic models
2. Modify `app/core/pipeline.py` to use new parameters
3. Add API endpoints in `app/api/routes/cameras.py`
4. Update frontend components in `web/components/`

### Configuration Changes
1. Modify schema in `app/config/schema.py`
2. Update default config in `config.yaml`
3. Add validation logic in `app/config/loader.py`
4. Test with `python test_service.py`

### Performance Monitoring
- Use `app/service/metrics.py` for new metrics
- Real-time data flows through WebSocket to frontend
- System metrics include CPU, memory, camera FPS, processing latency

## Common Troubleshooting

### Camera Connection Issues
- Check RTSP URL format and credentials in camera configuration
- Verify network connectivity and firewall settings
- Monitor error logs in service manager for reconnection attempts

### Performance Problems
- Adjust `tracking.period_frames` to process every N-th frame
- Use lighter YOLO models (yolov8n vs yolov8l) for better performance
- Check system metrics for CPU/memory bottlenecks

### TouchDesigner Integration
- Verify OSC host/port settings match TouchDesigner configuration
- Check `osc.channel_format` matches expected TouchDesigner channel names
- Monitor OSC worker logs for send failures

## Entry Points

- **Unified Entry Point**: `main.py` with subcommands (server, system, cli, service, test)
- **Legacy Scripts**: Available in `bin/` directory for compatibility
- **Testing**: `python main.py test` with granular options
- **Configuration**: Default configs in `config/` directory