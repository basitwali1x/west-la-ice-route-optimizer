import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { 
  Calendar, 
  Truck,
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw
} from 'lucide-react';
import { Customer, FourWeekSchedule as FourWeekScheduleType } from '../types';
import { api } from '../services/api';

interface FourWeekScheduleProps {
  customers: Customer[];
  selectedCustomers: Set<number>;
  vehicleDistribution: { [key: string]: number };
}

export function FourWeekSchedule({ customers, selectedCustomers, vehicleDistribution }: FourWeekScheduleProps) {
  const [schedule, setSchedule] = useState<FourWeekScheduleType | null>(null);
  const [selectedDepot, setSelectedDepot] = useState<string>('all');
  const [currentWeekIndex, setCurrentWeekIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const depots = ['Leesville', 'Lake Charles', 'Lufkin'];
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

  useEffect(() => {
    if (customers.length > 0) {
      generateFourWeekSchedule();
    }
  }, [customers, selectedCustomers]);

  const generateFourWeekSchedule = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const customersToSchedule = selectedCustomers.size > 0
        ? customers.filter(c => selectedCustomers.has(c.id))
        : customers;

      if (customersToSchedule.length === 0) {
        setError('No customers selected for scheduling');
        return;
      }

      const request = {
        customers: customersToSchedule,
        num_vehicles: Object.values(vehicleDistribution).reduce((sum, count) => sum + count, 0),
        depot_addresses: [
          "1707 Smart Street, Leesville, LA 71446",
          "220 Bunker Road, Lake Charles, LA 70615",
          "1107 Weiner St, Lufkin, TX 75904"
        ],
        vehicle_distribution: vehicleDistribution
      };

      const result = await api.generateFourWeekSchedule(request);
      setSchedule(result);
    } catch (err) {
      setError('Failed to generate 4-week schedule');
      console.error('Error generating schedule:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const currentWeek = schedule?.weeks[currentWeekIndex];
  const filteredRoutes = currentWeek?.routes.filter(route => 
    selectedDepot === 'all' || route.depot_name === selectedDepot
  ) || [];

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <RefreshCw className="h-5 w-5 animate-spin" />
            <span>4-Week Customer Schedule</span>
          </CardTitle>
          <CardDescription>Generating schedule...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Calendar className="h-5 w-5" />
              <span>4-Week Customer Schedule</span>
            </div>
            <div className="flex items-center space-x-2">
              <Select value={selectedDepot} onValueChange={setSelectedDepot}>
                <SelectTrigger className="w-48">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Filter by depot" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Depots</SelectItem>
                  {depots.map(depot => (
                    <SelectItem key={depot} value={depot}>{depot}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm" onClick={generateFourWeekSchedule}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </CardTitle>
          <CardDescription>
            Customer delivery assignments across all locations for the next 4 weeks
            {selectedCustomers.size > 0 && (
              <span className="ml-2 text-blue-600">
                ({selectedCustomers.size} customers selected)
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert className="mb-4 border-red-200 bg-red-50">
              <AlertDescription className="text-red-800">{error}</AlertDescription>
            </Alert>
          )}

          {!schedule && !error && (
            <div className="text-center py-8 text-gray-500">
              <Calendar className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Generate a 4-week schedule to see customer assignments</p>
              <Button onClick={generateFourWeekSchedule} className="mt-4">
                Generate Schedule
              </Button>
            </div>
          )}

          {schedule && (
            <>
              <div className="flex items-center justify-between mb-6">
                <Button
                  variant="outline"
                  onClick={() => setCurrentWeekIndex(Math.max(0, currentWeekIndex - 1))}
                  disabled={currentWeekIndex === 0}
                >
                  <ChevronLeft className="h-4 w-4 mr-2" />
                  Previous Week
                </Button>
                
                <div className="text-center">
                  <h3 className="text-lg font-semibold">
                    Week {currentWeekIndex + 1} of 4
                  </h3>
                  <Badge variant="outline" className="mt-1">
                    {currentWeek?.customer_count || 0} customers
                  </Badge>
                </div>

                <Button
                  variant="outline"
                  onClick={() => setCurrentWeekIndex(Math.min(3, currentWeekIndex + 1))}
                  disabled={currentWeekIndex === 3 || !schedule.weeks[currentWeekIndex + 1]}
                >
                  Next Week
                  <ChevronRight className="h-4 w-4 ml-2" />
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {depots.map(depot => {
                  const depotRoutes = filteredRoutes.filter(r => r.depot_name === depot);
                  const depotCustomers = depotRoutes.reduce((sum, route) => sum + route.route_points.length, 0);
                  
                  return (
                    <Card key={depot} className="bg-blue-50">
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium">{depot}</h4>
                            <p className="text-sm text-gray-600">{depotCustomers} customers</p>
                          </div>
                          <Truck className="h-8 w-8 text-blue-600" />
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              <div className="space-y-4">
                {days.map(day => {
                  const dayRoutes = filteredRoutes.filter(route => route.day === day);
                  const dayCustomers = dayRoutes.reduce((sum, route) => sum + route.route_points.length, 0);

                  return (
                    <Card key={day}>
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-lg">{day}</CardTitle>
                          <Badge variant="secondary">{dayCustomers} customers</Badge>
                        </div>
                      </CardHeader>
                      <CardContent>
                        {dayRoutes.length === 0 ? (
                          <p className="text-gray-500 text-center py-4">No deliveries scheduled</p>
                        ) : (
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {depots.map(depot => {
                              const depotRoutes = dayRoutes.filter(route => route.depot_name === depot);
                              const depotCustomers = depotRoutes.flatMap(route => route.route_points);

                              return (
                                <div key={depot} className="space-y-2">
                                  <h5 className="font-medium text-sm text-gray-700 border-b pb-1">
                                    {depot} ({depotCustomers.length})
                                  </h5>
                                  <div className="space-y-1 max-h-32 overflow-y-auto">
                                    {depotCustomers.map((point, index) => (
                                      <div key={point.customer_id} className="flex items-center space-x-2 text-sm">
                                        <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center text-xs">
                                          {index + 1}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                          <p className="font-medium truncate">{point.customer_name}</p>
                                          <p className="text-gray-500 text-xs truncate">{point.address}</p>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
