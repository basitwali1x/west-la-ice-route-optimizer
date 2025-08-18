import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { Loader2, Download, Upload, CheckCircle, AlertCircle } from 'lucide-react';
import { api, SheetsSync } from '../services/api';

interface GoogleSheetsSyncProps {
  onSyncComplete?: (data: any) => void;
  onOptimizeComplete?: (data: any) => void;
}

export function GoogleSheetsSync({ onSyncComplete, onOptimizeComplete }: GoogleSheetsSyncProps) {
  const [sheetId, setSheetId] = useState('1priXmXhtP2vVSQ1XUa-Y18-O96OsZ9Qw');
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'syncing' | 'optimizing' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [lastSync, setLastSync] = useState<string | null>(null);

  const handleSync = async () => {
    if (!sheetId.trim()) {
      setStatus('error');
      setMessage('Please enter a valid Google Sheets ID');
      return;
    }

    setIsLoading(true);
    setStatus('syncing');
    setMessage('Syncing data from Google Sheets...');

    try {
      const sheetsSync: SheetsSync = {
        sheet_id: sheetId,
        status: 'syncing'
      };

      const result = await api.syncFromSheets(sheetsSync);
      
      setStatus('success');
      setMessage(`Successfully synced ${Object.keys(result.data.customers || {}).length} depot(s) with customer data`);
      setLastSync(new Date().toLocaleString());
      
      if (onSyncComplete) {
        onSyncComplete(result.data);
      }
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Failed to sync from Google Sheets');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOptimize = async () => {
    if (!sheetId.trim()) {
      setStatus('error');
      setMessage('Please enter a valid Google Sheets ID');
      return;
    }

    setIsLoading(true);
    setStatus('optimizing');
    setMessage('Running route optimization with Google Sheets constraints...');

    try {
      const sheetsSync: SheetsSync = {
        sheet_id: sheetId,
        status: 'optimizing'
      };

      const result = await api.optimizeWithSheets(sheetsSync);
      
      setStatus('success');
      setMessage(`Successfully optimized routes for ${result.optimization_result.routes.length} vehicles`);
      setLastSync(new Date().toLocaleString());
      
      if (onOptimizeComplete) {
        onOptimizeComplete(result);
      }
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Failed to optimize with Google Sheets');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'syncing':
      case 'optimizing':
        return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'success':
        return 'border-green-200 bg-green-50';
      case 'error':
        return 'border-red-200 bg-red-50';
      default:
        return '';
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Upload className="h-5 w-5" />
          <span>Google Sheets Integration</span>
        </CardTitle>
        <CardDescription>
          Sync customer data and route assignments from Google Sheets to optimize delivery routes
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="sheet-id" className="text-sm font-medium">
            Google Sheets ID
          </label>
          <Input
            id="sheet-id"
            type="text"
            placeholder="Enter Google Sheets ID (e.g., 1priXmXhtP2vVSQ1XUa-Y18-O96OsZ9Qw)"
            value={sheetId}
            onChange={(e) => setSheetId(e.target.value)}
            disabled={isLoading}
          />
          <p className="text-xs text-gray-500">
            You can find the Sheet ID in the URL: docs.google.com/spreadsheets/d/[SHEET_ID]/edit
          </p>
        </div>

        <div className="flex space-x-3">
          <Button
            onClick={handleSync}
            disabled={isLoading || !sheetId.trim()}
            className="flex-1"
            variant="outline"
          >
            {status === 'syncing' ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Syncing...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Sync Data
              </>
            )}
          </Button>

          <Button
            onClick={handleOptimize}
            disabled={isLoading || !sheetId.trim()}
            className="flex-1"
          >
            {status === 'optimizing' ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Optimizing...
              </>
            ) : (
              <>
                <CheckCircle className="mr-2 h-4 w-4" />
                Optimize Routes
              </>
            )}
          </Button>
        </div>

        {message && (
          <Alert className={getStatusColor()}>
            <div className="flex items-center space-x-2">
              {getStatusIcon()}
              <AlertDescription>{message}</AlertDescription>
            </div>
          </Alert>
        )}

        {lastSync && (
          <div className="text-sm text-gray-500">
            Last sync: {lastSync}
          </div>
        )}

        <div className="text-xs text-gray-400 space-y-1">
          <p><strong>Sync Data:</strong> Pull customer lists from depot tabs (jasper, leesville, lufkin, all)</p>
          <p><strong>Optimize Routes:</strong> Run OR-Tools optimization with 75-mile radius constraints and balanced truck assignments</p>
        </div>
      </CardContent>
    </Card>
  );
}
