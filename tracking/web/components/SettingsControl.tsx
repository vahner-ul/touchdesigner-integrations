"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Settings, Save, RotateCcw, AlertTriangle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { apiClient, SettingsMetadataResponse, SettingUpdateRequest } from "@/lib/api";

interface SettingsControlProps {
  onSettingsChange?: () => void;
}

interface SettingItem {
  id: number;
  config_table: string;
  config_field: string;
  display_name: string;
  description: string;
  control_type: string;
  is_editable: boolean;
  is_visible: boolean;
  validation_rules: any;
  default_value: any;
  options: string[] | null;
  category: string;
  order_index: number;
  current_value: any;
}

export function SettingsControl({ onSettingsChange }: SettingsControlProps) {
  const [settings, setSettings] = useState<SettingsMetadataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [localValues, setLocalValues] = useState<Record<string, any>>({});

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getSettings();
      setSettings(data);
      
      // Initialize local values with current values
      const initialValues: Record<string, any> = {};
      Object.values(data.categories).flat().forEach((item: SettingItem) => {
        const key = `${item.config_table}.${item.config_field}`;
        initialValues[key] = item.current_value;
      });
      setLocalValues(initialValues);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  const handleValueChange = (setting: SettingItem, value: any) => {
    const key = `${setting.config_table}.${setting.config_field}`;
    setLocalValues(prev => ({ ...prev, [key]: value }));
  };

  const handleSaveSetting = async (setting: SettingItem) => {
    const key = `${setting.config_table}.${setting.config_field}`;
    const value = localValues[key];
    
    if (value === setting.current_value) {
      return; // No change
    }

    try {
      setUpdating(key);
      setError(null);
      
      await apiClient.updateSetting(setting.config_table, setting.config_field, value);
      
      // Update the settings data
      setSettings(prev => {
        if (!prev) return prev;
        
        const updatedCategories = { ...prev.categories };
        Object.keys(updatedCategories).forEach(category => {
          updatedCategories[category] = updatedCategories[category].map((item: SettingItem) => {
            if (item.config_table === setting.config_table && item.config_field === setting.config_field) {
              return { ...item, current_value: value };
            }
            return item;
          });
        });
        
        return {
          ...prev,
          categories: updatedCategories,
          current_values: {
            ...prev.current_values,
            [setting.config_table]: {
              ...prev.current_values[setting.config_table],
              [setting.config_field]: value
            }
          }
        };
      });
      
      setSuccessMessage(`${setting.display_name} updated successfully`);
      setTimeout(() => setSuccessMessage(null), 3000);
      
      onSettingsChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setUpdating(null);
    }
  };

  const handleResetToDefaults = async () => {
    try {
      setError(null);
      await apiClient.resetSettingsToDefaults();
      await loadSettings();
      setSuccessMessage("All settings reset to defaults");
      setTimeout(() => setSuccessMessage(null), 3000);
      onSettingsChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset settings");
    }
  };

  const renderControl = (setting: SettingItem) => {
    const key = `${setting.config_table}.${setting.config_field}`;
    const value = localValues[key] ?? setting.current_value;
    const isChanged = value !== setting.current_value;
    const isUpdating = updating === key;

    switch (setting.control_type) {
      case 'text':
        return (
          <Input
            value={value || ''}
            onChange={(e) => handleValueChange(setting, e.target.value)}
            disabled={!setting.is_editable || isUpdating}
            className={isChanged ? "border-orange-500" : ""}
          />
        );

      case 'number':
        return (
          <Input
            type="number"
            value={value || ''}
            onChange={(e) => handleValueChange(setting, parseFloat(e.target.value) || 0)}
            disabled={!setting.is_editable || isUpdating}
            className={isChanged ? "border-orange-500" : ""}
            min={setting.validation_rules?.min}
            max={setting.validation_rules?.max}
            step={setting.validation_rules?.step || 1}
          />
        );

      case 'slider':
        return (
          <div className="space-y-2">
            <Input
              type="range"
              value={value || 0}
              onChange={(e) => handleValueChange(setting, parseFloat(e.target.value))}
              disabled={!setting.is_editable || isUpdating}
              min={setting.validation_rules?.min || 0}
              max={setting.validation_rules?.max || 1}
              step={setting.validation_rules?.step || 0.01}
              className="w-full"
            />
            <div className="text-sm text-muted-foreground text-center">
              {value}
            </div>
          </div>
        );

      case 'select':
        return (
          <Select
            value={value || ''}
            onValueChange={(val) => handleValueChange(setting, val)}
            disabled={!setting.is_editable || isUpdating}
          >
            <SelectTrigger className={isChanged ? "border-orange-500" : ""}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {setting.options?.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      case 'switch':
        return (
          <Switch
            checked={Boolean(value)}
            onCheckedChange={(checked) => handleValueChange(setting, checked)}
            disabled={!setting.is_editable || isUpdating}
          />
        );

      default:
        return (
          <Input
            value={value || ''}
            onChange={(e) => handleValueChange(setting, e.target.value)}
            disabled={!setting.is_editable || isUpdating}
            className={isChanged ? "border-orange-500" : ""}
          />
        );
    }
  };

  const renderSettingItem = (setting: SettingItem) => {
    const key = `${setting.config_table}.${setting.config_field}`;
    const value = localValues[key] ?? setting.current_value;
    const isChanged = value !== setting.current_value;
    const isUpdating = updating === key;

    return (
      <motion.div
        key={key}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-2"
      >
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <Label className="text-sm font-medium">
              {setting.display_name}
              {isChanged && <Badge variant="secondary" className="ml-2">Modified</Badge>}
            </Label>
            {setting.description && (
              <p className="text-xs text-muted-foreground">{setting.description}</p>
            )}
          </div>
          {isChanged && (
            <Button
              size="sm"
              onClick={() => handleSaveSetting(setting)}
              disabled={isUpdating}
            >
              {isUpdating ? (
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
            </Button>
          )}
        </div>
        {renderControl(setting)}
        {setting.validation_rules && (
          <div className="text-xs text-muted-foreground">
            {setting.validation_rules.min !== undefined && `Min: ${setting.validation_rules.min}`}
            {setting.validation_rules.max !== undefined && ` Max: ${setting.validation_rules.max}`}
            {setting.validation_rules.step !== undefined && ` Step: ${setting.validation_rules.step}`}
          </div>
        )}
      </motion.div>
    );
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            System Settings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-muted rounded animate-pulse" />
                <div className="h-10 bg-muted rounded animate-pulse" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            System Settings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="w-4 h-4" />
            <span>{error}</span>
          </div>
          <Button onClick={loadSettings} className="mt-2">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!settings) {
    return null;
  }

  const categories = Object.keys(settings.categories);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            System Settings
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetToDefaults}
            disabled={updating !== null}
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset to Defaults
          </Button>
        </div>
        {successMessage && (
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle className="w-4 h-4" />
            <span>{successMessage}</span>
          </div>
        )}
      </CardHeader>
      <CardContent>
        <Tabs defaultValue={categories[0]} className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            {categories.map((category) => (
              <TabsTrigger key={category} value={category} className="capitalize">
                {category}
              </TabsTrigger>
            ))}
          </TabsList>

          {categories.map((category) => (
            <TabsContent key={category} value={category} className="space-y-6">
              {settings.categories[category].map((setting: SettingItem) => (
                <div key={`${setting.config_table}.${setting.config_field}`}>
                  {renderSettingItem(setting)}
                </div>
              ))}
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}
