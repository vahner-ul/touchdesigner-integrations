# RexTracking Web Interface

Next.js-based web interface for the RexTracking computer vision system.

## Features

- **Real-time Dashboard**: Monitor camera status, service health, and system metrics
- **Camera Management**: Add, remove, and control individual cameras
- **Network Scanner**: Automatically discover IP cameras on the network
- **System Control**: Start/stop the tracking service
- **Live Telemetry**: Real-time updates via WebSocket connections

## Getting Started

### Prerequisites

Make sure the RexTracking API server is running:

```bash
# From the root tracking directory
python main.py server
```

### Development Server

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to access the dashboard.

## Architecture

- **Framework**: Next.js 15 with App Router
- **Styling**: Tailwind CSS with custom UI components
- **API Communication**: TypeScript client with error handling and reconnection
- **Real-time Updates**: WebSocket connections for live telemetry
- **State Management**: React hooks with optimistic updates

## Key Components

- `app/page.tsx` - Main dashboard page
- `components/SystemStatus.tsx` - Service control and monitoring  
- `components/CameraControl.tsx` - Individual camera management
- `components/NetworkScanner.tsx` - Automatic camera discovery
- `lib/api.ts` - API client with WebSocket support

## API Integration

The web interface communicates with the RexTracking FastAPI backend:

- **REST API**: Camera management, configuration, metrics
- **WebSocket**: Real-time telemetry and status updates
- **Error Handling**: Automatic reconnection with exponential backoff

## Build and Deploy

```bash
npm run build
npm start
```

The production build can be deployed to any Node.js hosting platform.
