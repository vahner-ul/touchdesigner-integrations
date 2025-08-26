"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Camera, Play, Square, RotateCcw, Plus, Trash2, RefreshCw } from "lucide-react";
import { apiClient, CameraStatus, CameraAddRequest } from "@/lib/api";

interface CameraControlProps {
  cameras?: CameraStatus[];
  onCameraChange?: () => void;
}

export function CameraControl({ cameras: propCameras, onCameraChange }: CameraControlProps) {
  const cameras = propCameras || [];
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newCamera, setNewCamera] = useState<Partial<CameraAddRequest>>({
    id: "",
    name: "",
    stream: "",
    enabled: true,
  });

  // Generate a unique camera ID
  const generateUniqueId = () => {
    let id = `cam${cameras.length + 1}`;
    let counter = 1;
    while (cameras.find(cam => cam.camera_id === id)) {
      id = `cam${cameras.length + 1 + counter}`;
      counter++;
    }
    return id;
  };

  const handleStartCamera = async (cameraId: string) => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.startCamera(cameraId);
      onCameraChange?.(); // Notify parent that camera state changed
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start camera");
      console.error("Failed to start camera:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStopCamera = async (cameraId: string) => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.stopCamera(cameraId);
      onCameraChange?.(); // Notify parent that camera state changed
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop camera");
      console.error("Failed to stop camera:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRestartCamera = async (cameraId: string) => {
    try {
      setLoading(true);
      setError(null);
      await apiClient.restartCamera(cameraId);
      onCameraChange?.(); // Notify parent that camera state changed
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to restart camera");
      console.error("Failed to restart camera:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCamera = async () => {
    if (!newCamera.id || !newCamera.name || !newCamera.stream) {
      setError("Please fill in all required fields");
      return;
    }

    // Check if camera ID already exists
    const existingCamera = cameras.find(cam => cam.camera_id === newCamera.id);
    if (existingCamera) {
      setError(`Camera with ID "${newCamera.id}" already exists. Please use a different ID.`);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await apiClient.addCamera(newCamera as CameraAddRequest);
      setShowAddDialog(false);
      setNewCamera({ id: "", name: "", stream: "", enabled: true });
      onCameraChange?.(); // Notify parent that camera state changed
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to add camera";
      if (errorMessage.includes("409")) {
        setError(`Camera with ID "${newCamera.id}" already exists. Please use a different ID.`);
      } else {
        setError(errorMessage);
      }
      console.error("Failed to add camera:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveCamera = async (cameraId: string) => {
    if (!confirm(`Are you sure you want to remove camera ${cameraId}?`)) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await apiClient.removeCamera(cameraId);
      onCameraChange?.(); // Notify parent that camera state changed
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove camera");
      console.error("Failed to remove camera:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshCameras = async () => {
    try {
      setRefreshing(true);
      setError(null);
      // Вызываем callback для обновления списка камер
      onCameraChange?.();
      console.log("Camera list refresh requested");
      
      // Показываем краткое сообщение об успешном обновлении
      setTimeout(() => {
        setRefreshing(false);
      }, 1000); // Минимальное время показа анимации
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh cameras");
      console.error("Failed to refresh cameras:", err);
      setRefreshing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return <Badge variant="default">Running</Badge>;
      case "stopped":
        return <Badge variant="secondary">Stopped</Badge>;
      case "error":
        return <Badge variant="destructive">Error</Badge>;
      case "connecting":
        return <Badge variant="outline">Connecting</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Cameras</h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefreshCameras}
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="w-4 h-4 mr-1" />
                Add Camera
              </Button>
            </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Camera</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="camera-id">Camera ID</Label>
                <div className="flex gap-2">
                  <Input
                    id="camera-id"
                    value={newCamera.id}
                    onChange={(e) => setNewCamera({ ...newCamera, id: e.target.value })}
                    placeholder="cam1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setNewCamera({ ...newCamera, id: generateUniqueId() })}
                  >
                    Generate
                  </Button>
                </div>
                {cameras.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Existing IDs: {cameras.map(cam => cam.camera_id).join(", ")}
                  </p>
                )}
              </div>
              <div>
                <Label htmlFor="camera-name">Name</Label>
                <Input
                  id="camera-name"
                  value={newCamera.name}
                  onChange={(e) => setNewCamera({ ...newCamera, name: e.target.value })}
                  placeholder="Front Door Camera"
                />
              </div>
              <div>
                <Label htmlFor="camera-stream">Stream URL</Label>
                <Input
                  id="camera-stream"
                  value={newCamera.stream}
                  onChange={(e) => setNewCamera({ ...newCamera, stream: e.target.value })}
                  placeholder="rtsp://user:pass@host/stream"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAddDialog(false)}>
                  Cancel
                </Button>
                <Button onClick={handleAddCamera} disabled={loading}>
                  Add Camera
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
          {error}
        </div>
      )}

      {/* Camera List */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {cameras.map((camera) => (
          <Card key={camera.camera_id}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Camera className="w-4 h-4" />
                {camera.name}
                {getStatusBadge(camera.status)}
              </CardTitle>
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRestartCamera(camera.camera_id)}
                  disabled={loading}
                >
                  <RotateCcw className="w-3 h-3" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRemoveCamera(camera.camera_id)}
                  disabled={loading}
                >
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground truncate">
                  {camera.stream || "No stream URL"}
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">FPS:</span> {camera.fps_input.toFixed(1)}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Latency:</span> {camera.latency_ms.toFixed(0)}ms
                  </div>
                  <div>
                    <span className="text-muted-foreground">Objects:</span> {camera.objects_count}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Enabled:</span> {camera.enabled ? "Yes" : "No"}
                  </div>
                </div>
                {camera.error_message && (
                  <div className="text-xs text-red-600">
                    Error: {camera.error_message}
                  </div>
                )}
                <div className="flex gap-1">
                  {camera.status !== "running" ? (
                    <Button
                      size="sm"
                      onClick={() => handleStartCamera(camera.camera_id)}
                      disabled={loading || !camera.enabled}
                    >
                      <Play className="w-3 h-3 mr-1" />
                      Start
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleStopCamera(camera.camera_id)}
                      disabled={loading}
                    >
                      <Square className="w-3 h-3 mr-1" />
                      Stop
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {cameras.length === 0 && !loading && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8">
            <Camera className="w-8 h-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No cameras configured</p>
            <p className="text-xs text-muted-foreground">Add a camera to get started</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
