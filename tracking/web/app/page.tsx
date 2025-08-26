"use client";

import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Camera, Activity, AlertTriangle, Wifi, WifiOff, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { SystemStatus } from "@/components/SystemStatus";
import { CameraControl } from "@/components/CameraControl";
import { NetworkScanner } from "@/components/NetworkScanner";
import { SettingsControl } from "@/components/SettingsControl";
import { ServiceStatus } from "@/lib/api";
import { useDashboardWebSocket } from "@/lib/use-dashboard-websocket";

// Хук для проверки клиентского рендеринга
function useIsClient() {
  const [isClient, setIsClient] = useState(false);
  useEffect(() => {
    setIsClient(true);
  }, []);
  return isClient;
}

// Основной компонент
export default function RexTrackingDashboard() {
  const isClient = useIsClient();
  
  // Use WebSocket hook instead of HTTP polling
  const { 
    serviceStatus, 
    cameras, 
    isConnected, 
    error, 
    reconnect 
  } = useDashboardWebSocket();

  const handleServiceStatusChange = (status: ServiceStatus) => {
    // This is now handled by the WebSocket hook
    console.log("Service status changed:", status);
  };

  const handleCameraChange = useCallback(() => {
    // This is now handled by the WebSocket hook automatically
    console.log("Camera change detected");
  }, []);

  const handleCameraRefresh = useCallback(() => {
    // Принудительно переподключаем WebSocket для обновления данных
    console.log("Forcing camera list refresh...");
    reconnect();
  }, [reconnect]);

  const handleManualRetry = useCallback(() => {
    reconnect();
  }, [reconnect]);

  // Показываем загрузку только если мы на клиенте и данные еще загружаются
  if (isClient && !serviceStatus && !error) {
    return (
      <div className="min-h-screen bg-background text-foreground p-6">
        <Topbar isConnected={isConnected} />
        <div className="max-w-7xl mx-auto grid gap-4 grid-cols-1 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="h-48 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground p-6">
      <Topbar isConnected={isConnected} />

      <div className="max-w-7xl mx-auto">
        {/* DASHBOARD STATS */}
        <div className="grid gap-4 grid-cols-1 md:grid-cols-4 mb-6">
          <StatCard 
            title="Connection Status" 
            value={isConnected ? "Connected" : "Disconnected"} 
            subtitle={isConnected ? "API server online" : "API server offline"}
            icon={isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            status={isConnected ? "success" : "error"}
          />
          <StatCard 
            title="Service Status" 
            value={serviceStatus?.running ? "Running" : "Stopped"} 
            subtitle={serviceStatus?.healthy ? "Healthy" : "Issues detected"}
            icon={<Activity className="w-4 h-4" />}
            status={serviceStatus?.running ? "success" : "warning"}
          />
          <StatCard 
            title="Cameras Running" 
            value={cameras.filter((c) => c.status === "running").length} 
            subtitle={`of ${cameras.length} total`}
            icon={<Camera className="w-4 h-4" />}
            status="info"
          />
          <StatCard 
            title="Cameras with Issues" 
            value={cameras.filter((c) => c.status === "error").length} 
            subtitle="need attention"
            icon={<AlertTriangle className="w-4 h-4" />}
            status={cameras.filter((c) => c.status === "error").length > 0 ? "error" : "success"}
          />
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="w-4 h-4" />
              <span className="font-medium">Error:</span>
              <span>{error}</span>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleManualRetry}
              className="mt-2"
              disabled={false}
            >
              <>
                <RefreshCw className="w-4 h-4 mr-1" />
                Reconnect
              </>
            </Button>
          </div>
        )}

        {/* MAIN CONTENT */}
        <Tabs defaultValue="cameras" className="space-y-4">
          <TabsList>
            <TabsTrigger value="cameras">Cameras</TabsTrigger>
            <TabsTrigger value="scanner">Network Scanner</TabsTrigger>
            <TabsTrigger value="system">System</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="cameras" className="space-y-4">
            <CameraControl cameras={cameras} onCameraChange={handleCameraRefresh} />
          </TabsContent>

          <TabsContent value="scanner" className="space-y-4">
            <NetworkScanner onCameraAdded={handleCameraChange} />
          </TabsContent>

          <TabsContent value="system" className="space-y-4">
            <SystemStatus 
              serviceStatus={serviceStatus} 
              onStatusChange={handleServiceStatusChange} 
            />
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <SettingsControl onSettingsChange={handleCameraChange} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function Topbar({ isConnected }: { isConnected: boolean }) {
  const isClient = useIsClient();
  
  return (
    <div className="max-w-7xl mx-auto mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isClient ? (
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }} 
              animate={{ scale: 1, opacity: 1 }} 
              className="w-9 h-9 rounded-2xl bg-primary/10 flex items-center justify-center"
            >
              <Camera className="w-5 h-5" />
            </motion.div>
          ) : (
            <div className="w-9 h-9 rounded-2xl bg-primary/10 flex items-center justify-center">
              <Camera className="w-5 h-5" />
            </div>
          )}
          <div>
            <h1 className="text-xl font-semibold">RexTracking</h1>
            <p className="text-xs text-muted-foreground">Modular vision pipelines controller</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full text-sm border">
            {isConnected ? (
              <>
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-green-700">Connected</span>
              </>
            ) : (
              <>
                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                <span className="text-red-700">Disconnected</span>
              </>
            )}
          </div>
          <Button variant="outline" size="sm" onClick={() => window.open('http://localhost:8080/docs', '_blank')}>
            API Docs
          </Button>
        </div>
      </div>
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ReactNode;
  status?: "success" | "error" | "warning" | "info";
}

function StatCard({ title, value, subtitle, icon, status }: StatCardProps) {
  const getStatusStyles = () => {
    switch (status) {
      case "success":
        return "border-green-200 bg-green-50";
      case "error":
        return "border-red-200 bg-red-50";
      case "warning":
        return "border-yellow-200 bg-yellow-50";
      case "info":
        return "border-blue-200 bg-blue-50";
      default:
        return "";
    }
  };

  return (
    <Card className={getStatusStyles()}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold">{value}</div>
        <div className="text-xs text-muted-foreground">{subtitle}</div>
      </CardContent>
    </Card>
  );
}
