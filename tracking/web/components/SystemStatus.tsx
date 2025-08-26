"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Activity, Play, Square, RotateCcw, AlertTriangle, CheckCircle } from "lucide-react";
import { apiClient, ServiceStatus } from "@/lib/api";

interface SystemStatusProps {
  serviceStatus?: ServiceStatus | null;
  onStatusChange?: (status: ServiceStatus) => void;
}

export function SystemStatus({ serviceStatus, onStatusChange }: SystemStatusProps) {
  const status = serviceStatus;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartService = async () => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.startService();
      onStatusChange?.(status!); // Notify parent
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start service");
      console.error("Failed to start service:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStopService = async () => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.stopService();
      onStatusChange?.(status!); // Notify parent
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop service");
      console.error("Failed to stop service:", err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: ServiceStatus) => {
    if (!status.running) {
      return <Badge variant="secondary">Stopped</Badge>;
    }
    if (!status.healthy) {
      return <Badge variant="destructive">Degraded</Badge>;
    }
    return <Badge variant="default">Running</Badge>;
  };

  const getStatusIcon = (status: ServiceStatus) => {
    if (!status.running) {
      return <Square className="w-4 h-4" />;
    }
    if (!status.healthy) {
      return <AlertTriangle className="w-4 h-4" />;
    }
    return <CheckCircle className="w-4 h-4" />;
  };

  const formatUptime = (uptime: number) => {
    if (uptime === 0) return "0s";
    
    const hours = Math.floor(uptime / 3600);
    const minutes = Math.floor((uptime % 3600) / 60);
    const seconds = Math.floor(uptime % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  };

  if (!status) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            System Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            {error ? `Error: ${error}` : "Loading..."}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="w-4 h-4" />
          System Status
          {getStatusBadge(status)}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Status Info */}
          <div className="flex items-center gap-2">
            {getStatusIcon(status)}
            <span className="text-sm">
              {status.running ? "Service is running" : "Service is stopped"}
            </span>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-muted-foreground">Uptime</div>
              <div className="font-medium">{formatUptime(status.uptime)}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Cameras</div>
              <div className="font-medium">{status.cameras_count}</div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
              {error}
            </div>
          )}

          {/* Controls */}
          <div className="flex gap-2">
            {status.running ? (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleStopService}
                disabled={loading}
              >
                <Square className="w-4 h-4 mr-1" />
                Stop Service
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={handleStartService}
                disabled={loading}
              >
                <Play className="w-4 h-4 mr-1" />
                Start Service
              </Button>
            )}
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.reload()}
              disabled={loading}
            >
              <RotateCcw className="w-4 h-4 mr-1" />
              Refresh Page
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
