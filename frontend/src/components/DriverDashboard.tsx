import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import {
  Clock,
  Truck,
  Navigation,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Calendar
} from 'lucide-react';
import { api, DriverRoute, updateDeliveryCompletion } from '../services/api';

interface DriverDashboardProps {
  truckId?: string;
  day?: string;
}

interface RouteStop {
  customer_id: string;
  customer_name: string;
  address: string;
  latitude: number;
  longitude: number;
  estimated_time: string;
  priority: boolean;
  completed?: boolean;
}

export function DriverDashboard({ truckId = 'L1', day = 'Monday' }: DriverDashboardProps) {
  const [routes, setRoutes] = useState<DriverRoute[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTruck, setSelectedTruck] = useState(truckId);
  const [selectedDay, setSelectedDay] = useState(day);
  const [completedStops, setCompletedStops] = useState<Set<string>>(new Set());

  const availableTrucks = ['L1', 'L2', 'L3', 'Le1', 'Le2', 'Le3', 'LC1', 'LC2'];
  const availableDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

  useEffect(() => {
    fetchDriverRoutes();
  }, [selectedTruck, selectedDay]);

  const fetchDriverRoutes = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await api.getDriverRoutes(selectedTruck, selectedDay);
      setRoutes(result.routes || []);

      if (!result.routes || result.routes.length === 0) {
        setError(`No routes found for truck ${selectedTruck} on ${selectedDay}. Please run route optimization first or sync data from Google Sheets.`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch driver routes';
      if (errorMessage.includes('500')) {
        setError('Server error while fetching routes. Please check if the backend is running and try again.');
      } else if (errorMessage.includes('404')) {
        setError(`No route data found for truck ${selectedTruck} on ${selectedDay}. Please run route optimization first.`);
      } else {
        setError(errorMessage);
      }
      setRoutes([]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleStopCompletion = async (stopId: string) => {
    const newCompleted = new Set(completedStops);
    if (newCompleted.has(stopId)) {
      newCompleted.delete(stopId);
    } else {
      newCompleted.add(stopId);

      try {
        await updateDeliveryCompletion({
          sheet_id: '1priXmXhtP2vVSQ1XUa-Y18-O96OsZ9Qw',
          truck_id: selectedTruck,
          day: selectedDay,
          completed_stops: [stopId]
        });
      } catch (error) {
        console.error('Failed to update delivery completion in sheets:', error);
      }
    }
    setCompletedStops(newCompleted);
  };

  const openNavigation = (address: string) => {
    const encodedAddress = encodeURIComponent(address);
    const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodedAddress}`;
    window.open(googleMapsUrl, '_blank');
  };

  const getCompletionStats = () => {
    const totalStops = routes.reduce((sum, route) => sum + route.stops.length, 0);
    const completedCount = completedStops.size;
    const percentage = totalStops > 0 ? Math.round((completedCount / totalStops) * 100) : 0;

    return { totalStops, completedCount, percentage };
  };

  const stats = getCompletionStats();

  if (isLoading) {
    return (
      <Card className="w-full">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin mr-2" />
          <span>Loading driver routes...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Truck className="h-5 w-5" />
            <span>Driver Dashboard</span>
          </CardTitle>
          <CardDescription>
            Daily route management and navigation for delivery drivers
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Truck</label>
              <select
                value={selectedTruck}
                onChange={(e) => setSelectedTruck(e.target.value)}
                className="px-3 py-2 border rounded-md bg-white"
              >
                {availableTrucks.map(truck => (
                  <option key={truck} value={truck}>{truck}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Day</label>
              <select
                value={selectedDay}
                onChange={(e) => setSelectedDay(e.target.value)}
                className="px-3 py-2 border rounded-md bg-white"
              >
                {availableDays.map(day => (
                  <option key={day} value={day}>{day}</option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <Button onClick={fetchDriverRoutes} variant="outline">
                Refresh Routes
              </Button>
            </div>
          </div>

          {stats.totalStops > 0 && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Calendar className="h-4 w-4 text-blue-600" />
                  <span className="font-medium">Progress: {stats.completedCount}/{stats.totalStops} stops</span>
                </div>
                <Badge variant={stats.percentage === 100 ? "default" : "secondary"}>
                  {stats.percentage}% Complete
                </Badge>
              </div>
              <div className="mt-2 bg-white rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${stats.percentage}%` }}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertTriangle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      {routes.length === 0 && !error && !isLoading && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            No routes found for truck {selectedTruck} on {selectedDay}.
            Please run route optimization first or sync data from Google Sheets.
          </AlertDescription>
        </Alert>
      )}

      {routes.map((route, routeIndex) => (
        <Card key={routeIndex} className="w-full">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Truck className="h-5 w-5" />
                <span>Truck {route.truck_id} - {route.depot}</span>
              </div>
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <Clock className="h-4 w-4" />
                <span>{route.estimated_hours}h estimated</span>
              </div>
            </CardTitle>
            <CardDescription>
              {route.stops.length} stops • {route.priority_stops.length} priority deliveries
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {route.stops.map((stop: RouteStop, stopIndex) => {
                const isCompleted = completedStops.has(stop.customer_id);
                const isPriority = route.priority_stops.includes(stop.customer_id);

                return (
                  <div
                    key={stop.customer_id}
                    className={`p-4 rounded-lg border transition-all ${
                      isCompleted
                        ? 'bg-green-50 border-green-200'
                        : isPriority
                        ? 'bg-orange-50 border-orange-200'
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3 flex-1">
                        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                          isCompleted
                            ? 'bg-green-100 text-green-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}>
                          {stopIndex + 1}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            <h4 className="font-medium text-gray-900">{stop.customer_name}</h4>
                            {isPriority && (
                              <Badge variant="destructive" className="text-xs">
                                Priority
                              </Badge>
                            )}
                            {isCompleted && (
                              <CheckCircle className="h-4 w-4 text-green-600" />
                            )}
                          </div>

                          <p className="text-sm text-gray-600 mb-2">{stop.address}</p>

                          {stop.estimated_time && (
                            <div className="flex items-center space-x-1 text-xs text-gray-500">
                              <Clock className="h-3 w-3" />
                              <span>ETA: {stop.estimated_time}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 ml-4">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openNavigation(stop.address)}
                          className="flex items-center space-x-1"
                        >
                          <Navigation className="h-3 w-3" />
                          <span className="hidden sm:inline">Navigate</span>
                        </Button>

                        <Button
                          size="sm"
                          variant={isCompleted ? "default" : "outline"}
                          onClick={() => toggleStopCompletion(stop.customer_id)}
                          className="flex items-center space-x-1"
                        >
                          <CheckCircle className="h-3 w-3" />
                          <span className="hidden sm:inline">
                            {isCompleted ? 'Done' : 'Mark Done'}
                          </span>
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
