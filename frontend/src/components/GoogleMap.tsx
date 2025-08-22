import React, { useEffect, useRef, useState } from 'react';
import { Loader } from '@googlemaps/js-api-loader';
import { VehicleRoute } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { MapPin, AlertTriangle, Truck } from 'lucide-react';

interface GoogleMapProps {
  routes: VehicleRoute[];
  depotLocations: {
    name: string;
    address: string;
    latitude: number;
    longitude: number;
  }[];
  className?: string;
}

const GoogleMap: React.FC<GoogleMapProps> = ({ routes, depotLocations, className }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  console.log('GoogleMap component rendered with:', {
    routesCount: routes?.length || 0,
    depotLocationsCount: depotLocations?.length || 0,
    hasApiKey: !!GOOGLE_MAPS_API_KEY
  });

  useEffect(() => {
    const initMap = async () => {
      if (!GOOGLE_MAPS_API_KEY) {
        setMapError('Google Maps API key is not configured');
        setIsLoading(false);
        return;
      }

      const loader = new Loader({
        apiKey: GOOGLE_MAPS_API_KEY,
        version: 'weekly',
        libraries: ['places']
      });

      try {
        await loader.load();
        setIsLoaded(true);
        setMapError(null);

        if (mapRef.current) {
          try {
            const mapInstance = new google.maps.Map(mapRef.current, {
              center: depotLocations && depotLocations.length > 0 ? 
                { lat: depotLocations[0].latitude, lng: depotLocations[0].longitude } : 
                { lat: 31.1435, lng: -93.2607 },
              zoom: 8,
              mapTypeId: google.maps.MapTypeId.ROADMAP,
            });

            if (!mapInstance) {
              throw new Error('Failed to create Google Maps instance - map is null');
            }

            setMap(mapInstance);
            setIsLoading(false);
          } catch (mapError) {
            console.error('Error creating Google Maps instance:', mapError);
            const errorMessage = mapError instanceof Error ? mapError.message : 'Failed to create map instance';
            if (errorMessage.includes('ExpiredKeyMapError') || errorMessage.includes('InvalidKeyMapError') || errorMessage.includes('ApiNotActivatedMapError')) {
              setMapError('Google Maps API key is invalid or expired. Please update the API key in environment variables.');
            } else {
              setMapError(`Failed to create Google Maps instance: ${errorMessage}`);
            }
            setIsLoading(false);
            return;
          }
        } else {
          setMapError('Map container element not found');
          setIsLoading(false);
        }
      } catch (error) {
        console.error('Error loading Google Maps:', error);
        const errorMessage = error instanceof Error ? error.message : 'Failed to load Google Maps';
        if (errorMessage.includes('ExpiredKeyMapError') || errorMessage.includes('InvalidKeyMapError') || errorMessage.includes('ApiNotActivatedMapError')) {
          setMapError('Google Maps API key is invalid or expired. Please update the API key in environment variables.');
        } else {
          setMapError(`Failed to load Google Maps: ${errorMessage}`);
        }
        setIsLoading(false);
      }
    };

    initMap();
  }, [GOOGLE_MAPS_API_KEY, depotLocations]);

  useEffect(() => {
    if (!map || !isLoaded) {
      console.log('GoogleMap useEffect skipped:', { map: !!map, isLoaded });
      return;
    }

    console.log('GoogleMap useEffect running with:', {
      routesLength: routes.length,
      depotLocationsCount: depotLocations.length,
      mapInstance: !!map
    });

    depotLocations.forEach((depot, index) => {
      console.log('Creating depot marker at:', depot);
      const depotColors = ['#FF0000', '#00FF00', '#0000FF']; // Red, Green, Blue
      new google.maps.Marker({
        position: { lat: depot.latitude, lng: depot.longitude },
        map: map,
        title: `Depot: ${depot.name} - ${depot.address}`,
        icon: {
          url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
            <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
              <circle cx="16" cy="16" r="12" fill="${depotColors[index % depotColors.length]}" stroke="#FFFFFF" stroke-width="2"/>
              <text x="16" y="20" text-anchor="middle" fill="white" font-size="10" font-weight="bold">${depot.name.charAt(0)}</text>
            </svg>
          `),
          scaledSize: new google.maps.Size(32, 32),
        }
      });
    });

    const colors = [
      '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
      '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
    ];

    console.log('Processing routes:', routes.length);
    routes.forEach((route, routeIndex) => {
      console.log(`Processing route ${routeIndex}:`, {
        vehicle_id: route.vehicle_id,
        route_points_count: route.route_points.length,
        total_distance: route.total_distance_miles
      });
      
      const color = colors[routeIndex % colors.length];
      
      const path: google.maps.LatLng[] = [];
      
      const routeDepot = depotLocations.find(depot => depot.name === route.depot_name);
      if (routeDepot) {
        path.push(new google.maps.LatLng(routeDepot.latitude, routeDepot.longitude));
      }

      route.route_points.forEach((point) => {
        console.log(`Creating marker for customer ${point.customer_id}:`, point);
        new google.maps.Marker({
          position: { lat: point.latitude, lng: point.longitude },
          map: map,
          title: `${point.customer_name} (Stop ${point.order + 1})`,
          icon: {
            url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
              <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" fill="${color}" stroke="#FFFFFF" stroke-width="2"/>
                <text x="12" y="16" text-anchor="middle" fill="white" font-size="10" font-weight="bold">${route.vehicle_id}</text>
              </svg>
            `),
            scaledSize: new google.maps.Size(24, 24),
          }
        });

        path.push(new google.maps.LatLng(point.latitude, point.longitude));
      });

      if (routeDepot && route.route_points.length > 0) {
        path.push(new google.maps.LatLng(routeDepot.latitude, routeDepot.longitude));
      }

      if (path.length > 1) {
        new google.maps.Polyline({
          path: path,
          geodesic: true,
          strokeColor: color,
          strokeOpacity: 0.8,
          strokeWeight: 3,
          map: map
        });
      }
    });

    if (routes.length > 0 || depotLocations.length > 0) {
      const bounds = new google.maps.LatLngBounds();
      
      depotLocations.forEach(depot => {
        bounds.extend(new google.maps.LatLng(depot.latitude, depot.longitude));
      });
      
      routes.forEach(route => {
        route.route_points.forEach(point => {
          bounds.extend(new google.maps.LatLng(point.latitude, point.longitude));
        });
      });
      
      map.fitBounds(bounds);
    }

  }, [map, routes, depotLocations, isLoaded]);

  const RouteListFallback = () => (
    <div className="space-y-4">
      <div className="grid gap-4">
        {depotLocations.map((depot) => (
          <Card key={depot.name} className="border-l-4 border-l-blue-500">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center text-lg">
                <MapPin className="h-5 w-5 mr-2 text-blue-600" />
                Depot: {depot.name}
              </CardTitle>
              <p className="text-sm text-gray-600">{depot.address}</p>
            </CardHeader>
          </Card>
        ))}
      </div>
      
      {routes.map((route, routeIndex) => (
        <Card key={routeIndex} className="border-l-4 border-l-green-500">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center text-lg">
              <Truck className="h-5 w-5 mr-2 text-green-600" />
              Vehicle {route.vehicle_id} - {route.depot_name}
            </CardTitle>
            <p className="text-sm text-gray-600">
              {route.route_points.length} stops • {route.total_distance_miles} miles • {Math.round(route.total_time_minutes / 60)}h {Math.round(route.total_time_minutes % 60)}m
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {route.route_points.map((point, index) => (
                <div key={point.customer_id} className="flex items-center space-x-3 p-2 bg-gray-50 rounded">
                  <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center text-sm font-medium text-green-800">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{point.customer_name}</p>
                    <p className="text-sm text-gray-600">{point.address}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  if (isLoading) {
    return (
      <div className={`w-full h-full min-h-[400px] ${className || ''} flex items-center justify-center`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">Loading map...</p>
        </div>
      </div>
    );
  }

  if (mapError) {
    return (
      <div className={`w-full min-h-[400px] ${className || ''}`}>
        <Alert className="mb-4 border-orange-200 bg-orange-50">
          <AlertTriangle className="h-4 w-4 text-orange-600" />
          <AlertDescription className="text-orange-800">
            {mapError}
          </AlertDescription>
        </Alert>
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-4 flex items-center">
            <MapPin className="h-5 w-5 mr-2" />
            Route Information (List View)
          </h3>
          <RouteListFallback />
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={mapRef} 
      className={`w-full h-full min-h-[400px] ${className || ''}`}
      style={{ minHeight: '400px' }}
    />
  );
};

export default GoogleMap;
