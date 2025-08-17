import { useState, useEffect } from 'react';
import { Truck, MapPin, Clock, Route, Users, Play, Loader2 } from 'lucide-react';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Badge } from './components/ui/badge';
import { Progress } from './components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import GoogleMap from './components/GoogleMap.tsx';
import { api } from './services/api';
import { Customer, RouteOptimizationResponse } from './types';

function App() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerCount, setCustomerCount] = useState(0);
  const [numVehicles, setNumVehicles] = useState(8);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState<RouteOptimizationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setIsLoading(true);
      const [customersData, countData] = await Promise.all([
        api.getCustomers(),
        api.getCustomerCount()
      ]);
      
      setCustomers(customersData);
      setCustomerCount(countData.count);
      setError(null);
    } catch (err) {
      setError('Failed to load customer data');
      console.error('Error loading data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const optimizeRoutes = async () => {
    if (customers.length === 0) return;

    try {
      setIsOptimizing(true);
      setProgress(0);
      setError(null);

      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 500);

      const result = await api.optimizeRoutes({
        customers,
        num_vehicles: numVehicles,
        depot_addresses: [
          "1707 Smart Street, Leesville, LA 71446",
          "220 Bunker Road, Lake Charles, LA 70615", 
          "1107 Weiner St, Lufkin, TX 75904"
        ]
      });

      clearInterval(progressInterval);
      setProgress(100);
      setOptimizationResult(result);
    } catch (err) {
      setError('Failed to optimize routes');
      console.error('Error optimizing routes:', err);
    } finally {
      setIsOptimizing(false);
      setTimeout(() => setProgress(0), 1000);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading West LA Ice customers...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            West LA Ice Route Optimization
          </h1>
          <p className="text-gray-600">
            Optimize delivery routes for {customerCount} customers using advanced algorithms
          </p>
        </div>

        {error && (
          <Card className="mb-6 border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <p className="text-red-600">{error}</p>
              <Button 
                onClick={loadInitialData} 
                variant="outline" 
                className="mt-2"
              >
                Retry
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Customers</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{customerCount}</div>
              <p className="text-xs text-muted-foreground">
                West LA Ice customers
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Available Trucks</CardTitle>
              <Truck className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{numVehicles}</div>
              <p className="text-xs text-muted-foreground">
                Delivery vehicles
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Distance</CardTitle>
              <Route className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {optimizationResult ? `${optimizationResult.total_distance_miles} mi` : '--'}
              </div>
              <p className="text-xs text-muted-foreground">
                Optimized routes
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Time</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {optimizationResult ? `${Math.round(optimizationResult.total_time_minutes / 60)} hrs` : '--'}
              </div>
              <p className="text-xs text-muted-foreground">
                Estimated delivery time
              </p>
            </CardContent>
          </Card>
        </div>

        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Route Optimization</CardTitle>
            <CardDescription>
              Configure and run route optimization for all customers
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-4">
              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">
                  Number of Vehicles
                </label>
                <Select 
                  value={numVehicles.toString()} 
                  onValueChange={(value) => setNumVehicles(parseInt(value))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[1, 2, 3, 4, 5, 6, 7, 8].map(num => (
                      <SelectItem key={num} value={num.toString()}>
                        {num} {num === 1 ? 'Vehicle' : 'Vehicles'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">
                  Depot Locations
                </label>
                <div className="text-sm text-gray-600 p-2 bg-gray-100 rounded space-y-1">
                  <div>Leesville: 1707 Smart Street, Leesville, LA 71446</div>
                  <div>Lake Charles: 220 Bunker Road, Lake Charles, LA 70615</div>
                  <div>Lufkin: 1107 Weiner St, Lufkin, TX 75904</div>
                </div>
              </div>
            </div>

            {isOptimizing && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Optimizing routes...</span>
                  <span>{progress}%</span>
                </div>
                <Progress value={progress} className="w-full" />
              </div>
            )}

            <Button 
              onClick={optimizeRoutes} 
              disabled={isOptimizing || customers.length === 0}
              className="w-full"
            >
              {isOptimizing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Optimizing Routes...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Optimize Routes
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {optimizationResult && (
          <Tabs defaultValue="map" className="space-y-6">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="map">Map View</TabsTrigger>
              <TabsTrigger value="routes">Route Details</TabsTrigger>
            </TabsList>

            <TabsContent value="map">
              <Card>
                <CardHeader>
                  <CardTitle>Route Visualization</CardTitle>
                  <CardDescription>
                    Interactive map showing optimized delivery routes
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <GoogleMap 
                    routes={optimizationResult.routes}
                    depotLocations={optimizationResult.depot_locations}
                    className="rounded-lg border"
                  />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="routes">
              <div className="grid gap-6">
                {optimizationResult.routes.map((route) => (
                  <Card key={route.vehicle_id}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center">
                          <Truck className="mr-2 h-5 w-5" />
                          Vehicle {route.vehicle_id} - {route.depot_name}
                        </CardTitle>
                        <div className="flex space-x-2">
                          <Badge variant="secondary">
                            {route.route_points.length} stops
                          </Badge>
                          <Badge variant="outline">
                            {route.total_distance_miles} mi
                          </Badge>
                          <Badge variant="outline">
                            {Math.round(route.total_time_minutes)} min
                          </Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {route.route_points.map((point, index) => (
                          <div key={point.customer_id} className="flex items-center space-x-3 p-2 bg-gray-50 rounded">
                            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-sm font-medium">
                              {index + 1}
                            </div>
                            <div className="flex-1">
                              <p className="font-medium">{point.customer_name}</p>
                              <p className="text-sm text-gray-600">{point.address}</p>
                            </div>
                            <MapPin className="h-4 w-4 text-gray-400" />
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}

export default App;
