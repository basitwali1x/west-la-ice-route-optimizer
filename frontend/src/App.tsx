import { useState, useEffect } from 'react';
import { Truck, MapPin, Clock, Route, Users, Play, Loader2, BarChart3 } from 'lucide-react';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Badge } from './components/ui/badge';
import { Progress } from './components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import GoogleMap from './components/GoogleMap.tsx';
import { GoogleSheetsSync } from './components/GoogleSheetsSync';
import { DriverDashboard } from './components/DriverDashboard';
import { WeeklyVisitDashboard } from './components/WeeklyVisitDashboard';
import { api } from './services/api';
import { Customer, RouteOptimizationResponse } from './types';

function App() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerCount, setCustomerCount] = useState(0);
  const [numVehicles, setNumVehicles] = useState(8);
  const [vehicleDistribution, setVehicleDistribution] = useState({
    Leesville: 5,
    'Lake Charles': 2,
    Lufkin: 1
  });
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState<RouteOptimizationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [depotProgress, setDepotProgress] = useState<{[key: string]: number}>({});
  const [optimizationComplete, setOptimizationComplete] = useState(false);
  const [startTime, setStartTime] = useState<Date | null>(null);
  const [sheetsData, setSheetsData] = useState<any>(null);
  const [selectedTruck] = useState('L1');

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    const checkCompletion = async () => {
      if (progress >= 98 && isOptimizing) {
        try {
          const status = await api.verifyCompletion();
          if (status.complete) {
            setProgress(100);
            setDepotProgress({
              'Leesville': 100,
              'Lake Charles': 100,
              'Lufkin': 100
            });
            setOptimizationComplete(true);
          }
        } catch (error) {
          console.error('Failed to verify completion:', error);
        }
      }
    };

    if (progress >= 98) {
      checkCompletion();
    }
  }, [progress, isOptimizing]);

  const loadInitialData = async () => {
    try {
      setIsLoading(true);
      
      const defaultSheetId = '1et9tMDnHlc1nUQymyeyL2w_GLvzvBJL0XHN1NRzADgc';
      try {
        const sheetsSync = {
          sheet_id: defaultSheetId,
          status: 'syncing'
        };
        
        const sheetsResult = await api.syncFromSheets(sheetsSync);
        
        if (sheetsResult.data && sheetsResult.data.customers && sheetsResult.data.customers['all']) {
          const allCustomers = sheetsResult.data.customers['all'];
          setCustomerCount(allCustomers.length);
          setSheetsData(sheetsResult.data);
          
          const customersData = await api.getCustomers();
          setCustomers(customersData);
          setError(null);
          return; // Successfully loaded from Google Sheets
        }
      } catch (sheetsError) {
        console.warn('Google Sheets sync failed, falling back to Excel data:', sheetsError);
      }
      
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

    let progressInterval: NodeJS.Timeout | null = null;

    try {
      setIsOptimizing(true);
      setProgress(0);
      setError(null);
      setStartTime(new Date());

      const depots = ['Leesville', 'Lake Charles', 'Lufkin'];
      let currentDepot = 0;
      
      progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev < 85) {
            const depotName = depots[currentDepot % depots.length];
            setDepotProgress(prevDepot => ({
              ...prevDepot,
              [depotName]: Math.min((prevDepot[depotName] || 0) + 15, 100)
            }));
            
            if (prev % 25 === 0) currentDepot++;
            return prev + 5;
          }
          if (prev < 98) return prev + 1;
          return prev;
        });
      }, 300);

      const result = await api.optimizeRoutes({
        customers,
        num_vehicles: numVehicles,
        depot_addresses: [
          "1707 Smart Street, Leesville, LA 71446",
          "220 Bunker Road, Lake Charles, LA 70615", 
          "1107 Weiner St, Lufkin, TX 75904"
        ],
        vehicle_distribution: vehicleDistribution
      });

      console.log('Optimization result received:', result);

      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      
      setProgress(98);
      
      setTimeout(async () => {
        try {
          const status = await api.verifyCompletion();
          if (status.complete) {
            setProgress(100);
            setDepotProgress({
              'Leesville': 100,
              'Lake Charles': 100,
              'Lufkin': 100
            });
            setOptimizationComplete(true);
            setOptimizationResult(result);
          }
        } catch (error) {
          console.error('Failed to verify completion:', error);
          setProgress(100);
          setDepotProgress({
            'Leesville': 100,
            'Lake Charles': 100,
            'Lufkin': 100
          });
          setOptimizationComplete(true);
          setOptimizationResult(result);
        }
      }, 500);
      
      setTimeout(() => {
        console.log('Resetting optimizationComplete after 2 seconds');
        setOptimizationComplete(false);
      }, 2000);
      
      setTimeout(() => {
        console.log('Resetting all states after 3 seconds, setting isOptimizing to false');
        setProgress(0);
        setDepotProgress({});
        setOptimizationComplete(false);
        setIsOptimizing(false);
      }, 3000);
      
    } catch (err) {
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      setProgress(0);
      setDepotProgress({});
      setOptimizationComplete(false);
      setError('Failed to optimize routes. Please try again.');
      console.error('Error optimizing routes:', err);
      setIsOptimizing(false);
    } finally {
    }
  };

  const optimizeWeeklyRoutes = async () => {
    if (customers.length === 0) return;

    let progressInterval: NodeJS.Timeout | null = null;
    let failsafeTimeout: NodeJS.Timeout | null = null;

    try {
      setIsOptimizing(true);
      setProgress(0);
      setError(null);
      setStartTime(new Date());

      failsafeTimeout = setTimeout(() => {
        console.log('Failsafe timeout triggered - resetting isOptimizing state');
        setIsOptimizing(false);
        setProgress(0);
        setDepotProgress({});
        setError('Optimization timed out. Please try again.');
        if (progressInterval) {
          clearInterval(progressInterval);
        }
      }, 120000); // 2 minutes

      const depots = ['Leesville', 'Lake Charles', 'Lufkin'];
      let currentDepot = 0;
      
      progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev < 85) {
            const depotName = depots[currentDepot % depots.length];
            setDepotProgress(prevDepot => ({
              ...prevDepot,
              [depotName]: Math.min((prevDepot[depotName] || 0) + 15, 100)
            }));
            
            if (prev % 25 === 0) currentDepot++;
            return prev + 5;
          }
          if (prev < 98) return prev + 1;
          return prev;
        });
      }, 300);

      console.log('Calling API optimizeRoutes with:', { customers: customers.length, vehicleDistribution });
      let result;
      try {
        result = await api.optimizeRoutes({
          customers,
          num_vehicles: numVehicles,
          depot_addresses: [
            "1707 Smart Street, Leesville, LA 71446",
            "220 Bunker Road, Lake Charles, LA 70615", 
            "1107 Weiner St, Lufkin, TX 75904"
          ],
          vehicle_distribution: vehicleDistribution
        });
        console.log('API call completed successfully, result:', result);
        console.log('Result type:', typeof result, 'Result keys:', Object.keys(result || {}));
      } catch (apiError) {
        console.error('API call failed:', apiError);
        throw apiError;
      }
      console.log('About to set up timeouts for state reset');

      console.log('Weekly optimization result received:', result);

      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      
      if (failsafeTimeout) {
        clearTimeout(failsafeTimeout);
      }
      
      setProgress(100);
      setDepotProgress({
        'Leesville': 100,
        'Lake Charles': 100,
        'Lufkin': 100
      });
      setOptimizationComplete(true);
      setOptimizationResult(result);
      
      console.log('Immediately resetting isOptimizing state to prevent UI lock');
      setTimeout(() => {
        setIsOptimizing(false);
        console.log('isOptimizing state reset to false');
      }, 500);
      
      setTimeout(() => {
        console.log('Cleaning up completion state');
        setOptimizationComplete(false);
        setProgress(0);
        setDepotProgress({});
      }, 3000);
      
    } catch (err) {
      console.error('Error in optimizeWeeklyRoutes:', err);
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      if (failsafeTimeout) {
        clearTimeout(failsafeTimeout);
      }
      setProgress(0);
      setDepotProgress({});
      setOptimizationComplete(false);
      setError('Failed to optimize weekly routes. Please try again.');
      setIsOptimizing(false);
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
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <div className="flex-1">
                  <label className="text-sm font-medium mb-2 block">
                    Total Vehicles: {Object.values(vehicleDistribution).reduce((sum, count) => sum + count, 0)}
                  </label>
                  <div className="text-xs text-gray-500">
                    Distributed across all depots
                  </div>
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

              <div>
                <label className="text-sm font-medium mb-3 block">
                  Vehicle Distribution by Depot
                </label>
                <div className="grid grid-cols-3 gap-4">
                  {Object.entries(vehicleDistribution).map(([depot, count]) => (
                    <div key={depot} className="space-y-2">
                      <label className="text-xs font-medium text-gray-700 block">
                        {depot}
                      </label>
                      <Select 
                        value={count.toString()} 
                        onValueChange={(value) => {
                          const newCount = parseInt(value);
                          setVehicleDistribution(prev => ({
                            ...prev,
                            [depot]: newCount
                          }));
                          setNumVehicles(Object.values({
                            ...vehicleDistribution,
                            [depot]: newCount
                          }).reduce((sum, c) => sum + c, 0));
                        }}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {[0, 1, 2, 3, 4, 5, 6, 7, 8].map(num => (
                            <SelectItem key={num} value={num.toString()}>
                              {num} {num === 1 ? 'Vehicle' : 'Vehicles'}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium mb-3 block">
                  Depot Constraints & Isolation
                </label>
                <div className="grid grid-cols-1 gap-4 p-4 bg-gray-50 rounded-lg">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-700">Leesville</label>
                      <div className="text-xs text-gray-600">Max: 100 miles, 15 stops, 10 hours</div>
                      <div className="text-xs text-gray-600">Vehicles: {vehicleDistribution.Leesville}</div>
                      <div className="text-xs text-blue-600">Service time: 30min/stop</div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-700">Lake Charles</label>
                      <div className="text-xs text-gray-600">Max: 75 miles, 15 stops, 10 hours</div>
                      <div className="text-xs text-gray-600">Vehicles: {vehicleDistribution['Lake Charles']}</div>
                      <div className="text-xs text-blue-600">Service time: 30min/stop</div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-700">Lufkin (Monday)</label>
                      <div className="text-xs text-red-600">Max: 50 miles, 15 stops, 10 hours</div>
                      <div className="text-xs text-gray-600">Vehicles: {vehicleDistribution.Lufkin} (Truck 1 only)</div>
                      <div className="text-xs text-blue-600">Service time: 30min/stop</div>
                    </div>
                  </div>
                  
                  <div className="border-t pt-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">Cross-Depot Penalty:</span>
                      <span className="text-orange-600">1.5x distance multiplier</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Routes between different depots are penalized to enforce isolation
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {isOptimizing && (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-sm">
                  <span>Optimizing routes...</span>
                  <div className="flex items-center space-x-4">
                    {startTime && (
                      <span className="text-xs text-gray-500">
                        Elapsed: {Math.floor((new Date().getTime() - startTime.getTime()) / 1000)}s
                      </span>
                    )}
                    <span>{progress}%</span>
                  </div>
                </div>
                <Progress value={progress} className="w-full" />
                
                <div className="space-y-3">
                  <div className="text-sm font-medium text-gray-700">Depot Progress:</div>
                  {['Leesville', 'Lake Charles', 'Lufkin'].map((depot) => {
                    const depotProg = depotProgress[depot] || 0;
                    const isComplete = depotProg === 100;
                    return (
                      <div key={depot} className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">{depot}</span>
                            {isComplete && (
                              <div className="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
                                <span className="text-white text-xs">✓</span>
                              </div>
                            )}
                          </div>
                          <span className="text-xs">{depotProg}%</span>
                        </div>
                        <Progress value={depotProg} className="w-full h-3" />
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            
            {optimizationComplete && (
              <div className="flex items-center space-x-2 text-green-600 text-sm font-medium">
                <div className="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
                  <span className="text-white text-xs">✓</span>
                </div>
                <span>Optimization completed successfully!</span>
              </div>
            )}

            <div className="space-y-3">
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
              
              <Button 
                onClick={optimizeWeeklyRoutes} 
                disabled={isOptimizing || customers.length === 0}
                className="w-full"
                variant="outline"
              >
                {isOptimizing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Optimizing Weekly Routes...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Optimize Weekly Routes
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="sheets">Google Sheets</TabsTrigger>
            <TabsTrigger value="driver">Driver Dashboard</TabsTrigger>
            <TabsTrigger value="weekly">Weekly Visits</TabsTrigger>
            <TabsTrigger value="map">Route Map</TabsTrigger>
            <TabsTrigger value="routes">Route Details</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            {optimizationResult && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <BarChart3 className="h-5 w-5" />
                    <span>Performance Metrics</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Total Distance</span>
                      <span className="font-medium">{optimizationResult.total_distance_miles.toFixed(1)} miles</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Total Time</span>
                      <span className="font-medium">{(optimizationResult.total_time_minutes / 60).toFixed(1)} hours</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Avg. Distance per Route</span>
                      <span className="font-medium">
                        {(optimizationResult.total_distance_miles / optimizationResult.routes.length).toFixed(1)} miles
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Efficiency Score</span>
                      <Badge variant="default">
                        {Math.round((customerCount / (optimizationResult.total_time_minutes / 60)) * 10)}%
                      </Badge>
                    </div>
                    {sheetsData && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Sheets Integration</span>
                        <Badge variant="secondary">
                          {Object.keys(sheetsData.customers || {}).length} depots synced
                        </Badge>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="sheets" className="space-y-6">
            <GoogleSheetsSync 
              onSyncComplete={(data) => {
                setSheetsData(data);
                if (data && data.customers) {
                  const allCustomers = data.customers['all'] || [];
                  setCustomerCount(allCustomers.length);
                }
                console.log('Sheets data synced:', data);
              }}
              onOptimizeComplete={(result) => {
                setOptimizationResult(result.optimization_result);
                setSheetsData(result.sheet_data);
                if (result.sheet_data && result.sheet_data.customers) {
                  const allCustomers = result.sheet_data.customers['all'] || [];
                  setCustomerCount(allCustomers.length);
                }
                console.log('Optimization complete:', result);
              }}
            />
          </TabsContent>

          <TabsContent value="driver" className="space-y-6">
            <DriverDashboard truckId={selectedTruck} day="Monday" />
          </TabsContent>

          <TabsContent value="weekly" className="space-y-6">
            <WeeklyVisitDashboard />
          </TabsContent>

          {optimizationResult && (
            <>
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
                {(() => {
                  const routesByDay = optimizationResult.routes.reduce((acc, route) => {
                    const day = route.day || 'Unassigned';
                    if (!acc[day]) acc[day] = [];
                    acc[day].push(route);
                    return acc;
                  }, {} as Record<string, typeof optimizationResult.routes>);

                  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Unassigned'];
                  
                  return days.map(day => {
                    const dayRoutes = routesByDay[day];
                    if (!dayRoutes || dayRoutes.length === 0) return null;
                    
                    const totalCustomers = dayRoutes.reduce((sum, route) => sum + route.route_points.length, 0);
                    
                    return (
                      <div key={day} className="space-y-4">
                        <div className="flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg">
                          <h3 className="text-xl font-semibold text-blue-900">{day}</h3>
                          <div className="flex space-x-3">
                            <Badge variant="secondary">{dayRoutes.length} routes</Badge>
                            <Badge variant="outline">{totalCustomers} customers</Badge>
                          </div>
                        </div>
                        
                        {dayRoutes.map((route) => (
                          <Card key={`${day}-${route.vehicle_id}`}>
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
                                    {Math.round(route.total_time_minutes / 60)}h {Math.round(route.total_time_minutes % 60)}m
                                  </Badge>
                                  {route.compliance?.DOT_hours === false && (
                                    <Badge variant="destructive">⚠️ Exceeds 10h</Badge>
                                  )}
                                  {route.violations && route.violations.length > 0 && (
                                    <Badge variant="destructive">{route.violations.length} violations</Badge>
                                  )}
                                </div>
                              </div>
                            </CardHeader>
                            <CardContent>
                              {route.violations && route.violations.length > 0 && (
                                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded">
                                  <h4 className="text-sm font-medium text-red-800 mb-2">Constraint Violations:</h4>
                                  <ul className="text-sm text-red-700 space-y-1">
                                    {route.violations.map((violation, idx) => (
                                      <li key={idx}>• {violation}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
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
                    );
                  }).filter(Boolean);
                })()}
              </div>
            </TabsContent>
            </>
          )}
        </Tabs>
      </div>
    </div>
  );
}

export default App;
