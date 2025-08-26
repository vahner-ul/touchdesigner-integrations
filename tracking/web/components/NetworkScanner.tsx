"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Search, Camera, Plus, AlertTriangle, CheckCircle, Wifi, Loader2, Clock } from "lucide-react";
import { apiClient, DiscoveredCamera } from "@/lib/api";

interface NetworkScannerProps {
  onCameraAdded?: () => void;
}

export function NetworkScanner({ onCameraAdded }: NetworkScannerProps) {
  const [isScanning, setIsScanning] = useState(false);
  const [discoveredCameras, setDiscoveredCameras] = useState<DiscoveredCamera[]>([]);
  const [scanTime, setScanTime] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState<DiscoveredCamera | null>(null);
  const [newCamera, setNewCamera] = useState({
    id: "",
    name: "",
    enabled: true,
  });

  const [scanSettings, setScanSettings] = useState({
    network_range: "192.168.1.0/24",
    timeout: 2.0,
  });

  const handleScanNetwork = async () => {
    try {
      setIsScanning(true);
      setError(null);
      setDiscoveredCameras([]);

      const response = await apiClient.scanNetwork(scanSettings);
      setDiscoveredCameras(response.cameras);
      setScanTime(response.scan_time);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to scan network");
      console.error("Failed to scan network:", err);
    } finally {
      setIsScanning(false);
    }
  };

  const handleAddCamera = async (camera: DiscoveredCamera) => {
    setSelectedCamera(camera);
    setNewCamera({
      id: `camera_${camera.ip.replace(/\./g, '_')}`,
      name: `Camera ${camera.ip}`,
      enabled: true,
    });
    setShowAddDialog(true);
  };

  const handleConfirmAdd = async () => {
    if (!selectedCamera || !newCamera.id || !newCamera.name) {
      setError("Please fill in all required fields");
      return;
    }

    try {
      setError(null);
      await apiClient.addCamera({
        id: newCamera.id,
        name: newCamera.name,
        stream: selectedCamera.url,
        enabled: newCamera.enabled,
      });

      setShowAddDialog(false);
      setSelectedCamera(null);
      setNewCamera({ id: "", name: "", enabled: true });
      // WebSocket событие автоматически обновит список камер
      // onCameraAdded?.(); // Убираем немедленный callback
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add camera");
      console.error("Failed to add camera:", err);
    }
  };

  const getProtocolIcon = (protocol: string) => {
    switch (protocol.toLowerCase()) {
      case "rtsp":
        return <Camera className="w-4 h-4" />;
      case "http":
        return <Wifi className="w-4 h-4" />;
      default:
        return <Camera className="w-4 h-4" />;
    }
  };

  const getStatusIcon = (isAccessible: boolean) => {
    return isAccessible ? (
      <CheckCircle className="w-4 h-4 text-green-500" />
    ) : (
      <AlertTriangle className="w-4 h-4 text-yellow-500" />
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="w-5 h-5" />
          Network Scanner
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Scan Settings */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="network-range">Network Range</Label>
            <Input
              id="network-range"
              value={scanSettings.network_range}
              onChange={(e) => setScanSettings(prev => ({ ...prev, network_range: e.target.value }))}
              placeholder="192.168.1.0/24"
            />
          </div>
          <div>
            <Label htmlFor="timeout">Timeout (seconds)</Label>
            <Input
              id="timeout"
              type="number"
              step="0.1"
              min="0.5"
              max="10"
              value={scanSettings.timeout}
              onChange={(e) => setScanSettings(prev => ({ ...prev, timeout: parseFloat(e.target.value) }))}
            />
          </div>
        </div>

        {/* Scan Button */}
        <Button 
          onClick={handleScanNetwork} 
          disabled={isScanning}
          className="w-full"
        >
          {isScanning ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Scanning Network...
            </>
          ) : (
            <>
              <Search className="w-4 h-4 mr-2" />
              Scan Network
            </>
          )}
        </Button>

        {/* Error Display */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {/* Scan Results */}
        {discoveredCameras.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm text-gray-600">
              <span>Found {discoveredCameras.length} camera(s)</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {scanTime.toFixed(2)}s
              </span>
            </div>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {discoveredCameras.map((camera) => (
                <div
                  key={`${camera.ip}:${camera.port}`}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    {getProtocolIcon(camera.protocol)}
                    <div>
                      <div className="font-medium">{camera.ip}:{camera.port}</div>
                      <div className="text-sm text-gray-600">
                        {camera.protocol.toUpperCase()} • {camera.url}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {getStatusIcon(camera.is_accessible)}
                    <Badge variant={camera.is_accessible ? "default" : "secondary"}>
                      {camera.is_accessible ? "Accessible" : "Not Tested"}
                    </Badge>
                    <Button
                      size="sm"
                      onClick={() => handleAddCamera(camera)}
                      disabled={!camera.is_accessible}
                    >
                      <Plus className="w-3 h-3 mr-1" />
                      Add
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Add Camera Dialog */}
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Discovered Camera</DialogTitle>
            </DialogHeader>
            
            {selectedCamera && (
              <div className="space-y-4">
                <div className="p-3 bg-gray-50 rounded-md">
                  <div className="text-sm font-medium">Camera Details</div>
                  <div className="text-sm text-gray-600">
                    IP: {selectedCamera.ip}:{selectedCamera.port}<br />
                    Protocol: {selectedCamera.protocol}<br />
                    URL: {selectedCamera.url}
                  </div>
                </div>

                <div>
                  <Label htmlFor="camera-id">Camera ID</Label>
                  <Input
                    id="camera-id"
                    value={newCamera.id}
                    onChange={(e) => setNewCamera(prev => ({ ...prev, id: e.target.value }))}
                    placeholder="camera_192_168_1_100"
                  />
                </div>

                <div>
                  <Label htmlFor="camera-name">Camera Name</Label>
                  <Input
                    id="camera-name"
                    value={newCamera.name}
                    onChange={(e) => setNewCamera(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Front Door Camera"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="camera-enabled"
                    checked={newCamera.enabled}
                    onChange={(e) => setNewCamera(prev => ({ ...prev, enabled: e.target.checked }))}
                  />
                  <Label htmlFor="camera-enabled">Enable camera after adding</Label>
                </div>

                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowAddDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleConfirmAdd}>
                    Add Camera
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
